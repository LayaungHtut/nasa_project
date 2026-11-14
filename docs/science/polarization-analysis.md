# Polarization check and HH change map: Hlawga study area

**Outcome: HH carries the surface signal in this pair. HV fails two consistency checks and is shown for comparison only; it is not used to interpret the surface.**

The challenge asks which polarizations highlight surface change. Both granules are dual-polarization (`DHDH`) GCOV products containing `HHHH` and `HVHV`. This check compares the two channels over the same 14 km × 14 km AOI, with the same 3 × 3 Lee filter and −9.54 dB threshold as the served event. It does not change `metadata.json` results, `statistics.json`, the candidate polygons or the heuristic score. The HH water classes are recomputed with the pipeline's own code, and the run fails unless their pixel counts match `statistics.json` (45,172 apparent-loss and 556 candidate pixels; matched).

Record: [`polarization.json`](../../data/processed/yangon-track40-frame10/polarization.json). Code: `services/processing/polarimetry.py`, tests in `tests/test_polarimetry.py`.

## Channel statistics (speckle-filtered, whole AOI)

| Acquisition (UTC) | HH median | HV median | RFI likelihood HH / HV | Noise-equivalent backscatter HH / HV |
| ----------------- | --------: | --------: | ---------------------: | -----------------------------------: |
| Aug 27, 23:02:39  |  −4.28 dB |  −1.97 dB |           2.68 / 23.03 |                   −22.40 / −20.69 dB |
| Sep 8, 23:02:39   |  −4.16 dB |  −3.58 dB |            0.80 / 3.74 |                   −22.54 / −20.53 dB |

RFI likelihood and noise-equivalent backscatter are read from each product's `calibrationInformation/frequencyA` group; the noise values are averaged over the noise grid cells inside the AOI. Both products report `rfiMitigationApplied: False` and `noiseCorrectionApplied: False` (`processingInformation/parameters`). They are provisional products (`NISAR_L2_GCOV_PROVISIONAL_V1`).

## Why HV is not interpreted

Rule-based checks in `assess_hv()`:

1. **HV is brighter than HH on both dates.** Over natural surfaces, cross-polarized return is normally several dB below co-polarized return. Here HV exceeds HH by 2.3 dB (Aug 27) and 0.6 dB (Sep 8).
2. **HV is unstable over unchanged land.** Over the 1,898,254 pixels classified as land on both dates, HH shifts 0.10 dB between dates and HV shifts 1.60 dB.

Visually, HV shows a smooth west-to-east brightness ramp with wavy streaks on both dates and almost none of the field, road and urban structure visible in HH. The HH–HV pixel correlation is 0.38 (Aug 27) and 0.34 (Sep 8).

**Likely cause, not confirmed:** radio-frequency interference. The product's own HV interference score is 23.0 on Aug 27, versus 2.7 for HH, and no mitigation was applied. The Sep 8 HV score is lower (3.7), yet HV still fails both checks, so interference may not be the only factor. A future calibrated, RFI-mitigated product release should be checked before reusing HV here.

**What this teaches:** check a channel's quality before reading the surface from it. On clean scenes, HV is valuable for separating flooded vegetation and growing crops from open water, which HH alone cannot do.

## HH change map

`difference_hh.png` shows HH (repeat minus baseline, dB) over the AOI. Blue is darker on Sep 8, orange brighter. Changes within ±1 dB are transparent, and the drawn map is a 5 × 5 mean of the difference so residual speckle does not dominate. All statistics use the unsmoothed difference.

- Whole-AOI median change: +0.26 dB (5th–95th percentile: −1.88 to +2.65 dB).
- After display smoothing, 20.4% of the AOI brightened by more than 1 dB and 5.7% darkened by more than 1 dB.
- The brightening is concentrated in the rectangular paddy-field blocks west and north of the reservoir; the built-up corridor changes little.

## What the numbers say about the 4.517 km² apparent water loss

| Pixel class (HH, median) |    Aug 27 |    Sep 8 |
| ------------------------ | --------: | -------: |
| Apparent water loss      | −10.15 dB | −7.88 dB |
| Water on both dates      | −10.35 dB | −9.83 dB |
| Land on both dates       |  −4.17 dB | −4.07 dB |

- On the baseline date, reservoir pixels are already about 12 dB above the product's noise floor. Calm open water at L-band usually sits near that floor.
- The "lost" pixels brightened by a median 2.42 dB, enough to cross the −9.54 dB threshold, but they remain about 3.8 dB darker than stable land.

Investigation 2 in the [validation report](real-data-validation.md) ranked a wind-roughened water surface as the best-supported explanation for the apparent loss. **The [weather check](weather-check.md) does not support it:** both acquisition mornings were near calm, and the only rain fell before the first pass. The cause of the brightening, and of the water's high baseline level, remains open. Reservoir-level records have not been checked.

## Hypotheses shown in the app

`src/lib/data/drivers.ts` builds the app's "What could be driving the change?" panel from this record, `statistics.json`, the optical check and the weather check. Each hypothesis lists evidence for and against and an observation that would decide it:

| Hypothesis                                       | Explains                               | Support          |
| ------------------------------------------------ | -------------------------------------- | ---------------- |
| Something other than wind keeps the water bright | Reservoir bright even on calm mornings | Possible         |
| Water rose slightly at the reservoir edge        | 0.056 km² new-inundation candidate     | Possible         |
| Rice grew in the surrounding paddy fields        | 20% of the AOI brightened by over 1 dB | Possible         |
| Wind or rain roughened the reservoir surface     | 4.517 km² apparent water loss          | Weakly supported |
| The reservoir level actually fell                | 4.517 km² apparent water loss          | Weakly supported |

Before the weather check, the wind explanation was ranked best supported. It was downgraded by the recorded weather, not by editing the text.

The paddy hypothesis rests on timing (late August to September is the monsoon rice season in lower Myanmar) and on the known increase in L-band HH double-bounce scattering as rice stems grow above standing water. No crop calendar, field survey or optical vegetation index has been checked; rain-wetted soil could also raise backscatter.

## Preview display range

While building this check, the served HH previews were found to be 59% (Aug 27) and 63% (Sep 8) saturated white. The previous shared range of −25 to −5 dB sat below most of this scene, whose filtered HH spans about −10.3 to +5.3 dB (1st–99th percentile). The pipeline now records a shared `tiles.display_range_db`; this event uses −15 to +5 dB, which leaves about 1% of pixels saturated. Both dates still share one range. Only the preview PNGs changed: a re-run reproduced `statistics.json`, `change.geojson` and every `.npy` array byte for byte.

## Reproduce

After the pipeline command in the [validation report](real-data-validation.md) (add `--display-range-db -15 5`), run:

```sh
python -m services.processing.polarimetry \
  --baseline data/raw/NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001.h5 \
  --post-event data/raw/NISAR_L2_PR_GCOV_030_040_A_010_4005_DHDH_A_20260908T230239_20260908T230313_P05023_N_F_J_001.h5 \
  --baseline-granule-id NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001 \
  --post-event-granule-id NISAR_L2_PR_GCOV_030_040_A_010_4005_DHDH_A_20260908T230239_20260908T230313_P05023_N_F_J_001 \
  --aoi-lat 17.058 --aoi-lon 96.088 --aoi-half-width-km 7 \
  --threshold-db -9.54 --lee-filter-size 3 \
  --event-id yangon-track40-frame10
```
