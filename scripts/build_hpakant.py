"""Surface-change workflow on REAL NISAR data over the Hpakant jade-mining district.

Input: the study windows cached by scripts/fetch_hpakant.py (real NISAR L2
GCOV and GUNW granules, Track 062 descending, Frame 075, from ASF DAAC).
Output: src/lib/data/scenarios/hpakant-observed.json and images in
static/scenarios/hpakant-observed/.

Steps, each recorded in the output so the app can show it:
1. Pass selection. Only one acquisition mode (QPDH, 20 m) and one processing
   version (CRID P05023), so resolution and calibration match. Early-2026
   passes over this frame have non-physical scene-wide offsets (median HV up
   to +1.8 dB), so a pass is kept only if its scene median HV is within
   CALIBRATION_TOL_DB of the latest pass, in an unbroken run back from it.
   Every excluded pass is listed with its reason.
2. Each pass: Lee filter, then a per-pass offset so that persistently
   vegetated reference pixels match the latest pass (removes residual
   calibration and moisture offsets; it cannot remove local moisture change).
3. Change against a baseline composite (mean of the first two kept passes):
   - vegetation loss / new bare ground: formerly vegetated (HV within 3 dB
     of the reference) and HV down by more than DROP_DB;
   - new open water: HH below WATER_DB where it was not before.
   A change counts only when it appears on two consecutive passes.
4. Uncertainty: the same rule applied between the two baseline passes, where
   little real change is expected, gives a false-alarm rate. GUNW coherence
   over the changed ground versus the reference is reported as supporting
   evidence, not as proof.

The result is "surface change consistent with excavation or clearing". It is
not proof of mining and says nothing about legality: no verified permit
boundaries were available.

Run (after fetch_hpakant.py):
    python scripts/build_hpakant.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import build_scenarios as bs  # noqa: E402  (shared helpers: Grid, clean, ramps)
from services.processing.geo import corner_coordinates, utm_zone_from_epsg  # noqa: E402
from services.processing.speckle import lee_filter  # noqa: E402

CACHE = REPO / "data" / "raw" / "hpakant"
ID = "hpakant-observed"
OUT_STATIC = REPO / "static" / "scenarios" / ID
OUT_JSON = REPO / "src" / "lib" / "data" / "scenarios" / f"{ID}.json"

MODE, CRID = "QPDH", "P05023"
CALIBRATION_TOL_DB = 1.5
DROP_DB = 3.0
VEGETATED_BELOW_REF_DB = 3.0
WATER_DB = -18.0
MIN_CLUSTER_M2 = 10_000  # 1 ha minimum mapping unit (25 pixels at 20 m)
COHERENCE_LOW = 0.3
LEE_SIZE = 5


def parse_gcov(gid: str) -> dict:
    p = gid.split("_")
    return {"granule_id": gid, "mode": p[9], "crid": p[13], "date": f"{p[11][:4]}-{p[11][4:6]}-{p[11][6:8]}"}


def parse_gunw(gid: str) -> dict:
    p = gid.split("_")
    iso = lambda s: f"{s[:4]}-{s[4:6]}-{s[6:8]}"  # noqa: E731
    return {"granule_id": gid, "ref": iso(p[11]), "sec": iso(p[13])}


def load(gid: str) -> dict:
    z = np.load(CACHE / f"{gid}.npz")
    return {k: z[k] for k in z.files}


def valid_of(w: dict) -> np.ndarray:
    m = w["mask"]
    return (m != 0) & (m != 255) & np.isfinite(w["HVHV"]) & (w["HVHV"] > 0) & np.isfinite(w["HHHH"]) & (w["HHHH"] > 0)


def lee_db(lin: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Lee-filtered dB; invalid pixels are filled with the valid median first so they don't bleed in."""
    filled = np.where(valid, lin, np.median(lin[valid]))
    return np.where(valid, 10 * np.log10(np.clip(lee_filter(filled, LEE_SIZE), 1e-6, None)), np.nan)


def confirmed(flags: list[np.ndarray], k: int) -> np.ndarray:
    return flags[k] & flags[k - 1]


def area(mask: np.ndarray, px_m2: float) -> int:
    return int(round(mask.sum() * px_m2))


def save_sar(path: Path, d: np.ndarray, lo=-28.0, hi=-2.0):  # same scale as the legend and the demos
    v = np.clip((np.nan_to_num(d, nan=lo) - lo) / (hi - lo), 0, 1)
    g = (v * 255).astype(np.uint8)
    Image.fromarray(np.dstack([g, g, g, np.where(np.isfinite(d), 255, 0).astype(np.uint8)]), "RGBA").save(path, optimize=True)


def save_coherence(path: Path, coh: np.ndarray):
    rgb = bs._ramp(bs.COHERENCE_RAMP, np.nan_to_num(coh))
    alpha = np.where(np.isfinite(coh), 255, 0)
    Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA").save(path, optimize=True)


def main() -> int:
    manifest = json.loads((CACHE / "manifest.json").read_text(encoding="utf-8"))
    ok = [g for g in manifest["granules"] if not g["status"].startswith("error") and (CACHE / f"{g['granule_id']}.npz").exists()]
    gcov = sorted((parse_gcov(g["granule_id"]) for g in ok if g["level"] == "GCOV"), key=lambda g: g["date"])
    gunw = {p["sec"]: p for p in (parse_gunw(g["granule_id"]) for g in ok if g["level"] == "GUNW")}
    missing = [g["granule_id"] for g in manifest["granules"] if g not in ok]

    # 1. pass selection -------------------------------------------------------
    excluded = []
    cands = []
    for g in gcov:
        if g["mode"] != MODE or g["crid"] != CRID:
            excluded.append({**g, "reason": f"acquisition mode {g['mode']} / processing {g['crid']}: only {MODE} {CRID} passes are compared, so resolution and calibration match"})
            continue
        w = load(g["granule_id"])
        v = valid_of(w)
        g["median_hv_db"] = round(float(np.median(10 * np.log10(w["HVHV"][v]))), 2)
        cands.append(g)
    anchor = cands[-1]["median_hv_db"]
    kept = []
    for g in reversed(cands):
        if abs(g["median_hv_db"] - anchor) <= CALIBRATION_TOL_DB and len(kept) == len(cands) - 1 - cands.index(g):
            kept.insert(0, g)
        else:
            excluded.append({**g, "reason": f"scene median HV {g['median_hv_db']:+.1f} dB vs {anchor:+.1f} dB on the latest pass: calibration not consistent with the later passes"})
    excluded.sort(key=lambda g: g["date"])
    if len(kept) < 4:
        raise SystemExit(f"only {len(kept)} consistent passes; need at least 4 (2 baseline + 2 to confirm change)")

    # 2. per-pass filtering and reference normalisation ------------------------
    wins = [load(g["granule_id"]) for g in kept]
    x, y = wins[0]["x"], wins[0]["y"]
    for w in wins[1:]:
        if not (np.array_equal(w["x"], x) and np.array_equal(w["y"], y)):
            raise SystemExit("passes are not on the same grid; resampling is not implemented")
    zone, letter = utm_zone_from_epsg(int(wins[0]["epsg"]))
    px_m = float(abs(x[1] - x[0]))
    px_m2 = px_m * px_m
    valid = np.logical_and.reduce([valid_of(w) for w in wins])
    hv = [lee_db(w["HVHV"], valid) for w in wins]
    hh = [lee_db(w["HHHH"], valid) for w in wins]
    # Reference: pixels above their pass median on every pass (persistently vegetated), away from the mine belt.
    ref = valid & np.logical_and.reduce([d > np.nanmedian(d) for d in hv])
    ref_level = [float(np.nanmedian(d[ref])) for d in hv]
    offsets = [ref_level[-1] - r for r in ref_level]
    hv = [d + o for d, o in zip(hv, offsets)]
    hh = [d + o for d, o in zip(hh, offsets)]
    ref_db = ref_level[-1]

    # 3. change against the baseline composite --------------------------------
    lin = lambda d: 10 ** (d / 10)  # noqa: E731
    base_hv = 10 * np.log10((lin(hv[0]) + lin(hv[1])) / 2)
    base_hh = 10 * np.log10((lin(hh[0]) + lin(hh[1])) / 2)
    vegetated = valid & (base_hv >= ref_db - VEGETATED_BELOW_REF_DB)
    min_px = int(MIN_CLUSTER_M2 / px_m2)

    def flags_for(hv_k, hh_k, b_hv, b_hh):
        water = valid & (hh_k < WATER_DB) & ~(b_hh < WATER_DB)
        loss = vegetated & (hv_k - b_hv <= -DROP_DB) & ~water
        return loss, water

    loss_f, water_f = [], []
    for k in range(len(kept)):
        lo, wa = flags_for(hv[k], hh[k], base_hv, base_hh)
        loss_f.append(lo)
        water_f.append(wa)

    # 4. uncertainty: same rule (including the 1 ha minimum mapping unit) between the two baseline passes -----
    null_loss, null_water = flags_for(hv[1], hh[1], hv[0], hh[0])
    null_loss_clean = bs.clean(null_loss, min_px)
    null_rate = float(null_loss_clean.sum() / vegetated.sum())
    null_conf_rate = null_rate**2  # if errors on two passes were independent
    # Coherence for the 12-day (or 24-day) pair ending on each pass.
    coh = {}
    for g in kept:
        p = gunw.get(g["date"])
        if not p:
            continue
        w = load(p["granule_id"])
        if not (np.array_equal(w["x"], x) and np.array_equal(w["y"], y)):
            continue  # shortcut: GUNW grid must match the GCOV grid exactly; resample if a frame ever differs
        c = w["coherenceMagnitude"].astype(float)
        c[~valid | ~np.isfinite(c) | (w["mask"] == 0)] = np.nan
        coh[g["date"]] = (p, c)

    OUT_STATIC.mkdir(parents=True, exist_ok=True)
    for old in OUT_STATIC.glob("*.png"):
        old.unlink()
    grid = bs.Grid.__new__(bs.Grid)
    grid.x, grid.y, grid.zone, grid.letter = x, y, zone, letter
    last = date.fromisoformat(kept[-1]["date"])
    epochs, metrics, features = [], [], []
    for k, g in enumerate(kept):
        save_sar(OUT_STATIC / f"sar_{k}.png", hv[k])
        c = coh.get(g["date"])
        if c:
            save_coherence(OUT_STATIC / f"coherence_{k}.png", c[1])
        epochs.append({
            "date": g["date"],
            "day": (date.fromisoformat(g["date"]) - last).days,
            "label": "Baseline pass" if k < 2 else ("Latest pass" if k == len(kept) - 1 else "Pass"),
            "sar_url": f"/scenarios/{ID}/sar_{k}.png",
            "coherence_url": f"/scenarios/{ID}/coherence_{k}.png" if c else None,
            "displacement_url": None,
            "granule_id": g["granule_id"],
            "gunw_granule_id": c[0]["granule_id"] if c else None,
            "coherence_pair": [c[0]["ref"], c[0]["sec"]] if c else None,
        })
        if k < 3:
            metrics.append(None)  # baseline passes, and the first pass after them has nothing to confirm against
            continue
        loss = bs.clean(confirmed(loss_f, k), min_px)
        water = bs.clean(confirmed(water_f, k), min_px)
        m = {
            "disturbed_m2": area(loss, px_m2),
            "new_water_m2": area(water, px_m2),
            "drop_db_median": round(float(np.median((base_hv - hv[k])[loss])), 1) if loss.any() else None,
            "coherence_disturbed": None,
            "coherence_reference": None,
            "expected_false_m2": int(round(null_conf_rate * vegetated.sum() * px_m2)),
            "expected_false_upper_m2": int(round(null_rate * vegetated.sum() * px_m2)),
            "clusters": int(ndimage.label(loss)[1]),
        }
        if c and loss.any():
            m["coherence_disturbed"] = round(float(np.nanmedian(c[1][loss])), 2)
            m["coherence_reference"] = round(float(np.nanmedian(c[1][ref])), 2)
        metrics.append(m)
        features += grid.features(loss, {"kind": "disturbed", "epoch": k})
        features += grid.features(water, {"kind": "new_water", "epoch": k})

    final = metrics[-1]
    first, latest = kept[0]["date"], kept[-1]["date"]
    gunw_used = sorted({e["gunw_granule_id"] for e in epochs if e["gunw_granule_id"]})
    scenario = {
        "id": ID,
        "module": "observed",
        "data_status": "REAL",
        "title": "Hpakant jade-mining district: observed surface change",
        "location": {
            "name": "Hpakant",
            "region": "Kachin State, Myanmar",
            "center": [round(float(v), 5) for v in bs.pixel_to_lonlat(len(y) // 2, len(x) // 2, x, y, zone, letter)],
            "zoom": 12,
            "image_coordinates": [[round(v, 6) for v in p] for p in corner_coordinates(x, y, zone, letter)],
        },
        "story": {
            "headline": "Real NISAR radar over the world's largest jade-mining district",
            "context": (
                f"Hpakant's open-pit jade mines are hard to inspect on the ground and cloud hides them through the monsoon. "
                f"These are real NISAR L-band passes from {first} to {latest}. Between the baseline and the latest pass, "
                f"{final['disturbed_m2'] / 10_000:.0f} ha of formerly vegetated ground lost more than {DROP_DB:.0f} dB of radar return, "
                f"confirmed on two consecutive passes, and {final['new_water_m2'] / 10_000:.0f} ha became open water."
            ),
            "radar_insight": (
                "Vegetation scatters L-band radar many times (volume scattering), which keeps the cross-polarised (HV) return bright. "
                "Stripped, dug or dumped ground returns far less HV, and calm water reflects radar away, so it shows dark in HH too. "
                "InSAR coherence adds a clue: ground disturbed between two passes decorrelates."
            ),
        },
        "sensor": {
            "mission": "NASA-ISRO SAR (NISAR)",
            "band": "L-band",
            "wavelength_cm": 24,
            "repeat_days": 12,
            "backscatter_product": "NISAR L2 GCOV (geocoded, terrain-corrected backscatter)",
            "insar_product": "NISAR L2 GUNW (geocoded interferogram: coherence)",
            "polarization": "HV + HH",
            "pixel_m": px_m,
            "looks": round(float(np.median(wins[-1]["numberOfLooks"][valid])), 1),
        },
        "epochs": epochs,
        "metrics": metrics,
        "thresholds": {
            "drop_db": DROP_DB,
            "vegetated_below_reference_db": VEGETATED_BELOW_REF_DB,
            "water_db": WATER_DB,
            "min_cluster_m2": MIN_CLUSTER_M2,
            "calibration_tolerance_db": CALIBRATION_TOL_DB,
            "coherence_low": COHERENCE_LOW,
            "lee_window_px": LEE_SIZE,
        },
        "uncertainty": {
            "null_test": f"Same rule between the two baseline passes ({kept[0]['date']} and {kept[1]['date']}), where little real change is expected.",
            "single_pass_false_rate": round(null_rate, 4),
            "confirmed_false_rate": round(null_conf_rate, 6),
            "vegetated_m2": area(vegetated, px_m2),
            "reference_offsets_db": [round(o, 2) for o in offsets],
            "notes": [
                "Moisture changes between the dry-season baseline and the monsoon passes can lower or raise backscatter locally; the per-pass offset removes only scene-wide shifts.",
                "Steep terrain causes layover and shadow; a change on a steep slope may be a landslide or mine-waste slide rather than excavation.",
                "Provisional NISAR products: calibration may change when ASF reprocesses them.",
                f"Minimum mapping unit {MIN_CLUSTER_M2 / 10_000:.0f} ha; smaller workings are missed.",
                "Not yet validated against field data or optical imagery.",
            ],
        },
        "provenance": {
            "source_archive": "NASA ASF DAAC (Earthdata Cloud)",
            "track": manifest["track"],
            "frame": manifest["frame"],
            "orbit_direction": "descending",
            "epsg": int(wins[0]["epsg"]),
            "gcov_granules": [g["granule_id"] for g in kept],
            "gunw_granules": gunw_used,
            "excluded": [{"date": g["date"], "granule_id": g["granule_id"], "reason": g["reason"]} for g in excluded],
            "unreadable": missing,
        },
        "validation": {
            "note": "No independent reference yet: the false-alarm rate comes from the baseline-pair null test, not from field or optical data.",
            "recall": None,
            "precision": None,
        },
        "geojson": {"type": "FeatureCollection", "features": features},
    }
    OUT_JSON.write_text(json.dumps(scenario, indent=1) + "\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in OUT_STATIC.glob("*.png"))
    print(f"kept {len(kept)} passes {first}..{latest}; excluded {len(excluded)}; images {size / 1e6:.1f} MB")
    for e, m in zip(epochs, metrics):
        print(e["date"], e["label"], json.dumps(m) if m else "-")
    print("null single-pass false rate", round(null_rate, 4), "reference offsets", [round(o, 2) for o in offsets])
    return 0


if __name__ == "__main__":
    sys.exit(main())
