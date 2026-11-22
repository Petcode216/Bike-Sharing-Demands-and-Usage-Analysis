"""Compute every analytical result once, in one place.

The report, README figures and notebooks all read from `compute_all`, so each
number published anywhere traces back to the same code path.
"""
import json
from dataclasses import asdict, dataclass

import pandas as pd

from src.analysis import kpis as K
from src.analysis import stats as S
from src.config import FINDINGS_DIR
from src.data.clean import load_processed


@dataclass
class Results:
    day: pd.DataFrame
    hour: pd.DataFrame
    headline: pd.DataFrame
    by_season: pd.DataFrame
    by_day_type: pd.DataFrame
    by_weekday: pd.DataFrame
    by_weather: pd.DataFrame
    temp_bands: pd.DataFrame
    monthly: pd.DataFrame
    peaks: pd.DataFrame
    windows: pd.DataFrame
    profile_similarity: pd.DataFrame
    working_tests: list[S.TestResult]
    season_test: S.TestResult
    season_pairwise: pd.DataFrame
    correlations: pd.DataFrame
    regression: S.RegressionResult
    temp_turning_point: float

    def kpi(self, name: str) -> float:
        return float(self.headline.set_index("name").loc[name, "value"])

    def kpi_note(self, name: str) -> str:
        return str(self.headline.set_index("name").loc[name, "note"])


def compute_all() -> Results:
    day, hour = load_processed("day"), load_processed("hour")
    season_test, season_pw = S.compare_seasons(day)
    reg = S.demand_regression(day)
    return Results(
        day=day, hour=hour,
        headline=K.kpi_frame(K.headline_kpis(day)),
        by_season=K.daily_summary_by(day, "season_label"),
        by_day_type=K.daily_summary_by(day, "day_type"),
        by_weekday=K.daily_summary_by(day, "weekday_label"),
        by_weather=K.weather_sensitivity(day),
        temp_bands=K.temperature_bands(day),
        monthly=K.monthly_trend(day),
        peaks=K.peak_hours(hour),
        windows=K.demand_windows(hour),
        profile_similarity=S.hourly_profile_similarity(hour),
        working_tests=[S.compare_working_days(day, m) for m in ("cnt", "casual", "registered")],
        season_test=season_test, season_pairwise=season_pw,
        correlations=S.weather_correlations(day),
        regression=reg, temp_turning_point=S.temperature_turning_point(reg),
    )


def export_tables(res: Results) -> list[str]:
    """Write result tables to reports/findings/tables/ for transparency."""
    out_dir = FINDINGS_DIR / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "headline_kpis": res.headline, "by_season": res.by_season, "by_day_type": res.by_day_type,
        "by_weekday": res.by_weekday, "by_weather": res.by_weather, "temperature_bands": res.temp_bands,
        "monthly_trend": res.monthly, "peak_hours": res.peaks, "demand_windows": res.windows,
        "hourly_profile_similarity": res.profile_similarity, "season_pairwise": res.season_pairwise,
        "weather_correlations": res.correlations, "regression_coefficients": res.regression.coefficients,
        "regression_vif": res.regression.vif,
        "hypothesis_tests": S.results_frame(res.working_tests + [res.season_test]),
    }
    paths = []
    for name, df in tables.items():
        p = out_dir / f"{name}.csv"
        df.to_csv(p, index=not isinstance(df.index, pd.RangeIndex))
        paths.append(str(p))
    meta = {"regression": {"formula": res.regression.formula, "nobs": res.regression.nobs,
                           "r2": res.regression.r2, "adj_r2": res.regression.adj_r2,
                           "durbin_watson": res.regression.durbin_watson, "hac_lags": res.regression.hac_lags,
                           "temp_turning_point_c": res.temp_turning_point},
            "tests": [asdict(t) for t in res.working_tests + [res.season_test]]}
    (out_dir / "model_summary.txt").write_text(res.regression.summary_text)
    (out_dir / "results.json").write_text(json.dumps(meta, indent=2, default=str))
    return paths
