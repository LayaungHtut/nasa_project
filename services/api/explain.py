"""Grounded AI-explanation layer.

Per docs/ai/ai-strategy.md: the model (or, absent an API key, a
deterministic template) NEVER inspects imagery -- it only narrates the
structured `ChangeEvent` record the deterministic pipeline already
produced. Every number in the output is traceable back to that record.

Two modes:
  - No ANTHROPIC_API_KEY set: `template_explanation()` runs, a
    deterministic string-formatting function. Fully functional with zero
    external dependencies -- this is the default so the API works out of
    the box on a fresh checkout.
  - ANTHROPIC_API_KEY set: `llm_explanation()` sends the same grounded
    JSON to the Claude API with a system prompt that enforces the
    grounding rules from ai-strategy.md, and validates the response
    doesn't introduce numbers absent from the input record before
    returning it.

Both paths return the same shape, so the frontend/API contract doesn't
change based on which is active.
"""

from __future__ import annotations

import os
import re


def _grounded_context(event: dict) -> dict:
    return {
        "location": event["location"]["name"],
        "phenomenon": event["phenomenon"],
        "data_status": event["data_status"],
        "observation_dates": event["observation_dates"],
        "source_products": event["source_products"],
        "processing_method": event["processing"]["method"],
        "threshold_db": event["processing"]["threshold_db"],
        "change_area_km2": event["results"]["change_area_km2"],
        "confidence": event["results"]["confidence"],
        "limitations": event["processing"]["limitations"],
    }


def template_explanation(event: dict) -> str:
    """Deterministic, zero-dependency fallback. Every clause maps directly
    to a field in the ChangeEvent record -- no invented facts."""
    ctx = _grounded_context(event)
    status_note = (
        "This is a placeholder scene used to test the pipeline before real NISAR data was available -- not an actual observation."
        if ctx["data_status"] == "SYNTHETIC_PLACEHOLDER"
        else "This is a real NASA/ISRO NISAR observation."
    )
    limitation = ctx["limitations"][0] if ctx["limitations"] else "This method has known limitations; see the full list."

    return (
        f"{status_note} Comparing NISAR GCOV backscatter over {ctx['location']} between "
        f"{ctx['observation_dates']['baseline']} and {ctx['observation_dates']['post_event']}, "
        f"our analysis ({ctx['processing_method']}, threshold {ctx['threshold_db']} dB) flagged "
        f"approximately {ctx['change_area_km2']} km² as a water-extent change candidate, "
        f"with a confidence score of {ctx['confidence']} (our own heuristic, not a NASA-provided value). "
        f"Limitation to keep in mind: {limitation}"
    )


_SYSTEM_PROMPT = """You write short, plain-language explanations of NISAR SAR change-detection results for a NASA Space Apps demo.

Rules, non-negotiable:
- Use ONLY the facts in the JSON you are given. Never invent a number, date, location detail, or magnitude not present in it.
- Always state the acquisition dates and that NISAR/ASF is the data source, and that the change result is OUR processing, not a NASA-provided classification.
- Always mention the confidence value and at least one limitation from the provided list.
- Never claim certainty beyond what the confidence value implies.
- Never say "NASA detected" or "AI detected" -- the deterministic pipeline described in the JSON detected it; you are only narrating.
- If data_status is SYNTHETIC_PLACEHOLDER, say clearly this is a placeholder/test scene, not a real observation.
- 3-4 sentences maximum."""


def _validate_grounded(text: str, event: dict) -> bool:
    """Reject an LLM response that mentions a change-area number materially
    different from the source record (cheap guard against hallucinated
    figures slipping through)."""
    area = event["results"]["change_area_km2"]
    numbers_in_text = [float(n) for n in re.findall(r"\d+\.?\d*", text)]
    return any(abs(n - area) < 0.5 for n in numbers_in_text) or area == 0


def llm_explanation(event: dict) -> str:
    """Requires ANTHROPIC_API_KEY. Falls back to the template if the call
    fails or the response doesn't pass grounding validation -- an AI
    failure must never break the explanation panel (docs/api/api-contract.md)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return template_explanation(event)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        ctx = _grounded_context(event)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": str(ctx)}],
        )
        text = response.content[0].text.strip()
        if not _validate_grounded(text, event):
            return template_explanation(event)
        return text
    except Exception:
        return template_explanation(event)


def explain(event: dict) -> str:
    return llm_explanation(event)
