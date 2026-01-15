# src/llm_client.py
from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI


def call_llm(
    prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
) -> str:
    """
    Calls an OpenAI LLM with the given prompt and returns generated text.

    Robust behavior:
    - Uses OPENAI_API_KEY from environment variables.
    - Tries first with `temperature` (more controlled output).
    - If the model does not support `temperature`, retries without it automatically.

    Args:
        prompt: The full prompt/context string.
        model: Model name (e.g., "gpt-5-nano", "gpt-4o-mini").
        temperature: Sampling temperature (if model supports it).

    Returns:
        str: Assistant generated response text.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Set it as an environment variable before running."
        )

    client = OpenAI(api_key=api_key)

    base_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a clinical assistant generating structured patient summaries."},
            {"role": "user", "content": prompt},
        ],
    }

    # ✅ Attempt 1: with temperature (if supported)
    try:
        resp = client.chat.completions.create(
            **base_payload,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        # ✅ Attempt 2: retry without temperature if model rejects it
        err = str(e).lower()

        # typical OpenAI error signals when parameter unsupported
        if "temperature" in err and ("unsupported" in err or "only the default" in err or "does not support" in err):
            resp = client.chat.completions.create(**base_payload)
            return resp.choices[0].message.content.strip()

        # otherwise it's a real error (bad key, model not found, etc.)
        raise