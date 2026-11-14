"""Fetch the Hpakant study window from real NISAR granules on ASF DAAC.

Hpakant (Kachin State, Myanmar) is the world's largest jade-mining district.
NISAR Track 062 (descending), Frame 075 covers it. This script searches ASF
for that track and frame, then reads only the study window (16 x 16 km) from
each granule through authenticated HTTP range requests -- a full granule is
several GB, the window is a few MB per layer.

Layers cached per pass, in data/raw/hpakant/ (gitignored):
  GCOV  HHHH, HVHV (gamma-0 backscatter, linear), mask, numberOfLooks
  GUNW  wrapped-interferogram coherenceMagnitude (20 m) for each 12-day pair

Nothing is invented: if a granule cannot be read it is skipped and listed in
the manifest with the error. Credentials come from .env (never printed).

Run:
    python scripts/fetch_hpakant.py
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import asf_search as asf
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from services.processing.auth import get_authenticated_session  # noqa: E402
from services.processing.io_gcov import find_aoi_window, h5py  # noqa: E402  (pyfive when h5py is blocked)
from services.processing.remote_gcov import open_remote_granule  # noqa: E402

CACHE = REPO / "data" / "raw" / "hpakant"
TRACK, FRAME = 62, 75
EPSG = 32646  # UTM 46N, read from the granules' projection dataset
# Study window: the Hpakant-Lonkin mine belt along the Uru valley.
CENTER_E, CENTER_N = 833744.0, 2840898.0
HALF_M = 8000.0
SEARCH_POINT = "POINT(96.32 25.65)"

GCOV_LAYERS = ("HHHH", "HVHV", "mask", "numberOfLooks")
GCOV_GRID = "/science/LSAR/GCOV/grids/frequencyA"
GUNW_GRID = "/science/LSAR/GUNW/grids/frequencyA/wrappedInterferogram"


def search() -> list[dict]:
    rows = []
    for r in asf.geo_search(intersectsWith=SEARCH_POINT, dataset=asf.DATASET.NISAR, processingLevel=["GCOV", "GUNW"], maxResults=500):
        p = r.properties
        if p.get("pathNumber") != TRACK or p.get("frameNumber") != FRAME or not p["url"].endswith(".h5"):
            continue
        rows.append({"level": p["processingLevel"], "granule_id": p["fileID"], "start": p["startTime"], "url": p["url"]})
    return sorted(rows, key=lambda x: (x["level"], x["start"]))


@contextmanager
def opened(session, url: str):
    """Open a remote granule, retrying connection resets and expired signed URLs."""
    for attempt in range(5):
        try:
            cm = open_remote_granule(session, url, block_size=1024 * 1024)
            fobj = cm.__enter__()
            break
        except Exception as exc:  # noqa: BLE001 -- network errors come from several libraries
            if attempt == 4:
                raise
            print(f"    retry {attempt + 1} after {type(exc).__name__}", flush=True)
            time.sleep(20 * (attempt + 1))  # rides out short network and DNS drop-outs
    try:
        yield fobj
    finally:
        cm.__exit__(None, None, None)


def read_window(f, grid: str, layers: tuple[str, ...]) -> dict:
    g = f[grid]
    x = g["xCoordinates"][()]
    y = g["yCoordinates"][()]
    rows, cols = find_aoi_window(x, y, CENTER_E, CENTER_N, HALF_M)
    out = {"x": x[cols], "y": y[rows], "epsg": int(g["projection"][()]) if "projection" in g else -1}
    for name in layers:
        out[name.split("/")[-1]] = g[name][rows, cols]
    return out


def fetch(row: dict, session) -> str:
    path = CACHE / f"{row['granule_id']}.npz"
    if path.exists():
        return "cached"
    t0 = time.time()
    with opened(session, row["url"]) as fobj:
        f = h5py.File(fobj, "r")
        if row["level"] == "GCOV":
            data = read_window(f, GCOV_GRID, GCOV_LAYERS)
        else:
            data = read_window(f, GUNW_GRID, ("HH/coherenceMagnitude", "mask"))
    if data["epsg"] not in (EPSG, -1):
        raise RuntimeError(f"unexpected projection EPSG {data['epsg']}")
    tmp = path.with_name(path.stem + ".partial.npz")
    np.savez_compressed(tmp, **data)
    tmp.replace(path)  # only complete windows ever count as cached
    return f"{time.time() - t0:.0f} s"


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = search()
    print(f"ASF: {sum(r['level'] == 'GCOV' for r in rows)} GCOV and {sum(r['level'] == 'GUNW' for r in rows)} GUNW granules for track {TRACK} frame {FRAME}")
    session = get_authenticated_session()
    def attempt(row: dict) -> None:
        try:
            row["status"] = fetch(row, session)
        except Exception as exc:  # noqa: BLE001 -- record and keep going; the build only uses granules that read
            row["status"] = f"error: {type(exc).__name__}: {exc}"
        print(f"  {row['level']} {row['start'][:10]} {row['status'][:120]}", flush=True)

    for round_ in range(1, 4):  # failed granules get two more rounds; cached ones are skipped
        pending = [r for r in rows if not r.get("status") or r["status"].startswith("error")]
        if not pending:
            break
        print(f"round {round_}: {len(pending)} granules", flush=True)
        # One at a time: parallel reads triggered connection drops on this network.
        with ThreadPoolExecutor(max_workers=1) as pool:
            list(pool.map(attempt, pending))
    manifest = {
        "track": TRACK, "frame": FRAME, "epsg": EPSG, "center_utm": [CENTER_E, CENTER_N], "half_width_m": HALF_M,
        "granules": [{k: r[k] for k in ("level", "granule_id", "start", "status")} for r in rows],
    }
    (CACHE / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return 0 if all(not r["status"].startswith("error") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
