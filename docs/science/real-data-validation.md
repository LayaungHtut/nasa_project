> **Update 2026-11-12:** the 12-pass [time-series analysis](time-series.md) places 92% of the 4.517 km² apparent water loss on paddy fields (ESA WorldCover) and 0.031 km² on the reservoir. The surface-roughness explanation for the asymmetry below is superseded by that finding.

# Real-Data Validation Report (Authoritative)

**Later independent check:** the [Sentinel-2 optical comparison](independent-optical-validation.md) supplements this historical processing audit with dated imagery, agreement/disagreement counts, cloud exclusions, and timing limits. It leaves the water-change interpretation unconfirmed.

Compiled 2026-09-18, revised same day after a full scientific audit. This is the authoritative scientific record for the currently-served real event `yangon-track40-frame10`. Every number below was re-derived from the actual raster arrays at the time of the audit (not copied from memory) — see "Reproducibility" for the exact command and byte-for-bit confirmation. Read alongside [nisar-research.md](../research/nisar-research.md), [methodology.md](methodology.md), and [limitations.md](limitations.md).

## Dataset

|                                                                   | Baseline                                                                                      | Post-event                                                                                    |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Granule ID                                                        | `NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001` | `NISAR_L2_PR_GCOV_030_040_A_010_4005_DHDH_A_20260908T230239_20260908T230313_P05023_N_F_J_001` |
| Acquisition (zeroDopplerStartTime, read from the file)            | 2026-08-27T23:02:39Z                                                                          | 2026-09-08T23:02:39Z                                                                          |
| File size (downloaded, byte-verified against ASF's reported size) | 5,955,911,680 bytes                                                                           | 5,968,494,592 bytes                                                                           |

- Collection: `NISAR_L2_GCOV_PROVISIONAL_V1`
- Track / Frame: 40 / 10, orbit pass Ascending, look direction Left
- Temporal separation: 12 days (one NISAR repeat cycle)
- Product level: L2 (geocoded), product type GCOV, product version `1.0.11`
- Both files downloaded via an authenticated `asf_search.ASFSession` (Earthdata Login, credentials in a local, gitignored `.env`), streamed to `data/raw/` (gitignored), and byte-size verified against ASF's reported `bytes` metadata before use.

## Real HDF5 structure (verified, not assumed)

`scripts/inspect_nisar_product.py` was run against the real baseline file. All 7 documented paths from `services/processing/io_gcov.py` were present exactly as specified — the documented GCOV schema (per `nisar-docs.asf.alaska.edu/gcov/`) matched the real file with zero corrections needed.

Observed (both dates, identical grid): `HHHH`/`HVHV` shape `(33192, 33912)` float32, units `"1"`, `_FillValue = NaN`; `mask` uint8 (0 = invalid, 1..N = valid subswath, 255 = outside acquisition extent); pixel spacing **10.0 / -10.0 m**; projection EPSG **32647** (WGS84 / UTM zone 47N). Full-scene extent ~339 km × 332 km — `HHHH` alone is ~4.5 GB in memory per date, so `io_gcov.read_gcov_layer_window()` reads only an AOI-sized hyperslab directly via h5py slicing.

## AOI selection: what we tried, what failed, what worked

1. **Central Yangon, on the Yangon River (16.77°N, 96.165°E, ±15 km)**: almost no low-backscatter pixels at any reasonable threshold. Rejected — not a bug, a real finding (this Provisional-calibration product doesn't show strong specular darkening over this tidal, current-roughened stretch of river).
2. **Sanity check: Hlawga Reservoir (17.06°N, 96.10°E)**, a known, real lake north of Yangon: substantial, spatially coherent low-backscatter population, visually validated (ASCII min-pooled render) against the reservoir's real branching shoreline shape.
3. **Final AOI**: 17.058°N / 96.088°E, half-width 7 km (14 km × 14 km, 1,960,000 px at 10 m). BBox (WGS84): `[96.0213, 16.9939, 96.1546, 17.1221]`, AOI area **196.0 km²**.

## Audit finding 1: speckle filter size — 3×3 is authoritative, not 5×5

**Code**: `services/processing/speckle.py::lee_filter(image, size=5)` — the function default and `services/processing/pipeline_flood.py::run_pipeline(..., lee_filter_size: int = 5)`'s parameter default are both **5**, matching `methodology.md`'s stated default. **This run did not use the default.**

**What was actually run** (verified by re-executing the exact command below against the still-present real `.h5` files and confirming byte-identical output): `--lee-filter-size 3`. The authoritative event record's `processing.speckle_filter_size` field (added during this audit — see below) now records **3** explicitly and machine-readably.

**Was 5×5 tested?** Yes, interactively, against this same AOI, before selecting 3×3: at 5×5, the test window had **0 pixels below −17 dB** despite 1,677 existing in the unfiltered data — the 5×5 box filter smeared narrow water features into their higher-backscatter surroundings. This comparison was done in an interactive session and is documented here in prose; it is **not** captured by an automated test or script, which is a real reproducibility gap (see below) — a future improvement would be a `scripts/compare_filter_sizes.py` that reproduces this comparison mechanically.

**Do the docs agree?**

- `methodology.md`: describes a generic "small window" for speckle filtering, doesn't hardcode 5×5 as a number in the AOI-specific sense — consistent, not contradicted, since it never claimed 5×5 was mandatory.
- `real-data-validation.md` (this file, both before and after this audit): correctly states 3×3 throughout.
- **API metadata**: before this audit, `processing.speckle_filter_size` **did not exist as a field at all** — the actual filter size used was not recorded anywhere machine-readable, only in this doc's prose and in shell history. **This was a genuine gap, now fixed**: `services/processing/pipeline_flood.py` was updated to always emit `processing.speckle_filter_size` in the event record, and `services/api/models.py`'s `Processing` model was updated to include it. The event was regenerated and confirmed to report `"speckle_filter_size": 3`.

**Verdict: PASS after fix.** Before the fix: the actual pipeline code was correct (3×3 was genuinely used) but the _API contract_ did not expose it, so "whether API metadata agrees" would have been FAIL. Now fixed and verified live via `GET /api/events/yangon-track40-frame10`.

## Audit finding 2: the 0.639 score is a heuristic, not a probability

**Exact formula**, `services/processing/change_detection.py::change_stats()`:

```
size_confidence = min(1.0, changed_pixels / 2000.0)
confidence = round(0.5 * valid_fraction + 0.5 * size_confidence, 3)
```

For this run: `valid_fraction = 1.0`, `changed_pixels = 556` → `size_confidence = 556/2000 = 0.278` → `confidence = 0.5*1.0 + 0.5*0.278 = 0.639`. Confirmed by direct re-computation.

**What it is**: a **deterministic heuristic score**, not a probability, not a statistically calibrated confidence interval, not an ML output. It's a weighted average of (a) data completeness (fraction of non-nodata pixels in the AOI) and (b) a cluster-size heuristic (small detected areas are more likely to be residual speckle than a real event). It contains no statistical model, no training data, and no calibration against ground truth.

**Terminology decision**: the API's JSON field is named `confidence` and is now relied upon by the frontend (`results.confidence`, `ChangeEvent.confidence` in `src/lib/types/api.ts`, multiple Svelte components and tests). Renaming this field outright would be a breaking change across an already-integrated, actively-developed frontend, with real risk of another cross-agent merge conflict (this happened once already this session over a different field and cost significant time to resolve). Instead, this audit adds a sibling field: **`results.confidence_type: "heuristic_detection_score"`**, machine-readable and unambiguous, alongside a duplicate, more honestly-named field in the new **`statistics.json`** audit-trail file: **`detection_score`** with an explicit **`detection_score_formula`** string. All prose surfaces (AI explanation text, `docs/ai/ai-strategy.md`, `docs/science/limitations.md`) already describe this as "our own heuristic, not a NASA-provided value, not a statistical probability" — that language is correct and is retained.

**Verdict: PASS on substance (correctly non-probabilistic, correctly documented in prose), CONDITIONAL on the literal field name** — `confidence` alone, out of context, still reads as a probability to someone who only looks at the JSON key. Fully mitigated by the new `confidence_type` field and `statistics.json`, not by a breaking rename. Recommend a full `detection_score` rename as a deliberate, coordinated future migration if the team wants it — not done unilaterally here.

## Audit finding 3: reproducibility — confirmed, with one gap

The full command was re-run against the same real `.h5` files during this audit:

```
python -m services.processing.pipeline_flood --mode real \
  --baseline data/raw/NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001.h5 \
  --post-event data/raw/NISAR_L2_PR_GCOV_030_040_A_010_4005_DHDH_A_20260908T230239_20260908T230313_P05023_N_F_J_001.h5 \
  --baseline-granule-id NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001 \
  --post-event-granule-id NISAR_L2_PR_GCOV_030_040_A_010_4005_DHDH_A_20260908T230239_20260908T230313_P05023_N_F_J_001 \
  --aoi-lat 17.058 --aoi-lon 96.088 --aoi-half-width-km 7 \
  --threshold-db -9.54 --lee-filter-size 3 \
  --location-name "Hlawga Reservoir, Yangon Region, Myanmar" \
  --event-id yangon-track40-frame10
```

Result: **byte-for-bit identical** `change_area_km2: 0.056`, `changed_pixels: 556`, `confidence: 0.639` on re-run. The pipeline is deterministic given the same inputs and CLI flags.

**New in this audit**: every run now also writes `data/processed/<event-id>/statistics.json`, a full audit trail computed directly from the arrays (never hand-entered):

```json
{
	"total_pixels": 1960000,
	"aoi_area_km2": 196.0,
	"pixel_area_m2": 100.0,
	"baseline_water_pixels": 58564,
	"baseline_water_area_km2": 5.856,
	"post_event_water_pixels": 5712,
	"post_event_water_area_km2": 0.571,
	"new_inundation_pixels": 556,
	"new_inundation_area_km2": 0.056,
	"water_loss_pixels": 45172,
	"water_loss_area_km2": 4.517,
	"valid_pixels": 1960000,
	"valid_fraction": 1.0,
	"threshold_db": -9.54,
	"min_cluster_pixels": 8,
	"lee_filter_size": 3,
	"detection_score": 0.639,
	"detection_score_formula": "0.5 * valid_fraction + 0.5 * min(1, new_inundation_pixels / 2000)"
}
```

**Trace, raw NISAR → frontend**: `data/raw/*.h5` → `io_gcov.read_gcov_layer_window()` → `speckle.lee_filter(size=3)` → `change_detection.{to_db,water_mask,new_inundation_mask}` → `pipeline_flood.run_pipeline()` writes `data/processed/yangon-track40-frame10/{metadata.json,statistics.json,change.geojson,*.png}` → **manually copied into** `data/fixtures/events.json` (this step was done by hand during this session, twice, and both times it drifted from the authoritative pipeline output until corrected — see Audit finding 5) → `services/api/main.py` serves both. **Separately**, the SvelteKit frontend's own `src/routes/api/events/**/+server.ts` routes serve a **third, independently-maintained copy** in `src/lib/data/fixtures.ts` — confirmed by reading those route files directly: they import `CURATED_EVENTS` from the TS fixtures file and never call the Python FastAPI service. The frontend's `src/lib/api/client.ts` calls relative `/api/...` paths, which resolve to the SvelteKit routes (same origin), not to `services/api/main.py` (a separate `uvicorn` process on port 8000) unless something is added to proxy one into the other — nothing currently does.

**Verdict: PASS for the Python pipeline itself (fully deterministic and now self-documenting via statistics.json). FAIL, as an architecture matter, for end-to-end automated reproducibility**: there are three independent copies of the same "authoritative" numbers (`data/processed/.../metadata.json`, `data/fixtures/events.json`, `src/lib/data/fixtures.ts`) that must currently be kept in sync **by hand**, and this is the direct root cause of the contamination incidents in Audit finding 5. This is the single most important structural finding of this audit. Recommended fix (not implemented here, since the brief for this audit was verification, not new feature work): either (a) have the SvelteKit routes fetch from the FastAPI service server-side, or (b) generate `src/lib/data/fixtures.ts` programmatically from `data/processed/*/metadata.json` as a build step instead of hand-editing it, so there is exactly one authoritative source.

## Audit finding 4: provenance

Every field currently shown for `yangon-track40-frame10` traces to: NASA/ISRO NISAR (real granule IDs, confirmed via `asf_search` against ASF's public catalog, listed in `data/catalog.json`) → ASF DAAC (`NISAR_L2_GCOV_PROVISIONAL_V1`, downloaded with authenticated Earthdata Login) → YOUTHs processing (`services/processing/pipeline_flood.py`, this document). This chain is intact **content-wise** in all three copies (Python output, `events.json`, `fixtures.ts`) as of this audit — confirmed identical numbers in all three. The process-level caveat in Audit finding 3 (three hand-synced copies) is a reproducibility/maintainability risk, not a current factual error.

**Verdict: PASS**, with the same structural caveat noted above.

## Audit finding 5: fixture contamination sweep

Searched the entire repository for `23.898`, `259`, `78%`/`0.78`, `-17`, and the three previously-fabricated event IDs (`bago-flood-2026`, `ayeyarwady-delta-2026`, `sagaing-fault-deformation`).

- **`23.898` / `259`**: zero remaining occurrences as live numeric values in any served event. `259 km²` appears only as prose in `fixtures.ts`'s `limitations` array, `real-data-validation.md`, and `URGENT-do-not-use-17db-region-wide.md`, correctly describing it as a **rejected, implausible experiment**, not a current result. The two actual over-detection outputs are preserved, unserved, under `data/processed/_experiments/`.
- **`-17.0` occurrences**: all remaining instances belong to the _separate, clearly-labeled_ `demo-yangon-fixture` event (`data_status: "SYNTHETIC_PLACEHOLDER"`), which has its own independent synthetic scene and legitimately uses a different threshold. Not contamination — a different, correctly-labeled record.
- **`bago-flood-2026`, `ayeyarwady-delta-2026`, `sagaing-fault-deformation`**: still present in `src/lib/data/fixtures.ts` (and referenced in `client.ts` and the geometry route), but each explicitly carries `data_status: 'SYNTHETIC_PLACEHOLDER'` and a title suffixed `(Scenario Fixture)`. These are **not** served by the Python `/api/events` (they don't exist in `data/fixtures/events.json`) — they exist only in the frontend's static fallback fixtures, for offline/demo storytelling, and are honestly labeled where they appear.
- **`78%` / `0.78`**: no remaining occurrence tied to the real event; the real event's confidence is `0.639` (63.9%) everywhere checked.

**Verdict: PASS.** No stale fabricated number currently reaches a UI surface unlabeled. The three scenario fixtures are legitimate synthetic content under the project's own rules (clearly marked, not claiming to be real) — not a violation, but worth the team re-confirming they want three fictional "scenario" events in a science-communication product before the final demo, independent of this audit.

## Audit finding 6: scientific language

- "New inundation candidate" is the term used in this document, in `services/processing/pipeline_flood.py`'s generated `limitations` list (now explicitly states: _"This is a new-inundation CANDIDATE, not a confirmed flood — no independent ground truth was used to verify it."_ — added during this audit), and in the AI explanation text (both `services/api/explain.py`'s template and the SvelteKit route's independent template). No surface checked claims "confirmed flooding."
- Limitations lists (Python-generated and `docs/science/limitations.md`) already cover: false positives (smooth non-water surfaces), false negatives (flooded vegetation / double-bounce), threshold sensitivity (explicitly demonstrated by the rejected 259 km² region-wide experiment), and now explicitly the lack of independent ground truth. Acquisition-geometry effects were previously implicit ("threshold tuned to this scene") but not explicit — **added this audit**: see Audit finding 7 below regarding the baseline/post-event water-extent asymmetry, which is itself evidence of geometry/roughness sensitivity.

**Verdict: PASS**, strengthened during this audit.

## Audit finding 7 / Investigation 2 (2026-09-18): the 4.517 km² water-extent asymmetry, fully investigated

While adding `statistics.json`, a significant asymmetry was found: **baseline water pixels = 58,564 (5.856 km²) vs. post-event water pixels = 5,712 (0.571 km²)** — the post-event date shows roughly **10× less** detected water than the baseline date, across the whole 196 km² AOI, dwarfing the 0.056 km² "new inundation" headline figure. This section documents a full, dedicated investigation into that asymmetry, run before allowing Hlawga Reservoir to remain the primary demonstration event. **No data or parameters were altered to make the numbers look better** — every check below either confirmed a control (baseline vs. post-event compatibility) or ran the existing pipeline code unmodified with different, pre-declared inputs.

### 1–2. Arithmetic and AOI/grid compatibility — CONFIRMED IDENTICAL

Re-read both dates directly from the real `.h5` files with `io_gcov.read_gcov_layer_window()` at the exact same center/half-width used to produce the served event:

- Shapes: `(1400, 1400)` both dates.
- `x_coords` / `y_coords`: **bit-for-bit identical** (`np.array_equal` = `True`) — same AOI window, same grid, by construction (both reads use the same center/half-width against the same-projection files).
- Projection: EPSG 32647 both dates, confirmed via `utm_zone_from_epsg` → `(47, 'N')` both.
- GCOV quality mask: **100% valid (value 1) on both dates, 1,960,000/1,960,000 pixels** — no nodata, no invalid-subswath pixels on either date in this AOI.
- NaN count: 0 on both dates.
- Polarization: HHHH requested and read successfully on both dates (this product's dual-pol set is HH/HV; HHHH is the co-pol diagonal covariance term used throughout this project).
- `numberOfLooks`: baseline mean 5.0072, post mean 5.0072 (matching to 4 decimal places). `rtcGammaToSigmaFactor`: baseline mean 0.71530, post mean 0.71530 (matching to 5 decimal places). Both `lookDirection: Left`, both `orbitPassDirection: Ascending` (different `absoluteOrbitNumber`, 5675 vs 5848, as expected for different passes).

**Conclusion**: AOI, grid, resolution, polarization, geolocation, and valid/nodata handling are all confirmed identical between dates. The near-identical `numberOfLooks`/`rtcGammaToSigmaFactor` values confirm essentially identical acquisition geometry and terrain correction — **this rules out geometry, incidence-angle, and terrain-correction differences as the cause of the asymmetry.**

### 3. Raw (unfiltered) backscatter distribution comparison

|           | Baseline (raw) | Post-event (raw) |
| --------- | -------------- | ---------------- |
| Mean dB   | −4.880         | −4.517           |
| Median dB | −5.052         | −4.728           |
| Std dB    | 3.771          | 3.376            |
| Min dB    | −19.099        | −18.963          |

Whole-AOI mean shift: **+0.363 dB** (post minus baseline) — small, consistent with ordinary pass-to-pass variability, **not** a large uniform calibration offset (a miscalibration large enough to explain a 10× water-area collapse would show as a multi-dB whole-scene shift; it does not).

Raw pixel counts below threshold, however, already show an asymmetry **before any filtering**: at −9.54 dB, baseline has 183,053 raw sub-threshold pixels vs. post's 93,889 — a **2×** difference, much smaller than the 10× seen after filtering. **This is the key clue**: filtering amplifies, but does not create, the asymmetry.

### 4. Spatial examination (not just whole-AOI stats)

Connected-component analysis of the raw (pre-filter) sub-threshold pixels at −9.54 dB:

|                                         | Baseline (raw) | Post-event (raw) |
| --------------------------------------- | -------------- | ---------------- |
| Total sub-threshold pixels              | 183,053        | 93,889           |
| Number of connected components          | 61,331         | 52,917           |
| **Largest single component**            | **2,127 px**   | **72 px**        |
| Fraction of pixels in largest component | 1.2%           | 0.1%             |
| Components of size 1 (isolated speckle) | 63.8%          | 70.4%            |

After the 3×3 Lee filter: baseline's largest component grows to 3,682 px (the filter successfully consolidates a real, spatially coherent water body); post-event's largest component only reaches 68 px — filtering cannot manufacture spatial coherence that isn't present in the raw data.

**This is the central finding**: baseline has a genuine, large, spatially coherent low-backscatter region (consistent with calm open water), while post-event's low-backscatter pixels — even though only ~2× fewer in raw count — are overwhelmingly fragmented into isolated single pixels and tiny clusters, not a coherent water body. A real, permanent lake does not physically fragment like this in 12 days; a **wind/current-roughened water surface**, which disrupts the specular reflection responsible for water's characteristic darkness at L-band without removing the water, produces exactly this signature: scattered, isolated dips below threshold rather than one clean dark patch.

### 5. Explanation ranking

- **Acquisition geometry**: ruled out (identical `numberOfLooks`, `rtcGammaToSigmaFactor`, look direction, pass direction; both ascending, same track/frame).
- **Calibration differences**: unlikely as the _primary_ cause — whole-scene mean shift is only +0.36 dB, far too small to explain a 10× water-area collapse; a calibration drift would also be expected to shift land pixels roughly as much as water pixels, which is not what's observed (the effect is concentrated in the low-backscatter tail).
- **Geolocation/alignment**: ruled out (bit-identical coordinate grids).
- **Threshold sensitivity**: contributes to the _apparent magnitude_ (see sensitivity sweep below) but not to the _existence_ of the asymmetry, which is present in raw, unfiltered data at every threshold tested.
- **Filtering**: amplifies the asymmetry (10× after filtering vs. 2× before) but does not create it — ruled out as the root cause, confirmed as a magnifying factor.
- **Vegetation effects**: not a likely primary driver for an open-water reservoir body specifically, though could contribute at the fringes.
- **Surface roughness / wind / waves**: **best-supported explanation** — directly predicted by, and consistent with, the fragmentation pattern found in section 4. This is a well-documented physical effect: L-band specular backscatter from water is highly sensitive to even modest wind-driven surface roughness, which can raise backscatter well above the calm-water baseline without the water body physically shrinking.
- **Actual reservoir level change**: cannot be fully ruled out without an independent data source (optical imagery, reservoir operator records — not available to this project), but is **not the best-supported explanation**: a genuine large drawdown would be expected to leave the _remaining_ water (the deepest part of the reservoir) as a smaller but still spatially coherent dark patch, not fragment it into near-total speckle (largest post-event component: 72 px = 0.0072 km², when the reservoir's real surface area is several km²).
- **Another processing artifact**: not identified; the effect is present in the rawest form of the data this project reads (linear backscatter straight from the HDF5, before any of this project's own processing).

### 6–7. Threshold and filter sensitivity sweep (both 3×3 and 5×5, not chosen to minimize the discrepancy)

| Filter  | Threshold (dB)     | New-inundation (km²) | Water loss (km²) | Baseline water (km²) | Post water (km²) |
| ------- | ------------------ | -------------------- | ---------------- | -------------------- | ---------------- |
| 3×3     | −12.0              | 0.000                | 0.020            | 0.076                | 0.000            |
| 3×3     | −11.0              | 0.000                | 0.369            | 0.644                | 0.006            |
| 3×3     | −10.0              | 0.004                | 2.302            | 3.207                | 0.163            |
| **3×3** | **−9.54 (served)** | **0.056**            | **4.517**        | **5.856**            | **0.571**        |
| 3×3     | −9.0               | 0.288                | 8.209            | 10.614               | 1.905            |
| 3×3     | −8.0               | 1.149                | 15.289           | 24.229               | 9.300            |
| 3×3     | −7.0               | 1.508                | 17.911           | 41.835               | 24.494           |
| 5×5     | −12.0              | 0.000                | 0.002            | 0.003                | 0.000            |
| 5×5     | −11.0              | 0.000                | 0.113            | 0.157                | 0.000            |
| 5×5     | −10.0              | 0.002                | 1.285            | 1.465                | 0.005            |
| 5×5     | −9.54              | 0.010                | 3.026            | 3.324                | 0.049            |
| 5×5     | −9.0               | 0.097                | 6.664            | 7.306                | 0.446            |
| 5×5     | −8.0               | 0.868                | 14.577           | 19.906               | 5.806            |
| 5×5     | −7.0               | 1.046                | 18.217           | 37.622               | 19.966           |

**The baseline > post-event water-area asymmetry holds at every threshold and both filter sizes tested** — it is not an artifact of the specific −9.54 dB / 3×3 choice; this was verified, not assumed, exactly per the instruction not to pick a threshold that minimizes the discrepancy (no threshold in this range eliminates or reverses it).

**The 0.056 km² "new inundation" figure is, however, highly threshold- and filter-sensitive**: it changes by roughly two orders of magnitude across the tested threshold range (0.000 to 1.508 km² for 3×3), and by ~5× between filter sizes at the same threshold (0.056 vs. 0.010 km² at −9.54 dB). **This specific number does not survive sensitivity analysis as a precise, robust quantity.**

### 8–9. Spatial stability of the 0.056 km² candidate

Measured the distance from each of the 556 served "new inundation" pixels to the nearest baseline-water pixel (the reservoir's own shoreline), using a Euclidean distance transform:

- 62.1% of new-inundation pixels are within 30 m of existing baseline water.
- **96.8%** are within 100 m of existing baseline water.
- 0% are more than 500 m from any baseline water.

**This is genuinely reassuring evidence**: the 556 pixels are not scattered randomly across the 196 km² AOI (which would suggest generic false positives from unrelated land cover) — they sit specifically at the reservoir's own edge, consistent with a real, small, edge-of-reservoir phenomenon rather than noise from elsewhere in the scene. This partially offsets the threshold-instability finding above: while the _magnitude_ of the number is not robust, its _spatial location_ is consistently coupled to the real water body across the one configuration tested.

### 10. Classification

- **(A) Likely processing artifact**: not well supported. AOI/grid/geometry/mask/calibration-factor checks all confirmed clean; the asymmetry is present in the rawest backscatter this project reads, before any of its own processing.
- **(B) Likely SAR observation artifact / acquisition-condition effect**: **best-supported classification for the 4.517 km² apparent water loss.** Ruled-in by the fragmentation pattern (section 4), ruled-in by identical geometry/calibration factors pointing away from a geometric or terrain-correction cause, and consistent with a well-known physical sensitivity of L-band water backscatter to surface roughness/wind.
- **(C) Plausible real surface-water change but insufficient evidence**: applies to the small 0.056 km² new-inundation figure specifically — spatially plausible (edge-coupled to the real reservoir) but not numerically robust under reasonable parameter perturbation, and not corroborated by an independent data source.
- **(D) Strong evidence of real water change**: not supported for either statistic. No independent ground truth (optical imagery, gauge/operator records) was available to confirm a genuine hydrological event, and the dominant explanation for the large asymmetry points to an observation-condition effect rather than a real water-level change.

**No conclusion is forced beyond what the evidence supports.** The large asymmetry is most likely explained by (B); the small new-inundation candidate remains (C) — plausible, spatially consistent with the real reservoir, but not confirmed and not numerically stable.

### Decision: keep or discard the 0.056 km² figure?

**Kept, unchanged, exactly as originally reported — not manipulated.** Per instruction, no parameter was chosen after the fact to make this number look better or to minimize the water-loss discrepancy; it remains the deterministic output of the specific, documented method (threshold −9.54 dB, 3×3 Lee filter) applied to this AOI. What changes is the **surrounding disclosure**: this document, and any future frontend copy, must state plainly that (a) a much larger apparent water-extent decrease exists in the same data and is most likely an acquisition-condition artifact, not a real change, and (b) the 0.056 km² figure itself is sensitive to threshold/filter choice by roughly two orders of magnitude and should be read as an illustrative point estimate from one specific, documented configuration — not a precise, parameter-independent measurement.

## Visual/spatial validation (Step 9 checklist, unchanged from original validation, re-confirmed)

1. Geographically plausible: yes, small fringe change at the edge of a real reservoir.
2. Concentrated near water: the 556 new-inundation pixels are dispersed, not one dramatic blob — consistent with edge fluctuation, not a dramatic flood signature.
3. Baseline mask alone reproduces the reservoir's real branching shoreline (visually validated).
4. False positives from roads/buildings: not independently cross-checked against a land-cover map — open gap.
5. Nodata artifacts: none (`valid_fraction = 1.0` both dates).
6. Dominated by speckle: 3×3 filter + 8-pixel cluster floor is a light touch; some fraction of the 556 pixels is plausibly residual speckle.
7. Threshold sensitivity: high — demonstrated twice now (the rejected 259 km² region-wide experiment, and the newly-found baseline/post-event asymmetry in Audit finding 7).

**Conclusion, restated**: this is a **new inundation candidate**, not a confirmed flood, not NASA-certified, not evidence of a named event. The 0.639 score is a heuristic, not a probability. The result is small, and a much larger (4.517 km²) apparent water-extent decrease exists in the same data, most likely reflecting acquisition-geometry/roughness sensitivity rather than a real drawdown — genuinely uncertain, and reported as such.

## Provenance chain (updated)

```
NASA/ISRO NISAR L2 GCOV, Track 40/Frame 10, 2026-08-27 & 2026-09-08
  (ASF DAAC, NISAR_L2_GCOV_PROVISIONAL_V1, downloaded via authenticated asf_search)
→ services/processing/io_gcov.read_gcov_layer_window()
→ services/processing/speckle.lee_filter(size=3)
→ services/processing/change_detection.{to_db, water_mask(threshold_db=-9.54), new_inundation_mask}
→ services/processing/vectorize.change_mask_to_geojson()
→ services/processing/pipeline_flood.run_pipeline()
    writes data/processed/yangon-track40-frame10/{metadata.json, statistics.json, change.geojson, *.png}
→ [MANUAL SYNC STEP -- see Audit finding 3] data/fixtures/events.json
→ services/api/main.py  (serves both; not currently called by the SvelteKit frontend)
→ [SEPARATE, INDEPENDENTLY-MAINTAINED COPY -- see Audit finding 3] src/lib/data/fixtures.ts
→ SvelteKit routes (src/routes/api/**) → frontend UI
```

## Audit summary table

| #   | Audit                               | Verdict                                                                                            |
| --- | ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| 1   | Filter size discrepancy             | PASS (after adding `speckle_filter_size` to the API)                                               |
| 2   | Confidence terminology              | PASS on substance / CONDITIONAL on field name (mitigated via `confidence_type`, not renamed)       |
| 3   | Reproducibility                     | PASS for the pipeline / FAIL as an architecture matter (three hand-synced copies of the same data) |
| 4   | Provenance                          | PASS (with the same structural caveat as #3)                                                       |
| 5   | Fixture contamination               | PASS (no unlabeled stale value reaches a UI surface)                                               |
| 6   | Scientific language                 | PASS (strengthened this audit)                                                                     |
| 7   | New finding: water-extent asymmetry | Disclosed, unresolved — recommend follow-up, not a pass/fail item                                  |

## What remains / next steps

- Resolve the three-copies-of-the-truth architecture (Audit finding 3) before adding more real events — it's the direct cause of every contamination incident so far.
- Confirm the surface-roughness explanation with an independent source (optical imagery for the same two dates, or Hlawga reservoir operator records) if one becomes available — the current classification (B for the asymmetry, C for the small candidate) is evidence-based but not proof.
- Cross-check the 556 new-inundation pixels against land cover to separate genuine change from residual speckle (open since the original validation).
- If/when the team wants a second, more visually dramatic real result, repeat this exact rigor (real distribution check, adaptive threshold, visual shape validation, statistics.json audit trail, threshold/filter sensitivity sweep) on a new AOI — do not lower the standard applied here.

## Should Hlawga Reservoir remain the primary demonstration event?

**Yes, with adjusted framing.** Every structural check (AOI, grid, geometry, calibration factors, valid-pixel handling) came back clean, and the investigation produced a genuinely interesting, well-evidenced, honestly-explainable scientific finding (L-band water backscatter's sensitivity to surface roughness) rather than a dead end or a hidden bug. This is arguably a _better_ teaching moment for a NASA-audience demo than a clean, dramatic flood would be: it demonstrates real scientific rigor — running a sensitivity sweep, catching a threshold-unstable number before presenting it as fact, and distinguishing an acquisition-condition artifact from a real hydrological signal. The demo's framing should shift from "we detected a small flood" to "here's what NISAR reveals, including how a naive read of the numbers would have been misleading, and how we caught that" — which is a more defensible and more interesting story under judge questioning than a bigger number would have been.
