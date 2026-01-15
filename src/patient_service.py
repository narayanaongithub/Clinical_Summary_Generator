from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List

import pandas as pd


DATE_PRIORITY = [
    ("vitals", "visit_date"),
    ("notes", "note_date"),
    ("wounds", "visit_date"),
    ("oasis", "assessment_date"),
]


@dataclass
class PatientBundle:
    patient_id: int
    episode_ids: List[int]
    latest_episode_id: Optional[int]
    data: Dict[str, pd.DataFrame]


def _filter_by_patient(df: pd.DataFrame, patient_id: int) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if "patient_id" not in df.columns:
        return df.iloc[0:0]  # empty with same columns
    return df[df["patient_id"] == patient_id].copy()


def _filter_by_episode(df: pd.DataFrame, episode_id: int) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if "episode_id" not in df.columns:
        return df.iloc[0:0]
    return df[df["episode_id"] == episode_id].copy()


def get_patient_episodes(tables: Dict[str, pd.DataFrame], patient_id: int) -> List[int]:
    """
    Collect all unique episode_ids for the patient across tables.
    """
    episode_ids = set()

    for _, df in tables.items():
        if df is None or df.empty:
            continue
        if "patient_id" not in df.columns:
            continue

        patient_df = df[df["patient_id"] == patient_id]
        if "episode_id" in patient_df.columns:
            vals = patient_df["episode_id"].dropna().unique().tolist()
            episode_ids.update([int(v) for v in vals if pd.notna(v)])

    return sorted(list(episode_ids))


def get_latest_episode_id(tables: Dict[str, pd.DataFrame], patient_id: int) -> Optional[int]:
    """
    Choose the latest episode based on most recent date column among vitals/notes/wounds/oasis.
    Falls back to max episode_id if no dates exist.
    """
    episode_ids = get_patient_episodes(tables, patient_id)
    if not episode_ids:
        return None

    best_episode = None
    best_date = None

    # Look for most recent date per episode across date-priority tables
    for table_name, date_col in DATE_PRIORITY:
        df = tables.get(table_name)
        if df is None or df.empty:
            continue
        if date_col not in df.columns:
            continue

        patient_df = _filter_by_patient(df, patient_id)
        if patient_df.empty or "episode_id" not in patient_df.columns:
            continue

        # Ensure date col is datetime (data_loader.py should already guarantee this)
        patient_df = patient_df.dropna(subset=[date_col, "episode_id"])
        if patient_df.empty:
            continue

        # Find latest row overall
        latest_row = patient_df.sort_values(date_col, ascending=False).iloc[0]
        ep = int(latest_row["episode_id"])
        dt = latest_row[date_col]

        if best_date is None or dt > best_date:
            best_date = dt
            best_episode = ep

    # If no dates found anywhere, fallback to max episode id
    if best_episode is None:
        return max(episode_ids)

    return best_episode


def get_patient_bundle(tables: Dict[str, pd.DataFrame], patient_id: int) -> PatientBundle:
    """
    Returns all dataframes filtered by patient_id, plus episode_id metadata.
    """
    filtered = {}
    for name, df in tables.items():
        filtered[name] = _filter_by_patient(df, patient_id)

    episode_ids = get_patient_episodes(tables, patient_id)
    latest_episode_id = get_latest_episode_id(tables, patient_id)

    return PatientBundle(
        patient_id=patient_id,
        episode_ids=episode_ids,
        latest_episode_id=latest_episode_id,
        data=filtered,
    )


def get_episode_bundle(
    tables: Dict[str, pd.DataFrame],
    patient_id: int,
    episode_id: int
) -> Dict[str, pd.DataFrame]:
    """
    Returns all patient data filtered further to a specific episode_id (where possible).
    Some tables may not include episode_id (e.g., oasis might not always have episode_id).
    """
    bundle = get_patient_bundle(tables, patient_id)
    ep_data: Dict[str, pd.DataFrame] = {}

    for name, df in bundle.data.items():
        if df is None or df.empty:
            ep_data[name] = df
            continue

        if "episode_id" in df.columns:
            ep_data[name] = _filter_by_episode(df, episode_id)
        else:
            # no episode_id column -> keep as-is (rare, but safe)
            ep_data[name] = df

    return ep_data


def patient_exists(tables: Dict[str, pd.DataFrame], patient_id: int) -> bool:
    """
    Returns True if patient appears in any dataset.
    """
    for df in tables.values():
        if df is None or df.empty:
            continue
        if "patient_id" in df.columns:
            if (df["patient_id"] == patient_id).any():
                return True
    return False
