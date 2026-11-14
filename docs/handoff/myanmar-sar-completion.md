**Myanmar SAR modules — completion report, 15 November 2026**

The feature worktree is `D:/Nasa-project-feat`, on `feat/myanmar-sar-modules`. The separate `D:/Nasa-project` checkout is on `main` and contains pre-existing changes; those changes were not included in this feature commit. No push was performed.

Both monitoring modules now use real NASA-ISRO NISAR observations over Hpakant, Kachin State, Track 062 descending, Frame 075. The only illustrative content is the “How NISAR Sees It” physics explainer diagrams. The former simulated mining-compliance and landslide/river-diversion scenarios, images, panels and generator have been removed.

The surface-change module compares seven selected GCOV passes, identifies persistent vegetation loss and new open water, reports coherence and uncertainty, and supports inspecting individual patches. It describes changes consistent with excavation without claiming proof of mining or illegality.

The slope-motion module uses 21 GUNW pairs, including 12- and 24-day intervals, from 1 January through 16 October 2026. It subtracts the product ionosphere screen, converts phase to relative line-of-sight displacement, removes a fitted planar ramp and elevation trend, and references motion to coherent flat ground. NASADEM supplies terrain slopes. The current rebuild identifies one 5.12 ha candidate, with median slope 21.6 degrees and mean LOS rate +17.7 cm/year toward the satellite; reference scatter is 2.72 cm/year and rate coverage is 41.6%. This is an indicator to investigate, not a confirmed landslide.

The dashboard provides radar, before/after swipe and coherence views in both modules, with a cumulative mean LOS-rate layer for slope motion. The surface-change module explicitly explains why it does not offer deformation. Timelines support selection and playback; selecting the slope candidate zooms the map and exposes its motion chart. The judge tour has nine steps and uses values from the records.

**Files inspected and included in the change**

- Processing: `scripts/build_hpakant.py`, new `scripts/build_slope.py`, `scripts/fetch_hpakant_insar.py` and `scripts/sar_common.py`; removed `scripts/build_scenarios.py`.
- Records and outputs: new `src/lib/data/scenarios/hpakant-slopes.json` and all 63 PNGs under `static/scenarios/hpakant-slopes/`; removed both simulated JSON records and their image directories. `hpakant-observed.json` was inspected and verified against its rebuild.
- Map and analysis: `ScenarioMap.svelte`, `ScenarioLegend.svelte`, `MethodPanel.svelte`, `ObservedChangePanel.svelte`, new `SlopeMotionPanel.svelte`; removed `CompliancePanel.svelte` and `ForensicsPanel.svelte`.
- Interaction and data: `TimelineScrubber.svelte`, `JudgeTour.svelte`, `scenarios.ts`, `tour.ts`, `appState.svelte.ts`, and `types/scenario.ts`.
- Pages and documentation: `src/routes/+page.svelte`, `src/routes/+layout.svelte`, `src/routes/about/+page.svelte`, `README.md`, and this report.
- Tests: `scenarios.spec.ts`, `tour.spec.ts`, new `tests/test_slope.py`; removed the obsolete simulated-scenario tests. The slope wording assertion checks every occurrence of “confirmed landslide” for a preceding “not” or “not a”.

Additional inspection covered `AGENTS.md`, package and Vite configuration, Prettier configuration, `ComparisonSlider.svelte`, `TopNav.svelte`, `SarExplainerModal.svelte`, and `tests/test_hpakant.py`. During this completion pass the slope outputs were regenerated, the existing implementation was verified, and a browser test harness and screenshots were created under the ignored `D:/Nasa-project/scratch/` directory. No application-code correction was needed. The optional `.gitattributes` rule was not added because approval was not received; the current source passes Prettier.

**NASA datasets and provenance**

- [ASF NISAR L2 GCOV](https://nisar-docs.asf.alaska.edu/gcov/): calibrated geocoded backscatter, used for surface change and the radar backdrop. Every selected granule and excluded pass is recorded in the application.
- [ASF NISAR L2 GUNW](https://nisar-docs.asf.alaska.edu/gunw/): unwrapped phase, coherence, connected components and ionospheric phase screen. ASF documents that the ionospheric screen is supplied but not applied by default.
- [NASADEM_HGT v001, distributed by NASA LP DAAC](https://data.nasa.gov/dataset/nasadem-merged-dem-global-1-arc-second-v001): 1 arc-second elevation, used for slope and the fitted elevation trend. The fetcher uses [tile n25e096](https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/NASADEM_HGT.001/NASADEM_HGT_n25e096/NASADEM_HGT_n25e096.zip).
- [ISCE3 sign-convention source](https://github.com/isce-framework/isce3/blob/develop/python/packages/nisar/workflows/solid_earth_tides.py): the pipeline follows the reference-minus-secondary LOS correction and phase conversion to interpret positive displacement as toward the satellite. Its formula is `(unwrappedPhase - ionospherePhaseScreen) * wavelength / (4 * pi)`.

**Verification**

After `python scripts/build_slope.py`:

| Check | Outcome |
| --- | --- |
| `python -m pytest tests -q` | 34 passed; both real-data JSON records equal rebuilds from the cached inputs; no skipped tests |
| `npx svelte-check` | 0 errors, 0 warnings |
| `npx eslint src` | Clean |
| `npx prettier --check src` | All matched source files pass |
| `npx vitest run --project server` | 12 tests passed across 3 files |
| `git diff --check` | Clean |

The existing `.svelte-kit` directory was present. The handoff reported a clean Svelte autofixer run on changed components; no Svelte code was changed during this completion pass. Svelte testing documentation was consulted through the MCP CLI.

Headless Chromium passed at desktop 1440×1000 and phone 390×844. Both modules and all four layer controls were exercised, including the surface module's unavailable-deformation explanation. All seven surface nodes and all 21 slope nodes were selected; playback advanced correctly; the swipe divider responded to keyboard controls; all nine tour steps completed. Candidate selection changed the map scale from 2 km to 200 m on desktop and 5 km to 200 m on phone. Neither viewport had horizontal page overflow. All 77 referenced radar/coherence/LOS images decoded successfully in each viewport.

There were zero console errors, runtime errors, HTTP errors or non-cancellation network failures. MapLibre cancelled superseded image/tile requests during navigation and zoom (26 on desktop, 32 on phone); these `net::ERR_ABORTED` events are preserved separately in the results rather than described as zero request events. The external basemap also emitted a non-fatal missing `wood-pattern` sprite warning. Results and screenshots are in `D:/Nasa-project/scratch/sar-browser/`; the harness is `D:/Nasa-project/scratch/check-sar-browser.mjs`, launched with Vite by `run-sar-browser.sh` in one Bash process tree. The server was stopped after testing.

**Limits and refresh procedure**

Motion is relative LOS motion only; it is neither vertical elevation change nor downslope speed. Patchy tropospheric water vapour remains uncorrected. A broad centre-to-rim residual pattern remains unexplained and may include atmosphere or real motion. Two pairs have no usable phase (19 April–1 May and 24 July–17 August), excluding 36 days from measured time. Unwrapping errors within a connected component are not detected. Neither module has independent field, GNSS or optical validation, and the NISAR products are provisional. A permit-compliance check is impossible without verified official concession boundaries, so no legality claim is made.

The site serves processed JSON and georeferenced images. A browser cannot safely hold Earthdata credentials, and raw granules are GB-sized. The fetchers read the required windows into an ignored local cache; credentials and raw downloads are not committed. Refresh with authenticated Earthdata access by running:

```sh
python scripts/fetch_hpakant.py
python scripts/fetch_hpakant_insar.py
python scripts/build_hpakant.py
python scripts/build_slope.py
```

Then rerun the checks and review the resulting records and images. Cached-input rebuild tests skip on machines without that cache, so a passing cache-free run alone does not verify reproducibility.
