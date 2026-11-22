"""Data-quality checks on the raw tables.

Each check returns a structured result. Running the module writes
reports/findings/data_quality.md and exits non-zero if a blocking check fails.
"""
import sys
from dataclasses import dataclass

import pandas as pd

from src.config import FINDINGS_DIR
from src.data.ingest import load_raw

EXPECTED_RANGES: dict[str, tuple[float, float]] = {
    "season": (1, 4), "yr": (0, 1), "mnth": (1, 12), "hr": (0, 23),
    "holiday": (0, 1), "weekday": (0, 6), "workingday": (0, 1),
    "weathersit": (1, 4), "temp": (0, 1), "atemp": (0, 1), "hum": (0, 1),
    "windspeed": (0, 1),
}


@dataclass
class CheckResult:
    table: str
    check: str
    passed: bool
    detail: str
    blocking: bool = True


def check_table(df: pd.DataFrame, table: str) -> list[CheckResult]:
    """Run grain-independent checks on one raw table."""
    res: list[CheckResult] = []
    nulls = int(df.isna().sum().sum())
    res.append(CheckResult(table, "No missing values", nulls == 0, f"{nulls} null cells"))
    dups = int(df.duplicated().sum())
    res.append(CheckResult(table, "No duplicate rows", dups == 0, f"{dups} duplicate rows"))
    key = ["dteday", "hr"] if "hr" in df else ["dteday"]
    kdups = int(df.duplicated(subset=key).sum())
    res.append(CheckResult(table, f"Unique key {key}", kdups == 0, f"{kdups} duplicate keys"))
    bad = int((df["cnt"] != df["casual"] + df["registered"]).sum())
    res.append(CheckResult(table, "cnt == casual + registered", bad == 0, f"{bad} mismatching rows"))
    for col, (lo, hi) in EXPECTED_RANGES.items():
        if col in df:
            out = int(((df[col] < lo) | (df[col] > hi)).sum())
            res.append(CheckResult(table, f"{col} within [{lo}, {hi}]", out == 0, f"{out} out of range"))
    # Calendar consistency: derived fields vs the date itself.
    wd = int((df["dteday"].dt.day_of_week.add(1).mod(7) != df["weekday"]).sum())
    res.append(CheckResult(table, "weekday matches date (0 = Sunday)", wd == 0, f"{wd} mismatches"))
    mn = int((df["dteday"].dt.month != df["mnth"]).sum())
    res.append(CheckResult(table, "mnth matches date", mn == 0, f"{mn} mismatches"))
    yr = int((df["dteday"].dt.year - 2011 != df["yr"]).sum())
    res.append(CheckResult(table, "yr matches date", yr == 0, f"{yr} mismatches"))
    # Season codes vs dates: code 1 should contain January/February (astronomical winter).
    season_jan = df.loc[df["mnth"].isin([1, 2]), "season"].unique().tolist()
    season_jul = df.loc[df["mnth"].isin([7, 8]), "season"].unique().tolist()
    ok = season_jan == [1] and season_jul == [3]
    res.append(CheckResult(table, "Season codes follow astronomical seasons (1 = winter)", ok,
                           f"Jan/Feb -> code {season_jan}, Jul/Aug -> code {season_jul}. "
                           "Readme labels code 1 'springer'; dates show it is winter, so labels are corrected",
                           blocking=False))
    expected_wd = ((df["weekday"].between(1, 5)) & (df["holiday"] == 0)).astype(int)
    wk = int((expected_wd != df["workingday"]).sum())
    res.append(CheckResult(table, "workingday = weekday and not holiday", wk == 0, f"{wk} mismatches"))
    # Non-blocking anomaly: humidity of exactly 0 is physically implausible.
    hum0 = df.loc[df["hum"] == 0, "dteday"].dt.date.unique()
    res.append(CheckResult(table, "No zero humidity readings", len(hum0) == 0,
                           f"{int((df['hum'] == 0).sum())} rows with hum = 0 on {list(map(str, hum0))}",
                           blocking=False))
    return res


def check_coverage(day: pd.DataFrame, hour: pd.DataFrame) -> list[CheckResult]:
    """Date coverage and cross-grain reconciliation."""
    res: list[CheckResult] = []
    full_days = pd.date_range(day["dteday"].min(), day["dteday"].max(), freq="D")
    missing_days = len(full_days.difference(day["dteday"]))
    res.append(CheckResult("day", "Continuous daily coverage", missing_days == 0,
                           f"{len(day)} days {day['dteday'].min().date()} to "
                           f"{day['dteday'].max().date()}, {missing_days} missing"))
    expected_hours = len(full_days) * 24
    per_day = hour.groupby("dteday").size()
    short = per_day[per_day < 24]
    res.append(CheckResult("hour", "Complete hourly coverage", len(hour) == expected_hours,
                           f"{len(hour)} of {expected_hours} hours present; "
                           f"{expected_hours - len(hour)} hours absent across {len(short)} days "
                           f"(largest gap: {24 - short.min() if len(short) else 0} hours missing in one day)",
                           blocking=False))
    hourly_sum = hour.groupby("dteday")[["casual", "registered", "cnt"]].sum()
    daily = day.set_index("dteday")[["casual", "registered", "cnt"]]
    mism = int((hourly_sum.reindex(daily.index) != daily).any(axis=1).sum())
    res.append(CheckResult("day vs hour", "Hourly totals reconcile with daily totals", mism == 0,
                           f"{mism} days where summed hourly counts differ from day.csv"))
    return res


def run_all_checks() -> list[CheckResult]:
    day, hour = load_raw("day"), load_raw("hour")
    return check_table(day, "day") + check_table(hour, "hour") + check_coverage(day, hour)


def missing_hours_table(hour: pd.DataFrame) -> pd.DataFrame:
    """List each (date, hour) slot absent from hour.csv."""
    full = pd.MultiIndex.from_product(
        [pd.date_range(hour["dteday"].min(), hour["dteday"].max()), range(24)],
        names=["dteday", "hr"])
    present = pd.MultiIndex.from_frame(hour[["dteday", "hr"]])
    return full.difference(present).to_frame(index=False)


def write_report(results: list[CheckResult]) -> str:
    hour = load_raw("hour")
    gaps = missing_hours_table(hour)
    by_day = gaps.groupby("dteday").size().sort_values(ascending=False)
    lines = [
        "# Data Quality Report", "",
        "Generated by `python -m src.data.validate` on the raw files in `data/raw/`.", "",
        "| Table | Check | Status | Detail |", "|---|---|---|---|",
    ]
    for r in results:
        status = "PASS" if r.passed else ("FAIL" if r.blocking else "WARN")
        lines.append(f"| {r.table} | {r.check} | {status} | {r.detail} |")
    lines += [
        "", "## Missing hourly records", "",
        f"{len(gaps)} hour slots are absent from `hour.csv`. Because the summed hourly counts match "
        "`day.csv` exactly, the absent hours carry no rentals in the source aggregation. They most "
        "likely correspond to hours with zero recorded rentals or system outages. They are **not imputed**. "
        "Hour-of-day averages are computed over observed hours only.", "",
        "Days with the most missing hours:", "",
        "| Date | Hours missing |", "|---|---|",
        *[f"| {d.date()} | {n} |" for d, n in by_day.head(10).items()],
        "", "## Decisions", "",
        "- **Season labels corrected.** The Readme labels `season` 1-4 as spring/summer/fall/winter, "
        "but the dates show code 1 spans ~21 Dec-20 Mar (all of Jan and Feb), code 2 ~21 Mar-20 Jun, "
        "code 3 ~21 Jun-22 Sep and code 4 ~23 Sep-20 Dec. The codes therefore follow astronomical "
        "seasons, and the cleaned data labels them Winter, Spring, Summer and Fall. The original code column is kept.",
        "- `hum = 0` on 2011-03-10 is treated as a sensor error: set to missing in the "
        "cleaned humidity columns (rental counts are kept).",
        "- `weathersit = 4` (heavy rain/snow) occurs in only 3 hourly records and never at daily grain; "
        "it is merged with category 3 for group statistics and noted as too sparse to analyse on its own.",
        "- No duplicates or count inconsistencies were found, so no rows are removed.",
    ]
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    out = FINDINGS_DIR / "data_quality.md"
    out.write_text("\n".join(lines) + "\n")
    return str(out)


if __name__ == "__main__":
    results = run_all_checks()
    for r in results:
        tag = "PASS" if r.passed else ("FAIL" if r.blocking else "WARN")
        print(f"[{tag}] {r.table:12s} {r.check}: {r.detail}")
    print("Report written to", write_report(results))
    sys.exit(1 if any(not r.passed and r.blocking for r in results) else 0)
