# Dancing with the SARs - NISAR Earth Explorer

> **Local development:** `npm run dev` in this folder launches the real-data app from `../Nasa-project-feat` at `http://localhost:5173`. Open `NISAR-real-data.code-workspace` to edit that app. The older source files below remain preserved in this checkout.

Team **YOUTHs**, Yangon - Prepared for the **2026 NASA Space Apps Challenge**

An interactive explorer for two-date NASA-ISRO NISAR radar comparisons over Myanmar. Swipe between a baseline and a repeat radar scene, see where a deterministic threshold flags possible water-extent change, and learn why a changed radar signal does not necessarily mean a flood.

## What you can explore

- A synchronized before/after swipe map with one shared grayscale range for both dates.
- Baseline and repeat observations, acquisition dates in UTC, and two-scene playback.
- A separate candidate-change layer with downloadable GeoJSON and observation records.
- Processing parameters, source granule identifiers, heuristic score, and pipeline statistics.
- SAR physics explanations, a seven-step judge tour, and ideas for future NISAR applications in Myanmar.
- A deterministic, record-based explanation template. The current application does **not** call a live AI model.

All events currently in the catalog are synthetic teaching scenarios (`data_status: "SYNTHETIC_PLACEHOLDER"`). They are labeled explicitly and must not be presented as observations. Any change the pipeline flags is a candidate: confirm physical changes with independent imagery, water-level records, and relevant weather observations before using them in decisions.

See the [methodology](docs/science/methodology.md) and [limitations](docs/science/limitations.md).

## Run locally

Use Node.js 22.12+ (or a compatible newer version) and npm. From the repository root:

```sh
npm ci
npm run dev
```

On Windows PowerShell, use `npm.cmd` if execution policy blocks `npm.ps1`. Open the local URL printed by Vite. Committed processed previews and metadata support the web demo without downloading the raw satellite files. Basemap tiles require internet access.

```sh
npm run check
npm test
npm run build
npm run preview
```

`npm test` runs the configured server unit suite. Browser interaction testing is separate. The application needs a server runtime with access to `data/processed/` and `data/fixtures/`; configure the SvelteKit deployment adapter for your host and include those directories. No hosted deployment is configured here.

## Data flow and reproducibility

```text
NISAR GCOV HDF5 files
  -> AOI read and quality mask
  -> Lee filtering, dB conversion, thresholding, cluster filtering
  -> data/processed/<event-id>/{metadata.json,statistics.json,change.geojson,*.png}
  -> SvelteKit server loader and /api/events routes
  -> shared presentation and interactive map
```

The server reads processed outputs directly, overriding catalog fixtures. Shared presentation functions generate timeline steps and explanatory text from these records. The separate Python API is optional; it is not required by the SvelteKit application.

To reproduce the pixel processing:

1. Install Python dependencies from `services/processing/requirements.txt` in a virtual environment.
2. Obtain a NISAR GCOV repeat-pass pair through ASF/Earthdata using your own credentials. Search/download helpers are in `scripts/`; never commit credentials or raw downloads.
3. Place the HDF5 files in `data/raw/` and run `python -m services.processing.pipeline_flood --mode real` with the granule IDs, AOI, threshold and filter size for your scene (see `--help`). Outputs are written to `data/processed/<event-id>/`.
4. Inspect the regenerated metrics and previews. Interpret changes in calibration or parameters explicitly rather than silently replacing the narrative.

Raw products are several GB each and are gitignored. The current app visualizes prepared, georeferenced PNG previews; it does not provide arbitrary worldwide processing, a tiled COG service, or validated operational flood mapping.

## Sources and attribution

- [ASF NISAR GCOV product guide](https://nisar-docs.asf.alaska.edu/gcov/)
- [NASA NISAR mission](https://science.nasa.gov/mission/nisar/)
- Radar observations: NASA/ISRO NISAR, distributed by ASF DAAC / NASA Earthdata.
- Change detection and interpretation: Team YOUTHs.
- Basemap: OpenFreeMap, OpenMapTiles and OpenStreetMap contributors; attribution is displayed on the map.

## Sharing the project

Use the in-app downloads to share the observation record, candidate polygons, and statistics. This project is released under the open-source [MIT License](LICENSE). Third-party data, basemaps and dependencies retain their own terms.
"# nasa_project"
