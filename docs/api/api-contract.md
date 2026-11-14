# API Contract — `services/api`

Base URL (dev): `http://localhost:8000/api`

All responses are JSON. All geometries are GeoJSON, all coordinates WGS84 (EPSG:4326). All timestamps ISO 8601 UTC.

## Shared types

```ts
type Provenance = {
	mission: 'NISAR';
	product: 'GCOV' | 'GUNW'; // never omit — required for the NASA-vs-us distinction
	granule_id: string;
	daac: 'ASF';
	acquisition_date: string; // ISO date
};

type ChangeEvent = {
	id: string;
	title: string; // e.g. "Bago Region flood, Aug 2026"
	phenomenon: 'flood_extent_change' | 'surface_deformation';
	data_status: 'REAL' | 'SYNTHETIC_PLACEHOLDER'; // added during implementation -- see docs/handoff/demo-data.md. Frontend MUST show a visible indicator when not "REAL".
	location: {
		name: string;
		bbox: [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]
		center: [number, number];
	};
	observation_dates: {
		baseline: string;
		post_event: string;
	};
	source_products: Provenance[]; // one per date, at minimum
	processing: {
		method: string; // e.g. "backscatter_threshold_change_detection_v1"
		version: string;
		threshold_db: number;
		min_cluster_pixels: number;
		speckle_filter_size?: number; // e.g. 3 for a 3x3 Lee filter -- may differ from the methodology default; see real-data-validation.md for why
		limitations: string[]; // always non-empty, pulled from limitations.md
	};
	results: {
		change_area_km2: number;
		confidence: number; // 0-1, our own metric, not NASA's, kept for compatibility
		confidence_type?: 'heuristic_detection_score'; // explicit: NOT a statistical probability -- see real-data-validation.md
		changed_pixels: number;
		valid_fraction: number;
	};
	statistics_url?: string; // full audit-trail JSON (pixel counts, AOI area, filter/threshold used) -- see real-data-validation.md
	tiles: {
		preview_url: string; // 3-panel (baseline|post|change) strip PNG, kept for backward compat
		baseline_preview_url?: string; // single baseline-only PNG -- use this + the two below for per-layer MapLibre ImageSources
		post_event_preview_url?: string;
		change_preview_url?: string; // post-event image with the change mask highlighted
		corner_coordinates: [number, number][]; // 4 [lon,lat] pairs, TL/TR/BR/BL -- same for all four images above, for MapLibre GL ImageSource
	};
	change_geometry_url: string; // GeoJSON polygons of detected change
	ai_explanation: string | null; // null until generated; see /explain
};
```

`tier` is implicit but must always be inferable from the field name: `source_products`/`observation_dates` = **NASA observation**; `processing`/`results`/`tiles`/`change_geometry_url` = **our processing**; `ai_explanation` = **AI interpretation**. The frontend must visually separate these three (see [frontend-contract.md](../handoff/frontend-contract.md)) — the API shape enforces this by keeping them in distinctly named top-level keys, never merged into one flat blob.

## Endpoints

### `GET /api/events`

List all available `ChangeEvent`s (curated + any live-generated ones).

Response: `{ events: ChangeEvent[] }` (omit heavy fields like `ai_explanation` body if long; include a `has_explanation: boolean` instead in the list view — full record fetched via the detail endpoint).

### `GET /api/events/{id}`

Full `ChangeEvent` record, as above.

Errors: `404 { error: "event_not_found", id }`

### Tiling decision: resolved as static images, not a tile endpoint

No `/tiles/{z}/{x}/{y}` route was built. `services/api/main.py` mounts `data/processed/` as static files, and `tiles.preview_url` / `change_geometry_url` point directly at files under it. This was partly forced by environment constraints (GDAL/rasterio unavailable in the dev sandbox that built this — see `services/processing/geo.py`), and partly because it's simpler and sufficient for a curated, small event set. If real dynamic tiling is ever needed, add it as a new route without changing the fields above (a client that already reads `tiles.preview_url` shouldn't break).

### `POST /api/events/{id}/explain`

Triggers (or returns cached) AI explanation for an event. Body: `{}` (no input needed — the endpoint pulls the `ChangeEvent` record itself, per [ai-strategy.md](../ai/ai-strategy.md); the client never constructs the prompt).

Response: `{ ai_explanation: string, generated_at: string, cached: boolean }`

Errors: `502 { error: "explanation_failed" }` — frontend must render the rest of the event fine without this field; AI failure must never block viewing NASA data.

### `POST /api/analyze` (stretch — only if "try your own AOI" is built)

Body: `{ bbox: [number,number,number,number], phenomenon: "flood_extent_change", date_range: { start: string, end: string } }`

This kicks off `services/processing` as a background job (not inline — see architecture doc). Response: `{ job_id: string, status: "queued" }`.

### `GET /api/analyze/{job_id}`

Response: `{ status: "queued" | "running" | "done" | "failed", event_id: string | null, error: string | null }`

**Do not build `/api/analyze` unless the curated vertical slice (Phase 10) is fully working first.** It is explicitly the last thing to attempt, per the project brief's phase ordering.

## Error schema (all endpoints)

```json
{ "error": "<machine_readable_code>", "message": "<human readable>", "detail": {} }
```

## Pagination

Not needed at our scale (a handful of curated events). If `/api/events` ever exceeds ~50 items, add `?limit=&offset=` — not built preemptively.
