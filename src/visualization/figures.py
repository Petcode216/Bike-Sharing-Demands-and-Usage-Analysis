"""Static report figures (matplotlib / seaborn).

Each function takes the processed tables, returns a Figure, and states the grain
in the axis label or footnote. `save_all` writes them to reports/figures/.
"""
from collections.abc import Callable

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

from src.analysis import kpis as K
from src.analysis import stats as S
from src.config import FIGURES_DIR, WEEKDAY_ORDER
from src.visualization.style import (DAY_TYPE_COLORS, GRID, NEUTRAL, SEGMENT_COLORS, SEGMENT_NAMES,
                                     SEQUENTIAL_BLUE, TEXT_PRIMARY, TEXT_SECONDARY, WEATHER_COLORS,
                                     YEAR_COLORS, apply_matplotlib_style, finish, thousands)

DAILY_NOTE = "Source: UCI Bike Sharing Dataset (Capital Bikeshare, 2011-2012). Grain: one row per day."
HOURLY_NOTE = ("Source: UCI Bike Sharing Dataset (Capital Bikeshare, 2011-2012). Grain: one row per observed "
               "hour (165 absent hour slots excluded).")
SEQ_CMAP = LinearSegmentedColormap.from_list("seq_blue", SEQUENTIAL_BLUE)


def _label_line_end(ax: plt.Axes, x, y, text: str, color: str) -> None:
    ax.annotate(text, (x, y), xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=9, color=TEXT_PRIMARY,
                bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": color, "lw": 0.8})


def fig_daily_trend(day: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    d = day.set_index("dteday").sort_index()
    for seg in ["registered", "casual"]:
        ax.plot(d.index, d[seg], color=SEGMENT_COLORS[seg], alpha=0.18, lw=0.8)
        roll = d[seg].rolling(7, center=True).mean()
        ax.plot(d.index, roll, color=SEGMENT_COLORS[seg], lw=2, label=f"{SEGMENT_NAMES[seg]} (7-day mean)")
        _label_line_end(ax, roll.dropna().index[-1], roll.dropna().iloc[-1], SEGMENT_NAMES[seg],
                        SEGMENT_COLORS[seg])
    sandy = pd.Timestamp("2012-10-29")
    ax.annotate("29 Oct 2012: 22 rentals\n(Hurricane Sandy)", (sandy, d.loc[sandy, "registered"]),
                xytext=(pd.Timestamp("2012-06-20"), 2900), textcoords="data", fontsize=8, color=TEXT_SECONDARY,
                arrowprops={"arrowstyle": "-", "color": NEUTRAL, "lw": 0.8})
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(thousands))
    ax.set_ylabel("Rentals per day")
    ax.set_title("Rentals grew 65% from 2011 to 2012, following the same seasonal cycle")
    ax.legend(loc="upper left")
    return finish(fig, DAILY_NOTE + " Thin lines = daily values.")


def fig_distributions(day: pd.DataFrame, hour: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].hist(day["cnt"], bins=30, color=SEGMENT_COLORS["registered"], edgecolor="white", linewidth=1)
    axes[0].axvline(day["cnt"].median(), color=TEXT_PRIMARY, lw=1, ls="--")
    axes[0].set_title("Daily rentals: roughly symmetric")
    axes[0].set_xlabel("Rentals per day")
    axes[0].set_ylabel("Number of days")
    axes[1].hist(hour["cnt"], bins=40, color=SEGMENT_COLORS["registered"], edgecolor="white", linewidth=1)
    axes[1].axvline(hour["cnt"].median(), color=TEXT_PRIMARY, lw=1, ls="--")
    axes[1].set_title("Hourly rentals: strongly right-skewed")
    axes[1].set_xlabel("Rentals per hour")
    axes[1].set_ylabel("Number of hours")
    for ax in axes:
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(thousands))
    fig.tight_layout()
    return finish(fig, "Dashed line = median. Left: day.csv (731 days). Right: hour.csv (17,379 observed hours). "
                       "The two panels are different grains and are not comparable in scale.")


def fig_hourly_by_daytype(hour: pd.DataFrame) -> plt.Figure:
    prof = K.hourly_profile(hour, by="day_type")
    fig, ax = plt.subplots(figsize=(10, 4))
    for dt, g in prof.groupby("day_type", observed=True):
        c = DAY_TYPE_COLORS[str(dt)]
        ax.plot(g["hr"], g["mean_cnt"], color=c, marker="o", ms=4, label=str(dt))
        ax.fill_between(g["hr"], g["p10_cnt"], g["p90_cnt"], color=c, alpha=0.08, lw=0)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Mean rentals per hour")
    ax.set_title("Working days peak at 8:00 and 17:00; weekends and holidays peak at midday")
    ax.legend(loc="upper left")
    return finish(fig, HOURLY_NOTE + " Shaded bands = 10th-90th percentile of hourly rentals.")


def fig_hour_weekday_heatmap(hour: pd.DataFrame) -> plt.Figure:
    mat = K.hour_weekday_matrix(hour).reindex(WEEKDAY_ORDER)
    fig, ax = plt.subplots(figsize=(11, 3.6))
    sns.heatmap(mat, cmap=SEQ_CMAP, linewidths=1, linecolor="white", ax=ax,
                cbar_kws={"label": "Mean rentals per hour", "shrink": 0.8})
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("")
    ax.set_title("Weekday commute peaks vs weekend midday plateau")
    ax.tick_params(axis="y", rotation=0)
    ax.grid(False)
    return finish(fig, HOURLY_NOTE)


def fig_weekday_segments(day: pd.DataFrame) -> plt.Figure:
    s = K.daily_summary_by(day, "weekday_label")
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(s))
    ax.bar(x, s["mean_registered"], color=SEGMENT_COLORS["registered"], width=0.6,
           label="Registered", edgecolor=ax.get_facecolor(), linewidth=2)
    ax.bar(x, s["mean_casual"], bottom=s["mean_registered"], color=SEGMENT_COLORS["casual"], width=0.6,
           label="Casual", edgecolor=ax.get_facecolor(), linewidth=2)
    for i, (cs, tot) in enumerate(zip(s["casual_share"], s["mean_cnt"])):
        ax.text(i, tot + 60, f"{cs:.0%} casual", ha="center", fontsize=8, color=TEXT_SECONDARY)
    ax.set_xticks(x, s.index.astype(str))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(thousands))
    ax.set_ylabel("Mean rentals per day")
    ax.set_ylim(0, s["mean_cnt"].max() * 1.12)
    ax.set_title("Total demand varies ~10% across the week; its user mix varies far more", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 0.98), ncols=2)
    return finish(fig, DAILY_NOTE)


def fig_monthly_by_year(day: pd.DataFrame) -> plt.Figure:
    m = day.groupby(["year", "month_label"], observed=True)["cnt"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(9, 4))
    for yr, g in m.groupby("year"):
        ax.plot(g["month_label"].astype(str), g["cnt"], color=YEAR_COLORS[yr], marker="o", label=str(yr))
        _label_line_end(ax, len(g) - 1, g["cnt"].iloc[-1], str(yr), YEAR_COLORS[yr])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(thousands))
    ax.set_ylabel("Mean rentals per day")
    ax.set_title("Same seasonal shape both years; Jan-Mar grew fastest (2.1-2.6x)")
    ax.legend(loc="upper left")
    return finish(fig, DAILY_NOTE + " Monthly values are mean daily rentals (months differ in length).")


def fig_season_box(day: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.boxplot(data=day, x="season_label", y="cnt", hue="year", ax=ax, width=0.6,
                palette={2011: YEAR_COLORS[2011], 2012: YEAR_COLORS[2012]}, fliersize=3, linewidth=1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(thousands))
    ax.set_xlabel("Season (astronomical; see data-quality notes)")
    ax.set_ylabel("Rentals per day")
    ax.set_title("Summer is busiest, winter quietest - in both years")
    ax.legend(title="Year", loc="upper left")
    return finish(fig, DAILY_NOTE)


def fig_temperature(day: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for yr, g in day.groupby("year"):
        ax.scatter(g["temp_c"], g["cnt"], s=16, color=YEAR_COLORS[yr], alpha=0.55,
                   edgecolor="white", linewidth=0.5, label=str(yr))
        coef = np.polyfit(g["temp_c"], g["cnt"], 2)
        xs = np.linspace(g["temp_c"].min(), g["temp_c"].max(), 100)
        ax.plot(xs, np.polyval(coef, xs), color=YEAR_COLORS[yr], lw=2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(thousands))
    ax.set_xlabel("Daily mean temperature (°C, de-normalized)")
    ax.set_ylabel("Rentals per day")
    ax.set_title("Demand rises with temperature, then levels off above ~25-28 °C")
    ax.legend(title="Year", loc="upper left")
    return finish(fig, DAILY_NOTE + " Curves = quadratic fit per year (descriptive only).")


def fig_humidity_wind(day: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, var, label in [(axes[0], "hum_pct", "Humidity (%)"), (axes[1], "windspeed_kmh", "Wind speed (km/h)")]:
        sub = day.dropna(subset=[var])
        ax.scatter(sub[var], sub["cnt"], s=12, color=SEGMENT_COLORS["registered"], alpha=0.45,
                   edgecolor="white", linewidth=0.4)
        coef = np.polyfit(sub[var], sub["cnt"], 1)
        xs = np.linspace(sub[var].min(), sub[var].max(), 50)
        ax.plot(xs, np.polyval(coef, xs), color=TEXT_PRIMARY, lw=1.5)
        rho = sub[[var, "cnt"]].corr(method="spearman").iloc[0, 1]
        ax.set_title(f"{label.split(' (')[0]}: Spearman ρ = {rho:.2f}")
        ax.set_xlabel(label)
    axes[0].set_ylabel("Rentals per day")
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(thousands))
    fig.tight_layout()
    return finish(fig, DAILY_NOTE + " Line = linear fit. 2011-03-10 humidity (recorded 0%) excluded.")


def fig_weather_sensitivity(day: pd.DataFrame) -> plt.Figure:
    ws = K.weather_sensitivity(day)
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(ws))
    w = 0.36
    for i, seg in enumerate(["registered", "casual"]):
        bars = ax.bar(x + (i - 0.5) * w, ws[f"{seg}_index"], width=w - 0.03, color=SEGMENT_COLORS[seg],
                      label=SEGMENT_NAMES[seg])
        ax.bar_label(bars, fmt="%.0f", fontsize=8, color=TEXT_SECONDARY, padding=2)
    ax.axhline(100, color=NEUTRAL, lw=0.8, ls="--")
    ax.set_xticks(x, [f"{w_}\n({n} days)" for w_, n in zip(ws.index.astype(str), ws["days"])])
    ax.set_ylabel("Mean daily rentals (clear days = 100)")
    ax.set_title("Casual demand falls much further than registered demand in bad weather")
    ax.legend(loc="upper right")
    return finish(fig, DAILY_NOTE + " Weather categories 3 and 4 combined ('Rain / snow'); "
                                    "category 4 never occurs at daily grain.")


def fig_segment_hourly(hour: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    groups = {"Working days": hour[hour["workingday"] == 1], "Non-working days": hour[hour["workingday"] == 0]}
    for ax, (title, g) in zip(axes, groups.items()):
        prof = g.groupby("hr")[["registered", "casual"]].mean()
        for seg in ["registered", "casual"]:
            ax.plot(prof.index, prof[seg], color=SEGMENT_COLORS[seg], marker="o", ms=3.5, label=SEGMENT_NAMES[seg])
        ax.set_title(title)
        ax.set_xticks(range(0, 24, 3))
        ax.set_xlabel("Hour of day")
    axes[0].set_ylabel("Mean rentals per hour")
    axes[0].legend(loc="upper left")
    fig.suptitle("Registered riders commute; casual riders ride in the afternoon, mostly on days off",
                 x=0.01, ha="left", fontsize=12, fontweight="semibold")
    fig.tight_layout()
    return finish(fig, HOURLY_NOTE)


def fig_casual_share_month(day: pd.DataFrame) -> plt.Figure:
    m = day.groupby("year_month")[["casual", "cnt"]].sum()
    share = m["casual"] / m["cnt"]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(share.index, share, color=SEGMENT_COLORS["casual"], marker="o")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylabel("Casual share of monthly rentals")
    ax.set_title("Casual share: ~8-13% in Dec-Feb vs ~17-26% from March to October")
    return finish(fig, DAILY_NOTE)


def fig_correlations(corr: pd.DataFrame) -> plt.Figure:
    labels = {"temp_c": "Temperature", "atemp_c": "Feels-like temp.", "hum_pct": "Humidity",
              "windspeed_kmh": "Wind speed"}
    fig, ax = plt.subplots(figsize=(9, 4))
    targets = ["registered", "casual"]
    vars_ = list(labels)
    y = np.arange(len(vars_))
    for i, t in enumerate(targets):
        sub = corr[corr["target"] == t].set_index("variable").loc[vars_]
        yy = y + (i - 0.5) * 0.3
        ax.errorbar(sub["spearman_rho"], yy,
                    xerr=[sub["spearman_rho"] - sub["spearman_ci_low"], sub["spearman_ci_high"] - sub["spearman_rho"]],
                    fmt="o", ms=7, color=SEGMENT_COLORS[t], ecolor=SEGMENT_COLORS[t], elinewidth=1.5,
                    capsize=0, label=SEGMENT_NAMES[t])
    ax.axvline(0, color=NEUTRAL, lw=0.8)
    ax.set_yticks(y, [labels[v] for v in vars_])
    ax.invert_yaxis()
    ax.set_xlabel("Spearman ρ with daily rentals (95% block-bootstrap CI)")
    ax.set_title("Temperature is the strongest weather correlate, especially for casual riders")
    ax.legend(loc="lower right")
    return finish(fig, DAILY_NOTE + " CIs resample 14-day blocks to respect day-to-day dependence.")


def fig_regression(reg: S.RegressionResult) -> plt.Figure:
    pretty = {
        "C(weather_group)[T.Mist / cloudy]": "Mist / cloudy (vs clear)",
        "C(weather_group)[T.Rain / snow]": "Rain / snow (vs clear)",
        "C(season_label)[T.Spring]": "Spring (vs winter)",
        "C(season_label)[T.Summer]": "Summer (vs winter)",
        "C(season_label)[T.Fall]": "Fall (vs winter)",
        "C(year)[T.2012]": "Year 2012 (vs 2011)",
        "workingday": "Working day",
        "hum_pct": "Humidity, per +1 pp",
        "windspeed_kmh": "Wind speed, per +1 km/h",
    }
    c = reg.coefficients.loc[list(pretty)]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(c))
    ax.errorbar(c["coef"], y, xerr=[c["coef"] - c["ci_low"], c["ci_high"] - c["coef"]], fmt="o", ms=7,
                color=SEGMENT_COLORS["registered"], ecolor=SEGMENT_COLORS["registered"], elinewidth=1.5)
    ax.axvline(0, color=NEUTRAL, lw=0.8)
    ax.set_yticks(y, [pretty[i] for i in c.index])
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+,.0f}"))
    ax.set_xlabel("Associated change in rentals per day (95% CI, HAC standard errors)")
    ax.set_title(f"Daily demand model (R² = {reg.r2:.2f}): year and rain dominate")
    return finish(fig, DAILY_NOTE + " OLS with Newey-West errors; temperature enters as a quadratic "
                                    "(not shown). Associations, not causal effects.")


def fig_demand_windows(hour: pd.DataFrame) -> plt.Figure:
    w = K.demand_windows(hour)
    tiers = ["Low", "Moderate", "High", "Consistently high"]
    codes = w.assign(code=w["tier"].map({t: i for i, t in enumerate(tiers)}))
    mat = codes.pivot(index="day_type", columns="hr", values="code")
    cmap = LinearSegmentedColormap.from_list("tiers", [SEQUENTIAL_BLUE[0], SEQUENTIAL_BLUE[2],
                                                       SEQUENTIAL_BLUE[4], SEQUENTIAL_BLUE[6]], N=4)
    fig, ax = plt.subplots(figsize=(11, 2.6))
    sns.heatmap(mat, cmap=cmap, vmin=-0.5, vmax=3.5, linewidths=1, linecolor="white", ax=ax,
                cbar_kws={"ticks": range(4), "shrink": 0.9})
    ax.collections[0].colorbar.set_ticklabels(tiers)
    means = w.pivot(index="day_type", columns="hr", values="mean_cnt")
    for (i, dt) in enumerate(mat.index):
        for hr in mat.columns:
            v = means.loc[dt, hr]
            ax.text(hr + 0.5, i + 0.5, f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                    color="white" if mat.loc[dt, hr] >= 2 else TEXT_PRIMARY)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("")
    ax.set_title("Demand tiers by hour (cell value = mean rentals per hour)")
    ax.tick_params(axis="y", rotation=0)
    ax.grid(False)
    return finish(fig, HOURLY_NOTE + " Tiers: top/bottom quintile of slot means; 'consistently high' also "
                                     "requires the slot's 10th percentile > overall hourly median.")


def build_all(day: pd.DataFrame, hour: pd.DataFrame, corr: pd.DataFrame,
              reg: S.RegressionResult) -> dict[str, Callable[[], plt.Figure]]:
    return {
        "01_daily_trend": lambda: fig_daily_trend(day),
        "02_distributions": lambda: fig_distributions(day, hour),
        "03_hourly_by_daytype": lambda: fig_hourly_by_daytype(hour),
        "04_hour_weekday_heatmap": lambda: fig_hour_weekday_heatmap(hour),
        "05_weekday_segments": lambda: fig_weekday_segments(day),
        "06_monthly_by_year": lambda: fig_monthly_by_year(day),
        "07_season_box": lambda: fig_season_box(day),
        "08_temperature": lambda: fig_temperature(day),
        "09_humidity_wind": lambda: fig_humidity_wind(day),
        "10_weather_sensitivity": lambda: fig_weather_sensitivity(day),
        "11_segment_hourly": lambda: fig_segment_hourly(hour),
        "12_casual_share_month": lambda: fig_casual_share_month(day),
        "13_correlations": lambda: fig_correlations(corr),
        "14_regression": lambda: fig_regression(reg),
        "15_demand_windows": lambda: fig_demand_windows(hour),
    }


def save_all(day: pd.DataFrame, hour: pd.DataFrame, corr: pd.DataFrame,
             reg: S.RegressionResult) -> list[str]:
    apply_matplotlib_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, make in build_all(day, hour, corr, reg).items():
        fig = make()
        path = FIGURES_DIR / f"{name}.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(str(path))
    return paths
