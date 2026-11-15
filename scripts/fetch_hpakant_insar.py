"""Fetch the inputs for the real Hpakant slope-motion (landslide) module.

1. NISAR GUNW unwrapped interferograms (80 m) for Track 062 Frame 075: unwrapped
   phase, connected components, coherence and the ionosphere phase screen, read
   for the same 16 x 16 km window as fetch_hpakant.py, plus the incidence angle
   at the window centre from the product's radar-grid metadata.
2. NASADEM (NASA/JPL, SRTM-based 1 arc-second DEM) tile n25e096 from LP DAAC,
   used only for terrain slope.

Same rules as fetch_hpakant.py: only what reads is cached; failures are listed.
Run:  python scripts/fetch_hpakant_insar.py
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import fetch_hpakant as fh  # noqa: E402
from services.processing.auth import get_authenticated_session  # noqa: E402

CACHE = fh.CACHE / "insar"
UNW = "/science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram"
LAYERS = ("HH/unwrappedPhase", "HH/connectedComponents", "HH/coherenceMagnitude", "HH/ionospherePhaseScreen", "mask")
NASADEM_URL = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/NASADEM_HGT.001/NASADEM_HGT_n25e096/NASADEM_HGT_n25e096.zip"


def incidence_deg(f) -> float:
    """Incidence angle at the window centre, from the GUNW radar-grid cube (nearest node, middle height layer)."""
    rg = f["/science/LSAR/GUNW/metadata/radarGrid"]
    x, y = rg["xCoordinates"][()], rg["yCoordinates"][()]
    i, j = int(np.abs(y - fh.CENTER_N).argmin()), int(np.abs(x - fh.CENTER_E).argmin())
    cube = rg["incidenceAngle"]
    return float(cube[cube.shape[0] // 2, i, j])


def fetch(row, session) -> str:
    path = CACHE / f"{row['granule_id']}.npz"
    if path.exists():
        return "cached"
    with fh.opened(session, row["url"]) as fobj:
        f = fh.h5py.File(fobj, "r")
        data = fh.read_window(f, UNW, LAYERS)
        # The 3-D radar-grid cube is slow to read remotely and the geometry is fixed per frame: read it once.
        data["incidence_deg"] = incidence_deg(f) if not any(CACHE.glob("*.npz")) else float(np.load(next(CACHE.glob("*.npz")))["incidence_deg"])
        data["wavelength_m"] = 299_792_458.0 / float(f["/science/LSAR/GUNW/grids/frequencyA/centerFrequency"][()])
    if data["epsg"] != fh.EPSG:
        raise RuntimeError(f"unexpected projection EPSG {data['epsg']}")
    tmp = path.with_name(path.stem + ".partial.npz")
    np.savez_compressed(tmp, **data)
    tmp.replace(path)
    return "ok"


def fetch_dem(session) -> str:
    path = fh.CACHE / "nasadem_n25e096.npy"
    if path.exists():
        return "cached"
    r = session.get(NASADEM_URL, timeout=600)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = next(n for n in z.namelist() if n.endswith(".hgt"))
        h = np.frombuffer(z.read(name), dtype=">i2").reshape(3601, 3601)  # rows from 26N down to 25N, cols 96E..97E
    np.save(path, h.astype(np.int16))
    return "ok"


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    session = get_authenticated_session()
    status = {}
    try:
        status["nasadem_n25e096"] = fetch_dem(session)
    except Exception as exc:  # noqa: BLE001
        status["nasadem_n25e096"] = f"error: {type(exc).__name__}: {exc}"
    print("NASADEM", status["nasadem_n25e096"], flush=True)
    rows = [r for r in fh.search() if r["level"] == "GUNW"]
    for round_ in range(3):
        for r in rows:
            if status.get(r["granule_id"], "error").startswith("error"):
                try:
                    status[r["granule_id"]] = fetch(r, session)
                except Exception as exc:  # noqa: BLE001
                    status[r["granule_id"]] = f"error: {type(exc).__name__}: {exc}"
                print(r["start"][:10], status[r["granule_id"]][:120], flush=True)
    (CACHE / "manifest.json").write_text(json.dumps({"nasadem_url": NASADEM_URL, "status": status}, indent=1), encoding="utf-8")
    return 0 if not any(v.startswith("error") for v in status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
