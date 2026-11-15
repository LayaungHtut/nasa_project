# Data Provenance Log

## Update 2026-09-18: real data downloaded and processed

Earthdata Login was authenticated via a project-local `.env` (see `services/processing/auth.py`) after authorizing the "Alaska Satellite Facility NISAR Data Access" application on the team's Earthdata account. Both real granules below were downloaded (~5.96 GB and ~5.97 GB) and byte-size-verified. The full pipeline ran against real pixels; that processed case study has since been removed from the app and repository.

## Real granules identified (verified 2026-09-18)

Found via `scripts/search_nisar_myanmar.py` (asf_search v14.0.0, no auth needed for metadata search) against a Myanmar bounding box, then filtered to footprints containing Yangon (16.8N, 96.15E). Full result set: [data/catalog.json](../../data/catalog.json).

| Candidate                        | Product | Granule ID (baseline)                                                                         | Granule ID (post-event)                                                                       | Baseline date | Post-event date | AOI                    | Download status                                                                                               |
| -------------------------------- | ------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------- | --------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------- |
| yangon-track40-frame10 (primary) | GCOV    | `NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001` | `NISAR_L2_PR_GCOV_030_040_A_010_4005_DHDH_A_20260908T230239_20260908T230313_P05023_N_F_J_001` | 2026-08-27    | 2026-09-08      | Yangon Region, Myanmar | **DOWNLOADED** 2026-09-18 — byte-verified, 5,955,911,680 / 5,968,494,592 bytes; processed event since removed |
| yangon-track134-frame80 (backup) | GCOV    | `NISAR_L2_PR_GCOV_029_134_D_080_2005_DHDH_M_20260903T121136_20260903T121211_P05023_N_F_J_001` | `NISAR_L2_PR_GCOV_030_134_D_080_2005_SHSH_M_20260915T121136_20260915T121211_P05023_N_F_J_001` | 2026-09-03    | 2026-09-15      | Yangon Region, Myanmar | Not yet re-tested individually                                                                                |

## Exact download blocker (reproduced 2026-09-18)

```
$ curl -sI "https://nisar.asf.earthdatacloud.nasa.gov/.../..._QA_STATS.h5"
HTTP/1.1 303 See Other
location: https://d1mv8zhcvry6x4.cloudfront.net/...s3.us-west-2.amazonaws.com/..._QA_STATS.h5?Expires=...&Signature=...

$ curl -sL -o qa_stats.h5 "<same url>"
$ cat qa_stats.h5
HTTP Basic: Access denied.
```

This happened even for a 27-byte QA sidecar file, not just the ~5.9 GB main `.h5` product — confirming the entire `nisar.asf.earthdatacloud.nasa.gov` collection requires an authenticated NASA Earthdata Login (EDL) session, with no anonymous/public read path, despite NISAR being open data. This matches ASF's documented access model (Vertex/CMR search is public; downloads require EDL).

**Resolution (2026-09-18)**: switched from `_netrc` to a project-local `.env` (per updated instructions) loaded via `python-dotenv` in `services/processing/auth.py`. First authenticated attempt still failed with a _different_, more specific error: `ASFAuthenticationError: ... Pre authorization required for this application ... resolution_url=https://urs.earthdata.nasa.gov/approve_app?client_id=...` — Earthdata Login accepted the username/password but required a one-time manual authorization of the "Alaska Satellite Facility NISAR Data Access" application on the account's Earthdata profile page. Once authorized there, `scripts/verify_earthdata_auth.py` passed cleanly, and both real granules downloaded successfully.

## Lineage

```
NASA/ISRO NISAR L2 GCOV product (ASF DAAC, Earthdata Login required)
  -> services/processing/io_gcov.py            [reads real HDF5, per documented schema]
  -> services/processing/speckle.py             [Lee filter]
  -> services/processing/change_detection.py    [dB threshold + connected-component change mask]
  -> services/processing/vectorize.py           [mask -> WGS84 GeoJSON via scikit-image contours]
  -> services/processing/pipeline_flood.py       [orchestrates the above, writes data/processed/<id>/]
  -> services/api/main.py                       [serves the resulting ChangeEvent JSON + static files]
  -> services/api/explain.py                    [grounded AI narration of the same JSON, template-based by default]
  -> SvelteKit frontend                         [renders three-tier: NASA observation / our processing / AI interpretation]
```

**Every stage above has run against real pixel data** (2026-09-18). That processed event has since been removed from the repository; run `python -m services.processing.pipeline_flood --mode real` with your own granules, AOI, threshold and filter size to produce a new one (see the README).

The 22 fixture-based tests in `tests/` still pass unchanged and remain useful for fast, offline regression testing — they are not a substitute for the real run above, just a complement to it.

## Environment note: GDAL/pyproj unavailable in this dev sandbox

`rasterio` and `pyproj` both fail to import here (`ImportError: ... An Application Control policy has blocked this file.` — a Windows security control blocking their native GDAL/PROJ DLLs). Worked around with:

- `utm` (pure Python) for UTM<->WGS84 conversion instead of `pyproj`
- `scikit-image` contour finding for mask vectorization instead of `rasterio.features.shapes`
- Plain images (PNG) + 4 corner `[lon, lat]` coordinates (for MapLibre GL's `ImageSource`) instead of true COG tiles

This is a genuine environment constraint, documented so nobody re-debugs it from scratch, and so a teammate on a different machine (no such policy) knows they can swap in real rasterio/COG output without changing the API contract — see `services/processing/geo.py`'s module docstring.
