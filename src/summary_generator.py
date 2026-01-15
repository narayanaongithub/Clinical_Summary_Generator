from __future__ import annotations
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from typing import Dict, Any, Tuple
import pandas as pd

from src.patient_service import get_patient_bundle, get_episode_bundle, patient_exists
from src.summarizer import prepare_summary_inputs
from src.prompt_builder import build_prompt
from src.llm_client import call_llm


def _fmt_date(dt) -> str:
    if dt is None or pd.isna(dt):
        return "Not documented"
    try:
        return pd.to_datetime(dt).strftime("%Y-%m-%d")
    except Exception:
        return str(dt)


def _template_generate(summary_inputs: Dict[str, Any]) -> str:
    """
    Backup generator (no LLM). Used if LLM fails or key missing.
    """
    pid = summary_inputs.get("patient_id")
    eid = summary_inputs.get("episode_id")

    dx = summary_inputs.get("diagnoses_summary", [])
    meds = summary_inputs.get("medications_summary", [])
    vitals = summary_inputs.get("vitals_summary", {})
    wounds = summary_inputs.get("wounds_summary", [])
    oasis = summary_inputs.get("oasis_summary", {})
    notes = summary_inputs.get("note_highlights", [])

    dx_text = "\n".join([f"- {d}" for d in dx]) if dx else "Not documented"

    meds_text = (
        "\n".join([f"- {m['name']} ({m['frequency']}) — Reason: {m['reason']}" for m in meds])
        if meds else "Not documented"
    )

    latest_date = _fmt_date(vitals.get("latest_date"))
    lv = vitals.get("latest_vitals", {})
    abnormal = vitals.get("abnormal", [])

    vitals_text = (
        "\n".join([f"- {vt}: {info.get('reading')}" for vt, info in lv.items()])
        if lv else "Not documented"
    )

    abnormal_text = "\n".join([f"- {x}" for x in abnormal]) if abnormal else "None flagged"

    wound_text = (
        "\n".join([
            f"- {w.get('description')} | {w.get('location')} | onset {_fmt_date(w.get('onset_date'))} | last {_fmt_date(w.get('visit_date'))}"
            for w in wounds
        ])
        if wounds else "Not documented"
    )

    oasis_date = _fmt_date(oasis.get("latest_date"))
    oasis_type = oasis.get("assessment_type") or "Not documented"
    adl = oasis.get("adl", {})

    adl_text = "\n".join([f"- {k}: {v}" for k, v in adl.items()]) if adl else "Not documented"

    notes_text = (
        "\n".join([f"- [{_fmt_date(n.get('date'))}] {n.get('type')}: {n.get('snippet')}" for n in notes])
        if notes else "Not documented"
    )

    return f"""
1. Patient Overview
Patient ID: {pid}
Episode ID: {eid}

2. Active Diagnoses
{dx_text}

3. Current Medications
{meds_text}

4. Recent Vitals
Latest date: {latest_date}
{vitals_text}

Abnormal:
{abnormal_text}

5. Wound Summary
{wound_text}

6. Functional / ADL Status (OASIS)
Assessment date: {oasis_date}
Assessment type: {oasis_type}
{adl_text}

7. Recent Notes
{notes_text}
""".strip()


def generate_summary(
    tables: Dict[str, Any],
    patient_id: int,
    use_llm: bool = True,
    model: str = "gpt-4o-mini",
) -> Tuple[str, Dict[str, Any]]:
    """
    Generates summary by:
    - filtering data by patient + latest episode
    - building prompt context string
    - sending to LLM
    - fallback template if LLM fails
    """
    if not patient_exists(tables, patient_id):
        return f"No data found for patient_id={patient_id}.", {
            "patient_id": patient_id,
            "found": False
        }

    bundle = get_patient_bundle(tables, patient_id)
    episode_id = bundle.latest_episode_id

    ep_bundle = get_episode_bundle(tables, patient_id, episode_id)
    summary_inputs = prepare_summary_inputs(ep_bundle, patient_id, episode_id)

    prompt = build_prompt(summary_inputs)

    debug = {
        "patient_id": patient_id,
        "episode_id": episode_id,
        "use_llm": use_llm,
        "model": model,
    }

    # ✅ Primary mode: LLM
    if use_llm:
        try:
            llm_text = call_llm(prompt, model=model)
            return llm_text, {**debug, "llm_status": "success"}
        except Exception as e:
            # ✅ Always runnable fallback
            fallback = _template_generate(summary_inputs)
            return fallback, {
                **debug,
                "llm_status": "failed_fallback_used",
                "error": str(e),
                "prompt_preview": prompt[:500],
            }

    # Template-only
    return _template_generate(summary_inputs), {**debug, "llm_status": "skipped"}