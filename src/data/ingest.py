"""Ingestion: extract the original archive into data/raw/ and load raw tables.

The zip archive and the extracted CSVs are never modified.
"""
import zipfile

import pandas as pd

from src.config import RAW_DIR, RAW_ZIP

RAW_FILES: tuple[str, ...] = ("day.csv", "hour.csv", "Readme.txt")


def extract_raw(force: bool = False) -> list[str]:
    """Extract the dataset archive into data/raw/ if files are not already present."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and all((RAW_DIR / f).exists() for f in RAW_FILES):
        return list(RAW_FILES)
    with zipfile.ZipFile(RAW_ZIP) as zf:
        names = zf.namelist()
        missing = set(RAW_FILES) - set(names)
        if missing:
            raise FileNotFoundError(f"Archive is missing expected files: {missing}")
        zf.extractall(RAW_DIR, members=list(RAW_FILES))
    return list(RAW_FILES)


def load_raw(name: str) -> pd.DataFrame:
    """Load a raw table ('day' or 'hour') with the date column parsed."""
    if name not in {"day", "hour"}:
        raise ValueError("name must be 'day' or 'hour'")
    extract_raw()
    return pd.read_csv(RAW_DIR / f"{name}.csv", parse_dates=["dteday"])


if __name__ == "__main__":
    print("Extracted:", extract_raw())
    for n in ("day", "hour"):
        print(n, load_raw(n).shape)
