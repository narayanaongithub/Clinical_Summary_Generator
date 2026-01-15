# src/prompt_builder.py
from __future__ import annotations

from typing import Dict, Any
import pandas as pd


def _fmt_date(dt) -> str:
    if dt is None or (isinstance(dt, float) and pd.isna(dt)):
        return "N/A"
    if pd.isna(dt):
        return "N/A"
    try:
        return pd.to_datetime(dt).strftime("%Y-%m-%d")
    except Exception:
        return str(dt)


def build_prompt(summary_inputs: Dict[str, Any]) -> str:
    """
    Builds an LLM-ready context string (prompt) from summary_inputs.
    Updated to enforce citations and evidence-based output.
    """

    pid = summary_inputs.get("patient_id")
    eid = summary_inputs.get("episode_id")

    # ----------------------------
    # Diagnoses
    # ----------------------------
    dx = summary_inputs.get("diagnoses_summary", [])
    dx_text = "\n".join([f"- {d} [Source: diagnoses.csv]" for d in dx]) if dx else "- Not documented [Source: diagnoses.csv]"

    # ----------------------------
    # Medications
    # ----------------------------
    meds = summary_inputs.get("medications_summary", [])
    if meds:
        meds_text = "\n".join([
            f"- {m.get('name')} | {m.get('frequency')} | {m.get('classification')} | "
            f"Reason: {m.get('reason')} [Source: medications.csv]"
            for m in meds
        ])
    else:
        meds_text = "- Not documented [Source: medications.csv]"

    # ----------------------------
    # Vitals
    # ----------------------------
    vitals = summary_inputs.get("vitals_summary", {})
    latest_date = _fmt_date(vitals.get("latest_date"))

    latest_vitals = vitals.get("latest_vitals", {})
    if latest_vitals:
        vitals_lines = []
        for vt, info in latest_vitals.items():
            reading = info.get("reading")
            v_date = _fmt_date(info.get("date"))
            vitals_lines.append(
                f"- {vt}: {reading} (date: {v_date}) [Source: vitals.csv | visit_date={v_date}]"
            )
        vitals_text = "\n".join(vitals_lines)
    else:
        vitals_text = "- Not documented [Source: vitals.csv]"

    abnormal = vitals.get("abnormal", [])
    abnormal_text = "\n".join([f"- {a} [Source: vitals.csv]" for a in abnormal]) if abnormal else "- None flagged [Source: vitals.csv]"

    # ----------------------------
    # Notes
    # ----------------------------
    notes = summary_inputs.get("note_highlights", [])
    if notes:
        notes_text = "\n".join([
            f"- [{_fmt_date(n.get('date'))}] {n.get('type')}: {n.get('snippet')} "
            f"[Source: notes.csv | note_date={_fmt_date(n.get('date'))}]"
            for n in notes
        ])
    else:
        notes_text = "- Not documented [Source: notes.csv]"

    # ----------------------------
    # Wounds
    # ----------------------------
    wounds = summary_inputs.get("wounds_summary", [])
    if wounds:
        wound_lines = []
        for w in wounds:
            onset = _fmt_date(w.get("onset_date"))
            vdate = _fmt_date(w.get("visit_date"))
            wound_lines.append(
                f"- {w.get('description')} | Location: {w.get('location')} | "
                f"Onset: {onset} | Visit: {vdate} "
                f"[Source: wounds.csv | visit_date={vdate}]"
            )
        wounds_text = "\n".join(wound_lines)
    else:
        wounds_text = "- No wounds documented [Source: wounds.csv]"

    # ----------------------------
    # OASIS
    # ----------------------------
    oasis = summary_inputs.get("oasis_summary", {})
    oasis_date = _fmt_date(oasis.get("latest_date"))
    oasis_type = oasis.get("assessment_type") or "N/A"
    adl = oasis.get("adl", {})

    if adl:
        adl_text = "\n".join([
            f"- {k}: {v} [Source: oasis.csv | assessment_date={oasis_date}]"
            for k, v in adl.items()
        ])
    else:
        adl_text = f"- Not documented [Source: oasis.csv | assessment_date={oasis_date}]"

    # ----------------------------
    # Prompt (strict instructions)
    # ----------------------------
    prompt = f"""
You are a home health clinician. Your task is to generate an evidence-based clinical summary from the provided EHR data.

IMPORTANT RULES:
- Use ONLY the data provided below. Do NOT invent anything.
- Every claim MUST include a citation bracket in this format:
  [Source: <file>.csv | <key>=<value>]
  Examples:
  - Blood pressure elevated (145/88 on 2023-10-01) [Source: vitals.csv | visit_date=2023-10-01]
  - OASIS shows chairfast status [Source: oasis.csv | assessment_date=2025-12-03]
  - Pressure ulcer stage III [Source: wounds.csv | visit_date=2026-01-08]
- If something is missing, say "Not documented" AND still include the relevant source file citation.
- If you describe a trend, reference the involved dates.

Patient ID: {pid}
Episode ID: {eid}

========================
PATIENT EHR DATA
========================

1) Diagnoses:
{dx_text}

2) Medications:
{meds_text}

3) Vitals (latest vitals date overall: {latest_date}):
{vitals_text}

Abnormal vitals:
{abnormal_text}

4) Wounds:
{wounds_text}

5) Functional Status (OASIS):
Assessment Date: {oasis_date} [Source: oasis.csv | assessment_date={oasis_date}]
Assessment Type: {oasis_type} [Source: oasis.csv | assessment_date={oasis_date}]
ADL / Mobility:
{adl_text}

6) Recent Notes:
{notes_text}

========================
OUTPUT FORMAT
========================
Use the headings EXACTLY as written below, and include citations in every bullet/sentence:

1. Patient Overview
2. Primary Diagnoses
3. Recent Vital Signs & Trends
4. Active Wounds & Wound Care Status
5. Current Medications / Adherence Notes
6. Functional Status (OASIS)
7. Recent Clinician Notes (key events)
8. Risks / Red Flags
9. Recommended Care Focus (next 7 days)

Keep it concise, clinically meaningful, and verifiable.

Rules:
- Do not hallucinate.
- If data is missing, say "Not documented".
- Be concise but clinically meaningful.
- Highlight wound care, BP/oxygen abnormalities if present, immobility risks, infection risk, and dependence in ADLs.
""".strip()

    return prompt
