# RESOLVED — the −17 dB, region-wide "23.898 km² verified" result was scientifically invalid; do not resurrect it

**Status: RESOLVED 2026-09-18.** `scratch/generate_fixtures_ts.py`, `src/lib/data/fixtures.ts`, `data/fixtures/events.json`, and both frontend spec files now consistently use the corrected Hlawga Reservoir result (0.056 km², threshold −9.54 dB, confidence 0.639) under the id `yangon-track40-frame10`. All 31 backend tests and 15 frontend tests pass against this corrected state as of commit `ab4ecab`. Left below for the record and in case anyone regenerates fixtures from an older branch/stash.

Originally written 2026-09-18 after this result kept reappearing (in `data/processed/yangon-track40-frame10/` and in `data/fixtures/events.json`) faster than it could be corrected. If you are about to run `scratch/generate_fixtures_ts.py` or anything similar that bakes `yangon-track40-frame10` / "23.898 km²" / threshold "-17.0 dB" into `src/lib/data/fixtures.ts` — **stop and read this first**, then check whether your source data is stale.

## What's wrong with it

That result comes from running the change-detection pipeline with the _original, un-investigated_ default threshold (−17 dB) across the _entire_ Track 40/Frame 10 scene (a ~127 km × 144 km area spanning dense urban Yangon, forest, farmland, and coastline). Real backscatter distribution analysis (done by actually downloading and inspecting the real granules — see [docs/science/real-data-validation.md](../science/real-data-validation.md)) shows:

1. This is a **Provisional**-release NISAR product; its absolute radiometric calibration is not yet finalized. A literature threshold tuned for a fully-calibrated sensor (like Sentinel-1) does not port over directly — verified empirically: even a real, known lake (Hlawga Reservoir) required an empirically-derived **−9.54 dB** threshold to correctly isolate, not −17 dB.
2. A single threshold cannot be applied across a huge, land-cover-heterogeneous region — different land cover (urban, forest, farmland, water) has wildly different baseline backscatter. Applying the Hlawga-derived −9.54 dB threshold region-wide (as a deliberate test) produced **259 km²** of "new inundation" — obviously implausible, and rejected for exactly this reason. The −17 dB region-wide run has the same fundamental problem in the other direction (an even less-appropriate threshold for this scene) and its 23.898 km² figure has **not passed any of the Step 9 sanity checks** (not visually confirmed to concentrate near real water, not checked for urban/road false positives, generated with a `confidence` calculation that had a saturation bug — see below).
3. The `confidence: 1.0` on that result comes from a **known, already-fixed bug**: the original formula saturated to 1.0 on almost any real detection over ~200 pixels. 14,936 changed pixels saturates it trivially. It does not mean "100% certain." See the fix in `services/processing/change_detection.py` (2026-09-18 commit) — regenerating this result without pulling that fix reproduces the bug.

## What to use instead

`yangon-hlawga-track40-frame10` — real data, same granule pair (Track 40/Frame 10, 2026-08-27 & 2026-09-08), same download, but:

- a small, land-cover-homogeneous AOI (Hlawga Reservoir) where a threshold can be honestly justified
- threshold empirically derived and visually validated against the reservoir's known shape (see real-data-validation.md)
- the fixed confidence formula (result: 0.639, not saturated)
- explicitly reported as small and undramatic (0.056 km²) because that's what the real data actually shows

This is the event `data/fixtures/events.json` and the live API now serve. **If `scratch/generate_fixtures_ts.py` is regenerating `src/lib/data/fixtures.ts` from `data/processed/`, point it at `yangon-hlawga-track40-frame10`, not `yangon-track40-frame10`.**

## If the team wants a bigger, more visually dramatic real result

That's a legitimate ask — 0.056 km² is honest but not a dramatic demo. The right way to get one is **not** to lower standards on the existing AOI, but to repeat the same rigor (real distribution check, adaptive threshold, visual shape validation) somewhere more dynamic — e.g. a stretch of coastline or river mouth with real tidal/seasonal water extent change, using the same granule pair. I can do this next if asked — say so and I'll pick a candidate and run the same validation process documented in real-data-validation.md.

## Please don't re-run the naive version without reading this

Two copies of the naive result have already been generated and moved to `data/processed/_experiments/` (not served by the API) rather than deleted, specifically so this document has something concrete to point at. A third copy appearing means this note wasn't seen — if that keeps happening, flag it to the team directly rather than re-running the script again.
