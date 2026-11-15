# Frontend Handoff — for Antigravity

**Update:** the real Track 40 / Frame 10 event that was processed on 2026-09-18 has been removed from the project. The API currently serves only the synthetic fixture below.

Start the API with:

```
pip install -r services/api/requirements.txt -r services/processing/requirements.txt
uvicorn services.api.main:app --reload --port 8000
```

It serves one event:

- `demo-yangon-fixture` — the original synthetic placeholder, `data_status: "SYNTHETIC_PLACEHOLDER"`, kept for offline/deterministic testing.

**Keep the `data_status` check.** Real events can be added back through `data/processed/<event-id>/`; if your UI doesn't branch on it, it will misrepresent synthetic data as an observation.

## Response examples

### `GET /api/events`

```json
{
  "events": [
    {
      "id": "demo-yangon-fixture",
      "title": "Yangon Region, Myanmar (synthetic AOI) water-extent change",
      "phenomenon": "flood_extent_change",
      "data_status": "SYNTHETIC_PLACEHOLDER",
      "location": { "name": "Yangon Region, Myanmar (synthetic AOI)", "bbox": [94.6888, 16.7698, 94.7370, 16.8163], "center": [94.7129, 16.7930] },
      "observation_dates": { "baseline": "SYNTHETIC-NO-REAL-ACQUISITION", "post_event": "SYNTHETIC-NO-REAL-ACQUISITION" },
      "source_products": [
        { "mission": "NISAR", "product": "GCOV", "granule_id": "SYNTHETIC_FIXTURE_baseline_no_real_granule", "daac": "ASF", "acquisition_date": "SYNTHETIC-NO-REAL-ACQUISITION" },
        { "mission": "NISAR", "product": "GCOV", "granule_id": "SYNTHETIC_FIXTURE_post_event_no_real_granule", "daac": "ASF", "acquisition_date": "SYNTHETIC-NO-REAL-ACQUISITION" }
      ],
      "processing": {
        "method": "backscatter_threshold_change_detection_v1", "version": "1.0.0",
        "threshold_db": -17.0, "min_cluster_pixels": 8,
        "limitations": ["Flooded vegetation (forest, tall crops) may not be detected...", "Smooth non-water surfaces can produce false positives.", "..."]
      },
      "results": { "change_area_km2": 1.528, "confidence": 1.0, "changed_pixels": 3819, "valid_fraction": 1.0 },
      "tiles": { "preview_url": "/data/processed/demo-yangon-fixture/preview.png", "corner_coordinates": [[lon,lat],[lon,lat],[lon,lat],[lon,lat]] },
      "change_geometry_url": "/data/processed/demo-yangon-fixture/change.geojson",
      "generated_at": "2026-09-17T18:03:53Z",
      "has_explanation": false
    }
  ]
}
```

Note the real event's `confidence: 0.639` is not saturated at 1.0 like the fixture's — that's expected (the fixture's synthetic flood is a much larger, cleaner detection). Don't treat a lower confidence value on the real event as a display bug.

Note: the list endpoint omits `ai_explanation` entirely (use `has_explanation: boolean` to decide whether to show an "explained" badge in a gallery card) — fetch the detail endpoint to get the actual text.

### `GET /api/events/{id}` — same shape as above, plus `ai_explanation: string | null`.

### `POST /api/events/{id}/explain`

```json
{
	"ai_explanation": "This is a placeholder scene used to test the pipeline before real NISAR data was available -- not an actual observation. Comparing NISAR GCOV backscatter over Yangon Region, Myanmar (synthetic AOI) between SYNTHETIC-NO-REAL-ACQUISITION and SYNTHETIC-NO-REAL-ACQUISITION, our analysis (backscatter_threshold_change_detection_v1, threshold -17.0 dB) flagged approximately 1.528 km² as a water-extent change candidate, with a confidence score of 1.0 (our own heuristic, not a NASA-provided value). Limitation to keep in mind: ...",
	"generated_at": "2026-09-17T18:06:41Z",
	"cached": false
}
```

Second call to the same event returns `"cached": true` with identical text — safe to call eagerly once per event without worrying about cost/latency on repeat views.

### `GET /api/events/{unknown}` and `POST /api/events/{unknown}/explain`

Both return `404` with body `{"detail": {"error": "event_not_found", "id": "..."}}`. Handle this — don't assume every id in a URL param resolves.

## Rendering the raster layer — no COG/tile server in this environment

The dev sandbox this backend was built in blocks GDAL/rasterio (an OS-level security policy — see `services/processing/geo.py`), so **there is no XYZ tile endpoint**. Instead, `tiles.preview_url` is a plain PNG (three panels side by side: baseline / post-event / change-highlighted, each grayscale dB-stretched backscatter) and `tiles.corner_coordinates` gives the 4 image corners as `[lon, lat]` pairs in **top-left, top-right, bottom-right, bottom-left** order — this is exactly the format MapLibre GL's [`ImageSource`](https://maplibre.org/maplibre-gl-js/docs/API/classes/ImageSource/) `coordinates` option expects. Example:

```js
map.addSource('event-preview', {
	type: 'image',
	url: event.tiles.preview_url,
	coordinates: event.tiles.corner_coordinates
});
map.addLayer({ id: 'event-preview-layer', type: 'raster', source: 'event-preview' });
```

`preview.png` is still a 3-panel strip for convenience/debugging, but `baseline_preview_url` / `post_event_preview_url` / `change_preview_url` (each a single full-size image, same `corner_coordinates`) are now populated on every event — use those three separately as MapLibre `ImageSource`s rather than cropping the strip.

`change_geometry_url` is a standard GeoJSON `FeatureCollection` of `Polygon` features in WGS84 — load directly as a MapLibre GeoJSON source for a vector overlay of the detected change boundary (in addition to, or instead of, the raster change panel).

## Non-negotiable UX rule: three-tier visual separation

Every event view must visually distinguish:

1. **NASA observation** — `source_products[]`, `observation_dates` (mission, granule IDs, acquisition dates)
2. **Our processing** — `processing`, `results`, `tiles`, `change_geometry_url` (method, threshold, area, confidence)
3. **AI interpretation** — `ai_explanation` (must be labeled as AI-generated, must degrade gracefully — the rest of the event renders fine if `/explain` 502s)

Additionally: **whenever `data_status !== "REAL"`, show a visible "placeholder / test data" indicator** — don't let a judge mistake the synthetic fixture for a real observation. This isn't optional polish; it's the same scientific-honesty rule that governs the whole project (see [limitations.md](../science/limitations.md)).

## What NOT to do

- Don't fetch or render raw HDF5 — it isn't exposed by the API at all.
- Don't build free-text chat about arbitrary locations — `/explain` only narrates events already in `/api/events`.
- Don't hardcode event data into the frontend — always read from `/api/events`.
- Don't assume `tiles.preview_url` is tileable/zoomable infinitely — it's a fixed-resolution image for the current AOI, not a slippy-map tile source.

## Design tone

See [design-principles.md](design-principles.md).
