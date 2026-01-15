from __future__ import annotations

from typing import Dict, Any, List, Optional
import pandas as pd


# ----------------------------
# Utility helpers
# ----------------------------

def _safe_str(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def _top_n_recent(df: pd.DataFrame, date_col: str, n: int = 3) -> pd.DataFrame:
    if df is None or df.empty or date_col not in df.columns:
        return df.iloc[0:0]
    df = df.dropna(subset=[date_col]).sort_values(date_col, ascending=False)
    return df.head(n)


# ----------------------------
# Diagnoses
# ----------------------------

def summarize_diagnoses(diagnoses_df: pd.DataFrame) -> List[str]:
    """
    Returns list of diagnosis strings (code + description).
    """
    if diagnoses_df is None or diagnoses_df.empty:
        return []

    cols = diagnoses_df.columns
    desc_col = "diagnosis_description" if "diagnosis_description" in cols else None
    code_col = "diagnosis_code" if "diagnosis_code" in cols else None

    results = []
    for _, row in diagnoses_df.iterrows():
        desc = _safe_str(row.get(desc_col, "")) if desc_col else ""
        code = _safe_str(row.get(code_col, "")) if code_col else ""
        if code and desc:
            results.append(f"{desc} ({code})")
        elif desc:
            results.append(desc)
        elif code:
            results.append(code)

    # unique while keeping order
    seen = set()
    out = []
    for x in results:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ----------------------------
# Medications
# ----------------------------

def summarize_medications(meds_df: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Returns a list of unique medications with name, frequency, classification, reason.
    Deduplicates by (name, frequency, classification, reason).
    """
    if meds_df is None or meds_df.empty:
        return []

    out = []
    seen = set()

    for _, row in meds_df.iterrows():
        med = {
            "name": _safe_str(row.get("medication_name")),
            "frequency": _safe_str(row.get("frequency")),
            "classification": _safe_str(row.get("classification")),
            "reason": _safe_str(row.get("reason")),
        }

        key = (med["name"], med["frequency"], med["classification"], med["reason"])
        if key not in seen and med["name"]:
            seen.add(key)
            out.append(med)

    return out


# ----------------------------
# Vitals
# ----------------------------

def summarize_vitals(vitals_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Summarize most recent vitals reading per vital_type + abnormal flags.
    """
    if vitals_df is None or vitals_df.empty:
        return {
            "latest_date": None,
            "latest_vitals": {},
            "abnormal": [],
        }

    # ensure sorted by visit_date
    vitals_df = vitals_df.dropna(subset=["visit_date"]).sort_values("visit_date", ascending=False)
    latest_date = vitals_df["visit_date"].iloc[0]

    latest_vitals = {}
    abnormal = []

    # For each vital_type pick the most recent entry
    for vital_type, group in vitals_df.groupby("vital_type"):
        g = group.sort_values("visit_date", ascending=False).iloc[0]

        reading = g.get("reading")
        min_val = g.get("min_value")
        max_val = g.get("max_value")

        latest_vitals[vital_type] = {
            "reading": None if pd.isna(reading) else float(reading),
            "min": None if pd.isna(min_val) else float(min_val),
            "max": None if pd.isna(max_val) else float(max_val),
            "date": g.get("visit_date"),
        }

        # abnormal detection: outside range if min/max are present
        if pd.notna(reading):
            if pd.notna(min_val) and reading < min_val:
                abnormal.append(f"{vital_type}: {reading} (below min {min_val})")
            if pd.notna(max_val) and reading > max_val:
                abnormal.append(f"{vital_type}: {reading} (above max {max_val})")

    return {
        "latest_date": latest_date,
        "latest_vitals": latest_vitals,
        "abnormal": abnormal,
    }


# ----------------------------
# Notes
# ----------------------------

def summarize_notes(notes_df: pd.DataFrame, n: int = 3) -> List[Dict[str, Any]]:
    """
    Take last N notes and return note_type + date + short text snippet.
    """
    if notes_df is None or notes_df.empty:
        return []

    recent = _top_n_recent(notes_df, "note_date", n=n)
    out = []

    for _, row in recent.iterrows():
        text = _safe_str(row.get("note_text"))
        snippet = text[:300] + ("..." if len(text) > 300 else "")
        out.append({
            "date": row.get("note_date"),
            "type": _safe_str(row.get("note_type")),
            "snippet": snippet
        })
    return out


# ----------------------------
# Wounds
# ----------------------------

def summarize_wounds(wounds_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Summarize wounds with location, description, onset_date, last visit_date.
    """
    if wounds_df is None or wounds_df.empty:
        return []

    # sort for latest updates
    if "visit_date" in wounds_df.columns:
        wounds_df = wounds_df.sort_values("visit_date", ascending=False)

    out = []
    for _, row in wounds_df.iterrows():
        out.append({
            "location": _safe_str(row.get("location")),
            "description": _safe_str(row.get("description")),
            "onset_date": row.get("onset_date"),
            "visit_date": row.get("visit_date"),
        })
    return out


# ----------------------------
# OASIS / Functional status
# ----------------------------

def summarize_oasis(oasis_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Returns the latest OASIS assessment for grooming/bathing/transfers/ambulation.
    """
    if oasis_df is None or oasis_df.empty:
        return {"latest_date": None, "assessment_type": None, "adl": {}}

    oasis_df = oasis_df.dropna(subset=["assessment_date"]).sort_values("assessment_date", ascending=False)
    latest = oasis_df.iloc[0]

    adl_fields = ["grooming", "bathing", "toilet_transfer", "transfer", "ambulation"]

    adl = {}
    for f in adl_fields:
        if f in oasis_df.columns:
            adl[f] = _safe_str(latest.get(f))

    return {
        "latest_date": latest.get("assessment_date"),
        "assessment_type": _safe_str(latest.get("assessment_type")),
        "adl": adl
    }


# ----------------------------
# Main Preprocessor
# ----------------------------

def prepare_summary_inputs(patient_bundle: Dict[str, pd.DataFrame], patient_id: int, episode_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Build final structured summary inputs for prompt/template generation.
    patient_bundle should be a dict of filtered dfs (usually from get_episode_bundle or get_patient_bundle).
    """
    diagnoses_df = patient_bundle.get("diagnoses")
    meds_df = patient_bundle.get("medications")
    vitals_df = patient_bundle.get("vitals")
    notes_df = patient_bundle.get("notes")
    wounds_df = patient_bundle.get("wounds")
    oasis_df = patient_bundle.get("oasis")

    return {
        "patient_id": patient_id,
        "episode_id": episode_id,
        "diagnoses_summary": summarize_diagnoses(diagnoses_df),
        "medications_summary": summarize_medications(meds_df),
        "vitals_summary": summarize_vitals(vitals_df),
        "note_highlights": summarize_notes(notes_df, n=3),
        "wounds_summary": summarize_wounds(wounds_df),
        "oasis_summary": summarize_oasis(oasis_df),
    }