"""FastAPI read layer -- serves curated/processed ChangeEvents to the
SvelteKit frontend. Implements docs/api/api-contract.md.

Deliberately thin: no raster processing happens in a request handler
(see docs/architecture/system-architecture.md). This process only reads
data/fixtures/events.json + data/processed/<id>/metadata.json (if newer
real events exist there) and serves static files from data/processed and
data/fixtures for previews/GeoJSON.

Run:
    uvicorn services.api.main:app --reload
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.api.explain import explain
from services.api.models import ChangeEvent, ExplainResponse

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_PATH = REPO_ROOT / "data" / "fixtures" / "events.json"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

app = FastAPI(title="YOUTHs NISAR API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon demo scope; tighten if ever deployed beyond it
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/data/processed", StaticFiles(directory=str(PROCESSED_DIR)), name="processed")

# in-process cache of generated AI explanations, keyed by event id --
# per ai-strategy.md, regenerating on every request is wasteful and the
# explanation is deterministic-ish given the same grounded record.
_explanation_cache: dict[str, dict] = {}


def _load_events() -> dict[str, dict]:
    events: dict[str, dict] = {}
    if FIXTURES_PATH.exists():
        for event in json.loads(FIXTURES_PATH.read_text())["events"]:
            events[event["id"]] = event
    if PROCESSED_DIR.exists():
        for metadata_path in PROCESSED_DIR.glob("*/metadata.json"):
            event = json.loads(metadata_path.read_text())
            events[event["id"]] = event  # a real processed run overrides a same-id fixture
    return events


@app.get("/api/events")
def list_events():
    events = list(_load_events().values())
    summaries = []
    for e in events:
        summary = {k: v for k, v in e.items() if k != "ai_explanation"}
        summary["has_explanation"] = e["id"] in _explanation_cache
        summaries.append(summary)
    return {"events": summaries}


@app.get("/api/events/{event_id}", response_model=ChangeEvent)
def get_event(event_id: str):
    events = _load_events()
    if event_id not in events:
        raise HTTPException(status_code=404, detail={"error": "event_not_found", "id": event_id})
    event = dict(events[event_id])
    cached = _explanation_cache.get(event_id)
    event["ai_explanation"] = cached["ai_explanation"] if cached else None
    return event


@app.post("/api/events/{event_id}/explain", response_model=ExplainResponse)
def explain_event(event_id: str):
    events = _load_events()
    if event_id not in events:
        raise HTTPException(status_code=404, detail={"error": "event_not_found", "id": event_id})

    if event_id in _explanation_cache:
        cached = _explanation_cache[event_id]
        return ExplainResponse(**cached, cached=True)

    try:
        text = explain(events[event_id])
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": "explanation_failed", "message": str(e)})

    result = {"ai_explanation": text, "generated_at": datetime.now(timezone.utc).isoformat()}
    _explanation_cache[event_id] = result
    return ExplainResponse(**result, cached=False)
