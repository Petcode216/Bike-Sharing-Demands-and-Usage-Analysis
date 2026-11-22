"""Descriptive KPIs.

Every metric carries an explicit grain: "per day" metrics come from day.csv,
"per hour" metrics from hour.csv. The two are never mixed.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass
class Kpi:
    name: str
    value: float
    unit: str
    grain: str  # "per day", "per hour", "period total", "ratio"
    note: str = ""


def headline_kpis(day: pd.DataFrame) -> list[Kpi]:
    """Headline totals and daily distribution, from the daily table."""
    total = int(day["cnt"].sum())
    casual, registered = int(day["casual"].sum()), int(day["registered"].sum())
    max_row = day.loc[day["cnt"].idxmax()]
    min_row = day.loc[day["cnt"].idxmin()]
    by_year = day.groupby("year")["cnt"].sum()
    return [
        Kpi("Total rentals", total, "rentals", "period total", "2011-01-01 to 2012-12-31"),
        Kpi("Registered rentals", registered, "rentals", "period total"),
        Kpi("Casual rentals", casual, "rentals", "period total"),
        Kpi("Registered share", registered / total, "share", "ratio"),
        Kpi("Casual share", casual / total, "share", "ratio"),
        Kpi("Casual-to-registered ratio", casual / registered, "ratio", "ratio"),
        Kpi("Mean daily rentals", day["cnt"].mean(), "rentals", "per day"),
        Kpi("Median daily rentals", day["cnt"].median(), "rentals", "per day"),
        Kpi("Max daily rentals", int(max_row["cnt"]), "rentals", "per day", str(max_row["dteday"].date())),
        Kpi("Min daily rentals", int(min_row["cnt"]), "rentals", "per day", str(min_row["dteday"].date())),
        Kpi("2011 total", int(by_year[2011]), "rentals", "period total"),
        Kpi("2012 total", int(by_year[2012]), "rentals", "period total"),
        Kpi("Year-over-year growth", by_year[2012] / by_year[2011] - 1, "share", "ratio", "2012 vs 2011"),
    ]


def kpi_frame(kpis: list[Kpi]) -> pd.DataFrame:
    return pd.DataFrame([k.__dict__ for k in kpis])


def daily_summary_by(day: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Mean/median daily rentals (and segment means) per group. Grain: per day."""
    g = day.groupby(by, observed=True)
    out = g.agg(days=("cnt", "size"), mean_cnt=("cnt", "mean"), median_cnt=("cnt", "median"),
                mean_casual=("casual", "mean"), mean_registered=("registered", "mean"),
                total_cnt=("cnt", "sum"))
    out["casual_share"] = g["casual"].sum() / g["cnt"].sum()
    return out


def hourly_profile(hour: pd.DataFrame, by: str | list[str] | None = None) -> pd.DataFrame:
    """Mean rentals per observed hour, by hour of day (optionally split). Grain: per hour.

    Missing hour slots (165, see data_quality.md) are excluded, not treated as zero.
    """
    keys = ([by] if isinstance(by, str) else list(by or [])) + ["hr"]
    return (hour.groupby(keys, observed=True)
            .agg(hours=("cnt", "size"), mean_cnt=("cnt", "mean"), median_cnt=("cnt", "median"),
                 p10_cnt=("cnt", lambda s: s.quantile(0.1)), p90_cnt=("cnt", lambda s: s.quantile(0.9)),
                 mean_casual=("casual", "mean"), mean_registered=("registered", "mean"))
            .reset_index())


def peak_hours(hour: pd.DataFrame) -> pd.DataFrame:
    """Peak hour of mean demand per day type and user segment. Grain: per hour."""
    rows = []
    for dt, grp in hour.groupby("day_type", observed=True):
        prof = grp.groupby("hr")[["cnt", "casual", "registered"]].mean()
        for seg in ["cnt", "casual", "registered"]:
            rows.append({"day_type": dt, "segment": seg, "peak_hour": int(prof[seg].idxmax()),
                         "peak_mean_per_hour": prof[seg].max(), "trough_hour": int(prof[seg].idxmin()),
                         "trough_mean_per_hour": prof[seg].min()})
    return pd.DataFrame(rows)


def monthly_trend(day: pd.DataFrame) -> pd.DataFrame:
    """Monthly totals with month-over-month and year-over-year change. Grain: per month."""
    m = day.groupby("year_month")[["cnt", "casual", "registered"]].sum()
    m["days"] = day.groupby("year_month").size()
    m["mean_daily_cnt"] = m["cnt"] / m["days"]
    m["mom_change"] = m["cnt"].pct_change()
    m["yoy_change"] = m["cnt"].pct_change(12)
    return m.reset_index()


def hour_weekday_matrix(hour: pd.DataFrame, value: str = "cnt") -> pd.DataFrame:
    """Mean rentals per observed hour for each weekday x hour cell. Grain: per hour."""
    return hour.pivot_table(index="weekday_label", columns="hr", values=value,
                            aggfunc="mean", observed=True)


def demand_windows(hour: pd.DataFrame, high_q: float = 0.8, low_q: float = 0.2) -> pd.DataFrame:
    """Classify (day_type, hour) slots into demand tiers using their mean hourly rentals.

    'Consistently high' = slot mean in the top quintile of slot means AND slot p10
    above the overall hourly median, i.e. even its weaker hours are busy.
    """
    prof = hourly_profile(hour, by="day_type")
    hi_cut, lo_cut = prof["mean_cnt"].quantile(high_q), prof["mean_cnt"].quantile(low_q)
    overall_median = hour["cnt"].median()
    prof["tier"] = "Moderate"
    prof.loc[prof["mean_cnt"] >= hi_cut, "tier"] = "High"
    prof.loc[(prof["mean_cnt"] >= hi_cut) & (prof["p10_cnt"] > overall_median), "tier"] = "Consistently high"
    prof.loc[prof["mean_cnt"] <= lo_cut, "tier"] = "Low"
    return prof


def weather_sensitivity(day: pd.DataFrame) -> pd.DataFrame:
    """Mean daily rentals by weather group per segment, indexed to clear days = 100."""
    m = day.groupby("weather_group", observed=True)[["cnt", "casual", "registered"]].mean()
    idx = m.div(m.iloc[0]).mul(100)
    idx.columns = [f"{c}_index" for c in idx.columns]
    return m.join(idx).join(day.groupby("weather_group", observed=True).size().rename("days"))


def temperature_bands(day: pd.DataFrame, width: float = 5.0) -> pd.DataFrame:
    """Mean daily rentals by actual-temperature band (°C). Grain: per day."""
    edges = list(range(0, 40, int(width)))
    bands = pd.cut(day["temp_c"], bins=edges, right=False)
    return (day.groupby(bands, observed=True)
            .agg(days=("cnt", "size"), mean_cnt=("cnt", "mean"),
                 mean_casual=("casual", "mean"), mean_registered=("registered", "mean"))
            .reset_index().rename(columns={"temp_c": "temp_band"}))
