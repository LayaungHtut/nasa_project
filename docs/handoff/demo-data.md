# Demo Data Strategy — for Antigravity and anyone building the pipeline

## Why this exists

We will not gate the live demo on a real-time NASA API call succeeding on stage. Per Phase 7 of the project brief: live data when practical, curated/cached NASA-derived data for guaranteed demonstration.

## The rule

Every curated event in `data/fixtures/` was produced by actually running `services/processing` against real, downloaded NISAR granules (per [methodology.md](../science/methodology.md)) — **ahead of time**, not fabricated. The word "curated" means "pre-computed from real data and checked in," never "synthetic placeholder pretending to be NASA data." If a fixture's numbers are ever placeholder/synthetic during early development, it must be obviously marked (`"status": "PLACEHOLDER_DO_NOT_DEMO"` in the JSON) and never wired into the default demo path.

## Structure

```
data/fixtures/
  events.json              # array of ChangeEvent records (see api-contract.md), this is what /api/events serves by default
  <event-id>/
    baseline.tif            # COG, cropped backscatter, baseline date
    post_event.tif           # COG, cropped backscatter, post-event date
    change_mask.tif          # COG, classified change raster
    change.geojson           # vectorized change polygons
```

`services/api` reads `data/fixtures/events.json` directly for `/api/events*` in the default/demo configuration — no database, no live dependency, on by default. If/when a live `/api/analyze` path exists, it writes new records into `data/processed/` in the same shape, and the API can be configured to merge both sources — but the curated fixtures must always work with zero network access.

## Provenance requirement

Every fixture's `source_products[].granule_id` must be a real ASF granule ID we can point to if questioned. Never invent a granule ID. If we end up simulating a scene during early dev before we've finished a real download, mark it clearly as above and swap it before the final build.

## Recommended demo set (to be finalized once granule search is done — outstanding task #2 in the research doc)

1. One flood event, ideally Myanmar/South-Asia monsoon 2026, as the primary story.
2. One additional flood or (stretch) deformation event elsewhere, to show the method generalizes beyond one location.

Two solid, verified events beat five shaky ones. Do not over-build the fixture library at the expense of pipeline correctness.
