"""Build the two SIMULATED Myanmar SAR scenarios shown in the app.

Nothing here is a satellite observation. Each scenario is a physically
plausible synthetic scene built from NISAR mission parameters (L-band,
24 cm wavelength, 12-day repeat, 10-20 m GCOV pixels): backscatter with
multiplicative speckle, InSAR coherence and line-of-sight displacement.

The scene is then run through the same detection steps a real NISAR
analysis would use (Lee filter, log-ratio change detection, water
thresholding, coherence masking), so every number the app shows is
*measured* from the simulated images, never typed in. Because the
simulation knows its own ground truth, the detector's accuracy against
it is recorded too.

Sites, operators and permits are fictional; locations are illustrative.

Run:
    python scripts/build_scenarios.py
Writes static/scenarios/<id>/*.png and src/lib/data/scenarios/<id>.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import utm
from PIL import Image
from scipy import ndimage
from skimage.draw import ellipse, polygon
from skimage.measure import points_in_poly

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from services.processing.geo import corner_coordinates, pixel_to_lonlat  # noqa: E402
from services.processing.speckle import lee_filter  # noqa: E402
from services.processing.vectorize import change_mask_to_geojson  # noqa: E402

STATIC_DIR = REPO / "static" / "scenarios"
DATA_DIR = REPO / "src" / "lib" / "data" / "scenarios"
LOOKS = 8  # equivalent number of looks of a multilooked GCOV pixel
COHERENCE_MIN = 0.3  # phase below this coherence is too noisy to read displacement from


# ---------------------------------------------------------------- helpers
def db(x):
    return 10 * np.log10(np.maximum(x, 1e-6))


def lin(d):
    return 10 ** (d / 10)


def smooth_noise(shape, scale_px, rng):
    n = ndimage.gaussian_filter(rng.standard_normal(shape), scale_px)
    return n / (n.std() or 1)


def speckled(sigma0_db, rng):
    """Multiplicative gamma speckle of a multilooked intensity image."""
    return lin(sigma0_db) * rng.gamma(LOOKS, 1 / LOOKS, sigma0_db.shape)


def clean(mask, min_px):
    """Morphological opening, then drop clusters smaller than min_px."""
    mask = ndimage.binary_opening(mask, iterations=1)
    lab, n = ndimage.label(mask)
    if n == 0:
        return mask
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    return np.isin(lab, 1 + np.flatnonzero(sizes >= min_px))


def poly_mask(shape, rc):
    m = np.zeros(shape, bool)
    rr, cc = polygon([p[0] for p in rc], [p[1] for p in rc], shape)
    m[rr, cc] = True
    return m


def ellipse_mask(shape, r, c, rr_, cr_):
    m = np.zeros(shape, bool)
    rr, cc = ellipse(r, c, rr_, cr_, shape)
    m[rr, cc] = True
    return m


class Grid:
    def __init__(self, lat, lon, rows, cols, px):
        e, n, self.zone, self.letter = utm.from_latlon(lat, lon)
        self.rows, self.cols, self.px = rows, cols, px
        self.shape = (rows, cols)
        self.x = e - cols * px / 2 + (np.arange(cols) + 0.5) * px
        self.y = n + rows * px / 2 - (np.arange(rows) + 0.5) * px
        self.area = px * px

    def corners(self):
        return [[round(v, 6) for v in p] for p in corner_coordinates(self.x, self.y, self.zone, self.letter)]

    def features(self, mask, props, min_points=8):
        """Mask outlines as polygons; a ring inside another becomes its hole, so holes are not filled twice."""
        fc = change_mask_to_geojson(mask, self.x, self.y, self.zone, self.letter, min_contour_points=min_points)
        rings = [np.array(f["geometry"]["coordinates"][0]) for f in fc["features"]]
        inside = [[j for j, o in enumerate(rings) if j != i and points_in_poly(r[:1], o)[0]] for i, r in enumerate(rings)]
        area = [abs(np.sum(r[:-1, 0] * r[1:, 1] - r[1:, 0] * r[:-1, 1])) for r in rings]
        polys = {i: [r] for i, r in enumerate(rings) if len(inside[i]) % 2 == 0}
        for i, r in enumerate(rings):
            if len(inside[i]) % 2:
                polys[min((j for j in inside[i] if j in polys), key=lambda j: area[j])].append(r)
        return [
            {"type": "Feature", "properties": dict(props), "geometry": {"type": "Polygon", "coordinates": [np.round(r, 6).tolist() for r in rs]}}
            for rs in polys.values()
        ]

    def line(self, rows_cols, props):
        coords = [[round(v, 6) for v in pixel_to_lonlat(int(r), int(round(c)), self.x, self.y, self.zone, self.letter)] for r, c in rows_cols]
        return {"type": "Feature", "properties": dict(props), "geometry": {"type": "LineString", "coordinates": coords}}

    def rc_polygon(self, rc, props):
        ring = [[round(v, 6) for v in pixel_to_lonlat(r, c, self.x, self.y, self.zone, self.letter)] for r, c in rc]
        ring.append(ring[0])
        return {"type": "Feature", "properties": dict(props), "geometry": {"type": "Polygon", "coordinates": [ring]}}


def save_gray(path, d, lo=-28.0, hi=-2.0):
    v = np.clip((d - lo) / (hi - lo), 0, 1)
    Image.fromarray((v * 255).astype(np.uint8), "L").save(path, optimize=True)


def _ramp(stops, t):
    t = np.clip(t, 0, 1)[..., None]
    xs = np.linspace(0, 1, len(stops))
    stops = np.array(stops, float)
    out = np.zeros(t.shape[:-1] + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(t[..., 0], xs, stops[:, ch])
    return out


def hexrgb(h):
    return [int(h[i : i + 2], 16) for i in (1, 3, 5)]


# Sequential (one hue, dark = incoherent) and diverging (blue toward / orange away, grey midpoint) ramps.
COHERENCE_RAMP = [hexrgb(c) for c in ("#07173f", "#0042a6", "#3987e5", "#cfe3fb")]
DISPLACEMENT_RAMP = [hexrgb(c) for c in ("#d95926", "#e9a07f", "#8a94a8", "#8fb8ee", "#3987e5")]


def save_coherence(path, coh):
    rgb = _ramp(COHERENCE_RAMP, coh)
    Image.fromarray(rgb.astype(np.uint8), "RGB").save(path, optimize=True)


def save_displacement(path, disp_cm, valid, vmax):
    rgb = _ramp(DISPLACEMENT_RAMP, (disp_cm + vmax) / (2 * vmax))
    alpha = np.where(valid, 235, 0)
    Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA").save(path, optimize=True)


def coherence_field(base, rng, noise=0.06):
    return np.clip(base + noise * smooth_noise(base.shape, 1.2, rng), 0.02, 0.98)


def write(scenario, out_static):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / f"{scenario['id']}.json").write_text(json.dumps(scenario, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {scenario['id']}: {len(list(out_static.glob('*.png')))} images")


SENSOR = {
    "mission": "NASA-ISRO SAR (NISAR)",
    "band": "L-band",
    "wavelength_cm": 24,
    "repeat_days": 12,
    "backscatter_product": "NISAR L2 GCOV (geocoded, terrain-corrected backscatter)",
    "insar_product": "NISAR L2 GUNW (geocoded unwrapped interferogram: phase and coherence)",
}


# ---------------------------------------------------------------- scenario 1: mining compliance
def build_mining(seed=7):
    rng = np.random.default_rng(seed)
    g = Grid(18.705, 95.955, 320, 320, 10.0)
    sid = "mining-compliance-mc07"
    out = STATIC_DIR / sid
    out.mkdir(parents=True, exist_ok=True)
    rows, cols = np.indices(g.shape)

    # Terrain and land cover (HV: volume scattering from forest canopy is what clearing removes).
    dem = 25 * smooth_noise(g.shape, 40, rng) + 0.05 * rows * g.px
    slope_x = np.gradient(dem, axis=1) / g.px
    river_c = 248 + 22 * np.sin(rows / 55.0)
    river = np.abs(cols - river_c) < 3.5
    bar = (np.abs(cols - river_c) < 6.5) & ~river
    forest_db = -12.5 + 1.0 * smooth_noise(g.shape, 2.5, rng) + np.clip(-12 * slope_x, -2.5, 2.5)

    permit_rc = [(90, 118), (84, 202), (196, 212), (204, 124)]
    permit = poly_mask(g.shape, permit_rc)

    # Ground truth: the pit grows each pass; it leaves the permit on pass 3 and reaches the riverbank on pass 5.
    blobs = [
        [(150, 160, 15, 12)],
        [(150, 160, 28, 20)],
        [(150, 160, 40, 28), (112, 150, 12, 10), (130, 204, 9, 7)],
        [(150, 160, 42, 30), (112, 150, 14, 12), (148, 214, 30, 16)],
        [(152, 162, 44, 32), (112, 150, 16, 14), (160, 222, 36, 21), (76, 168, 12, 15)],
    ]
    truth = []
    acc = np.zeros(g.shape, bool)
    for epoch_blobs in blobs:
        for r, c, a, b in epoch_blobs:
            acc |= ellipse_mask(g.shape, r, c, a, b)
        truth.append(acc.copy() & ~river)

    dates = ["2026-06-04", "2026-06-16", "2026-06-28", "2026-07-10", "2026-07-22"]
    intensity, sar_db = [], []
    for k, ex in enumerate(truth):
        s = forest_db.copy()
        s[bar] = -21.0
        s[river] = -28.0
        s[ex] = -19.0 + 0.8 * smooth_noise(g.shape, 1.5, rng)[ex]
        s[truth[0] & (ellipse_mask(g.shape, 150, 160, 9, 7))] = -25.0  # monsoon water in the oldest pit
        i = speckled(s, rng)
        intensity.append(i)
        sar_db.append(db(i))
        save_gray(out / f"sar_{k}.png", db(i))

    # Detection: Lee-filtered log ratio against the first pass; clearing = HV drop > 3 dB on formerly vegetated ground.
    filt = [lee_filter(i, 5) for i in intensity]
    vegetated0 = db(filt[0]) > -16
    tolerance_px = 2  # 20 m band for geolocation error and speckle at the boundary
    permit_tol = ndimage.binary_dilation(permit, iterations=tolerance_px)
    dist_out = ndimage.distance_transform_edt(~permit) * g.px

    # InSAR between consecutive passes.
    coh_pairs, disp_pairs = [None], [np.zeros(g.shape)]
    cum_disp = np.zeros(g.shape)
    bank_zone = (np.abs(cols - river_c) < 30) & ~river & ~permit
    for k in range(1, len(dates)):
        base = np.full(g.shape, 0.55)
        base[river] = 0.05
        base[bar] = 0.7
        base[truth[k - 1]] = 0.3  # worked pit: surface keeps changing
        base[truth[k] & ~truth[k - 1]] = 0.12  # dug during this interval
        coh = coherence_field(base, rng)
        d = 0.25 * smooth_noise(g.shape, 25, rng)  # atmosphere, cm
        if k >= 3:  # riverbank between pit and river starts slumping once digging leaves the permit
            near = ndimage.distance_transform_edt(~truth[k]) * g.px
            d += -2.4 * np.exp(-((near / 60.0) ** 2)) * bank_zone
        coh_pairs.append(coh)
        disp_pairs.append(d)
        cum_disp = cum_disp + d
        save_coherence(out / f"coherence_{k}.png", coh)
        save_displacement(out / f"displacement_{k}.png", cum_disp, coh >= COHERENCE_MIN, 5.0)

    epochs, features, metrics = [], [], []
    features.append(g.rc_polygon(permit_rc, {"kind": "permit", "label": "Permitted concession boundary"}))
    cum = np.zeros(g.shape)
    detected = []
    for k, date in enumerate(dates):
        if k == 0:
            det = np.zeros(g.shape, bool)
        else:
            ratio = db(filt[k]) - db(filt[0])
            det = clean((ratio < -3.0) & vegetated0, 20)
            cum = cum + disp_pairs[k]
        detected.append(det)
        inside = det & permit
        outside = det & ~permit
        beyond = det & ~permit_tol
        coh = coh_pairs[k]
        valid = coh >= COHERENCE_MIN if coh is not None else np.ones(g.shape, bool)
        ring = (~permit) & (dist_out <= 150) & valid
        metrics.append(
            {
                "new_clearing_m2": round(float(det.sum() * g.area)),
                "inside_m2": round(float(inside.sum() * g.area)),
                "outside_m2": round(float(outside.sum() * g.area)),
                "outside_beyond_tolerance_m2": round(float(beyond.sum() * g.area)),
                "max_distance_outside_m": round(float(dist_out[det].max()) if det.any() else 0.0),
                "low_coherence_outside_m2": round(float(((coh < COHERENCE_MIN) & ~permit_tol & ~river).sum() * g.area)) if coh is not None else 0,
                "max_subsidence_outside_cm": round(float(max(0.0, -cum[ring].min())) if ring.any() else 0.0, 1),
            }
        )
        if inside.any():
            features += g.features(inside, {"kind": "excavation_inside", "epoch": k})
        if outside.any():
            features += g.features(outside, {"kind": "excavation_outside", "epoch": k})
        epochs.append(
            {
                "date": date,
                "day": (k - len(dates) + 1) * 12,
                "label": ["Baseline pass", "Routine pass", "Routine pass", "Routine pass", "Latest pass"][k],
                "sar_url": f"/scenarios/{sid}/sar_{k}.png",
                "coherence_url": f"/scenarios/{sid}/coherence_{k}.png" if k else None,
                "displacement_url": f"/scenarios/{sid}/displacement_{k}.png" if k else None,
            }
        )

    new_truth = truth[-1] & ~truth[0]
    det = detected[-1]
    scenario = {
        "id": sid,
        "module": "mining",
        "data_status": "SIMULATED",
        "title": "Concession MC-07: digging beyond the permit",
        "location": {
            "name": "Illustrative site, Bago Yoma foothills",
            "region": "Bago Region, Myanmar",
            "center": [95.955, 18.705],
            "zoom": 13.4,
            "image_coordinates": g.corners(),
        },
        "story": {
            "headline": "A sand and gravel pit that grew past its permit toward the river",
            "context": "Operator \"Golden Bank Aggregates\" (fictional) holds a permit to dig inside the yellow boundary. Head office cannot visit the site through the monsoon, and clouds hide it from optical satellites for weeks. Every 12 days NISAR's L-band radar sees it anyway.",
            "radar_insight": "Forest canopy scatters radar many times between leaves and branches (volume scattering), which keeps its cross-polarised (HV) return bright. Clearing and digging leave bare, rough ground that returns far less HV signal, so a drop of more than 3 dB marks newly cleared land. InSAR adds two clues: active digging destroys coherence between passes, and the ground beside the pit sinking away from the satellite warns of riverbank collapse.",
        },
        "sensor": {**SENSOR, "polarization": "HV", "pixel_m": g.px, "looks": LOOKS},
        "epochs": epochs,
        "metrics": metrics,
        "thresholds": {
            "breach_outside_m2": 5000,
            "tolerance_m": tolerance_px * g.px,
            "subsidence_watch_cm": 2.0,
            "clearing_drop_db": 3.0,
            "min_cluster_m2": 20 * g.area,
            "coherence_min": COHERENCE_MIN,
        },
        "permit": {"operator": "Golden Bank Aggregates (fictional)", "permit_id": "MC-07 (fictional)", "area_m2": round(float(permit.sum() * g.area))},
        "validation": {
            "note": "Detected new clearing on the latest pass compared with the simulation's own ground truth.",
            "recall": round(float((det & new_truth).sum() / new_truth.sum()), 3),
            "precision": round(float((det & new_truth).sum() / max(1, det.sum())), 3),
        },
        "geojson": {"type": "FeatureCollection", "features": features},
    }
    write(scenario, out)
    return scenario


# ---------------------------------------------------------------- scenario 2: landslide and river diversion
def build_landslide(seed=11):
    rng = np.random.default_rng(seed)
    g = Grid(23.205, 93.455, 400, 250, 20.0)
    sid = "landslide-river-diversion"
    out = STATIC_DIR / sid
    out.mkdir(parents=True, exist_ok=True)
    rows, cols = np.indices(g.shape)

    center = 125 + 20 * np.sin(rows / 60.0)  # river centreline column per row, before the event
    dist_c = cols - center
    # Height above the river: flat floor, steepening valley walls cut by side ridges and gullies.
    height = g.px * (0.06 * np.abs(dist_c) + 0.02 * dist_c**2 / 10) + 60 * smooth_noise(g.shape, 9, rng) * np.clip(np.abs(dist_c) / 25, 0, 1)
    bed = 0.4 * (g.rows - rows)  # river bed rises 2% per 20 m row going upstream
    dem = 400 + bed + height
    slope_x = np.gradient(dem, axis=1) / g.px
    forest_db = -8.0 + 0.9 * smooth_noise(g.shape, 2.5, rng) + np.clip(-6 * slope_x, -4, 4)

    half_w = 3.2  # ~130 m channel
    dam_r0, dam_r1 = 118, 140
    reach_r0, reach_r1 = 270, 340
    shift = np.where((rows >= reach_r0) & (rows <= reach_r1), 14 * np.sin(np.pi * (rows - reach_r0) / (reach_r1 - reach_r0)), 0.0)
    scar_truth = ellipse_mask(g.shape, 128, 125 + 20 * np.sin(128 / 60.0) - 22, 20, 24)
    debris = (rows >= dam_r0) & (rows <= dam_r1) & (dist_c > -4) & (dist_c < 4)
    lake_level = {2: 12.0, 3: 20.0}  # impounded water surface, metres above the bed at the dam

    dates = ["2026-07-15", "2026-07-27", "2026-08-08", "2026-08-20"]
    failed = [False, False, True, True]
    diverted = [False, False, False, True]
    intensity, water_truth = [], []
    for k in range(4):
        s = forest_db.copy()
        water = np.abs(dist_c) < half_w
        bars = (np.abs(dist_c) < half_w + 2.5) & ~water
        if failed[k]:
            s[scar_truth] = -12.5 + 0.8 * smooth_noise(g.shape, 1.5, rng)[scar_truth]
            water &= ~debris
            water |= (rows >= dam_r0) & (rows <= dam_r1) & (dist_c >= 4) & (dist_c < 7)  # flow squeezed past the debris toe
            # The lake fills the valley floor behind the debris up to its water level.
            surface = 400 + 0.4 * (g.rows - dam_r0) + lake_level[k]
            pool, _ = ndimage.label(ndimage.binary_opening((rows < dam_r0) & (dem < surface) & (np.abs(dist_c) < 40), iterations=2))
            water |= pool == pool[dam_r0 - 1, int(round(center[dam_r0 - 1, 0]))]  # only water connected to the dam
        if diverted[k]:
            reach = (rows >= reach_r0) & (rows <= reach_r1)
            old = water & reach
            water = (water & ~reach) | (reach & (np.abs(cols - (center + shift)) < half_w))
            s[old & ~water] = -13.0  # abandoned channel: wet sediment, rougher than water
        s[bars] = -14.0
        if failed[k]:
            s[debris] = -11.0
        s[water] = -24.0
        i = speckled(s, rng)
        intensity.append(i)
        water_truth.append(water)
        save_gray(out / f"sar_{k}.png", db(i))

    filt = [lee_filter(i, 5) for i in intensity]
    # Water needs a smaller window than the channel width, or banks smear into it.
    water_det = [clean(db(lee_filter(i, 3)) < -18.0, 6) for i in intensity]
    corridor = ndimage.binary_dilation(np.abs(dist_c) < half_w + 3, iterations=3)
    upper = (rows > 45) & (rows < dam_r0)
    control = rows <= 45
    reach_m = (rows >= 200) & (rows <= 390)

    coh_pairs, cum = [None], np.zeros(g.shape)
    for k in range(1, 4):
        base = np.full(g.shape, 0.45)
        base[water_truth[k] | water_truth[k - 1]] = 0.05
        d = 0.2 * smooth_noise(g.shape, 25, rng)
        if k == 1:  # slow creep on the slope before it fails
            body = ndimage.distance_transform_edt(~scar_truth) * g.px
            d += -1.4 * np.exp(-((body / 80.0) ** 2))
        if failed[k] and not failed[k - 1]:
            base[scar_truth | debris] = 0.05
        elif failed[k]:
            base[scar_truth] = 0.15
        if diverted[k] and not diverted[k - 1]:
            base[(water_truth[k] ^ water_truth[k - 1]) & reach_m] = 0.08
        coh = coherence_field(base, rng)
        coh_pairs.append(coh)
        cum = cum + d
        if not failed[k]:
            pre_fail_k, pre_fail_cum = k, cum.copy()
        save_coherence(out / f"coherence_{k}.png", coh)
        save_displacement(out / f"displacement_{k}.png", cum, coh >= COHERENCE_MIN, 3.0)

    def centroid_cols(mask, r0, r1):
        out_ = {}
        for r in range(r0, r1):
            cs = np.flatnonzero(mask[r])
            if cs.size:
                out_[r] = cs.mean()
        return out_

    base_c = centroid_cols(water_det[0], 0, g.rows)
    features, metrics, epochs = [], [], []
    landslide_any = np.zeros(g.shape, bool)
    for k, date in enumerate(dates):
        if k:
            ratio = db(filt[k]) - db(filt[0])
            dropped = (ratio < -3.0) & ~corridor & ~water_det[k]  # water is dark too; it is not a landslide
            ls = clean(dropped & ((coh_pairs[k] < 0.3) | landslide_any), 25)
            landslide_any |= ls
        else:
            ls = np.zeros(g.shape, bool)
        imp = water_det[k] & ~ndimage.binary_dilation(water_det[0], iterations=1) & upper
        imp = clean(imp, 10)
        new_ch = water_det[k] & ~ndimage.binary_dilation(water_det[0], iterations=1) & reach_m
        new_ch = clean(new_ch, 10)
        aband = water_det[0] & ~ndimage.binary_dilation(water_det[k], iterations=1) & reach_m
        aband = clean(aband, 10)
        now_c = centroid_cols(water_det[k], 200, 390)
        shifts = [abs(now_c[r] - base_c[r]) * g.px for r in now_c if r in base_c]
        ctrl0, ctrlk = water_det[0][control].sum(), water_det[k][control].sum()
        metrics.append(
            {
                "landslide_m2": round(float(ls.sum() * g.area)),
                "impoundment_m2": round(float(imp.sum() * g.area)),
                "channel_shift_m": round(float(max(shifts)) if shifts else 0.0),
                "new_channel_m2": round(float(new_ch.sum() * g.area)),
                "abandoned_channel_m2": round(float(aband.sum() * g.area)),
                "control_reach_water_change_pct": round(float(100 * (ctrlk - ctrl0) / max(1, ctrl0)), 1),
            }
        )
        if ls.any():
            features += g.features(ls, {"kind": "landslide", "epoch": k})
        if imp.any():
            features += g.features(imp, {"kind": "impoundment", "epoch": k})
        if new_ch.any():
            features += g.features(new_ch, {"kind": "new_channel", "epoch": k})
        if aband.any():
            features += g.features(aband, {"kind": "abandoned_channel", "epoch": k})
        epochs.append(
            {
                "date": date,
                "day": (k - 3) * 12,
                "label": ["Baseline pass", "Routine pass", "Landslide detected", "River diversion detected"][k],
                "sar_url": f"/scenarios/{sid}/sar_{k}.png",
                "coherence_url": f"/scenarios/{sid}/coherence_{k}.png" if k else None,
                "displacement_url": f"/scenarios/{sid}/displacement_{k}.png" if k else None,
            }
        )

    for k in range(1, 4):  # coherence over the detected slide footprint, for every pair
        metrics[k]["coherence_at_slide"] = round(float(np.median(coh_pairs[k][landslide_any])), 2)
    metrics[0]["coherence_at_slide"] = None

    # Creep on the ground that later failed, read only where the pre-failure pair stayed coherent.
    body = landslide_any & (coh_pairs[pre_fail_k] >= COHERENCE_MIN)
    precursor_cm = round(float(-np.median(pre_fail_cum[body])), 1) if body.any() else 0.0

    # River distance from the slide to the diverted reach, along the pre-event centreline.
    slide_row = int(np.mean(np.nonzero(landslide_any)[0]))
    shift_rows = [r for r in range(200, 390) if r in base_c and r in centroid_cols(water_det[3], r, r + 1)]
    shift_by_row = {r: abs(centroid_cols(water_det[3], r, r + 1)[r] - base_c[r]) for r in shift_rows}
    max_row = max(shift_by_row, key=shift_by_row.get)
    path = [(r, base_c[r]) for r in range(slide_row, max_row + 1) if r in base_c]
    river_km = sum(np.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]) for i in range(len(path) - 1)) * g.px / 1000

    before = [(r, base_c[r]) for r in range(0, g.rows, 4) if r in base_c]
    after_c = centroid_cols(water_det[3], 0, g.rows)
    after = [(r, after_c[r]) for r in range(0, g.rows, 4) if r in after_c]
    features.append(g.line(before, {"kind": "river_before", "label": "River centreline, baseline pass"}))
    features.append(g.line(after, {"kind": "river_after", "label": "River centreline, latest pass", "epoch": 3}))

    scenario = {
        "id": sid,
        "module": "landslide",
        "data_status": "SIMULATED",
        "title": "Upper-valley landslide and a river that moved",
        "location": {
            "name": "Illustrative valley, Chin Hills",
            "region": "Chin State, Myanmar",
            "center": [93.455, 23.205],
            "zoom": 12.2,
            "image_coordinates": g.corners(),
        },
        "story": {
            "headline": f"A river changed course. The cause was a landslide 12 days earlier, {river_km:.1f} km upstream",
            "context": "In remote mountain valleys nobody may see a landslide fall. The first sign downstream is a river that suddenly runs somewhere new, cutting off paths and fields. NISAR passes every 12 days through monsoon cloud, so the radar record can be read backwards like a forensic timeline.",
            "radar_insight": "Calm water reflects radar away like a mirror (specular reflection), so river channels look dark and a moved channel shows up as a dark line in a new place. A landslide strips forest, dropping the return by several dB, and destroys InSAR coherence between the passes either side of it. In the pass before it failed, InSAR also caught the slope creeping away from the satellite.",
        },
        "sensor": {**SENSOR, "polarization": "HH", "pixel_m": g.px, "looks": LOOKS},
        "epochs": epochs,
        "metrics": metrics,
        "thresholds": {
            "landslide_drop_db": 3.0,
            "landslide_min_m2": 25 * g.area,
            "water_db": -18.0,
            "channel_shift_m": 100,
            "new_channel_min_m2": 20000,
            "coherence_min": COHERENCE_MIN,
            "link_max_km": 20,
            "link_max_days": 36,
        },
        "linkage": {
            "river_distance_km": round(float(river_km), 1),
            "slide_is_upstream": slide_row < max_row,
            "precursor_creep_cm": precursor_cm,
            "precursor_pass": pre_fail_k,
        },
        "validation": {
            "note": "Detected landslide area on the latest pass compared with the simulation's own ground truth.",
            "recall": round(float((landslide_any & scar_truth).sum() / scar_truth.sum()), 3),
            "precision": round(float((landslide_any & scar_truth).sum() / max(1, landslide_any.sum())), 3),
        },
        "geojson": {"type": "FeatureCollection", "features": features},
    }
    write(scenario, out)
    return scenario


if __name__ == "__main__":
    for s in (build_mining(), build_landslide()):
        print(s["id"], json.dumps(s["metrics"][-1]), json.dumps(s["validation"]), json.dumps(s.get("linkage", {})))
