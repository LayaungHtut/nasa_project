"""HH/HV polarization comparison and HH change map for a processed event.

CLI usage (same AOI, filter and threshold as the served event):
    python -m services.processing.polarimetry \\
        --baseline data/raw/<baseline>.h5 --post-event data/raw/<post>.h5 \\
        --baseline-granule-id <id> --post-event-granule-id <id> \\
        --aoi-lat 17.058 --aoi-lon 96.088 --aoi-half-width-km 7 \\
        --threshold-db -9.54 --lee-filter-size 3 \\
        --event-id yangon-track40-frame10

Writes to data/processed/<event-id>/:
    baseline_hv.png, post_event_hv.png  -- speckle-filtered HV quicklooks
    difference_hh.png                   -- RGBA map of HH change (repeat minus baseline, dB)
    polarization.json                   -- per-date HH/HV statistics, the product's own
                                           RFI/noise metadata, and a rule-based HV usability check

Does not modify metadata.json, statistics.json or change.geojson. The water
classes reuse change_detection exactly as pipeline_flood does, so the pixel
counts here must match that event's statistics.json (checked on write).
See docs/science/polarization-analysis.md for the interpretation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import utm
from PIL import Image
from scipy.ndimage import uniform_filter

from services.processing.change_detection import new_inundation_mask, to_db, water_mask
from services.processing.io_gcov import read_gcov_layer_window
from services.processing.speckle import lee_filter

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

CALIBRATION_TMPL = "/science/LSAR/GCOV/metadata/calibrationInformation/frequency{freq}"
PARAMETERS_PATH = "/science/LSAR/GCOV/metadata/processingInformation/parameters"

HV_RANGE_DB = (-12.0, 2.0)
"""HV display stretch. Wider than the HH range (-25..-5 dB) would saturate this
AOI's HV to white; the range is reported in polarization.json and the legend."""

DIFFERENCE_LIMIT_DB = 3.0
DIFFERENCE_FLOOR_DB = 1.0
DIFFERENCE_DISPLAY_SMOOTHING = 5
"""The drawn change map is a 5x5 mean of the dB difference, so residual speckle
does not dominate it. Statistics in polarization.json use the unsmoothed difference."""
"""Changes within +-1 dB are drawn transparent: that is ordinary speckle and
pass-to-pass variability after a 3x3 filter, not a change worth drawing."""


def hv_preview_band(db_image: np.ndarray, lo: float = HV_RANGE_DB[0], hi: float = HV_RANGE_DB[1]) -> np.ndarray:
    clipped = np.nan_to_num(np.clip(db_image, lo, hi), nan=lo)
    return ((clipped - lo) / (hi - lo) * 255).astype(np.uint8)


def difference_rgba(diff_db: np.ndarray, limit: float = DIFFERENCE_LIMIT_DB, floor: float = DIFFERENCE_FLOOR_DB) -> np.ndarray:
    """Blue where the repeat scene is darker, orange where it is brighter.
    Opacity grows from `floor` to `limit` dB; NaN and small changes are clear."""
    d = np.nan_to_num(diff_db, nan=0.0)
    strength = np.clip((np.abs(d) - floor) / (limit - floor), 0.0, 1.0)
    rgba = np.zeros(d.shape + (4,), dtype=np.uint8)
    darker = d < 0
    rgba[darker] = (59, 130, 246, 0)  # blue-500
    rgba[~darker] = (249, 115, 22, 0)  # orange-500
    rgba[..., 3] = (strength * 230).astype(np.uint8)
    return rgba


def cross_track_ramp_db(db_image: np.ndarray, edge_fraction: float = 0.1) -> float:
    """Median of the right-most columns minus the left-most columns. A surface
    signal has no reason to brighten steadily across a 14 km AOI; a large value
    is a signature of an instrument or interference artifact."""
    n = max(1, int(db_image.shape[1] * edge_fraction))
    return round(float(np.nanmedian(db_image[:, -n:]) - np.nanmedian(db_image[:, :n])), 2)


def class_summary(mask: np.ndarray, layers: dict[str, dict[str, np.ndarray]]) -> dict:
    out: dict = {"pixels": int(mask.sum())}
    for pol, dates in layers.items():
        out[pol] = {
            date: (round(float(np.nanmedian(arr[mask])), 2) if mask.any() else None) for date, arr in dates.items()
        }
    return out


STABLE_LAND_SHIFT_DB = 1.0
"""Pixels that are land on both dates are the reference surface: if HV moves
by more than this between dates while HH stays within half of it, the HV change
is attributed to the observation, not the surface."""


def assess_hv(per_date: list[dict], stable_land: dict) -> dict:
    """Rule-based usability check. HV over natural surfaces is normally several
    dB below HH, and an unchanged reference surface should read the same on both
    dates. If either fails, HV is not interpreted as surface information."""
    reasons = []
    if all(d["median_db"]["HV"] > d["median_db"]["HH"] for d in per_date):
        reasons.append("HV median exceeds HH median on every date; over natural surfaces HV is normally several dB lower.")
    hh_shift = abs(stable_land["HH"]["repeat"] - stable_land["HH"]["baseline"])
    hv_shift = abs(stable_land["HV"]["repeat"] - stable_land["HV"]["baseline"])
    if hv_shift > STABLE_LAND_SHIFT_DB and hh_shift < STABLE_LAND_SHIFT_DB / 2:
        reasons.append(
            f"Over pixels classified as land on both dates, HV shifts {hv_shift:.2f} dB between dates while HH shifts {hh_shift:.2f} dB."
        )
    return {"hv_usable_for_interpretation": not reasons, "reasons": reasons}


def _read_product_quality(h5_path: str, freq: str, x_bounds: tuple[float, float], y_bounds: tuple[float, float]) -> dict:
    with h5py.File(h5_path, "r") as f:
        cal = f[CALIBRATION_TMPL.format(freq=freq)]
        rfi = {pol: round(float(cal[f"{pol}/rfiLikelihood"][()]), 3) for pol in ("HH", "HV")}
        neb_group = cal["noiseEquivalentBackscatter"]
        x, y = neb_group["xCoordinates"][()], neb_group["yCoordinates"][()]
        cols = (x >= x_bounds[0]) & (x <= x_bounds[1])
        rows = (y >= y_bounds[0]) & (y <= y_bounds[1])
        neb = {}
        for pol in ("HH", "HV"):
            grid = neb_group[pol][()][np.ix_(rows, cols)]
            neb[pol] = round(float(10 * np.log10(np.nanmean(grid))), 2) if grid.size else None
        params = f[PARAMETERS_PATH]
        flags = {
            "noise_correction_applied": params["noiseCorrectionApplied"][()] == b"True",
            "rfi_mitigation_applied": params["rfiMitigationApplied"][()] == b"True",
        }
    return {"rfi_likelihood": rfi, "noise_equivalent_backscatter_db": neb, "flags": flags}


def run_polarimetry(
    *,
    event_id: str,
    hh: dict[str, np.ndarray],
    hv: dict[str, np.ndarray],
    quality: dict[str, dict],
    granules: dict[str, str],
    threshold_db: float,
    lee_filter_size: int,
    aoi: dict,
) -> dict:
    """`hh`/`hv` map "baseline"/"repeat" to speckle-filtered dB arrays."""
    baseline_water = water_mask(hh["baseline"], threshold_db)
    repeat_water = water_mask(hh["repeat"], threshold_db)
    classes = {
        "apparent_water_loss": new_inundation_mask(repeat_water, baseline_water),
        "new_inundation_candidate": new_inundation_mask(baseline_water, repeat_water),
        "water_both_dates": baseline_water & repeat_water,
        "land_both_dates": ~baseline_water & ~repeat_water,
    }
    layers = {"HH": hh, "HV": hv}
    diff = hh["repeat"] - hh["baseline"]

    per_date = []
    for date in ("baseline", "repeat"):
        per_date.append(
            {
                "date": date,
                "granule_id": granules[date],
                "rfi_likelihood": quality[date]["rfi_likelihood"],
                "noise_equivalent_backscatter_db": quality[date]["noise_equivalent_backscatter_db"],
                "median_db": {pol: round(float(np.nanmedian(layers[pol][date])), 2) for pol in layers},
                "cross_track_ramp_db": {pol: cross_track_ramp_db(layers[pol][date]) for pol in layers},
                "hh_hv_correlation": round(
                    float(np.corrcoef(hh[date].ravel()[::25], hv[date].ravel()[::25])[0, 1]), 3
                ),
            }
        )

    out_dir = PROCESSED_DIR / event_id
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(hv_preview_band(hv["baseline"]), mode="L").save(out_dir / "baseline_hv.png")
    Image.fromarray(hv_preview_band(hv["repeat"]), mode="L").save(out_dir / "post_event_hv.png")
    display_diff = uniform_filter(diff, DIFFERENCE_DISPLAY_SMOOTHING)
    Image.fromarray(difference_rgba(display_diff), mode="RGBA").save(out_dir / "difference_hh.png")

    loss = classes["apparent_water_loss"]
    summaries = {name: class_summary(mask, layers) for name, mask in classes.items()}
    record = {
        "event_id": event_id,
        "method": "polarimetric_quality_check_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "granules": granules,
            "aoi": aoi,
            "lee_filter_size": lee_filter_size,
            "threshold_db": threshold_db,
            "water_classes_from": "HH only (same rule as pipeline_flood)",
        },
        "display": {
            "hv_range_db": list(HV_RANGE_DB),
            "difference_range_db": [-DIFFERENCE_LIMIT_DB, DIFFERENCE_LIMIT_DB],
            "difference_transparent_below_db": DIFFERENCE_FLOOR_DB,
            "difference_display_smoothing": f"{DIFFERENCE_DISPLAY_SMOOTHING}x{DIFFERENCE_DISPLAY_SMOOTHING} mean",
        },
        "layers": {
            "baseline_hv_url": f"/data/processed/{event_id}/baseline_hv.png",
            "post_event_hv_url": f"/data/processed/{event_id}/post_event_hv.png",
            "difference_hh_url": f"/data/processed/{event_id}/difference_hh.png",
        },
        "product_flags": {
            date: quality[date]["flags"] for date in ("baseline", "repeat")
        },
        "dates": per_date,
        "classes": summaries,
        "hh_difference_db": {
            "aoi_median": round(float(np.nanmedian(diff)), 2),
            "aoi_p05": round(float(np.nanpercentile(diff, 5)), 2),
            "aoi_p95": round(float(np.nanpercentile(diff, 95)), 2),
            "apparent_water_loss_median": round(float(np.nanmedian(diff[loss])), 2) if loss.any() else None,
            "display_fraction_brighter": round(float((display_diff > DIFFERENCE_FLOOR_DB).mean()), 4),
            "display_fraction_darker": round(float((display_diff < -DIFFERENCE_FLOOR_DB).mean()), 4),
        },
        "hv_assessment": assess_hv(per_date, summaries["land_both_dates"]),
    }

    stats_path = out_dir / "statistics.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text())
        expected = (stats["water_loss_pixels"], stats["new_inundation_pixels"])
        got = (record["classes"]["apparent_water_loss"]["pixels"], record["classes"]["new_inundation_candidate"]["pixels"])
        if expected != got:
            raise ValueError(f"Water classes {got} do not match statistics.json {expected}; check AOI/threshold/filter.")
        record["inputs"]["matches_statistics_json"] = True

    (out_dir / "polarization.json").write_text(json.dumps(record, indent=2))
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--post-event", required=True)
    parser.add_argument("--baseline-granule-id", required=True)
    parser.add_argument("--post-event-granule-id", required=True)
    parser.add_argument("--freq", default="A")
    parser.add_argument("--aoi-lat", type=float, required=True)
    parser.add_argument("--aoi-lon", type=float, required=True)
    parser.add_argument("--aoi-half-width-km", type=float, required=True)
    parser.add_argument("--threshold-db", type=float, required=True)
    parser.add_argument("--lee-filter-size", type=int, required=True)
    args = parser.parse_args()

    easting, northing, _, _ = utm.from_latlon(args.aoi_lat, args.aoi_lon)
    half = args.aoi_half_width_km * 1000.0
    paths = {"baseline": args.baseline, "repeat": args.post_event}
    granules = {"baseline": args.baseline_granule_id, "repeat": args.post_event_granule_id}

    hh, hv, quality = {}, {}, {}
    for date, path in paths.items():
        for pol, target in (("HHHH", hh), ("HVHV", hv)):
            layer = read_gcov_layer_window(path, granules[date], easting, northing, half, args.freq, pol)
            target[date] = to_db(lee_filter(layer.backscatter, size=args.lee_filter_size))
        quality[date] = _read_product_quality(
            path, args.freq, (easting - half, easting + half), (northing - half, northing + half)
        )

    record = run_polarimetry(
        event_id=args.event_id,
        hh=hh,
        hv=hv,
        quality=quality,
        granules=granules,
        threshold_db=args.threshold_db,
        lee_filter_size=args.lee_filter_size,
        aoi={"lat": args.aoi_lat, "lon": args.aoi_lon, "half_width_km": args.aoi_half_width_km},
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
