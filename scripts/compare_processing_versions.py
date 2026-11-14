"""Record what differs between the two NISAR GCOV processing versions in the season.

The season mixes PROVISIONAL (P05023) and V1 (P05036) products. Absolute backscatter
shifts by about 2 dB between them, and more over the reservoir. This reads the
metadata of the last provisional and the first V1 pass and saves what changed, so
the shift is documented rather than guessed at.

    python scripts/compare_processing_versions.py --event-id yangon-track40-frame10
"""

import argparse
import difflib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.processing.io_gcov import h5py  # noqa: E402
from services.processing.polarimetry import CALIBRATION_TMPL, PARAMETERS_PATH  # noqa: E402
from services.processing.remote_gcov import open_remote_granule  # noqa: E402
from services.processing.timeseries import CACHE_DIR, _session, track_granules  # noqa: E402

IDENT = "science/LSAR/identification"
_text = lambda v: v.decode() if isinstance(v, bytes) else str(v)


def describe(g: dict, aoi: tuple[float, float, float, float]) -> dict:
    x0, x1, y0, y1 = aoi
    with open_remote_granule(_session(), g["url"]) as fo, h5py.File(fo, "r") as f:
        p, cal, ident = f[PARAMETERS_PATH], f[CALIBRATION_TMPL.format(freq="A")], f[IDENT]
        neb = cal["noiseEquivalentBackscatter"]
        cols = (neb["xCoordinates"][()] >= x0) & (neb["xCoordinates"][()] <= x1)
        rows = (neb["yCoordinates"][()] >= y0) & (neb["yCoordinates"][()] <= y1)
        hh = neb["HH"][()][np.ix_(rows, cols)]
        return {
            "date": g["date"],
            "granule_id": g["granule_id"],
            "product_version": _text(ident["productVersion"][()]),
            "product_doi": _text(ident["productDoi"][()]),
            "product_specification_version": _text(ident["productSpecificationVersion"][()]),
            "flags": {k: _text(p[k][()]) for k in sorted(p.keys()) if k.endswith("Applied")},
            "aoi_noise_equivalent_backscatter_hh_db": round(float(10 * np.log10(np.nanmean(hh))), 2) if hh.size else None,
            "rfi_likelihood": {pol: round(float(cal[f"{pol}/rfiLikelihood"][()]), 3) for pol in ("HH", "HV")},
            # The SDS job directory names the processing software release that made the product.
            "software_release": next(iter(re.findall(r"SCIFLO_GCOV__(.+?)-gcov_", _text(p["runConfigurationContents"][()]))), None),
            "_runconfig": _text(p["runConfigurationContents"][()]).splitlines(),
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-id", default="yangon-track40-frame10")
    args = ap.parse_args()
    ts = json.loads((ROOT / "data/processed" / args.event_id / "timeseries.json").read_text(encoding="utf-8"))
    crids = [d["processing_crid"] for d in ts["dates"]]
    last_old = max(i for i, c in enumerate(crids) if c == crids[0])
    pair = [ts["dates"][last_old]["date"], ts["dates"][last_old + 1]["date"]]
    meta = json.loads((ROOT / "data/processed" / args.event_id / "metadata.json").read_text(encoding="utf-8"))
    lon, lat = meta["location"]["center"]
    granules = {g["date"]: g for g in track_granules(lat, lon, ts["track"], ts["frame"])}
    # The analysed window's UTM bounds, from the cached read of the first compared pass.
    z = np.load(CACHE_DIR / f"{granules[pair[0]]['granule_id']}_A_HHHH.npz")
    aoi = (float(z["x"].min()), float(z["x"].max()), float(z["y"].min()), float(z["y"].max()))
    a, b = (describe(granules[d], aoi) for d in pair)
    diff = [
        line
        for line in difflib.unified_diff(a.pop("_runconfig"), b.pop("_runconfig"), lineterm="", n=0)
        if not line.startswith(("---", "+++", "@@")) and "Time}" not in line and "_P050" not in line and "/data/work/" not in line
    ]
    rel = lambda d, cls: next(x for x in ts["dates"] if x["date"] == d)["relative_to_forest_db"][cls]
    record = {
        "event_id": args.event_id,
        "compared": [a, b],
        "flags_that_differ": {k: [a["flags"][k], b["flags"].get(k)] for k in a["flags"] if a["flags"][k] != b["flags"].get(k)},
        "runconfig_lines_that_differ": [line.strip() for line in diff if line.strip("+- ")],
        "forest_relative_db_change": {
            cls: round(rel(pair[1], cls) - rel(pair[0], cls), 2) for cls in ("cropland", "built_up", "permanent_water")
        },
        "software_release_changed": a["software_release"] != b["software_release"],
        "note": "Neither version applies noise correction and the noise floor is unchanged, so the shift is not noise removal. The processing software release changed; the GCOV run configurations differ only in DEM version and ionosphere options. Which upstream change causes the shift is not recorded in the product.",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    assert not record["flags_that_differ"], record["flags_that_differ"]  # the note above relies on this
    out = ROOT / "data/validation" / args.event_id / "processing-versions.json"
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "compared"}, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
