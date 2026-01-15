# main.py
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.data_loader import load_data
from src.patient_service import patient_exists
from src.summary_generator import generate_summary


# -----------------------------
# FastAPI App
# -----------------------------
app = FastAPI(
    title="Clinical Summary Generator API",
    version="1.0.0",
    description="Generates evidence-based clinical summaries from CSV EHR tables using an LLM.",
)

# Allow Streamlit frontend to call API (localhost use-case)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo-friendly; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Request / Response models
# -----------------------------
class GenerateSummaryRequest(BaseModel):
    patient_id: int = Field(..., description="Patient ID to generate summary for", examples=[1002])
    use_llm: bool = Field(default=True, description="Use LLM (True) or fallback template (False)")
    model: str = Field(default="gpt-4o-mini", description="OpenAI model name")


class GenerateSummaryResponse(BaseModel):
    patient_id: int
    summary: str
    debug: Dict[str, Any]


# -----------------------------
# Data cache
# -----------------------------
@lru_cache(maxsize=1)
def get_tables():
    """
    Load CSV data once, cache in memory for API lifetime.
    """
    return load_data()


# -----------------------------
# Endpoints
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate_summary", response_model=GenerateSummaryResponse)
def generate_summary_endpoint(payload: GenerateSummaryRequest):
    """
    POST /generate_summary
    Body: { patient_id: int }
    Returns: generated clinical summary
    """
    tables = get_tables()

    if not patient_exists(tables, payload.patient_id):
        raise HTTPException(
            status_code=404,
            detail=f"No data found for patient_id={payload.patient_id}",
        )

    summary_text, debug = generate_summary(
        tables=tables,
        patient_id=payload.patient_id,
        use_llm=payload.use_llm,
        model=payload.model,
    )

    return {
        "patient_id": payload.patient_id,
        "summary": summary_text,
        "debug": debug,
    }