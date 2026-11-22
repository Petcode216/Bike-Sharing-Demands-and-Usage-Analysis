"""Inferential statistics.

Design notes (why these methods):
- Daily rentals are right-skewed within groups and strongly trending (2012 >> 2011), so
  each mean comparison is paired with a rank-based test (Mann-Whitney / Kruskal-Wallis).
- Consecutive days are autocorrelated, so the effective sample size is smaller than n.
  p-values from i.i.d. tests are therefore optimistic; confidence intervals use a
  moving-block bootstrap, and the regression uses HAC (Newey-West) standard errors.
- All results describe associations in observational data, not causal effects.
"""
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

RNG_SEED = 42
BLOCK_LEN = 14  # days; ~2 weeks of serial dependence per block


@dataclass
class TestResult:
    question: str
    method: str
    statistic: float
    p_value: float
    effect_name: str
    effect: float
    ci_low: float | None = None
    ci_high: float | None = None
    n: dict = field(default_factory=dict)
    note: str = ""
    extra: dict = field(default_factory=dict)


def _block_bootstrap_indices(n: int, rng: np.random.Generator, block: int = BLOCK_LEN) -> np.ndarray:
    """Moving-block bootstrap: resample contiguous blocks to preserve serial dependence."""
    starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
    return np.concatenate([np.arange(s, s + block) for s in starts])[:n]


def block_bootstrap_ci(df: pd.DataFrame, stat_fn, n_boot: int = 2000, alpha: float = 0.05,
                       block: int = BLOCK_LEN) -> tuple[float, float]:
    """Percentile CI for stat_fn(df) using a moving-block bootstrap over date-ordered rows."""
    rng = np.random.default_rng(RNG_SEED)
    ordered = df.sort_values("dteday").reset_index(drop=True)
    vals = []
    for _ in range(n_boot):
        v = stat_fn(ordered.iloc[_block_bootstrap_indices(len(ordered), rng, block)])
        if np.isfinite(v):
            vals.append(v)
    return float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def compare_working_days(day: pd.DataFrame, metric: str = "cnt") -> TestResult:
    """Working vs non-working day mean daily rentals for one metric."""
    w = day.loc[day["workingday"] == 1, metric]
    nw = day.loc[day["workingday"] == 0, metric]
    t = stats.ttest_ind(w, nw, equal_var=False)
    u = stats.mannwhitneyu(w, nw, alternative="two-sided")
    rank_biserial = 1 - 2 * u.statistic / (len(w) * len(nw))
    pooled_sd = np.sqrt((w.var(ddof=1) + nw.var(ddof=1)) / 2)

    def diff(d: pd.DataFrame) -> float:
        return d.loc[d["workingday"] == 1, metric].mean() - d.loc[d["workingday"] == 0, metric].mean()

    lo, hi = block_bootstrap_ci(day, diff)
    return TestResult(
        question=f"Mean daily {metric}: working vs non-working days",
        method="Welch t-test + Mann-Whitney U; block-bootstrap CI for mean difference",
        statistic=float(t.statistic), p_value=float(t.pvalue),
        effect_name="Mean difference (working - non-working)", effect=float(w.mean() - nw.mean()),
        ci_low=lo, ci_high=hi, n={"working": len(w), "non_working": len(nw)},
        note=(f"Mann-Whitney p = {u.pvalue:.3g}; rank-biserial r = {-rank_biserial:.3f}; "
              f"Cohen's d = {(w.mean() - nw.mean()) / pooled_sd:.3f}; "
              f"means {w.mean():.0f} vs {nw.mean():.0f}"),
        extra={"mean_working": float(w.mean()), "mean_non_working": float(nw.mean()),
               "cohens_d": float((w.mean() - nw.mean()) / pooled_sd), "mannwhitney_p": float(u.pvalue),
               "rank_biserial": float(-rank_biserial)})


def compare_seasons(day: pd.DataFrame, metric: str = "cnt") -> tuple[TestResult, pd.DataFrame]:
    """Kruskal-Wallis across seasons (ANOVA as a check) plus Holm-corrected pairwise tests."""
    groups = {s: g[metric].values for s, g in day.groupby("season_label", observed=True)}
    kw = stats.kruskal(*groups.values())
    an = stats.f_oneway(*groups.values())
    lev = stats.levene(*groups.values())
    n = sum(len(v) for v in groups.values())
    epsilon_sq = (kw.statistic - len(groups) + 1) / (n - len(groups))
    grand = day[metric].mean()
    eta_sq = sum(len(v) * (v.mean() - grand) ** 2 for v in groups.values()) / ((day[metric] - grand) ** 2).sum()
    pairs = []
    for a, b in combinations(groups, 2):
        u = stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
        pairs.append({"season_a": a, "season_b": b, "median_a": np.median(groups[a]),
                      "median_b": np.median(groups[b]), "p_raw": u.pvalue})
    pw = pd.DataFrame(pairs)
    pw["p_holm"] = multipletests(pw["p_raw"], method="holm")[1]
    res = TestResult(
        question=f"Does daily {metric} differ across seasons?",
        method="Kruskal-Wallis H (one-way ANOVA as robustness check); Holm-corrected Mann-Whitney post-hoc",
        statistic=float(kw.statistic), p_value=float(kw.pvalue),
        effect_name="Epsilon-squared (rank effect size)", effect=float(epsilon_sq),
        n={str(k): len(v) for k, v in groups.items()},
        note=(f"ANOVA F = {an.statistic:.1f}, p = {an.pvalue:.3g}, eta² = {eta_sq:.3f}; "
              f"Levene p = {lev.pvalue:.3g} (unequal variances -> rank test preferred)"),
        extra={"anova_f": float(an.statistic), "anova_p": float(an.pvalue), "eta_sq": float(eta_sq),
               "levene_p": float(lev.pvalue)})
    return res, pw


def weather_correlations(day: pd.DataFrame,
                         variables: tuple[str, ...] = ("temp_c", "atemp_c", "hum_pct", "windspeed_kmh"),
                         targets: tuple[str, ...] = ("cnt", "casual", "registered")) -> pd.DataFrame:
    """Pearson and Spearman correlations (daily grain) with block-bootstrap CIs on Spearman."""
    rows = []
    for t in targets:
        for v in variables:
            sub = day[["dteday", v, t]].dropna()
            pr = stats.pearsonr(sub[v], sub[t])
            sr = stats.spearmanr(sub[v], sub[t])
            lo, hi = block_bootstrap_ci(sub, lambda d: stats.spearmanr(d[v], d[t]).statistic, n_boot=1000)
            rows.append({"target": t, "variable": v, "n": len(sub), "pearson_r": pr.statistic,
                         "spearman_rho": sr.statistic, "spearman_ci_low": lo, "spearman_ci_high": hi})
    return pd.DataFrame(rows)


def hourly_profile_similarity(hour: pd.DataFrame) -> pd.DataFrame:
    """How similar are casual and registered intraday shapes, per day type?

    Each segment's mean-by-hour curve is normalized to sum to 1 (share of a typical
    day's rentals per hour); we report the correlation between the two shapes and
    the share each segment books in the commute windows (7-9h and 17-19h).
    """
    rows = []
    for dt, grp in hour.groupby("day_type", observed=True):
        prof = grp.groupby("hr")[["casual", "registered"]].mean()
        shape = prof / prof.sum()
        commute = shape.loc[[7, 8, 9, 17, 18, 19]].sum()
        rows.append({"day_type": dt, "shape_correlation": shape["casual"].corr(shape["registered"]),
                     "casual_commute_share": commute["casual"],
                     "registered_commute_share": commute["registered"],
                     "casual_peak_hour": int(prof["casual"].idxmax()),
                     "registered_peak_hour": int(prof["registered"].idxmax())})
    return pd.DataFrame(rows)


# temp_ctr = temperature centred on its sample mean; centring removes the artificial
# collinearity between the linear and squared terms without changing the fitted curve.
REGRESSION_FORMULA = ("cnt ~ temp_ctr + I(temp_ctr ** 2) + hum_pct + windspeed_kmh "
                      "+ C(weather_group) + C(season_label) + C(year) + workingday")


@dataclass
class RegressionResult:
    formula: str
    nobs: int
    r2: float
    adj_r2: float
    durbin_watson: float
    hac_lags: int
    coefficients: pd.DataFrame
    vif: pd.DataFrame
    summary_text: str
    temp_mean: float


def demand_regression(day: pd.DataFrame, hac_lags: int = 7) -> RegressionResult:
    """OLS of daily rentals on weather, calendar, and year, with HAC standard errors.

    atemp is excluded: it is near-collinear with temp (r ~ 0.99) and adds no
    separate information. A quadratic temperature term captures the observed
    flattening/decline of demand on the hottest days. The 2011-03-10 row with
    implausible zero humidity is dropped (missing hum_pct).
    """
    data = day.dropna(subset=["hum_pct"]).sort_values("dteday").copy()
    data["temp_ctr"] = data["temp_c"] - data["temp_c"].mean()
    model = smf.ols(REGRESSION_FORMULA, data=data).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    ci = model.conf_int()
    coefs = pd.DataFrame({"coef": model.params, "std_err_hac": model.bse, "p_value": model.pvalues,
                          "ci_low": ci[0], "ci_high": ci[1]})
    exog = model.model.exog
    names = model.model.exog_names
    vif = pd.DataFrame({"term": names[1:],
                        "vif": [variance_inflation_factor(exog, i) for i in range(1, exog.shape[1])]})
    return RegressionResult(REGRESSION_FORMULA, int(model.nobs), float(model.rsquared),
                            float(model.rsquared_adj), float(durbin_watson(model.resid)), hac_lags,
                            coefs, vif, str(model.summary()), float(data["temp_c"].mean()))


def temperature_turning_point(reg: RegressionResult) -> float:
    """Temperature (°C) at which the fitted quadratic temperature effect peaks."""
    b1 = reg.coefficients.loc["temp_ctr", "coef"]
    b2 = reg.coefficients.loc["I(temp_ctr ** 2)", "coef"]
    return float(reg.temp_mean - b1 / (2 * b2)) if b2 < 0 else float("nan")


def results_frame(results: list[TestResult]) -> pd.DataFrame:
    return pd.DataFrame([r.__dict__ for r in results])
