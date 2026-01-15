from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pandas as pd


DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "data"

CSV_FILES = {
    "diagnoses": "diagnoses.csv",
    "medications": "medications.csv",
    "vitals": "vitals.csv",
    "notes": "notes.csv",
    "wounds": "wounds.csv",
    "oasis": "oasis.csv",
}

# Explicit datetime columns per dataset
DATETIME_COLUMNS = {
    "vitals": ["visit_date"],
    "notes": ["note_date"],
    "wounds": ["onset_date", "visit_date"],
    "oasis": ["assessment_date"],
}


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip() for c in df.columns]
    return df


def _convert_datetime(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Safely convert specific columns to datetime (coerce invalid to NaT)."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _convert_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Safely convert numeric columns."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _convert_int(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Convert columns to pandas nullable integer dtype.
    This avoids crashing if there are missing/invalid values.
    """
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def load_data(data_dir: str | os.PathLike | None = None) -> Dict[str, pd.DataFrame]:
    """
    Loads all required CSV files from the data directory into pandas DataFrames
    with correct datatypes.
    """
    data_path = Path(data_dir) if data_dir else DEFAULT_DATA_PATH
    tables: Dict[str, pd.DataFrame] = {}

    for table_name, filename in CSV_FILES.items():
        file_path = data_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Missing required file: {file_path}")

        df = pd.read_csv(file_path)
        df = _clean_columns(df)

        # Convert datetime columns explicitly
        if table_name in DATETIME_COLUMNS:
            df = _convert_datetime(df, DATETIME_COLUMNS[table_name])

        # Common ID columns
        df = _convert_int(df, ["patient_id", "episode_id"])

        # Vitals numeric values
        if table_name == "vitals":
            df = _convert_numeric(df, ["reading", "min_value", "max_value"])

        tables[table_name] = df

    return tables


def validate_loaded_tables(tables: Dict[str, pd.DataFrame]) -> Dict[str, dict]:
    """
    Optional helper to validate dtypes after loading.
    Returns dtype info per table (useful during development/testing).
    """
    report = {}
    for name, df in tables.items():
        report[name] = {
            "shape": df.shape,
            "dtypes": df.dtypes.astype(str).to_dict(),
            "null_counts": df.isna().sum().to_dict(),
        }
    return report
