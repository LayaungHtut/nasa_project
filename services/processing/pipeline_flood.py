"""End-to-end flood/water-extent change-detection pipeline.

CLI usage:
    python -m services.processing.pipeline_flood --mode fixture --event-id demo-yangon-fixture

    python -m services.processing.pipeline_flood --mode real \\
        --baseline data/raw/<baseline>.h5 --post-event data/raw/<post>.h5 \\
        --baseline-granule-id <id> --post-event-granule-id <id> \\
        --aoi-lat 16.8 --aoi-lon 96.15 --aoi-half-width-km 15 \\
        --event-id <event-id>

Writes to data/processed/<event-id>/:
    baseline_db.npy, post_event_db.npy    -- speckle-filtered dB backscatter
    change_mask.npy                        -- boolean new-inundation mask
    baseline.png, post_event.png, change.png, preview.png -- quicklooks
    change.geojson                         -- vectorized change polygons (WGS84)
    metadata.json                          -- ChangeEvent record per docs/api/api-contract.md

Never writes a "REAL" data_status unless --mode real was used with actual
GCOV files read via services.processing.io_gcov. Fixture runs are always
stamped SYNTHETIC_PLACEHOLDER -- see docs/handoff/demo-data.md.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import utm
from PIL import Image

from services.processing.change_detection import change_stats, new_inundation_mask, to_db, water_mask
from services.processing.fixtures import make_fixture_pair
from services.processing.geo import bbox_wgs84, corner_coordinates, pixel_area_m2, utm_zone_from_epsg
from services.processing.io_gcov import read_gcov_layer, read_gcov_layer_window
from services.processing.speckle import lee_filter
from services.processing.vectorize import change_mask_to_geojson

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

_GRANULE_DATE_RE = re.compile(r"_(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})_")


def _parse_acquisition_from_granule_id(granule_id: str, default: str) -> str:
    """Real NISAR granule IDs encode their zeroDopplerStartTime in the
    filename (confirmed against the real downloaded granules, e.g.
    ..._20260827T230239_...). Falls back to `default` if the id doesn't
    match (e.g. the synthetic fixture's placeholder id)."""
    m = _GRANULE_DATE_RE.search(granule_id)
    if not m:
        return default
    y, mo, d, hh, mm, ss = m.groups()
    return f"{y}-{mo}-{d}T{hh}:{mm}:{ss}Z"


def _db_to_preview_band(db_image: np.ndarray, lo: float = -25.0, hi: float = -5.0) -> np.ndarray:
    clipped = np.nan_to_num(np.clip(db_image, lo, hi), nan=lo)
    return ((clipped - lo) / (hi - lo) * 255).astype(np.uint8)


DEFAULT_DISPLAY_RANGE_DB = (-25.0, -5.0)


def _write_preview_images(
    baseline_db: np.ndarray,
    post_db: np.ndarray,
    change_mask: np.ndarray,
    out_dir: Path,
    display_range_db: tuple[float, float] = DEFAULT_DISPLAY_RANGE_DB,
) -> None:
    """Both dates share one grayscale range so brightness is comparable."""
    b = _db_to_preview_band(baseline_db, *display_range_db)
    p = _db_to_preview_band(post_db, *display_range_db)
    c = np.where(change_mask, 255, p).astype(np.uint8)
    Image.fromarray(b, mode="L").save(out_dir / "baseline.png")
    Image.fromarray(p, mode="L").save(out_dir / "post_event.png")
    Image.fromarray(c, mode="L").save(out_dir / "change.png")
    panel = np.concatenate([b, p, c], axis=1)
    Image.fromarray(panel, mode="L").save(out_dir / "preview.png")


def run_pipeline(
    *,
    event_id: str,
    location_name: str,
    baseline_db_source: np.ndarray,
    post_db_source: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    zone_number: int,
    zone_letter: str,
    baseline_granule_id: str,
    post_event_granule_id: str,
    baseline_acquisition: str,
    post_event_acquisition: str,
    data_status: str,
    mask_valid: np.ndarray | None = None,
    threshold_db: float | None = None,
    lee_filter_size: int = 5,
    product_fields: dict | None = None,
    display_range_db: tuple[float, float] = DEFAULT_DISPLAY_RANGE_DB,
) -> dict:
    """`product_fields` (e.g. polarization, frequency_band) is copied onto
    both source_products records -- only pass what was actually read."""
    baseline_filt = lee_filter(baseline_db_source, size=lee_filter_size)
    post_filt = lee_filter(post_db_source, size=lee_filter_size)

    baseline_dbimg = to_db(baseline_filt)
    post_dbimg = to_db(post_filt)

    threshold_kwargs = {} if threshold_db is None else {"threshold_db": threshold_db}
    baseline_water = water_mask(baseline_dbimg, **threshold_kwargs)
    post_water = water_mask(post_dbimg, **threshold_kwargs)
    change_mask = new_inundation_mask(baseline_water, post_water)
    # Symmetric check, per audit: report water LOST as well as water GAINED.
    # A large asymmetry between the two (much more water at baseline than
    # post-event, or vice versa) is itself a finding to disclose, not to
    # bury -- see docs/science/real-data-validation.md.
    water_loss_mask = new_inundation_mask(post_water, baseline_water)

    px_area = pixel_area_m2(x_coords, y_coords)
    stats = change_stats(change_mask, px_area, valid_mask=mask_valid)
    if threshold_db is not None:
        stats["threshold_db"] = threshold_db  # change_stats() only knows the module default otherwise

    # Full audit trail -- every number a reviewer might ask to trace, computed
    # directly from the actual arrays, never hand-entered. See
    # docs/science/real-data-validation.md "Reproducibility" section.
    total_pixels = int(change_mask.size)
    baseline_water_pixels = int(baseline_water.sum())
    post_water_pixels = int(post_water.sum())
    water_loss_pixels = int(water_loss_mask.sum())
    aoi_area_km2 = round(total_pixels * px_area / 1e6, 3)
    statistics = {
        "total_pixels": total_pixels,
        "aoi_area_km2": aoi_area_km2,
        "pixel_area_m2": px_area,
        "baseline_water_pixels": baseline_water_pixels,
        "baseline_water_area_km2": round(baseline_water_pixels * px_area / 1e6, 3),
        "post_event_water_pixels": post_water_pixels,
        "post_event_water_area_km2": round(post_water_pixels * px_area / 1e6, 3),
        "new_inundation_pixels": stats["changed_pixels"],
        "new_inundation_area_km2": stats["change_area_km2"],
        "water_loss_pixels": water_loss_pixels,
        "water_loss_area_km2": round(water_loss_pixels * px_area / 1e6, 3),
        "note": (
            "baseline_water_pixels vs post_event_water_pixels shows a large raw asymmetry "
            "(see real-data-validation.md) -- likely surface-roughness/acquisition-geometry "
            "sensitivity of this threshold-based method, not necessarily true water-level change. "
            "Disclosed here rather than only reporting the smaller new_inundation figure."
        ),
        "valid_pixels": stats["valid_pixels"],
        "valid_fraction": stats["valid_fraction"],
        "threshold_db": stats["threshold_db"],
        "min_cluster_pixels": stats["min_cluster_pixels"],
        "lee_filter_size": lee_filter_size,
        "detection_score": stats["confidence"],
        "detection_score_formula": "0.5 * valid_fraction + 0.5 * min(1, new_inundation_pixels / 2000)",
    }

    out_dir = PROCESSED_DIR / event_id
    out_dir.mkdir(parents=True, exist_ok=True)

    np.save(out_dir / "baseline_db.npy", baseline_dbimg)
    np.save(out_dir / "post_event_db.npy", post_dbimg)
    np.save(out_dir / "change_mask.npy", change_mask)
    _write_preview_images(baseline_dbimg, post_dbimg, change_mask, out_dir, display_range_db)

    geojson = change_mask_to_geojson(change_mask, x_coords, y_coords, zone_number, zone_letter)
    (out_dir / "change.geojson").write_text(json.dumps(geojson, indent=2))
    (out_dir / "statistics.json").write_text(json.dumps(statistics, indent=2))

    bbox = bbox_wgs84(x_coords, y_coords, zone_number, zone_letter)
    corners = corner_coordinates(x_coords, y_coords, zone_number, zone_letter)
    center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]

    event = {
        "id": event_id,
        "title": f"{location_name} water-extent change",
        "phenomenon": "flood_extent_change",
        "data_status": data_status,  # "REAL" | "SYNTHETIC_PLACEHOLDER" -- see demo-data.md
        "location": {"name": location_name, "bbox": bbox, "center": center},
        "observation_dates": {"baseline": baseline_acquisition, "post_event": post_event_acquisition},
        "source_products": [
            {
                "mission": "NISAR",
                "product": "GCOV",
                "granule_id": baseline_granule_id,
                "daac": "ASF",
                "acquisition_date": baseline_acquisition,
                **(product_fields or {}),
            },
            {
                "mission": "NISAR",
                "product": "GCOV",
                "granule_id": post_event_granule_id,
                "daac": "ASF",
                "acquisition_date": post_event_acquisition,
                **(product_fields or {}),
            },
        ],
        "processing": {
            "method": "backscatter_threshold_change_detection_v1",
            "version": "1.0.0",
            "threshold_db": stats["threshold_db"],
            "min_cluster_pixels": stats["min_cluster_pixels"],
            "speckle_filter_size": lee_filter_size,  # structured, machine-readable -- see real-data-validation.md for why this run used 3, not the 5 module default
            "limitations": [
                "Flooded vegetation (forest, tall crops) may not be detected -- double-bounce scattering can increase, not decrease, backscatter under a flooded canopy.",
                "Smooth non-water surfaces (bare soil, some paved areas, radar shadow) can produce false positives.",
                "Threshold is tuned for this AOI/scene and is not claimed to generalize globally without recalibration.",
                "Acquisition dates reflect whatever NISAR happened to image, not necessarily the true event peak.",
                "This is a new-inundation CANDIDATE, not a confirmed flood -- no independent ground truth was used to verify it.",
                "Surface roughness/wind can raise water's backscatter above threshold without the water disappearing -- a large apparent decrease in detected water between two dates is not, by itself, evidence of real water loss (see docs/science/real-data-validation.md, 'Investigation 2').",
                "Small area figures (well under 1 km2) can be sensitive to threshold/filter choice by an order of magnitude or more -- treat as an illustrative estimate from this specific configuration, not a precise measurement, unless a sensitivity sweep has confirmed stability.",
            ],
        },
        "results": {
            "change_area_km2": stats["change_area_km2"],
            "confidence": stats["confidence"],  # kept for API/frontend compatibility -- see confidence_type below
            "confidence_type": "heuristic_detection_score",  # NOT a statistical probability -- see docs/science/real-data-validation.md
            "changed_pixels": stats["changed_pixels"],
            "valid_fraction": stats["valid_fraction"],
        },
        "statistics_url": f"/data/processed/{event_id}/statistics.json",
        "tiles": {
            "preview_url": f"/data/processed/{event_id}/preview.png",
            "baseline_preview_url": f"/data/processed/{event_id}/baseline.png",
            "post_event_preview_url": f"/data/processed/{event_id}/post_event.png",
            "change_preview_url": f"/data/processed/{event_id}/change.png",
            "corner_coordinates": corners,
            "display_range_db": list(display_range_db),
        },
        "change_geometry_url": f"/data/processed/{event_id}/change.geojson",
        "ai_explanation": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    (out_dir / "metadata.json").write_text(json.dumps(event, indent=2))
    return event


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fixture", "real"], required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--location-name", default="Yangon Region, Myanmar (synthetic AOI)")
    parser.add_argument("--baseline", help="path to baseline .h5 (--mode real)")
    parser.add_argument("--post-event", help="path to post-event .h5 (--mode real)")
    parser.add_argument("--baseline-granule-id")
    parser.add_argument("--post-event-granule-id")
    parser.add_argument("--baseline-acquisition", help="override the auto-parsed ISO 8601 acquisition timestamp for baseline")
    parser.add_argument("--post-event-acquisition", help="override the auto-parsed ISO 8601 acquisition timestamp for post-event")
    parser.add_argument("--freq", default="A")
    parser.add_argument("--pol", default="HHHH")
    parser.add_argument("--aoi-lat", type=float, default=16.8, help="AOI center latitude (--mode real)")
    parser.add_argument("--aoi-lon", type=float, default=96.15, help="AOI center longitude (--mode real)")
    parser.add_argument("--aoi-half-width-km", type=float, default=15.0)
    parser.add_argument("--bbox", nargs=4, type=float, default=None, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"), help="AOI bounding box (min_lon min_lat max_lon max_lat)")
    parser.add_argument("--stride", type=int, default=1, help="Decimation stride factor (e.g. 4 for 40m resolution)")
    parser.add_argument("--threshold-db", type=float, default=None, help="override the default water threshold after inspecting the real backscatter distribution")
    parser.add_argument("--display-range-db", nargs=2, type=float, default=list(DEFAULT_DISPLAY_RANGE_DB), metavar=("LO", "HI"), help="shared grayscale range for both dates' previews; choose it from the scene's backscatter distribution so the previews are not saturated")
    parser.add_argument("--lee-filter-size", type=int, default=5, help="Lee speckle filter window; a smaller window (e.g. 3) preserves narrower water features at the cost of more residual speckle")
    args = parser.parse_args()

    if args.mode == "fixture":
        fx = make_fixture_pair()
        event = run_pipeline(
            event_id=args.event_id,
            location_name=args.location_name,
            baseline_db_source=fx.baseline,
            post_db_source=fx.post_event,
            x_coords=fx.x_coords,
            y_coords=fx.y_coords,
            zone_number=fx.zone_number,
            zone_letter=fx.zone_letter,
            baseline_granule_id=fx.baseline_granule_id,
            post_event_granule_id=fx.post_event_granule_id,
            baseline_acquisition="SYNTHETIC-NO-REAL-ACQUISITION",
            post_event_acquisition="SYNTHETIC-NO-REAL-ACQUISITION",
            data_status="SYNTHETIC_PLACEHOLDER",
            threshold_db=args.threshold_db,
            lee_filter_size=args.lee_filter_size,
            display_range_db=tuple(args.display_range_db),
        )
    else:
        if not (args.baseline and args.post_event and args.baseline_granule_id and args.post_event_granule_id):
            parser.error("--mode real requires --baseline, --post-event, --baseline-granule-id, --post-event-granule-id")

        if args.bbox is not None:
            baseline_layer = read_gcov_layer(
                args.baseline,
                args.baseline_granule_id,
                args.freq,
                args.pol,
                bbox_wgs84=tuple(args.bbox),
                stride=args.stride,
            )
            post_layer = read_gcov_layer(
                args.post_event,
                args.post_event_granule_id,
                args.freq,
                args.pol,
                bbox_wgs84=tuple(args.bbox),
                stride=args.stride,
            )
        else:
            center_easting, center_northing, _, _ = utm.from_latlon(args.aoi_lat, args.aoi_lon)
            half_width_m = args.aoi_half_width_km * 1000.0

            baseline_layer = read_gcov_layer_window(
                args.baseline, args.baseline_granule_id, center_easting, center_northing, half_width_m, args.freq, args.pol
            )
            post_layer = read_gcov_layer_window(
                args.post_event, args.post_event_granule_id, center_easting, center_northing, half_width_m, args.freq, args.pol
            )

        if baseline_layer.epsg is None:
            parser.error(f"Could not read a projection/EPSG from {args.baseline} -- cannot geolocate this AOI.")
        zone_number, zone_letter = utm_zone_from_epsg(baseline_layer.epsg)

        # GCOV's own quality mask: 0 = invalid (partially focused radar
        # samples), 1..N = valid subswath number, 255 = outside the radar
        # acquisition extent. Combine with a NaN check on both dates'
        # backscatter (GCOV's documented _FillValue for HHHH/HVHV).
        valid = np.ones(baseline_layer.backscatter.shape, dtype=bool)
        for layer in (baseline_layer, post_layer):
            if layer.mask is not None:
                valid &= (layer.mask > 0) & (layer.mask < 255)
        valid &= ~np.isnan(baseline_layer.backscatter) & ~np.isnan(post_layer.backscatter)

        b_acq = args.baseline_acquisition or _parse_acquisition_from_granule_id(args.baseline_granule_id, args.baseline)
        p_acq = args.post_event_acquisition or _parse_acquisition_from_granule_id(args.post_event_granule_id, args.post_event)

        event = run_pipeline(
            event_id=args.event_id,
            location_name=args.location_name,
            baseline_db_source=baseline_layer.backscatter,
            post_db_source=post_layer.backscatter,
            x_coords=baseline_layer.x_coords,
            y_coords=baseline_layer.y_coords,
            zone_number=zone_number,
            zone_letter=zone_letter,
            baseline_granule_id=baseline_layer.granule_id,
            post_event_granule_id=post_layer.granule_id,
            baseline_acquisition=b_acq,
            post_event_acquisition=p_acq,
            data_status="REAL",
            mask_valid=valid,
            threshold_db=args.threshold_db,
            lee_filter_size=args.lee_filter_size,
            product_fields={
                # GCOV diagonal term "HHHH" is the HH channel; /science/LSAR is the L-band instrument.
                "polarization": args.pol[:2],
                "frequency_band": "L-band (24 cm)",
            },
            display_range_db=tuple(args.display_range_db),
        )

    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()
