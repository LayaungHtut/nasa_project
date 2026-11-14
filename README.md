# Dancing with the SARs - NISAR Myanmar Surface Watch

Team **YOUTHs**, Yangon - Prepared for the **2026 NASA Space Apps Challenge**

A SAR monitoring and early-warning app for remote parts of Myanmar, where inspectors cannot go and monsoon cloud blinds optical satellites for weeks. It shows what NASA-ISRO NISAR's L-band radar (24 cm wavelength, 12-day repeat) and InSAR can watch through the clouds.

> **Data status.** The **Hpakant** module runs on **real NISAR L2 GCOV and GUNW granules** (Track 062 descending, Frame 075) from NASA's ASF DAAC. Every granule used and every pass excluded is listed in the app with the reason. The **permit-check** and **landslide** modules are **simulated demos**: synthetic scenes with fictional sites, operators and permits, labelled SIMULATED on every screen.

## The three modules

### 0. Hpakant jade-mining district: observed surface change (real data)

Hpakant, Kachin State, is the world's largest jade-mining district. `scripts/fetch_hpakant.py` reads a 16 km window from every NISAR pass over it on ASF (range requests, a few MB per pass instead of several GB). `scripts/build_hpakant.py` then:

1. **Selects comparable passes:** one acquisition mode (QPDH, 20 m) and one processing version (P05023). Early-2026 passes over this frame have non-physical scene-wide offsets (median HV up to +1.8 dB), so a pass is used only if its scene median HV is within 1.5 dB of the latest pass.
2. **Filters and normalises:** a Lee filter on HV and HH, then a per-pass offset so stable vegetated ground matches the latest pass.
3. **Detects change against a two-pass baseline:**
   - **vegetation loss / new bare ground** is formerly vegetated ground whose HV drops by more than 3 dB;
   - **new open water** is HH below −18 dB.

   A change counts only when two consecutive passes agree, in patches of 1 ha or more.
4. **Estimates uncertainty:** the same rule run between the two baseline passes gives a false-alarm rate. GUNW coherence over the changed ground is reported as supporting evidence.

What it does **not** claim:
- **Mining:** it reports surface change *consistent with* excavation, because mine-waste slides, landslides and moisture can look similar.
- **Legality:** no verified permit boundaries were available, so no legality claim is made.
- **Elevation loss:** no InSAR deformation is shown, because dug ground decorrelates and the atmospheric corrections were not validated.

### 1. Permit check (simulated demo): digging beyond the permit

A fictional sand and gravel concession, MC-07, beside a river. The yellow polygon is the permitted boundary. Five passes, 12 days apart:

- **Radar pass:** HV backscatter. Forest canopy scatters radar many times (volume scattering) and stays bright. Cleared, dug ground does not, so a drop of more than 3 dB marks new clearing.
- **Detections:** new clearing inside the permit (blue) and outside it (orange), with a 20 m tolerance band for geolocation error.
- **InSAR coherence:** active digging destroys coherence between passes.
- **InSAR deformation:** line-of-sight phase shows the riverbank beside the pit moving away from the satellite (slumping) once digging leaves the permit.
- **Compliance Breach Alert:** fires when more than 0.5 ha is cleared beyond the band. The storyline goes from within the permit, to a watch (0.3 ha past the line on Day −24), to a breach (9.8 ha on Day −12, 25 ha and 350 m beyond the boundary by Day 0). A pass-by-pass table shows each step.

### 2. Landslide and river diversion (simulated demo): a forensic timeline

A fictional mountain valley in the Chin Hills. Four passes, 12 days apart:

- **Day −24:** InSAR measures a slope creeping 1.3 cm away from the satellite.
- **Day −12, early warning:** the slope fails. Return drops more than 3 dB (forest stripped to debris), coherence collapses to 0.06, and a lake starts ponding behind the debris dam.
- **Day 0, Automated Root-Cause Insight:** 3.8 km downstream, the river has moved up to 290 m. The app links the shift to the slide 12 days earlier and upstream on the same river.
- **Alternatives tested:** a basin-wide flood is ruled out, because water in the reach above the lake changed by at most 3%. Gradual meander migration is also ruled out (290 m in 12 days), and dredging is judged unlikely.

Water is dark because calm water reflects radar away (specular reflection), so each pass maps the river, and a moved channel appears as a dark line in a new place.

Both modules use a timeline with play, a before/after swipe against the baseline pass, and coherence and deformation layers. Each panel lists the method, the thresholds and the detector's accuracy against the simulation's own ground truth (mining: precision 100%, recall 98%; landslide: precision 100%, recall 72%).

## NASA resources the method follows

- NISAR mission and products: L2 GCOV (geocoded backscatter) and L2 GUNW (geocoded unwrapped interferogram), distributed by ASF DAAC: <https://nisar-docs.asf.alaska.edu/>
- NASA Earthdata Search: <https://search.earthdata.nasa.gov/>
- ASF HyP3 on-demand RTC and InSAR processing: <https://hyp3-docs.asf.alaska.edu/>
- The SAR Handbook (NASA SERVIR, 2019): <https://ntrs.nasa.gov/citations/20190002563>

With real data, the simulated images would be replaced by GCOV backscatter and GUNW coherence and displacement for the same area and dates. The app's data contract (`src/lib/types/scenario.ts`) would not change.

## How the real data are fetched

```bash
python scripts/verify_earthdata_auth.py   # Earthdata Login from .env (never printed)
python scripts/fetch_hpakant.py           # study windows into data/raw/hpakant/ (gitignored)
python scripts/build_hpakant.py           # src/lib/data/scenarios/hpakant-observed.json + images
```

The cache is not committed. A test rebuilds the record from it and checks it matches the committed JSON; the test is skipped where the cache is absent.

## How the simulated data are made

`scripts/build_scenarios.py` builds each scene:

1. Terrain, forest, rivers and the evolving change (pit growth, slope failure, lake, channel shift) on a UTM grid with NISAR GCOV pixel sizes (10 m and 20 m).
2. Backscatter for each pass with multiplicative gamma speckle (8 looks).
3. InSAR coherence and line-of-sight displacement for each 12-day pair, with atmospheric noise. Phase is masked where coherence is below 0.3.
4. Detection, reusing the project's NISAR processing code (`services/processing`):
   - a Lee speckle filter;
   - log-ratio change detection;
   - water thresholds;
   - coherence masks;
   - connected-component cleaning;
   - vectorization to GeoJSON.
5. Every metric is computed from those detections and written to `src/lib/data/scenarios/<id>.json`, with images in `static/scenarios/<id>/`.

The generator is seeded, so it's reproducible. A test rebuilds both scenarios and fails if the committed JSON differs from a rebuild.

```bash
python scripts/build_scenarios.py
```

## Run it

```bash
npm install
npm run dev
```

The site is fully static: the scenario records are bundled, and the images are served from `static/`. It can be deployed to any static or Node host.

## Checks

```bash
npx svelte-check            # types
npx eslint src              # lint
npx vitest run --project server   # alert and root-cause logic
python -m pytest            # scenario storyline, real-data regression, NISAR readers and filters
```

## Project layout

```text
src/
  routes/+page.svelte          the dashboard: module picker, map, timeline, analysis panel
  routes/about/                science and team page
  lib/components/map/          ScenarioMap (MapLibre, swipe compare, overlays), legend, slider
  lib/components/panels/       ObservedChangePanel (real data), CompliancePanel, ForensicsPanel, MethodPanel
  lib/components/tour/         judge tour (steps generated from the records in lib/data/tour.ts)
  lib/components/timeline/     pass timeline with play and alert markers
  lib/data/scenarios.ts        observedStatus(), compliance(), forensics(): tested status logic
  lib/data/scenarios/*.json    generated scenario records
static/scenarios/              generated radar, coherence and displacement images
scripts/fetch_hpakant.py       reads the Hpakant window from real NISAR granules on ASF
scripts/build_hpakant.py       real-data pass selection, change detection, uncertainty
scripts/build_scenarios.py     simulated demos: simulation and detection
services/processing/           NISAR GCOV readers (local and remote), Lee filter, geo, vectorizer
scripts/                       ASF search, download, product inspection, Earthdata login check
```

## Limits

- Hpakant: the products are provisional, so values may change when ASF reprocesses them. The baseline is pre-monsoon and later passes are in the monsoon, so local moisture change can mimic or hide change. The result has not been validated against field data or optical imagery.
- The demo scenes are simulated, so real NISAR scenes will be harder. Slope, soil moisture, crop cycles, layover and shadow in steep terrain all change backscatter, so thresholds must be calibrated on real data.
- InSAR line-of-sight motion is not vertical motion. A metres-deep pit decorrelates and gives no phase at all: coherence loss, not displacement, is the digging signal there.
- A compliance alert has legal weight. Real use needs permit boundaries from the licensing authority, calibration against field inspections, and a person to verify every alert before any action.

## Credits

Radar parameters and methods: NASA-ISRO NISAR, ASF DAAC, NASA Earthdata, NASA SAR Handbook. Basemap: OpenFreeMap, OpenMapTiles, OpenStreetMap contributors. Built with SvelteKit, TypeScript, MapLibre GL JS, Tailwind CSS, NumPy, SciPy and scikit-image. Brand: NASA Space Apps Challenge 2026 guidelines and official logos.

MIT License.
