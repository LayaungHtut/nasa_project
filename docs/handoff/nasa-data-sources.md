**Data sources for Dancing with the SARs**

The active Hpakant modules use NISAR measurements from NASA's ASF DAAC, the archive linked as **ASF Data Search Vertex** in the [challenge resources](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/?tab=resources) supplied for this project.

| Challenge resource                                                | Use in this project                                                                                                                                                              |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [ASF Data Search Vertex](https://search.asf.alaska.edu/)          | The fetchers use ASF Search to discover NISAR products, then authenticated HTTP range reads from `nisar.asf.earthdatacloud.nasa.gov` to obtain the Hpakant study window.         |
| [NASA Earthdata Search](https://search.earthdata.nasa.gov/search) | NASA data discovery portal; Earthdata Login supplies authentication for protected archive downloads.                                                                             |
| [NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/)       | Product definitions and interpretation for [L2 GCOV backscatter](https://nisar-docs.asf.alaska.edu/gcov/) and [L2 GUNW interferograms](https://nisar-docs.asf.alaska.edu/gunw/). |

The app displays seven selected GCOV passes for surface change and 21 GUNW pairs for slope motion, with GCOV radar backdrops. They cover Hpakant, Myanmar, Track 062 descending, Frame 075. NASADEM_HGT v001 tile n25e096 from NASA LP DAAC supplies terrain elevation for slopes and the fitted elevation trend; it is an additional NASA dataset supporting the NISAR analysis. The individual granule IDs are available in each module's provenance panel.

**Verification performed at 2026-11-14T23:42:07.195320+00:00**

- All 42 unique granules referenced by the active records were found in the live ASF catalog. None were missing, and all download URLs belong to NASA's NISAR ASF Earthdata archive.
- A fresh read of the latest used GCOV window exactly matched its cached backscatter, mask, looks, coordinates and projection.
- A fresh read of the latest used GUNW window exactly matched its cached unwrapped phase, connected components, coherence, ionosphere screen, mask, coordinates and projection.
- The prior full verification rebuilt both scenario JSON records from the cached measurements and confirmed equality (34 Python tests passed).

The [machine-readable audit](nasa-data-source-audit.json) preserves canonical archive URLs, granule IDs, record hashes and per-array comparison results. The direct pixel comparison sampled one GCOV product and one GUNW product; it did not re-download every product. The catalog check covered every active granule.

The measured modules contain no simulated observations. The “How NISAR Sees It” diagrams illustrate radar physics. Surface-change patches and slope-motion candidates are derived estimates with uncertainty, not independently validated events. Motion is LOS-only, and a candidate is not a confirmed landslide.

The site serves processed records and images because a public browser cannot safely hold Earthdata credentials and raw granules are GB-sized. Refresh the inputs and outputs with `scripts/fetch_hpakant.py`, `scripts/fetch_hpakant_insar.py`, `scripts/build_hpakant.py` and `scripts/build_slope.py`, using private Earthdata authentication. Fetch failures are recorded; the workflow does not fabricate replacement measurements.
