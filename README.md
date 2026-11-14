# Dancing with the SARs - NISAR Earth Explorer

Team **YOUTHs**, Yangon - Prepared for the **2026 NASA Space Apps Challenge**

An interactive story of one monsoon rice season north of Yangon, told through **12 NASA-ISRO NISAR radar passes** (June 16 to November 7, 2026) over Hlawga Reservoir and the paddy fields around it. Watch the fields flood and green through the clouds, see how a land-cover map turned a two-date "water loss" puzzle into a rice-growth signal, and learn why a changed radar signal does not necessarily mean a flood.

**Headline finding:** a two-date comparison (Aug 27 vs Sep 8) flagged 4.517 km² of "apparent water loss" near the reservoir. Checked against the independent ESA WorldCover map, **92% of it lies on paddy fields and only 0.031 km² on the reservoir**. Across the season, the paddy fields are darkest on Aug 27 (flooded fields look like water) and then brighten by 2.0 dB relative to forest by Oct 14, as rice grows above the standing water. Tested patch by patch, 72% of paddy brightened by more than 1 dB, against 4% of forest, the control. The fields changed, not the reservoir. See the [time-series analysis](docs/science/time-series.md).

## What you can explore

- **Monsoon Series:** play all 12 NISAR passes on the map, and follow paddy, reservoir and built-up land pass by pass in a chart that removes the scene-wide brightness shift by comparing each surface with forest.
- **Compare Periods:** swipe between any two of the 12 passes, or pick a suggested period such as "Flooded → grown" (Aug 27 → Oct 14). A readout gives the days between them and how much paddy, reservoir and built-up land changed relative to forest, and warns when the two passes use different processing versions.
- **Land Cover:** paddy fields, the reservoir and built-up land from ESA WorldCover, with the two-date "apparent water loss" in white on top, so you can see that it falls on the fields, not the reservoir.
- **Field Timing:** a map of when each paddy field was darkest (most likely flooded, around planting) before its radar return rose, with the forest false-positive rate in the legend.
- A Sentinel-2 greenness (NDVI) chart on the same fields, showing honestly why optical data cannot confirm the radar rise in a cloudy monsoon (8 of 37 scenes usable).
- A synchronized before/after swipe map with one shared grayscale range for both dates (-15 to +5 dB for Hlawga), in HH or HV.
- An HH change map showing where the radar return brightened or darkened between the dates.
- An HH/HV polarization comparison with the products' own interference and noise metadata. In these provisional scenes HV fails our consistency checks, so classification uses HH only.
- Five competing physical explanations for the change, each with evidence for and against and the observation that would settle it, including a test against recorded wind and rain at both acquisition times.
- Baseline and repeat observations, acquisition dates in UTC, and two-scene playback.
- A separate candidate-change layer with downloadable GeoJSON and observation records.
- **Download analysis report:** one self-contained HTML file (about 0.5 MB, works offline, prints to PDF) with the findings, the season chart and table, the land-cover and field-timing maps, the competing explanations, independent checks, method, limits and sources. It is built from the same records as the app (`/api/events/<id>/report`), and only real observations get one.
- Processing parameters, source granule identifiers, heuristic score, and pipeline statistics.
- An independent Sentinel-2 check with dated optical overlays, agreement/disagreement counts, and downloadable evidence.
- An **Optical Evidence** swipe mode: choose either radar date and one of three Sentinel-2 images, with the acquisition-time gap displayed on the map.
- Click any of 46 candidate markers, or select one in **Explore candidate evidence**, to inspect its area, dates, reference classifications, and missing coverage.
- SAR physics explanations, a nine-step judge tour, and ideas for future NISAR applications in Myanmar.
- A deterministic, record-based explanation template. The current application does **not** call a live AI model.

## The real case study

| Item                            | Recorded value                                                           |
| ------------------------------- | ------------------------------------------------------------------------ |
| Location                        | Hlawga Reservoir, Yangon Region, Myanmar                                 |
| Acquisitions                    | 12 passes, June 16 to November 7, 2026; detailed pair Aug 27 and Sep 8   |
| Product                         | NISAR L2 GCOV, Track 40 / Frame 10, frequency A, HH intensity (HHHH)     |
| Study area                      | 196 km²; 10 m pixel spacing                                              |
| Processing                      | 3 x 3 Lee filtering; -9.54 dB threshold; minimum 8-pixel change clusters |
| New-inundation candidate        | 0.056 km², 556 pixels                                                    |
| Heuristic score                 | 0.639; not a statistical probability                                     |
| Apparent water loss             | 4.517 km² after cluster filtering                                        |
| Classified water before / after | 5.856 / 0.571 km² before change-cluster filtering                        |

**Interpretation remains uncertain.** The recorded sensitivity sweep shows that the candidate area changes substantially with threshold and filter settings. The larger apparent water loss lies almost entirely on paddy fields (ESA WorldCover), which points to the rice fields changing rather than the reservoir; no crop calendar or field survey has confirmed it. No independent ground truth confirms flooding or reservoir drawdown. Pixel spacing is not a claim of independent spatial resolution.

This case study can guide inspection and teach SAR interpretation. Confirm physical changes with independent imagery, reservoir records, and relevant weather observations before using them in decisions. Synthetic demonstrations are labeled explicitly and must not be presented as observations.

**Season check completed:** all 12 Track 40 / Frame 10 passes were analysed; the 10 not on disk were read remotely, fetching only the 14 km window (about 0.17% of each roughly 6 GB granule). Every surface brightens and darkens together from pass to pass, following recent rain (correlation 0.69), so the app compares each surface with forest. The Oct 26 and Nov 7 passes use newer processing (`NISAR_L2_GCOV_V1`) that reads about 2 dB darker everywhere; they are shown but not compared on the fixed threshold. A metadata comparison of the two versions shows identical processing flags, no noise correction in either, and an unchanged noise floor; the software release changed. The reservoir stays bright on every pass regardless of wind (correlation -0.02), but drops 5.4 dB relative to forest in the newer products while land moves under 0.7 dB, so part of that brightness is likely processing. See the [time-series analysis](docs/science/time-series.md).

**Independent optical check completed:** Sentinel-2 scenes within ±3 days provide no paired clear coverage over the candidates. In an exploratory ±7-day comparison (August 24 and September 13), 9 candidate cells change from optical land to water, 101 remain land, and 446 are unknown. The reference is coarser and temporally displaced; the water-change interpretation remains unconfirmed. See the [independent optical report](docs/science/independent-optical-validation.md) and [dated overlays](data/validation/yangon-track40-frame10/optical-comparison.png).

**Polarization check completed:** HV is brighter than HH on both dates and shifts 1.6 dB over unchanged land while HH shifts 0.1 dB. The product reports an HV interference likelihood of 23.0 on August 27 and no RFI mitigation. HH carries the surface signal here. The HH change map shows about 20% of the study area brightening by more than 1 dB, concentrated in surrounding paddy fields. See the [polarization analysis](docs/science/polarization-analysis.md).

**Weather check completed:** both acquisition mornings (05:32 Myanmar time) were near calm. Yangon airport reported 0 and at most 1 m/s, and ERA5 gives 2.1 m/s on both. Wind therefore does not explain why the reservoir was brighter on the second date, and the earlier "wind-roughened water" explanation is now weakly supported. The cause remains open. See the [weather check](docs/science/weather-check.md).

See the [scientific validation report](docs/science/real-data-validation.md), [methodology](docs/science/methodology.md), and [limitations](docs/science/limitations.md). The validation report records historical findings; its old frontend architecture description is superseded by the data flow below.

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

With the production preview running, verify the optical explorer in a second terminal:

```sh
node scripts/check_optical_explorer.mjs http://127.0.0.1:4173
```

This Playwright check covers the bundled geometry worker, candidate clicks, date gaps, swipe controls, mobile width, failed optical loads, and recovery to radar views. It deliberately disables the remote basemap to verify that local observations and evidence remain usable.

`npm test` runs the configured server unit suite. Browser interaction testing is separate. The application needs a server runtime with access to `data/processed/`, `data/fixtures/`, and `data/validation/`; configure the SvelteKit deployment adapter for your host and include those directories. No hosted deployment is configured here.

## Data flow and reproducibility

```text
NISAR GCOV HDF5 files
  -> AOI read and quality mask
  -> Lee filtering, dB conversion, thresholding, cluster filtering
  -> data/processed/<event-id>/{metadata.json,statistics.json,change.geojson,*.png}
  -> SvelteKit server loader and /api/events routes
  -> shared presentation and interactive map
```

The server reads processed outputs directly, overriding catalog fixtures. The real offline event imports the same metadata and statistics, and its geometry fallback uses the processed GeoJSON. Shared presentation functions generate timeline steps and explanatory text from these records. The separate Python API is optional; it is not required by the SvelteKit application.

To reproduce the pixel processing:

1. Install Python dependencies from `services/processing/requirements.txt` in a virtual environment.
2. Obtain the two granules named in `data/processed/yangon-track40-frame10/metadata.json` through ASF/Earthdata using your own credentials. Search/download helpers are in `scripts/`; never commit credentials or raw downloads.
3. Place the HDF5 files in `data/raw/` and run the exact real-mode command in the [validation report](docs/science/real-data-validation.md), under Audit finding 3, adding `--display-range-db -15 5`. It specifies the AOI, threshold and filter size. Re-running that command replaces the processed outputs for this event. Then run the polarimetry command in the [polarization analysis](docs/science/polarization-analysis.md#reproduce) to regenerate the HV previews, HH change map and `polarization.json`, and `python -m services.processing.timeseries --event-id yangon-track40-frame10` for the 12-pass season record (it reads the other passes remotely; see the [time-series analysis](docs/science/time-series.md)). `python -m services.processing.ndvi --event-id yangon-track40-frame10` regenerates the Sentinel-2 check and `python scripts/compare_processing_versions.py` the processing-version record.
4. Compare the regenerated metrics with the table above. Interpret changes in calibration or parameters explicitly rather than silently replacing the narrative.

Raw products total approximately 12 GB and are gitignored. The current app visualizes prepared, georeferenced PNG previews; it does not provide arbitrary worldwide processing, a tiled COG service, or validated operational flood mapping.

## Sources and attribution

- [ASF NISAR GCOV product guide](https://nisar-docs.asf.alaska.edu/gcov/)
- [NASA NISAR mission](https://science.nasa.gov/mission/nisar/)
- Radar observations: NASA/ISRO NISAR, distributed by ASF DAAC / NASA Earthdata.
- Land cover: ESA WorldCover 10 m 2021 v200 (© ESA WorldCover project, CC BY 4.0).
- Independent optical reference: modified Copernicus Sentinel data (2026), via Element 84 Earth Search; acquisition identifiers and source URLs are retained in `data/validation/`.
- Weather: ERA5 reanalysis via [Open-Meteo](https://open-meteo.com/) (CC BY 4.0); Yangon International Airport (VYYY) METAR reports via the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/). Raw responses are kept in `data/validation/yangon-track40-frame10/weather/`.
- Change detection and interpretation: Team YOUTHs.
- Basemap: OpenFreeMap, OpenMapTiles and OpenStreetMap contributors; attribution is displayed on the map.

## Sharing the project

Use the in-app downloads to share the analysis report, observation record, candidate polygons, and statistics. This project is released under the open-source [MIT License](LICENSE). Third-party data, basemaps and dependencies retain their own terms.
"# nasa_project" 
