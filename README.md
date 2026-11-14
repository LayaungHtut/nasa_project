# Dancing with the SARs - NISAR Myanmar Surface Watch

Team **YOUTHs**, Yangon - Prepared for the **2026 NASA Space Apps Challenge**

A SAR monitoring and early-warning demo for remote parts of Myanmar, where inspectors cannot go and monsoon cloud blinds optical satellites for weeks. Two modules show what NASA-ISRO NISAR's L-band radar (24 cm wavelength, 12-day repeat) and InSAR can watch through the clouds.

> **Data status: simulated.** Both modules run on synthetic radar scenes built from NISAR mission parameters. They are not satellite observations. Sites, operators and permits are fictional, and locations are illustrative. Every screen is labelled **SIMULATED**. The detection is real code: every number in the app is measured from the simulated images, never typed in.

## The two modules

### 1. Mining compliance: digging beyond the permit

A fictional sand and gravel concession, MC-07, beside a river. The yellow polygon is the permitted boundary. Five passes, 12 days apart:

- **Radar pass:** HV backscatter. Forest canopy scatters radar many times (volume scattering) and stays bright. Cleared, dug ground does not, so a drop of more than 3 dB marks new clearing.
- **Detections:** new clearing inside the permit (blue) and outside it (orange), with a 20 m tolerance band for geolocation error.
- **InSAR coherence:** active digging destroys coherence between passes.
- **InSAR deformation:** line-of-sight phase shows the riverbank beside the pit moving away from the satellite (slumping) once digging leaves the permit.
- **Compliance Breach Alert:** fires when more than 0.5 ha is cleared beyond the band. The storyline goes from within the permit, to a watch (0.3 ha past the line on Day −24), to a breach (9.8 ha on Day −12, 25 ha and 350 m beyond the boundary by Day 0). A pass-by-pass table shows each step.

### 2. Landslide and river diversion: a forensic timeline

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
python -m pytest            # scenario storyline, regression, NISAR readers and filters
```

## Project layout

```text
src/
  routes/+page.svelte          the dashboard: module picker, map, timeline, analysis panel
  routes/about/                science and team page
  lib/components/map/          ScenarioMap (MapLibre, swipe compare, overlays), legend, slider
  lib/components/panels/       CompliancePanel, ForensicsPanel, MethodPanel, SAR explainer
  lib/components/timeline/     pass timeline with play and alert markers
  lib/data/scenarios.ts        compliance() and forensics(): alert levels and root cause, tested
  lib/data/scenarios/*.json    generated scenario records
static/scenarios/              generated radar, coherence and displacement images
scripts/build_scenarios.py     simulation and detection
services/processing/           NISAR GCOV readers (local and remote), Lee filter, geo, vectorizer
scripts/                       ASF search, download, product inspection, Earthdata login check
```

## Limits

- The scenes are simulated, so real NISAR scenes will be harder. Slope, soil moisture, crop cycles, layover and shadow in steep terrain all change backscatter, so thresholds must be calibrated on real data.
- InSAR line-of-sight motion is not vertical motion. A metres-deep pit decorrelates and gives no phase at all: coherence loss, not displacement, is the digging signal there.
- A compliance alert has legal weight. Real use needs permit boundaries from the licensing authority, calibration against field inspections, and a person to verify every alert before any action.

## Credits

Radar parameters and methods: NASA-ISRO NISAR, ASF DAAC, NASA Earthdata, NASA SAR Handbook. Basemap: OpenFreeMap, OpenMapTiles, OpenStreetMap contributors. Built with SvelteKit, TypeScript, MapLibre GL JS, Tailwind CSS, NumPy, SciPy and scikit-image. Brand: NASA Space Apps Challenge 2026 guidelines and official logos.

MIT License.
