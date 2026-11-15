# Scientific Methodology

## 1. Candidate use cases, scored

Scale 1 (weak) – 5 (strong). Based on findings in [nisar-research.md](../research/nisar-research.md).

| Use case                              | Product            | Data availability                                                                                                            | Sci. validity                                                                          | Ease of processing                                                                                                                                 | Compute cost                | Visualization                                                                           | AI potential                                                 | Storytelling                                                           | Uniqueness                                          |
| ------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- | --------------------------------------------------- |
| A. Flood / water-extent change        | GCOV (backscatter) | 5 — GCOV explicitly built for inundation mapping, global coverage                                                            | 5 — low backscatter over calm water is textbook, well-published SAR technique          | 5 — single-date or two-date threshold on amplitude, no phase unwrapping needed                                                                     | 5 — cheap (raster ops only) | 5 — before/after water mask is immediately legible to anyone                            | 4 — good "how much area, how many people affected" narration | 5 — directly relevant to Myanmar monsoon flooding, judges' home region | 3 — common SAR demo, but well-loved for good reason |
| B. Agriculture / field change         | GCOV               | 4                                                                                                                            | 4                                                                                      | 3 — needs multi-date backscatter/phenology baseline to mean anything                                                                               | 3                           | 3 — subtler visual signal                                                               | 3                                                            | 3                                                                      | 3                                                   |
| C. Deforestation / forest disturbance | GCOV               | 4                                                                                                                            | 4 — GCOV lists disturbance detection as a design use case                              | 3 — needs a stable forest baseline + threshold tuning to avoid false positives from moisture/wind                                                  | 3                           | 4                                                                                       | 4                                                            | 4 (regionally relevant — Southeast Asia deforestation)                 | 3                                                   |
| D. Wetland change                     | GCOV               | 3 — less certain of dense temporal stack near event                                                                          | 4                                                                                      | 3                                                                                                                                                  | 3                           | 3                                                                                       | 3                                                            | 3                                                                      | 3                                                   |
| E. Glacier/ice motion                 | GOFF/ROFF          | 2 — not our region, thin evidence of easy AOI selection                                                                      | 4                                                                                      | 2 — offset-tracking is more involved                                                                                                               | 2                           | 4 (visually striking)                                                                   | 3                                                            | 2 (not locally relevant to Yangon)                                     | 4                                                   |
| F. Earthquake/surface deformation     | GUNW               | 3 — depends entirely on whether a usable pre/post pair exists for a real 2026 event; NISAR's own record only starts mid-2026 | 5 — InSAR deformation is the flagship "wow" SAR capability                             | 2 — needs a real coherent interferogram pair, phase unwrapping already done for us in GUNW but still requires careful coherence/atmosphere caveats | 3                           | 5 (fringes / displacement maps are visually the most "this shows something invisible" ) | 4                                                            | 5 if tied to a real regional event                                     | 5                                                   |
| G. Landslide detection                | GUNW               | 2                                                                                                                            | 4                                                                                      | 2                                                                                                                                                  | 3                           | 4                                                                                       | 3                                                            | 3                                                                      | 4                                                   |
| H. Urban/land-surface change          | GCOV               | 4                                                                                                                            | 3 — harder to make scientifically crisp (many causes for backscatter change in cities) | 3                                                                                                                                                  | 3                           | 3                                                                                       | 3                                                            | 3                                                                      | 2                                                   |

## 2. Selection

**Primary: A — Flood / water-extent change detection using GCOV backscatter.**

Reasons: it is the use case GCOV was explicitly engineered for, requires no phase-unwrapping subtleties, is cheap and fast to process (meets our hackathon compute/time budget), produces an intuitive before/after visual that any judge or non-expert immediately understands, and is directly relevant to Myanmar's monsoon flood risk — giving the team a genuine local storytelling angle for a Yangon event. It also sidesteps NISAR's biggest current constraint (limited historical archive) least badly, since we only need _any_ two GCOV acquisitions that straddle a known flood event, not a long deformation time series.

**Secondary / stretch goal: F — Deformation via GUNW**, added only if:
(a) team capacity allows a second pipeline, and
(b) a genuine, real, verifiable displacement event with two coherent NISAR acquisitions can be found (per the outstanding verification tasks in the research doc).

We explicitly reject building the deformation story as the _only_ pillar of the submission, because its data dependency (a real event landing inside NISAR's short current archive with usable coherence) is the least controllable variable in this project. Flood detection works with any two cloud-free, water-relevant acquisitions we can find over any monsoon-affected AOI — much lower risk.

Do not attempt B, D, E, G, H for the MVP; they are documented here only to show the comparison was done, not skipped.

## 3. Flood/water-extent pipeline (primary)

```
GCOV granule (HDF5, geocoded, terrain-corrected backscatter, co-pol e.g. HH or VV)
  → read target polarization subdataset (rasterio/h5py)
  → reproject/crop to AOI (rasterio/pyproj — GCOV is already geocoded, so this is a crop + possible CRS check, not full ortho-rectification)
  → speckle filtering (Lee or boxcar filter, small window — SAR backscatter is inherently noisy; skipping this step produces salt-and-pepper false positives)
  → convert to dB (10·log10) for interpretable thresholding
  → water mask per date: threshold backscatter below an empirically chosen dB cutoff (water is a smooth surface → specular reflection → very low return, well below vegetation/soil/urban)
  → change mask = water_mask(post-event) AND NOT water_mask(baseline)  → "new inundation"
  → connected-component filtering: drop change regions below a minimum pixel-cluster size (removes speckle-driven single-pixel false positives)
  → compute: total new-inundation area (km²), bounding geometry, per-pixel confidence score
  → rasterize result to COG (uint8 classes: no-change / permanent-water / new-flood) + vectorize to GeoJSON polygons for the frontend
  → write structured JSON record (see AI strategy / API contract) describing the event
```

### Inputs

- Two (or more) GCOV granules covering the same AOI: one "baseline" (dry/normal conditions), one "post-event" (during/after a known flood).
- A manually curated AOI polygon (bounding box) — not user-arbitrary in the MVP; see [demo-data.md](../handoff/demo-data.md).

### Output

- `change_score` (0–1, fraction of AOI newly classified as water)
- `confidence` (derived from speckle-filter agreement / cluster size, not a black-box ML score)
- GeoJSON polygons of new-flood extent
- COG tiles of raw backscatter (before/after) for visual comparison

### Limitations (must be surfaced in UI, not hidden)

- **False positives**: any smooth, low-backscatter surface can be confused with water — flat bare soil, some paved surfaces, radar shadow. Our threshold is tuned per-AOI, not universal; do not claim this generalizes to an arbitrary new location without re-tuning.
- **False negatives**: flooded vegetation (forest, tall crops) often does NOT show the expected backscatter drop (can even increase, due to double-bounce) — we will not detect flooded-forest inundation with this simple threshold method, and must say so explicitly.
- **Speckle noise**: inherent to all SAR; mitigated but not eliminated by filtering; small/isolated "changes" below our cluster-size floor are deliberately discarded and should be described as such.
- **Temporal mismatch**: our "baseline" and "post-event" dates are whatever NISAR happened to acquire — not necessarily the true flood peak. We report acquisition dates prominently so nobody assumes precision we don't have.
- **Surface-roughness / wind sensitivity**: open water's characteristic low L-band backscatter comes from specular reflection off a smooth surface — wind or currents that roughen the surface can raise backscatter well above our threshold without the water actually disappearing. **A large apparent decrease in detected water between two dates is not, by itself, evidence the water is gone** — check spatial coherence (is the remaining/lost "water" one coherent patch, or scattered speckle?) before trusting either an increase or a decrease at face value.
- **Threshold/filter sensitivity of small results**: a "new inundation" figure derived from a threshold near the edge of the water/non-water separation can change by an order of magnitude or more with a ±1 dB threshold shift or a different speckle-filter window size. Small results (well under 1 km²) should be treated as order-of-magnitude estimates from one specific configuration, not precise, parameter-independent measurements, unless a sensitivity sweep has been run and shown the figure is stable.
- **This is not a NASA-certified flood product.** It's our own processing of NASA data. See [limitations.md](limitations.md) for exact language to use.

### Why not more ML here

A dB-threshold + speckle-filter + connected-component pipeline is standard, peer-reviewed SAR flood-mapping practice, fully explainable to a judge in one sentence, and auditable (we can show the exact threshold and why). An opaque ML classifier would add risk (overfitting to our two demo scenes, no training data of our own, harder to defend under judge questioning) without improving the actual demo. We reserve AI for the _language layer_ on top of these deterministic numbers — see [ai-strategy.md](../ai/ai-strategy.md).

## 4. Deformation pipeline (secondary/stretch, GUNW)

Only pursued if an appropriate real pair is confirmed available (research doc, outstanding task #2).

```
GUNW granule (already unwrapped, geocoded line-of-sight displacement, plus coherence layer)
  → crop to AOI
  → mask low-coherence pixels (coherence layer < threshold) — unwrapped phase is meaningless where coherence is poor (vegetation, water, large temporal decorrelation)
  → convert phase/displacement layer to cm of line-of-sight motion (per product metadata)
  → classify displacement magnitude into bands for visualization (not a detection algorithm — GUNW already did the hard SAR processing)
  → output: displacement raster (COG), coherence mask (COG), summary stats (max |displacement|, area with |displacement| > X cm)
```

Limitations to disclose: line-of-sight only (not true 3D motion), atmospheric artifacts are not separately corrected by us, low-coherence areas are masked (data gaps, not "no motion").

## 5. Non-goals

- No training of a custom deep learning model. No claim of "AI-detected wildfire/earthquake/flood" — the phenomenon label always comes from us pairing a known real-world event with the SAR evidence, never from a model inferring the event type from pixels alone.
