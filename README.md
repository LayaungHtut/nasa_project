# Dancing with the SARs - NISAR Myanmar Surface Watch

Team **YOUTHs**, Yangon - Prepared for the **2026 NASA Space Apps Challenge**

A SAR monitoring and early-warning app for remote parts of Myanmar, where inspectors cannot go and monsoon cloud blinds optical satellites for weeks. It shows what NASA-ISRO NISAR's L-band radar (24 cm wavelength, 12-day repeat) and InSAR can watch through the clouds.

> **Data status.** Both modules run on **real NISAR granules** (Track 062 descending, Frame 075) from NASA's ASF DAAC: L2 GCOV backscatter for surface change, and L2 GUNW interferograms plus NASA's NASADEM elevation for slope motion. Every granule used and every pass excluded is listed in the app. There is no simulated data in the app.

## The two modules

### 1. Hpakant jade-mining district: observed surface change (real data)

Hpakant, Kachin State, is the world's largest jade-mining district. `scripts/fetch_hpakant.py` reads a 16 km window from every NISAR pass over it on ASF (range requests, a few MB per pass instead of several GB). `scripts/build_hpakant.py` then:

1. **Selects comparable passes:** one acquisition mode (QPDH, 20 m) and one processing version (P05023). Early-2026 passes over this frame have non-physical scene-wide offsets (median HV up to +1.8 dB), so a pass is used only if its scene median HV is within 1.5 dB of the latest pass.
2. **Filters and normalises:** a Lee filter on HV and HH, then a per-pass offset so stable vegetated ground matches the latest pass.
3. **Detects change against a two-pass baseline:**
   - **vegetation loss / new bare ground** is formerly vegetated ground whose HV drops by more than 3 dB;
   - **new open water** is HH below −18 dB.

   A change counts only when two consecutive passes agree, in patches of 1 ha or more.

4. **Estimates uncertainty:** the same rule run between the two baseline passes gives a false-alarm rate. GUNW coherence over the changed ground is reported as supporting evidence.

What it does **not** claim:

- **Mining:** it reports surface change _consistent with_ excavation, because mine-waste slides, landslides and moisture can look similar.
- **Legality:** no verified permit boundaries were available, so no legality claim is made.
- **Elevation loss:** no InSAR deformation is shown in this module, because dug ground decorrelates within 12 days.

### 2. Hpakant slopes: ground motion from InSAR (real data)

Hpakant's mine-waste slopes fail often, most deadly in the monsoon. `scripts/fetch_hpakant_insar.py` reads the same 16 km window from every NISAR L2 GUNW pair on ASF (unwrapped phase, connected components, coherence, ionosphere phase screen, 80 m) and NASADEM tile n25e096 from LP DAAC. `scripts/build_slope.py` then:

1. **Converts phase to line-of-sight (LOS) motion:** (unwrapped phase − ionosphere phase screen) × wavelength / 4π. Positive is toward the satellite. The sign follows ISCE3, the NISAR processor (`nisar/workflows/solid_earth_tides.py`). Pixels are kept where coherence ≥ 0.3 and the unwrapper assigned a connected component.
2. **Corrects and references each pair:** removes a planar ramp and a linear trend with elevation, fitted on ground under 20°, then ties the pair to flat (< 5° in NASADEM), usually coherent ground in the same connected component.
3. **Mean LOS rate** per pixel: measured motion divided by measured time, for pixels read on at least 60% of pairs. Gaps between pairs are not filled in. The scatter of the same rate over the flat reference ground is the noise figure.
4. **Candidates:** ground steeper than 20° moving faster than 3× that scatter, the same way on most pairs, in patches of at least 1.9 ha.

What it does **not** claim:

- **Confirmed landslides:** a moving steep slope is an indicator to check. Excavation, dumping and erosion move ground too.
- **Elevation or downslope speed:** LOS motion only. A slope sliding downhill can read as toward, away or near zero, depending on which way it faces.
- **Full atmospheric correction:** each pair has a planar ramp and a linear trend with NASADEM elevation removed (fitted on ground under 20°). Without that, rates tracked elevation at r = 0.71. Patchy monsoon water vapour is not removed; its noise is part of the reference scatter.

Both modules have a timeline with play, a before/after swipe, and InSAR coherence; the slope module adds the LOS rate layer and a pass-by-pass motion chart for each candidate.

## NASA resources the method follows

The radar measurements come from **ASF DAAC / NASA Earthdata**, linked by the [Dancing with the SARs challenge resources](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/?tab=resources). All 42 active granules were verified against the live ASF catalog, and fresh GCOV/GUNW study-window reads matched the cached measurements. See the [source audit](docs/handoff/nasa-data-sources.md) for archive URLs, verification scope and results.

- NISAR mission and products: L2 GCOV (geocoded backscatter) and L2 GUNW (geocoded unwrapped interferogram), distributed by ASF DAAC: <https://nisar-docs.asf.alaska.edu/>
- NASA Earthdata Search: <https://search.earthdata.nasa.gov/>
- ASF HyP3 on-demand RTC and InSAR processing: <https://hyp3-docs.asf.alaska.edu/>
- The SAR Handbook (NASA SERVIR, 2019): <https://ntrs.nasa.gov/citations/20190002563>

## How the real data are fetched

```bash
python scripts/verify_earthdata_auth.py   # Earthdata Login from .env (never printed)
python scripts/fetch_hpakant.py           # GCOV and GUNW coherence windows into data/raw/hpakant/ (gitignored)
python scripts/fetch_hpakant_insar.py     # GUNW unwrapped phase windows and the NASADEM tile
python scripts/build_hpakant.py           # src/lib/data/scenarios/hpakant-observed.json + images
python scripts/build_slope.py             # src/lib/data/scenarios/hpakant-slopes.json + images
```

The cache is not committed. Tests rebuild both records from it and check they match the committed JSON; they are skipped where the cache is absent.

The site serves the processed records and images, not the raw granules: a browser cannot hold Earthdata credentials safely, and each granule is several GB. Rerunning the scripts above refreshes everything from ASF.

## Run it

```bash
npm install
npm run dev
```

Open <http://127.0.0.1:5173/>. The server runs this checkout directly and uses a strict port: if 5173 is already occupied, it reports the conflict instead of switching ports.

The site is fully static: the scenario records are bundled, and the images are served from `static/`. It can be deployed to any static or Node host.

## Checks

```bash
npx svelte-check            # types
npx eslint src              # lint
npx vitest run --project server   # status logic, tour wording, record integrity
python -m pytest            # real-data regressions, sign convention, NISAR readers and filters
```

## Project layout

```text
src/
  routes/+page.svelte          the dashboard: module picker, map, timeline, analysis panel
  routes/about/                science and team page
  lib/components/map/          ScenarioMap (MapLibre, swipe compare, overlays), legend, slider
  lib/components/panels/       ObservedChangePanel, SlopeMotionPanel, MethodPanel
  lib/components/tour/         judge tour (steps generated from the records in lib/data/tour.ts)
  lib/components/timeline/     pass timeline with play and alert markers
  lib/data/scenarios.ts        observedStatus() and patch lookups: tested status logic
  lib/data/scenarios/*.json    generated scenario records (real data only)
static/scenarios/              generated radar, coherence and LOS-rate images
scripts/fetch_hpakant.py       reads the Hpakant GCOV and GUNW coherence windows on ASF
scripts/fetch_hpakant_insar.py reads the GUNW unwrapped-phase windows and NASADEM
scripts/build_hpakant.py       surface change: pass selection, change detection, uncertainty
scripts/build_slope.py         slope motion: LOS rate, reference scatter, candidates
scripts/sar_common.py          shared cleaning, colour ramps and outlines
services/processing/           NISAR GCOV readers (local and remote), Lee filter, geo, vectorizer
scripts/                       ASF search, download, product inspection, Earthdata login check
```

## Limits

- The NISAR products are provisional, so values may change when ASF reprocesses them. Neither module has been validated against field data, GNSS or optical imagery.
- Surface change: the baseline is pre-monsoon and later passes are in the monsoon, so local moisture change can mimic or hide change.
- Slope motion: only the planar and height-dependent parts of the atmosphere are removed, a broad centre-to-rim pattern remains unexplained, unwrapping errors inside a connected component are not detected, gaps between pairs are not measured, and dug or densely forested ground often cannot be read.
- InSAR line-of-sight motion is not vertical motion. A metres-deep pit decorrelates and gives no phase at all: coherence loss, not displacement, is the digging signal there.
- A permit check needs concession boundaries from the licensing authority, which are not public. Any real use needs calibration against field inspections and a person to verify every flag before any action.

## Credits

Radar parameters and methods: NASA-ISRO NISAR, ASF DAAC, NASA Earthdata, NASA SAR Handbook. Basemap: OpenFreeMap, OpenMapTiles, OpenStreetMap contributors. Built with SvelteKit, TypeScript, MapLibre GL JS, Tailwind CSS, NumPy, SciPy and scikit-image. Brand: NASA Space Apps Challenge 2026 guidelines and official logos.

MIT License.
