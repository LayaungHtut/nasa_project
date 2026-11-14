# NISAR Research Notes

Compiled 2026-09-18 by the technical lead, for NASA Space Apps 2026 (Yangon), challenge "Dancing with the SARs."

All claims below are sourced from official NASA/ASF/JPL pages fetched on 2026-09-18. Anything not directly confirmed by a source is flagged as **UNVERIFIED** and must be re-checked closer to build time (data availability is changing week to week in 2026).

## 1. The challenge itself

We could not retrieve the literal, current text of "Dancing with the SARs" from `spaceappschallenge.org/2026/challenges/` — the page is a JS-rendered SPA that our fetch tool could not execute, and the 2026 challenge list was not yet indexed by search at the time of research. **This is a gap, not a fabrication**: someone on the team should open the live challenge page in a browser and paste the exact objective/background/resources text into this file before we finalize scope.

What we do know with confidence:

- The 2026 global event runs **14–15 Nov 2026** under the theme "The Next Frontier," 14 challenges total. [spaceappschallenge.org/2026](https://www.spaceappschallenge.org/2026/)
- A near-identical challenge existed in 2025: **"Through the Radar Looking Glass: Revealing Earth Processes with SAR"** — same theme (use SAR, likely NISAR, to reveal Earth surface processes). [spaceappschallenge.org/2025 challenge page](https://www.spaceappschallenge.org/2025/challenges/through-the-radar-looking-glass-revealing-earth-processes-with-sar/)
- Space Apps SAR-themed challenges historically ask teams to (a) explain what SAR/InSAR is to a general audience, and (b) demonstrate a real, visualizable Earth-surface-change use case from real data — not build a generic map. The user's brief for this project is consistent with that pattern.

**Action item**: confirm exact 2026 wording before the final submission write-up references "the challenge asks X" verbatim.

## 2. What NISAR actually is

- NASA-ISRO joint mission. Launched **30 July 2025**. L-band (NASA-built radar) + S-band (ISRO-built radar).
- Transitioned commissioning → science operations through late 2025/2026.
- Designed for: ecosystem structure/biomass, agriculture, wetlands/inundation, cryosphere, solid-earth deformation (earthquakes, landslides, volcanoes), and general land-surface change — confirmed by [NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/products-overview/).

## 3. Data products (source: [NISAR Data Products — Data User Guide](https://nisar-docs.asf.alaska.edu/products-overview/))

All products are **HDF5**. Processing levels:

| Level | Product           | Geometry                          | Resolution           | Purpose                                                                                                                                                                                               |
| ----- | ----------------- | --------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0     | RRSD (raw signal) | radar                             | —                    | Raw data, SAR-processing specialists only                                                                                                                                                             |
| 1     | RSLC              | range-Doppler (not map-projected) | full res             | Base focused SAR image; foundation for other L1 products                                                                                                                                              |
| 1     | RIFG              | range-Doppler                     | 30 m                 | Wrapped interferogram; grounding-line detection                                                                                                                                                       |
| 1     | ROFF              | range-Doppler                     | 90 m                 | Pixel offsets; cryosphere motion tracking                                                                                                                                                             |
| 1     | RUNW              | range-Doppler                     | 80 m                 | Unwrapped interferogram; ground displacement                                                                                                                                                          |
| 2     | **GSLC**          | geocoded map projection           | 5–40 m               | Backscatter amplitude analysis; can be combined across time to derive interferograms/change maps                                                                                                      |
| 2     | GOFF              | geocoded                          | 80 m                 | Cryosphere offset tracking                                                                                                                                                                            |
| 2     | **GCOV**          | geocoded                          | 10 / 20 / 80 m       | Radiometrically terrain-corrected backscatter (polarimetric covariance). Explicitly designed for **biomass, soil moisture, disturbance detection, inundation (flood) mapping, crop-area delineation** |
| 2     | **GUNW**          | geocoded                          | 20 or 80 m           | Unwrapped differential interferogram — ground displacement, map-ready                                                                                                                                 |
| 3     | SME2              | geocoded                          | 200 m (500 m Sahara) | Soil moisture, 3 algorithms                                                                                                                                                                           |

**GCOV and GUNW are the two products directly relevant to change detection and are already map-projected (no radar-geometry math needed on our side)** — this matters a lot for hackathon feasibility.

## 4. Current data availability (source: [Available NISAR Data](https://nisar-docs.asf.alaska.edu/availability-overview/), [ASF notice](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/), [Earthdata news](https://www.earthdata.nasa.gov/news/nisar-l-band-data-released-expanding-record-surface-changes))

- **Jan 2026**: first L1–L3 L-band products released (preview).
- **Feb 2026 "Beta" release**: full L1–L3 products for acquisitions 17 Oct 2025 – 20 Jan 2026. Pre-calibration quality; do not mix with Provisional data in one analysis.
- **20 Jul 2026 "Provisional" release**: fully calibrated L0B–L3 products, covering acquisitions from **17 Jun 2026 onward**, nearly global L-band land coverage. This is the dataset we should build against. Processing latency: 2–10 hrs (raw) / 36–72 hrs (L1–L3) after acquisition.
- **Known gap**: permanent instrument data gap **27 Jul – 10 Aug 2026** (avoid picking a "before/after" pair that straddles only this gap unless intentional).
- S-band (ISRO instrument) sample data (RSLC/GSLC/GCOV, Jan–Feb 2026) is separately hosted on ISRO's **Bhoonidhi** hub, not ASF. We will not rely on S-band for the MVP — L-band via ASF is simpler and better documented for a US/NASA-facing submission.
- Full science-phase record expected complete by **end of 2026**; a **validated reprocessing campaign (Q4 2026)** will later replace Provisional products with improved versions — worth a caveat in our limitations doc, not a blocker.

**Practical implication for our timeline**: by the Nov 2026 event, several months of real, calibrated, global L-band GCOV/GUNW granules will exist. A live before/after pair for almost any land location on Earth (subject to revisit cadence — see open question below) should be obtainable.

**Open question — revisit cadence**: the exact repeat-pass interval for a given point (12-day exact repeat orbit is NISAR's designed cycle) determines how many usable "before/after" pairs exist for Myanmar specifically between 17 Jun 2026 and the event. **UNVERIFIED — must check Vertex for actual Myanmar-area granule count before committing to a live-data flood/deformation story.**

## 5. Access tools

- **ASF Vertex** (`search.asf.alaska.edv`) — web GUI, draw AOI, filter by product/date, direct HTTPS download. Best for manual exploration and curating our demo fixtures.
- **NASA Earthdata Search** — alternative GUI, same CMR-backed catalog.
- **CMR Search API** (`cmr.earthdata.nasa.gov/search`) — the actual REST API behind both GUIs. This is what our backend should call programmatically (collection + granule search, bbox/temporal filters). Public collections require an Earthdata Login (EDL) token for data download, not for metadata search.
- **`asf_search` (Python package)** — ASF's official Python client wrapping Vertex/CMR search. Confirmed to exist and be the standard tool for scripted ASF searches; use this instead of hand-rolling CMR queries.
- **HyP3** (`hyp3-docs.asf.alaska.edu`) — ASF's on-demand cloud processing service (submit jobs via Vertex UI, Python SDK, or REST API) that turns raw SAR into ready-to-use InSAR products (e.g., unwrapped displacement, correlation) without us running ISCE/GDAL pipelines ourselves. **UNVERIFIED**: whether HyP3 already supports NISAR inputs specifically (historically Sentinel-1-focused); a 2026 Earthdata Forum thread titled "Will ASF HyP3 support NISAR?" suggests this was still being rolled out. If HyP3 does not yet support NISAR by build time, we fall back to downloading pre-made GUNW/GCOV granules directly (which are already processed to L2, so we don't need HyP3 for our MVP anyway — HyP3 mainly matters for on-demand pairs it hasn't already produced).

## 6. Format / access implications for architecture

- HDF5 granules can be large (per-scene L-band swaths cover ~100s of km); we will **not** ship raw HDF5 to the browser. We extract/reproject the specific bands/layers we need into **Cloud-Optimized GeoTIFF (COG)** server-side, then serve map tiles from those COGs. (Standard practice — confirmed by general geospatial tooling knowledge, GDAL/rasterio support HDF5 read + COG write.)
- GCOV/GUNW being already geocoded means our processing is "read HDF5 subdataset → reproject if needed → compute change metric → write COG/PNG tiles," not full SAR focusing — well within hackathon scope.

## Sources

- [NISAR Data Products — NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/products-overview/) (fetched 2026-09-18)
- [Available NISAR Data — NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/availability-overview/) (fetched 2026-09-18)
- [NISAR L-Band Data Now Publicly Available — ASF](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/)
- [NISAR L-Band Data Released, Expanding Record of Surface Changes — NASA Earthdata](https://www.earthdata.nasa.gov/news/nisar-l-band-data-released-expanding-record-surface-changes)
- [NISAR Mission Team releases over 100K new data products — NASA Earthdata](https://www.earthdata.nasa.gov/news/nisar-mission-team-releases-over-100k-new-data-products)
- [Finding NISAR Data with Vertex — NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/vertex/)
- [HyP3: ASF's On Demand Processing Platform](https://hyp3-docs.asf.alaska.edu/about/)
- [CMR Search API docs](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)
- [2026 NASA Space Apps Challenge](https://www.spaceappschallenge.org/2026/)
- [2025 "Through the Radar Looking Glass" challenge](https://www.spaceappschallenge.org/2025/challenges/through-the-radar-looking-glass-revealing-earth-processes-with-sar/)

## Outstanding verification tasks (do before Phase 10 vertical slice)

1. Get exact 2026 "Dancing with the SARs" challenge text from a team member's browser session.
2. In ASF Vertex, manually search GCOV + GUNW granules over a candidate Myanmar/South-Asia AOI for the Jun–Nov 2026 window; record actual granule count/dates.
3. Confirm whether HyP3 accepts NISAR inputs yet, or whether we only consume pre-built L2 granules.
4. Confirm EDL (Earthdata Login) account creation works for the team and note token flow for backend downloads.
