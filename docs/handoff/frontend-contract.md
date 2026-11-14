# Frontend Handoff — for Antigravity

**Update 2026-09-18: real NISAR data is now live.** Earthdata Login was authorized, both real Track 40/Frame 10 granules (~5.96 GB / ~5.97 GB) were downloaded and byte-verified, and the full pipeline ran against real pixels. There is now a real, `"data_status": "REAL"` event — `yangon-hlawga-track40-frame10` — served alongside the synthetic fixture. Full methodology, what was tried and rejected, and honest limitations are in [real-data-validation.md](../science/real-data-validation.md) — read it before writing UI copy about this event, especially the "results" numbers (they're small and undramatic on purpose; do not imply more than 0.056 km² of change).

Start the API with:

```
pip install -r services/api/requirements.txt -r services/processing/requirements.txt
uvicorn services.api.main:app --reload --port 8000
```

It now serves **two** events:

- `yangon-hlawga-track40-frame10` — **real** NISAR data, Hlawga Reservoir north of Yangon, `data_status: "REAL"`. Small result (0.056 km², confidence 0.639) — this is honest, not a bug; see the validation report.
- `demo-yangon-fixture` — the original synthetic placeholder, `data_status: "SYNTHETIC_PLACEHOLDER"`, kept for offline/deterministic testing.

**The `data_status` check is no longer optional or future-proofing — it's live now.** Both values genuinely occur in the current event list; if your UI doesn't branch on it, it will misrepresent one of these two events today.

## Real response examples (captured 2026-09-18, after the real-data run)

### `GET /api/events`

```json
{
  "events": [
    {
      "id": "yangon-hlawga-track40-frame10",
      "title": "Hlawga Reservoir, Yangon Region, Myanmar water-extent change",
      "phenomenon": "flood_extent_change",
      "data_status": "REAL",
      "location": { "name": "Hlawga Reservoir, Yangon Region, Myanmar", "bbox": [96.0213, 16.9939, 96.1546, 17.1221], "center": [96.0880, 17.0580] },
      "observation_dates": { "baseline": "2026-08-27T23:02:39Z", "post_event": "2026-09-08T23:02:39Z" },
      "source_products": [
        { "mission": "NISAR", "product": "GCOV", "granule_id": "NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001", "daac": "ASF", "acquisition_date": "2026-08-27T23:02:39Z" },
        { "mission": "NISAR", "product": "GCOV", "granule_id": "NISAR_L2_PR_GCOV_030_040_A_010_4005_DHDH_A_20260908T230239_20260908T230313_P05023_N_F_J_001", "daac": "ASF", "acquisition_date": "2026-09-08T23:02:39Z" }
      ],
      "processing": {
        "method": "backscatter_threshold_change_detection_v1", "version": "1.0.0",
        "threshold_db": -9.54, "min_cluster_pixels": 8,
        "limitations": ["Flooded vegetation (forest, tall crops) may not be detected...", "Threshold is tuned for this AOI/scene and is not claimed to generalize globally without recalibration.", "..."]
      },
      "results": { "change_area_km2": 0.056, "confidence": 0.639, "changed_pixels": 556, "valid_fraction": 1.0 },
      "tiles": { "preview_url": "/data/processed/yangon-hlawga-track40-frame10/preview.png", "baseline_preview_url": "/data/processed/yangon-hlawga-track40-frame10/baseline.png", "post_event_preview_url": "/data/processed/yangon-hlawga-track40-frame10/post_event.png", "change_preview_url": "/data/processed/yangon-hlawga-track40-frame10/change.png", "corner_coordinates": [[lon,lat],[lon,lat],[lon,lat],[lon,lat]] },
      "change_geometry_url": "/data/processed/yangon-hlawga-track40-frame10/change.geojson",
      "generated_at": "2026-09-17T20:07:26Z",
      "has_explanation": false
    },
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
