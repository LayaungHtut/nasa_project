# AI Strategy

## Principle

**The AI never looks at pixels and decides what happened. The AI narrates numbers our deterministic pipeline already computed.**

This is the single rule that prevents this project from becoming fake science. Every LLM call is grounded in a structured JSON record produced by [methodology.md](../science/methodology.md)'s pipeline — never given raw imagery and asked "what changed here?"

## Grounded input contract

The only object the LLM ever receives to write an explanation is a `ChangeEvent` record, e.g.:

```json
{
  "location": { "name": "Bago Region, Myanmar", "bbox": [...] },
  "phenomenon": "flood_extent_change",
  "observation_dates": { "baseline": "2026-06-20", "post_event": "2026-08-14" },
  "source_product": { "mission": "NISAR", "product": "GCOV", "granule_id": "..." },
  "processing_method": "backscatter_threshold_change_detection_v1",
  "change_area_km2": 42.7,
  "confidence": 0.78,
  "known_limitations": ["flooded vegetation likely underrepresented", "threshold tuned to this AOI"]
}
```

The system prompt instructs the model explicitly:

- Only state facts present in the JSON.
- Always mention data source, acquisition dates, and at least one limitation.
- Never assert certainty beyond the `confidence` value.
- Never invent a phenomenon type, magnitude, or human-impact number not in the record.

This is enforced by keeping the LLM call as pure text-generation-over-structured-data (a "report writer," not an "analyst"), and by post-generation validation: reject/regenerate any output that mentions a number not traceable to the input JSON (simple regex/number-extraction check against the source record is enough for hackathon scope — no need for a heavier verifier model).

## Where AI actually helps

1. **Plain-language explanation ("What you're seeing" panel)** — turns the structured record into 2-3 sentences a non-expert can read. Highest value, lowest risk, since it's fully grounded.
2. **"How NISAR sees it" explainer** — static/templated content mostly (what SAR/backscatter/L-band means), possibly LLM-assisted drafting during development, but shipped as reviewed, fixed copy in the product — not generated live per user session. Educational accuracy matters too much to regenerate at runtime.
3. **Event ranking / "most interesting changes" summarization** — if we curate multiple demo AOIs, an LLM can help write a one-line teaser per event from the same structured records, again strictly grounded.
4. **Semantic search over curated stories** ("show me a flood story," "show me something in Southeast Asia") — a light natural-language front-end onto our small, curated set of `ChangeEvent` records. Not a general open-ended chat about arbitrary NISAR data we haven't processed.

## Where AI does NOT belong (v1)

- No live classification of "is this a flood/fire/earthquake" from imagery — that's the deterministic pipeline's job.
- No open-ended chatbot that can be asked about locations/dates we haven't actually processed — it will either refuse or hallucinate; scope the assistant strictly to the events in our database.
- No autonomous "AI detected N new events" claims — every event in the system was selected and processed by us ahead of time (curated) or via our own on-demand pipeline (live path), never by a model scanning raw NISAR data unsupervised.

## Suggested implementation

- Backend owns the `ChangeEvent` → prompt → LLM call → validated-explanation pipeline as one FastAPI endpoint (`POST /api/analyze/explain` or similar — finalize in [api-contract.md](../api/api-contract.md)), so the frontend never talks to an LLM directly and never sees an ungrounded response.
- Cache generated explanations per `ChangeEvent` id (they're deterministic-ish and expensive to regenerate) — store alongside the curated fixture, not regenerated on every page load.
- Model choice: any current Claude model is sufficient for this grounded-summarization task; no need for a large/expensive model given the narrow, structured task.
