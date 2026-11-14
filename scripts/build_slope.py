"""Build the real Hpakant slope-motion (landslide indicator) record from cached NISAR GUNW pairs.

Inputs (fetched by scripts/fetch_hpakant_insar.py and scripts/fetch_hpakant.py):
  NISAR L2 GUNW unwrapped interferograms, Track 062 D, Frame 075 (80 m), 12-day pairs.
  NASADEM 1 arc-second elevation (NASA/JPL, LP DAAC), for terrain slope only.
  NISAR L2 GCOV HV of each pair's second date, as the radar backdrop.

Method
1. Each pair: LOS displacement d = (unwrappedPhase - ionospherePhaseScreen) * lambda / (4 pi).
   Positive d = ground moved toward the satellite. Sign from ISCE3 (the NISAR processor):
   solid_earth_tides.py builds its correction phase as -4 pi / lambda * (reference - secondary)
   displacement projected on the target-to-sensor LOS vector, in the same convention as
   unwrappedPhase. The ionosphere screen ships in the product but is not applied (ASF guide).
   Kept: connected component > 0 and coherence >= COHERENCE_MIN.
2. Each pair: a planar ramp and a linear trend with NASADEM elevation, fitted together on ground
   under SLOPE_MIN_DEG, are removed (residual ionosphere/orbit, and stratified monsoon troposphere:
   without it, rates tracked elevation at r = 0.71). Then the pair is referenced to flat (slope < FLAT_MAX_DEG), usually coherent ground
   in the same connected component, so only motion relative to that ground is measured.
3. Mean LOS rate per pixel = sum of measured pair displacements / sum of their spans; gaps
   between pairs are not measured and do not count. Uncertainty: scatter of the same rate over
   the flat reference ground, which holds atmospheric noise that was not corrected.
4. Candidates: steep ground (slope >= SLOPE_MIN_DEG) whose rate exceeds SIGMA_K reference
   scatters, with most pairs agreeing in sign, in patches of at least MIN_CLUSTER_M2.
   LOS motion on a steep slope is a landslide indicator, not a confirmed landslide: mining
   cuts, dumping and erosion also move ground, and LOS is not the downslope direction.

Run:  python scripts/build_slope.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import build_hpakant as bh  # noqa: E402  (shared GCOV loading, rendering and patch helpers)
import sar_common as bs  # noqa: E402
from services.processing.geo import corner_coordinates, utm_zone_from_epsg  # noqa: E402

INSAR = bh.CACHE / "insar"
DEM = bh.CACHE / "nasadem_n25e096.npy"
ID = "hpakant-slopes"
OUT_STATIC = REPO / "static" / "scenarios" / ID
OUT_JSON = REPO / "src" / "lib" / "data" / "scenarios" / f"{ID}.json"

COHERENCE_MIN = 0.3
FLAT_MAX_DEG = 5.0
SLOPE_MIN_DEG = 20.0
MIN_VALID_FRAC = 0.6  # a pixel needs this share of pairs measured to get a rate
SIGMA_K = 3.0
SIGN_AGREEMENT_MIN = 0.65
MIN_CLUSTER_M2 = 3 * 80 * 80
DISPLAY_CM_YR = 15.0  # colour ramp range of the rate layer
SIGN_SOURCE = "https://github.com/isce-framework/isce3/blob/develop/python/packages/nisar/workflows/solid_earth_tides.py"
DEM_SOURCE = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/NASADEM_HGT.001/NASADEM_HGT_n25e096/NASADEM_HGT_n25e096.zip"


def parse(gid: str) -> dict:
    p = gid.split("_")
    iso = lambda s: f"{s[:4]}-{s[4:6]}-{s[6:8]}"  # noqa: E731
    return {"granule_id": gid, "ref": iso(p[11]), "sec": iso(p[13]), "crid": p[15]}


def days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def terrain_on_grid(x, y, epsg) -> tuple[np.ndarray, np.ndarray]:
    """(elevation m, slope degrees) from NASADEM, sampled at the window pixels (nearest 1-arcsecond post)."""
    h = np.load(DEM).astype(float)  # rows 26N -> 25N, cols 96E -> 97E, 3601 x 3601
    dy = 6_371_000 * np.pi / 180 / 3600
    dx = dy * np.cos(np.deg2rad(25.65))
    gy, gx = np.gradient(ndimage.uniform_filter(h, 3), dy, dx)
    s = np.degrees(np.arctan(np.hypot(gx, gy)))
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(*np.meshgrid(x, y))
    r = np.clip(np.round((26 - lat) * 3600).astype(int), 0, 3600)
    c = np.clip(np.round((lon - 96) * 3600).astype(int), 0, 3600)
    return h[r, c], s[r, c]


def los_cm(unwrapped_phase, ionosphere_phase, wavelength_m):
    """LOS displacement in cm, positive toward the satellite (ISCE3 convention, see module docstring)."""
    return (unwrapped_phase - ionosphere_phase) * wavelength_m / (4 * np.pi) * 100


def save_rate(path: Path, v: np.ndarray):
    valid = np.isfinite(v)
    rgb = bs._ramp(bs.DISPLACEMENT_RAMP, np.clip((np.nan_to_num(v) + DISPLAY_CM_YR) / (2 * DISPLAY_CM_YR), 0, 1))
    Image.fromarray(np.dstack([rgb, np.where(valid, 255, 0)]).astype(np.uint8), "RGBA").save(path, optimize=True)


def nearest_gcov(sec: str, gcov: list[dict]) -> dict | None:
    same = [g for g in gcov if g["date"] == sec]
    return same[0] if same else None


def main() -> int:
    pairs = sorted((parse(p.stem) for p in INSAR.glob("NISAR_L2_*GUNW*.npz")), key=lambda p: p["sec"])
    if len(pairs) < 3:
        raise SystemExit(f"only {len(pairs)} GUNW pairs cached; run scripts/fetch_hpakant_insar.py")
    wins = [dict(np.load(INSAR / f"{p['granule_id']}.npz")) for p in pairs]
    x, y, epsg = wins[0]["x"], wins[0]["y"], int(wins[0]["epsg"])
    for w in wins:
        if not (np.array_equal(w["x"], x) and np.array_equal(w["y"], y)) or int(w["epsg"]) != epsg:
            raise SystemExit("GUNW pairs are not on one grid")
    zone, letter = utm_zone_from_epsg(epsg)
    px_m = float(abs(x[1] - x[0]))
    px_m2 = px_m * px_m
    lam = float(wins[0]["wavelength_m"])
    elev, slope = terrain_on_grid(x, y, epsg)
    n = len(pairs)
    span = np.array([days(p["ref"], p["sec"]) for p in pairs], float)

    # 1-2. per-pair LOS displacement (cm, + toward the satellite), referenced to flat coherent ground
    raw, ok = [], []
    for w in wins:
        cc = w["connectedComponents"]
        r = los_cm(w["unwrappedPhase"], w["ionospherePhaseScreen"], lam)
        good = (cc > 0) & (cc != 65535) & np.isfinite(r) & (w["coherenceMagnitude"] >= COHERENCE_MIN)
        raw.append(r)
        ok.append(good)
    flat = (slope < FLAT_MAX_DEG) & (np.mean(ok, axis=0) >= 0.8)
    if flat.sum() < 50:
        raise SystemExit("too little flat, coherent reference ground")
    X, Y = np.meshgrid((x - x.mean()) / 1000, (y - y.mean()) / 1000)  # km from the window centre
    d, height_slopes = [], []
    for w, r, g in zip(wins, raw, ok):
        out = np.full(r.shape, np.nan)
        cc = w["connectedComponents"]
        for comp in np.unique(cc[g]):
            m = g & (cc == comp)
            refm = m & flat
            if refm.sum() < 50:  # components without enough reference ground cannot be tied to it
                continue
            # Remove a planar ramp (residual ionosphere, orbit) and a linear trend with elevation (stratified
            # troposphere) in one least-squares fit, made only off the steep slopes so real slope motion
            # cannot be absorbed into it. A landslide spans hundreds of metres; the ramp spans the window.
            fit = m & (slope < SLOPE_MIN_DEG)
            design = np.column_stack([np.ones(fit.sum()), X[fit], Y[fit], elev[fit]])
            coef = np.linalg.lstsq(design, r[fit], rcond=None)[0]
            height_slopes.append(coef[3] * 100)
            c = r - coef[1] * X - coef[2] * Y - coef[3] * elev
            out[m] = c[m] - np.median(c[refm])
        d.append(out)
    d = np.array(d)
    meas = np.isfinite(d)

    # 3. mean LOS rate (cm/yr) over the measured pairs only
    frac = meas.mean(axis=0)
    has_rate = frac >= MIN_VALID_FRAC
    tot_d = np.nansum(d, axis=0)
    tot_t = (meas * span[:, None, None]).sum(axis=0)
    rate = np.where(has_rate, tot_d / np.maximum(tot_t, 1) * 365, np.nan)
    ref_rates = rate[flat & has_rate]
    sigma = float(1.4826 * np.median(np.abs(ref_rates - np.median(ref_rates))))  # robust scatter
    agree = np.where(has_rate, (np.sign(np.nan_to_num(d)) == np.sign(np.nan_to_num(rate))[None]).sum(axis=0) / np.maximum(meas.sum(axis=0), 1), 0)

    # 4. candidates
    min_px = int(np.ceil(MIN_CLUSTER_M2 / px_m2))
    rule = has_rate & (np.abs(np.nan_to_num(rate)) > SIGMA_K * sigma) & (agree >= SIGN_AGREEMENT_MIN)
    steep = has_rate & (slope >= SLOPE_MIN_DEG)
    # Size filter only (8-connected): a morphological opening would add an unstated ~3-pixel width requirement.
    lab, nlab = ndimage.label(rule & steep, structure=np.ones((3, 3)))
    sizes_all = ndimage.sum(rule & steep, lab, range(1, nlab + 1)) if nlab else np.array([])
    cand = np.isin(lab, 1 + np.flatnonzero(sizes_all >= min_px))
    lab, nlab = ndimage.label(cand, structure=np.ones((3, 3)))
    pass_pct = lambda m: round(float((rule & m).sum() / max(m.sum(), 1) * 100), 1)  # noqa: E731
    # Broad pattern left after the corrections: median rate near the window centre versus near its edge.
    radius = np.hypot(X, Y)
    centre_rate = float(np.nanmedian(np.where(radius < 3, rate, np.nan)))
    rim_rate = float(np.nanmedian(np.where(radius > 6, rate, np.nan)))
    grid = bs.Grid(x, y, zone, letter)

    # Rate layer per epoch: the same mean rate, from the pairs up to that date only
    cum_d = np.cumsum(np.nan_to_num(d), axis=0)
    cum_t = np.cumsum(meas * span[:, None, None], axis=0)
    cum_n = np.cumsum(meas, axis=0)
    rate_so_far = [np.where(cum_n[k] >= MIN_VALID_FRAC * (k + 1), cum_d[k] / np.maximum(cum_t[k], 1) * 365, np.nan) for k in range(n)]
    gaps = [0] + [days(pairs[k - 1]["sec"], pairs[k]["ref"]) for k in range(1, n)]

    def series(mask) -> list[float | None]:
        """Median over the mask of each pair, summed: robust to pixels dropping out."""
        out, s = [], 0.0
        for k in range(n):
            v = d[k][mask & meas[k]]
            if v.size < max(3, 0.3 * mask.sum()):
                out.append(None)
                continue
            s += float(np.median(v))
            out.append(round(s, 2))
        return out

    OUT_STATIC.mkdir(parents=True, exist_ok=True)
    for f in OUT_STATIC.glob("*.png"):
        f.unlink()
    manifest = json.loads((bh.CACHE / "manifest.json").read_text(encoding="utf-8"))
    gcov = [bh.parse_gcov(g["granule_id"]) for g in manifest["granules"] if g["level"] == "GCOV" and (bh.CACHE / f"{g['granule_id']}.npz").exists()]
    epochs, metrics = [], []
    for k, p in enumerate(pairs):
        g = nearest_gcov(p["sec"], gcov)
        if g is None:
            raise SystemExit(f"no cached GCOV pass on {p['sec']} for the radar backdrop")
        w = bh.load(g["granule_id"])
        bh.save_sar(OUT_STATIC / f"sar_{k}.png", bh.lee_db(w["HVHV"], bh.valid_of(w)))
        coh = np.where(np.isfinite(wins[k]["coherenceMagnitude"]), wins[k]["coherenceMagnitude"], np.nan)
        bh.save_coherence(OUT_STATIC / f"coherence_{k}.png", coh)
        save_rate(OUT_STATIC / f"los_{k}.png", rate_so_far[k])
        epochs.append({
            "date": p["sec"],
            "day": days(pairs[-1]["sec"], p["sec"]),
            "label": "First pair" if k == 0 else ("Latest pair" if k == n - 1 else "Pair"),
            "sar_url": f"/scenarios/{ID}/sar_{k}.png",
            "coherence_url": f"/scenarios/{ID}/coherence_{k}.png",
            "displacement_url": f"/scenarios/{ID}/los_{k}.png",
            "granule_id": g["granule_id"],
            "gunw_granule_id": p["granule_id"],
            "coherence_pair": [p["ref"], p["sec"]],
        })
        refd = d[k][flat & meas[k]]
        metrics.append({
            "measured_pct": round(float(meas[k].mean() * 100), 1),
            "reference_scatter_cm": round(float(1.4826 * np.median(np.abs(refd - np.median(refd)))), 2) if refd.size else None,
            "gap_before_days": gaps[k],
            "rate_coverage_pct": round(float(np.isfinite(rate_so_far[k]).mean() * 100), 1),
        })

    sizes = ndimage.sum(cand, lab, range(1, nlab + 1)) if nlab else []
    candidates, features = [], []
    for rank, j in enumerate(np.argsort(-np.asarray(sizes), kind="stable"), start=1):
        pm = lab == j + 1
        rows, cols = np.nonzero(pm)
        cr, cc_ = ndimage.center_of_mass(pm)
        r = float(np.median(rate[pm]))
        c = {
            "candidate_id": f"s-{rank}",
            "area_m2": bh.area(pm, px_m2),
            "slope_deg": round(float(np.median(slope[pm])), 1),
            "rate_cm_yr": round(r, 1),
            "direction": "toward" if r > 0 else "away",
            "sign_agreement": round(float(np.median(agree[pm])), 2),
            "pairs_measured": int(np.median(meas[:, pm].sum(axis=0))),
            "series_cm": series(pm),
            "centroid": [round(v, 6) for v in bs.pixel_to_lonlat(int(round(cr)), int(round(cc_)), x, y, zone, letter)],
            "bbox": bh.lonlat_bbox(rows, cols, grid),
        }
        candidates.append(c)
        features += grid.features(pm, min_points=4, props={"kind": "slope_motion", "patch_id": c["candidate_id"], "area_m2": c["area_m2"], "rate_cm_yr": c["rate_cm_yr"]})

    first, last = pairs[0], pairs[-1]
    gap_days = sum(g for g in gaps if g > 0)
    no_cc = [p for p, w in zip(pairs, wins) if not ((w["connectedComponents"] > 0) & (w["connectedComponents"] != 65535)).any()]
    unread = [f"{p['ref']} to {p['sec']}" for p in no_cc]
    unread_days = sum(days(p["ref"], p["sec"]) for p in no_cc)
    total = sum(c["area_m2"] for c in candidates)
    scenario = {
        "id": ID,
        "module": "slope",
        "data_status": "REAL",
        "title": "Hpakant slope motion (real NISAR InSAR)",
        "location": {
            "name": "Hpakant slopes",
            "region": "Kachin State, Myanmar",
            "center": [round(float(v), 5) for v in bs.pixel_to_lonlat(len(y) // 2, len(x) // 2, x, y, zone, letter)],
            "zoom": 12,
            "image_coordinates": [[round(v, 6) for v in q] for q in corner_coordinates(x, y, zone, letter)],
        },
        "story": {
            "headline": "Real NISAR InSAR over Hpakant's landslide-prone mine slopes",
            "context": (
                f"Mine-waste slopes around Hpakant fail often, most deadly in the monsoon. {n} real NISAR interferograms (12- and 24-day pairs) "
                f"from {first['ref']} to {last['sec']} measure how the ground moved along the radar's line of sight. "
                f"{len(candidates)} patch{'' if len(candidates) == 1 else 'es'} of steep ground ({total / 10_000:.1f} ha in all) moved faster than {SIGMA_K:.0f}x the "
                f"scatter on flat reference ground ({sigma:.1f} cm/yr). Each is a place to check, not a confirmed landslide."
            ),
            "radar_insight": (
                "InSAR compares the phase of two passes 12 or 24 days apart: a shift of half the 24 cm wavelength means the ground moved "
                "12 cm closer to or further from the satellite. Only motion along that line of sight is measured, not elevation or "
                "downslope movement, and ground that changes too much between passes (dug pits, dense wet forest) loses coherence "
                "and cannot be read."
            ),
        },
        "sensor": {
            "mission": "NASA-ISRO SAR (NISAR)",
            "band": "L-band",
            "wavelength_cm": round(lam * 100, 1),
            "repeat_days": 12,
            "backscatter_product": "NISAR L2 GCOV HV (radar backdrop)",
            "insar_product": "NISAR L2 GUNW (unwrapped phase, coherence, ionosphere screen)",
            "polarization": "HH (InSAR)",
            "pixel_m": px_m,
            "looks": 0,
        },
        "epochs": epochs,
        "metrics": metrics,
        "candidates": candidates,
        "reference_series_cm": series(flat),
        "thresholds": {
            "coherence_min": COHERENCE_MIN,
            "flat_max_deg": FLAT_MAX_DEG,
            "slope_min_deg": SLOPE_MIN_DEG,
            "min_valid_frac": MIN_VALID_FRAC,
            "sigma_k": SIGMA_K,
            "sign_agreement_min": SIGN_AGREEMENT_MIN,
            "min_cluster_m2": MIN_CLUSTER_M2,
            "display_cm_yr": DISPLAY_CM_YR,
        },
        "uncertainty": {
            "rate_sigma_cm_yr": round(sigma, 2),
            "reference_m2": bh.area(flat, px_m2),
            "rate_coverage_pct": round(float(has_rate.mean() * 100), 1),
            "unmeasured_gap_days": gap_days,
            "centre_rate_cm_yr": round(centre_rate, 1),
            "rim_rate_cm_yr": round(rim_rate, 1),
            "residual_rate_vs_elevation_cm_yr_per_100m": round(float(np.polyfit(elev[has_rate & (slope < SLOPE_MIN_DEG)], rate[has_rate & (slope < SLOPE_MIN_DEG)], 1)[0] * 100), 2),
            "unread_pairs": unread,
            "rule_pass_flat_pct": pass_pct(flat & has_rate),
            "rule_pass_steep_pct": pass_pct(steep),
            "notes": [
                "Line-of-sight only: the satellite looks down at about "
                f"{float(np.median([w['incidence_deg'] for w in wins])):.0f} degrees from vertical, so a slope sliding downhill can read as toward, away or near zero depending on which way it faces.",
                "Relative motion: every pair is tied to flat, coherent ground in the same connected component; motion of that reference ground itself is not seen.",
                f"Atmosphere: the product's ionosphere phase screen is subtracted. Pair by pair, a planar ramp (leftover ionosphere or orbit error) and a linear trend with NASADEM elevation (height-dependent troposphere) are fitted on ground under {SLOPE_MIN_DEG:.0f} degrees and removed (height trends ranged {min(height_slopes):+.1f} to {max(height_slopes):+.1f} cm per 100 m). Real motion spread across the whole 16 km window would be removed too. Patchy, turbulent water vapour is not corrected; its noise is part of the reference scatter.",
                f"Null comparison: the same speed-and-direction rule passes {pass_pct(flat & has_rate)}% of flat reference pixels and {pass_pct(steep)}% of steep ones. Steep pixels are read on fewer pairs, so their rates are noisier and part of that excess may be noise.",
                *([f"No usable phase in this window for {len(unread)} pairs ({'; '.join(unread)}): the unwrapper assigned no connected component, so those {unread_days} days are not counted."] if unread else []),
                *([f"Gaps: {gap_days} days between pairs are not measured."] if gap_days else []),
                f"A broad pattern remains after the corrections: the median rate is {centre_rate:+.1f} cm/yr within 3 km of the window centre (the mining valley) and {rim_rate:+.1f} cm/yr beyond 6 km. It may be real ground motion or leftover atmosphere; this data cannot tell which. A candidate in the outer zone may be part of that pattern rather than a separate moving slope.",
                "Unwrapping errors (whole 2 pi jumps) inside a connected component are not detected.",
                "Not yet validated against field reports, GNSS or optical imagery.",
            ],
        },
        "provenance": {
            "source_archive": "ASF DAAC (NASA Earthdata)",
            "track": 62,
            "frame": 75,
            "orbit_direction": "Descending",
            "epsg": epsg,
            "gunw_granules": [p["granule_id"] for p in pairs],
            "gcov_granules": [e["granule_id"] for e in epochs],
            "dem": {"product": "NASADEM_HGT v001 tile n25e096 (NASA/JPL, LP DAAC)", "url": DEM_SOURCE},
            "sign_convention": {"statement": "Positive = toward the satellite; d = (unwrappedPhase - ionospherePhaseScreen) x wavelength / 4 pi", "source": SIGN_SOURCE},
        },
        "validation": {"note": "No independent reference yet: no field, GNSS or optical check of these slopes.", "recall": None, "precision": None},
        "geojson": {"type": "FeatureCollection", "features": features},
    }
    OUT_JSON.write_text(json.dumps(scenario, indent=1), encoding="utf-8")
    print(f"{n} pairs {first['ref']}..{last['sec']}; rate sigma {sigma:.2f} cm/yr over {flat.sum()} flat px; rate coverage {has_rate.mean():.0%}")
    for c in candidates:
        print("  ", {k: c[k] for k in ("candidate_id", "area_m2", "slope_deg", "rate_cm_yr", "sign_agreement", "pairs_measured")})
    for k, m in enumerate(metrics):
        print("  ", pairs[k]["ref"], pairs[k]["sec"], m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
