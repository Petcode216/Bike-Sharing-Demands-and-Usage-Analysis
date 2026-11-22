"""Project-wide paths and dataset constants (taken from data/raw/Readme.txt)."""
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_ZIP: Path = DATA_DIR / "bike+sharing+dataset.zip"
RAW_DIR: Path = DATA_DIR / "raw"
INTERIM_DIR: Path = DATA_DIR / "interim"
PROCESSED_DIR: Path = DATA_DIR / "processed"
FIGURES_DIR: Path = PROJECT_ROOT / "reports" / "figures"
FINDINGS_DIR: Path = PROJECT_ROOT / "reports" / "findings"

# Season labels: Readme.txt says 1=spring, 2=summer, 3=fall, 4=winter, but the dates
# contradict it. Code 1 spans ~Dec 21 - Mar 20 (Jan/Feb are entirely code 1), code 2
# ~Mar 21 - Jun 20, code 3 ~Jun 21 - Sep 22, code 4 ~Sep 23 - Dec 20. These are the
# astronomical seasons, so we label by the dates (verified in validate.py), not the Readme.
SEASON_LABELS: dict[int, str] = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Fall"}
SEASON_README_LABELS: dict[int, str] = {1: "springer", 2: "summer", 3: "fall", 4: "winter"}
YEAR_LABELS: dict[int, int] = {0: 2011, 1: 2012}
WEATHER_LABELS: dict[int, str] = {
    1: "Clear / partly cloudy",
    2: "Mist / cloudy",
    3: "Light rain / snow",
    4: "Heavy rain / snow",
}
# weekday encoding is verified in validate.py (2011-01-01 was a Saturday -> 6).
WEEKDAY_LABELS: dict[int, str] = {
    0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"
}
WEEKDAY_ORDER: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Readme: values were divided by these maxima, so multiplying recovers raw units.
DENORM_FACTORS: dict[str, tuple[str, float]] = {
    "temp": ("temp_c", 41.0),
    "atemp": ("atemp_c", 50.0),
    "hum": ("hum_pct", 100.0),
    "windspeed": ("windspeed_kmh", 67.0),
}
