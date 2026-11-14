# Conflict flag: `src/lib/data/fixtures.ts` presents fabricated events as verified

**Status: unresolved, needs a team decision before demo. Not fixed automatically by the backend team — this is frontend-owned code, flagged per the project's conflict-resolution process instead of being silently overwritten.**
**Status: RESOLVED (2026-09-18). Adopted Recommendation: `src/lib/types/api.ts` and `src/lib/data/fixtures.ts` now strictly implement `data_status: "SYNTHETIC_PLACEHOLDER"` on all demonstration events. The primary event is now `demo-yangon-fixture`, produced by `services/processing/pipeline_flood.py`, referencing the real candidate granules for Yangon (Track 40 / Frame 10) confirmed in `data/catalog.json`. The UI visibly surfaces the data status and pending EDL credentials.**

## What was found (2026-09-18)

`src/lib/data/fixtures.ts` (written by Antigravity, the frontend agent) defines three `ChangeEvent` records — `bago-flood-2026`, `ayeyarwady-delta-2026`, `sagaing-fault-deformation` — with a file-header comment stating:

> "Curated NISAR Change Events ... All granule IDs, dates, coordinates, and limitations are scientifically grounded."

None of these three events were produced by any real processing run. Specifically:

1. **Granule IDs are invented, not real.** Compare `NISAR_L2_PR_GCOV_001_024_A_084_2000_HH_20260620T234500_20260620T234530_P01101_F_N_001` (fixtures.ts) against a real one confirmed via `asf_search` in [data/catalog.json](../../data/catalog.json): `NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001`. The real naming pattern encodes cycle/track/frame/polarization-set (`029_040_A_010_4005_DHDH`) and a real CRID (`P05023`) that the fabricated IDs don't match — they read as plausible-looking guesses, not granules that exist in ASF's catalog.
2. **The numbers were hand-authored, not computed.** `change_area_km2: 42.7`, `confidence: 0.78`, the GeoJSON flood polygons with specific meander shapes — none of these came from `services/processing`'s pipeline (or any pipeline). They're narratively plausible, but there is no computation behind them.
3. **The location/dates don't match our verified real candidates.** Our actual, `asf_search`-confirmed Yangon-covering repeat-pass pair is 2026-08-27 / 2026-09-08 (see `data/catalog.json`, candidate `yangon-track40-frame10`). Antigravity's Bago event uses 2026-06-20 / 2026-08-14, and Ayeyarwady uses 2026-05-18 / 2026-07-22, at track/frame numbers I did not verify exist.
4. **This is the exact failure mode the project's own docs exist to prevent.** See [docs/science/limitations.md](../science/limitations.md) ("we must NOT claim... that this method has been validated") and [docs/handoff/demo-data.md](demo-data.md) ("curated" means pre-computed from real data and checked in, never synthetic pretending to be real; any placeholder must be obviously marked, e.g. `"status": "PLACEHOLDER_DO_NOT_DEMO"`).

To be fair to Antigravity: nothing here suggests bad faith — this reads like a frontend agent building a rich, demo-ready UI ahead of the real pipeline being available, exactly as `demo-data.md` anticipated might happen ("If a fixture's numbers are ever placeholder/synthetic during early development, it must be obviously marked"). The content is well-constructed and would make a great demo. The problem is only that it is not marked, and the header comment actively claims the opposite of what's true.

## What the backend actually has, for comparison

- Real, `asf_search`-verified granule IDs, dates, and a Yangon-covering AOI: [data/catalog.json](../../data/catalog.json).
- One event produced by an actual, tested, deterministic pipeline run (`services/processing/pipeline_flood.py`) on a clearly synthetic input scene, correctly labeled `"data_status": "SYNTHETIC_PLACEHOLDER"`: `data/fixtures/events.json` / `GET /api/events` from `services/api`.
- The `data_status` field (`"REAL" | "SYNTHETIC_PLACEHOLDER"`) added to the API contract specifically so a not-yet-real event can be displayed without misrepresenting it — see [docs/api/api-contract.md](../api/api-contract.md) and [docs/handoff/frontend-contract.md](frontend-contract.md).

## Recommended resolution (not yet implemented — frontend team's call)

Pick one:

1. **Best for the actual demo**: swap `fixtures.ts` to consume the real backend (`services/api`) instead of a local TS fixture, so the frontend always reflects `data_status` honestly and there's only one source of truth. The API is running and documented with real examples in `frontend-contract.md`.
2. **If keeping local TS fixtures for offline frontend dev**: add `data_status: "SYNTHETIC_PLACEHOLDER"` to all three events, replace the granule IDs with an obvious placeholder pattern (e.g. prefixed `SYNTHETIC_FIXTURE_...` as `services/processing/fixtures.py` does), and delete or rewrite the "scientifically grounded"/"Verified" header comment. The story content (headline, radar_insight, quote) can stay — it's good writing — but it needs to be clearly labeled as an illustrative scenario, not a completed analysis, until real data backs it.
3. If the team wants to actually pursue the Bago River / Ayeyarwady Delta locations for real (they're reasonable choices), I can run `scripts/search_nisar_myanmar.py`-style queries against those specific AOIs to check what real NISAR coverage actually exists there, the same way I did for Yangon — say the word and I'll do it next.

Whichever path is chosen, please update this file's "Status" line at the top once resolved, so it doesn't linger as a stale warning.
