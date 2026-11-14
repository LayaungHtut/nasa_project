# System Architecture

## Guiding constraint

Hackathon, 6 people, ~48 hours of build time. Optimize for: reliable demo > completeness. No Kubernetes, no microservices beyond the two we already need, no auth system, no realtime infra. See Phase 13 in the project brief — this doc follows it.

## High-level shape

```
┌─────────────────────┐        ┌──────────────────────────┐        ┌─────────────────────┐
│  apps/web (SvelteKit)│  HTTP  │  services/api (FastAPI)  │  reads │  data/ (local files /│
│  MapLibre GL, UI     │◄──────►│  scenes, changes, tiles, │◄──────►│  object storage)     │
│                      │  JSON  │  analyze, ai-explain     │        │  COGs, GeoJSON, JSON │
└─────────────────────┘        └──────────────────────────┘        └─────────────────────┘
                                          ▲
                                          │ invoked offline / on-demand
                                          │
                                ┌──────────────────────────┐        ┌─────────────────────┐
                                │ services/processing        │  ASF   │  ASF Vertex / CMR /   │
                                │ (Python: rasterio, GDAL,   │◄──────►│  asf_search / EDL     │
                                │  h5py, numpy, scipy,       │  https │  download             │
                                │  geopandas)                │        │                       │
                                └──────────────────────────┘        └─────────────────────┘
```

Two Python codebases, not one, because they have different lifecycles: `processing` runs ahead-of-time (or via an explicit "analyze" job) and is compute-heavy/slow; `api` is a thin, fast, always-up read layer the frontend polls. Sharing one FastAPI process for both would risk the live demo hanging on a slow raster job — unacceptable for a stage demo.

## Frontend (owned by Antigravity)

SvelteKit + TypeScript + TailwindCSS + DaisyUI + Lucide + MapLibre GL JS (vector/raster tiles, good COG/XYZ tile support, no token/billing dependency unlike some alternatives — important for a hackathon demo running on unknown wifi). Full contract in [frontend-contract.md](../handoff/frontend-contract.md).

## Backend: `services/api` (FastAPI)

Responsibilities:

- Serve curated + (if time allows) live `ChangeEvent` metadata as JSON
- Serve tile endpoints (proxy/redirect to statically-hosted COG tiles, or serve XYZ tiles directly via `rio-tiler`/`titiler`-style dynamic tiling if we have time — see open decision below)
- Own the grounded AI-explanation endpoint (see [ai-strategy.md](../ai/ai-strategy.md))
- Never perform heavy raster processing inline in a request handler — that's `processing`'s job, invoked ahead of time or as an explicitly async/background job if we build the "live analyze" stretch feature

Does NOT need a database for the MVP: our data volume is a handful of curated `ChangeEvent`s + their derived files. Flat JSON + files on disk (or object storage) is simpler, more reliable, and easier to git-diff/review than standing up Postgres for a few dozen records. If a live-search-by-AOI feature is built and scenes multiply, revisit — see "growth path" below.

## Processing: `services/processing` (Python)

Responsibilities (per [methodology.md](../science/methodology.md)):

- `fetch.py` — search/download NISAR granules via `asf_search` (wraps CMR), given AOI + date range
- `pipeline_flood.py` — GCOV → speckle filter → threshold → change mask → stats → COG + GeoJSON output
- `pipeline_deform.py` (stretch) — GUNW → coherence mask → classify → COG output
- `to_cog.py` — shared raster→COG writer (rasterio `COG` driver)
- Output of every run: one `ChangeEvent` JSON record + associated COG/GeoJSON files, written into `data/processed/<event-id>/`

This is a CLI-invoked pipeline (`python -m processing.pipeline_flood --aoi ... --before ... --after ...`), not a long-running service. Run it ahead of the event to build our curated demo set; optionally exposed via a background job in the API as a "try your own AOI" stretch feature — never on the critical demo path.

## Data storage

| Data type                                             | Where                                                                   | Why                                                                                                                                   |
| ----------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Raw downloaded NISAR HDF5                             | `data/raw/` (gitignored, large)                                         | Working cache, not committed                                                                                                          |
| Derived rasters (change masks, backscatter snapshots) | `data/processed/<event-id>/*.tif` (COG)                                 | Small enough post-crop-and-compress to commit or host directly; COG allows range-request tile serving without a tile server if needed |
| Vectorized change polygons                            | `data/processed/<event-id>/change.geojson`                              | Directly consumable by MapLibre, tiny                                                                                                 |
| Curated event metadata                                | `data/metadata/events.json` (or one JSON per event in `data/fixtures/`) | Source of truth the API reads; hand-editable, git-diffable                                                                            |
| Cached AI explanations                                | alongside event metadata, keyed by event id                             | Avoid regenerating on every request/demo run                                                                                          |

**No PostgreSQL/Neon for the MVP.** Flat files fully satisfy "metadata + small derived outputs" at our scale and remove a moving part from the live demo. Revisit only if we end up with hundreds of live-generated events or need concurrent multi-user writes (we won't, for a hackathon judged demo).

**No raw HDF5 or large uncropped rasters ever reach the frontend.** The frontend only ever fetches: small JSON, GeoJSON, and tiled/cropped COGs.

## Tiling decision (needs a team call once we know time budget)

Two options, pick one early:

1. **Pre-rendered PNG/COG tiles, statically served** — simplest, zero runtime raster cost, but tied to fixed zoom range/AOIs (fine, since our AOIs are curated).
2. **Dynamic tiling via `rio-tiler`/`titiler`-style endpoint in the FastAPI service, reading COGs on demand** — more flexible (pan/zoom anywhere within the COG, adjustable rendering/stretch), moderate added complexity.

**Recommendation: start with (1)** for guaranteed demo reliability; add (2) only as a stretch if the curated set feels too rigid and time remains.

## Growth path (explicitly out of scope for v1, noted so nobody "accidentally" builds it early)

- Postgres/PostGIS if we need spatial querying across many live-generated events
- Object storage (S3-compatible) if local disk stops being enough — architecture above already assumes file paths are swappable for object storage URLs without an API contract change
- Auth — not needed, this is a public demo with no user accounts
