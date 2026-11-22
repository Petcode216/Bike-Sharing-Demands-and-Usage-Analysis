"""Cleaning and feature preparation.

Daily and hourly tables are processed separately and never combined.
Original columns are preserved; derived columns are added alongside them.
"""
import numpy as np
import pandas as pd

from src.config import (DENORM_FACTORS, INTERIM_DIR, PROCESSED_DIR, SEASON_LABELS,
                        WEATHER_LABELS, WEEKDAY_LABELS, WEEKDAY_ORDER, YEAR_LABELS)
from src.data.ingest import load_raw

HOUR_BUCKETS: list[tuple[str, range]] = [
    ("Night (0-5)", range(0, 6)),
    ("Morning peak (6-9)", range(6, 10)),
    ("Midday (10-15)", range(10, 16)),
    ("Evening peak (16-19)", range(16, 20)),
    ("Late evening (20-23)", range(20, 24)),
]


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Map documented integer codes to ordered, labelled categoricals."""
    out = df.copy()
    out["season_label"] = pd.Categorical(out["season"].map(SEASON_LABELS),
                                         categories=list(SEASON_LABELS.values()), ordered=True)
    out["year"] = out["yr"].map(YEAR_LABELS).astype(int)
    out["weekday_label"] = pd.Categorical(out["weekday"].map(WEEKDAY_LABELS),
                                          categories=WEEKDAY_ORDER, ordered=True)
    out["weather_label"] = pd.Categorical(out["weathersit"].map(WEATHER_LABELS),
                                          categories=list(WEATHER_LABELS.values()), ordered=True)
    # Category 4 is extremely rare (3 hourly rows); merge into 3 for group comparisons.
    out["weather_group"] = pd.Categorical(
        np.where(out["weathersit"] >= 3, "Rain / snow", out["weather_label"].astype(str)),
        categories=[WEATHER_LABELS[1], WEATHER_LABELS[2], "Rain / snow"], ordered=True)
    out["month"] = out["dteday"].dt.month
    out["month_label"] = pd.Categorical(out["dteday"].dt.strftime("%b"),
                                        categories=pd.date_range("2000-01-01", periods=12, freq="MS")
                                        .strftime("%b").tolist(), ordered=True)
    out["year_month"] = out["dteday"].dt.to_period("M").dt.to_timestamp()
    return out


def add_day_type(df: pd.DataFrame) -> pd.DataFrame:
    """Working day / weekend / holiday (holiday takes precedence over weekend)."""
    out = df.copy()
    is_weekend = out["weekday"].isin([0, 6])
    out["day_type"] = pd.Categorical(
        np.select([out["holiday"] == 1, is_weekend], ["Holiday", "Weekend"], default="Working day"),
        categories=["Working day", "Weekend", "Holiday"], ordered=True)
    return out


def denormalize_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Recover physical units per Readme; flag implausible zero humidity as missing."""
    out = df.copy()
    for col, (new_col, factor) in DENORM_FACTORS.items():
        out[new_col] = out[col] * factor
    out.loc[out["hum"] == 0, "hum_pct"] = np.nan
    return out


def add_hour_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    lookup = {h: name for name, hours in HOUR_BUCKETS for h in hours}
    out["hour_bucket"] = pd.Categorical(out["hr"].map(lookup),
                                        categories=[b[0] for b in HOUR_BUCKETS], ordered=True)
    out["timestamp"] = out["dteday"] + pd.to_timedelta(out["hr"], unit="h")
    return out


def add_user_share(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["casual_share"] = out["casual"] / out["cnt"]
    return out


def clean_table(name: str) -> pd.DataFrame:
    raw = load_raw(name)
    n_in = len(raw)
    df = add_labels(raw)
    df = add_day_type(df)
    df.to_csv(INTERIM_DIR / f"{name}_labelled.csv", index=False)
    df = denormalize_weather(df)
    if name == "hour":
        df = add_hour_features(df)
    df = add_user_share(df)
    assert len(df) == n_in, f"{name}: row count changed {n_in} -> {len(df)}"
    assert (df["cnt"] == df["casual"] + df["registered"]).all()
    return df


def load_processed(name: str) -> pd.DataFrame:
    """Load a processed table and restore categorical dtypes lost in CSV round-trip."""
    path = PROCESSED_DIR / f"{name}_clean.csv"
    if not path.exists():
        run_pipeline()
    dates = ["dteday", "year_month"] + (["timestamp"] if name == "hour" else [])
    df = pd.read_csv(path, parse_dates=dates)
    df = add_labels(df[[c for c in df.columns if c not in {
        "season_label", "weekday_label", "weather_label", "weather_group", "month_label"}]])
    df["day_type"] = pd.Categorical(df["day_type"], categories=["Working day", "Weekend", "Holiday"],
                                    ordered=True)
    if name == "hour":
        df["hour_bucket"] = pd.Categorical(df["hour_bucket"], categories=[b[0] for b in HOUR_BUCKETS],
                                           ordered=True)
    return df


def run_pipeline() -> dict[str, int]:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for name in ("day", "hour"):
        df = clean_table(name)
        df.to_csv(PROCESSED_DIR / f"{name}_clean.csv", index=False)
        counts[name] = len(df)
    return counts


if __name__ == "__main__":
    print("Processed row counts:", run_pipeline())
