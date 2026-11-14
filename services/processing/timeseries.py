"""Eight-date HH time series for the Hlawga study area (NISAR Track 40 / Frame 10).

CLI usage (same AOI, filter and threshold as the served event):
    python -m services.processing.timeseries --event-id yangon-track40-frame10

Finds every Track 40 / Frame 10 GCOV acquisition over the AOI on ASF, reads only
the AOI window of each (from data/raw/ if the file is there, otherwise through
remote_gcov's HTTP range reads), and writes to data/processed/<event-id>/:
    timeseries/hh_<YYYYMMDD>.png  -- HH quicklook per date, the event's shared dB range
    timeseries.json               -- per-date statistics by ESA WorldCover land-cover class

Land cover comes from ESA WorldCover 2021 v200, an independent 10 m map, so the
paddy, reservoir and built-up regions are not defined from the radar itself. Built-up
land is the stability reference: its HH should not move much between passes, so a
shift there points to calibration or processing, not to the surface.

Expects data/raw/worldcover/ESA_WorldCover_10m_2021_v200_N15E096_Map.tif, from
https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N15E096_Map.tif
"""

from __future__ import annotations

import argparse
import functools
import json
import re
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asf_search as asf
import numpy as np
import tifffile
import utm
from PIL import Image
from scipy.ndimage import binary_erosion, uniform_filter

from services.processing.auth import get_authenticated_session
from services.processing.change_detection import new_inundation_mask, to_db, water_mask
from services.processing.geo import pixel_area_m2
from services.processing.io_gcov import GcovLayer, read_gcov_layer_window
from services.processing.pipeline_flood import _db_to_preview_band
from services.processing.remote_gcov import open_remote_granule
from services.processing.speckle import lee_filter
from services.processing.weather import _parse_utc, build_record, fetch

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
VALIDATION_DIR = REPO_ROOT / "data" / "validation"
RAW_DIR = REPO_ROOT / "data" / "raw"
WORLDCOVER_TILE = RAW_DIR / "worldcover" / "ESA_WorldCover_10m_2021_v200_N15E096_Map.tif"
WORLDCOVER_ORIGIN = (96.0, 18.0)  # tile's upper-left lon/lat, from its ModelTiepointTag
WORLDCOVER_STEP = 1 / 12000  # degrees per pixel
WORLDCOVER_CLASSES = {10: "tree_cover", 30: "grassland", 40: "cropland", 50: "built_up", 80: "permanent_water", 90: "herbaceous_wetland"}
MIN_CLASS_FRACTION = 0.01
STABLE_CLASS = "built_up"
REFERENCE_CLASS = "tree_cover"
EROSION_PX = 2  # 20 m: drop class-edge pixels that mix land cover
PIXEL_SMOOTH = 7  # 70 m mean before per-pixel tests; fields are larger, speckle is not
RICE_RISE_DB = 1.5
COHERENCE_LAG_PX = 15  # twice the smoothing window  # brightening after a pixel's darkest pass that counts as a growth signal
CACHE_DIR = RAW_DIR / "timeseries_cache"
# One hue, three clearly separated steps, light enough to read on the dark radar map: early, around the darkest pass, later.
PERIOD_COLORS = ("#3f8f5a", "#a3e08f", "#f0ffc0")
# Land-cover layer: the app's chart colours for these classes (validated colourblind-safe as a set).
LANDCOVER_MAP_CLASSES = {40: ("cropland", "Paddy fields", "#199e70"), 80: ("permanent_water", "Reservoir", "#3987e5"), 50: ("built_up", "Built-up", "#d95926")}
_CRID_RE = re.compile(r"_(P\d{5})_")


def track_granules(lat: float, lon: float, track: int, frame: int) -> list[dict]:
    results = asf.search(platform=["NISAR"], processingLevel=["GCOV"], intersectsWith=f"POINT({lon} {lat})", maxResults=1000)
    rows = [
        {"granule_id": r.properties["fileID"], "date": r.properties["startTime"], "url": r.properties["url"]}
        for r in results
        if r.properties.get("pathNumber") == track and r.properties.get("frameNumber") == frame
    ]
    return sorted(rows, key=lambda row: row["date"])


def read_tiff_window(path: Path, r0: int, r1: int, c0: int, c1: int) -> np.ndarray:
    """Rows r0:r1, columns c0:c1 of a tiled single-band TIFF, decoding only the tiles they touch."""
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        th, tw = page.tilelength, page.tilewidth
        across = -(-page.imagewidth // tw)
        out = np.zeros((r1 - r0, c1 - c0), page.dtype)
        for tr in range(r0 // th, (r1 - 1) // th + 1):
            for tc in range(c0 // tw, (c1 - 1) // tw + 1):
                i = tr * across + tc
                tif.filehandle.seek(page.dataoffsets[i])
                tile = page.decode(tif.filehandle.read(page.databytecounts[i]), i)[0].reshape(th, tw)
                ys, xs = max(r0, tr * th), max(c0, tc * tw)
                ye, xe = min(r1, (tr + 1) * th), min(c1, (tc + 1) * tw)
                out[ys - r0:ye - r0, xs - c0:xe - c0] = tile[ys - tr * th:ye - tr * th, xs - tc * tw:xe - tc * tw]
        return out


def worldcover_classes(x_coords: np.ndarray, y_coords: np.ndarray, zone_number: int) -> np.ndarray:
    """Nearest WorldCover class at each UTM pixel center."""
    east, north = np.meshgrid(x_coords, y_coords)
    lat, lon = utm.to_latlon(east, north, zone_number, northern=True)
    rows = ((WORLDCOVER_ORIGIN[1] - lat) / WORLDCOVER_STEP).astype(int)
    cols = ((lon - WORLDCOVER_ORIGIN[0]) / WORLDCOVER_STEP).astype(int)
    # Only the study area's tiles: decoding the whole 36000 x 36000 tile needs 1.3 GB.
    r0, c0 = rows.min(), cols.min()
    return read_tiff_window(WORLDCOVER_TILE, r0, rows.max() + 1, c0, cols.max() + 1)[rows - r0, cols - c0]


@functools.cache
def _session():
    return get_authenticated_session()


def read_window(g: dict, center_e: float, center_n: float, half_width_m: float, freq: str, pol: str, session) -> tuple[GcovLayer, str]:
    """AOI window for one granule: from the local cache, a local .h5, or ASF range reads."""
    cache = CACHE_DIR / f"{g['granule_id']}_{freq}_{pol}.npz"
    if cache.exists():
        z = np.load(cache)
        return GcovLayer(z["backscatter"], z["x"], z["y"], int(z["epsg"]), z["mask"], g["granule_id"], str(cache)), str(z["origin"])
    local = RAW_DIR / f"{g['granule_id']}.h5"
    origin = "local" if local.exists() else "remote"
    for attempt in range(3):
        try:
            with nullcontext(str(local)) if local.exists() else open_remote_granule(session(), g["url"]) as h5:
                layer = read_gcov_layer_window(h5, g["granule_id"], center_e, center_n, half_width_m, freq, pol)
            break
        except (OSError, TimeoutError, RuntimeError) as exc:  # network stalls; signed URLs also expire
            if attempt == 2 or origin == "local":
                raise
            print(f"  retrying {g['granule_id']} after {type(exc).__name__}", flush=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, backscatter=layer.backscatter, x=layer.x_coords, y=layer.y_coords, epsg=layer.epsg, mask=layer.mask, origin=origin)
    return layer, origin


def pixel_season(stack: list[np.ndarray], dates: list[dict], cores: dict, out_dir: Path, event_id: str, px_area: float) -> dict:
    """Per-pixel tests on the passes that share the first date's processing, with forest as a control.

    Medians can hide a few strongly changing fields. Here every 70 m neighbourhood is tested: did it
    brighten between the season's darkest and brightest paddy dates, and did it show a dark pass
    followed by a rise (a flooded field, then a growing crop)? Forest pixels go through the same tests;
    their pass rate is the false-positive rate from speckle and calibration noise.
    """
    same = [i for i, d in enumerate(dates) if d["processing_crid"] == dates[0]["processing_crid"]]
    rel = np.stack([uniform_filter(stack[i], PIXEL_SMOOTH) - dates[i]["hh_by_landcover"][REFERENCE_CLASS]["median_db"] for i in same])
    paddy = [dates[i]["relative_to_forest_db"]["cropland"] for i in same]
    low_t = int(np.argmin(paddy))
    peak_t = low_t + int(np.argmax(paddy[low_t:]))
    delta = rel[peak_t] - rel[low_t]

    darkest = np.argmin(rel, axis=0)
    max_after = np.maximum.accumulate(rel[::-1], axis=0)[::-1]
    rise = np.take_along_axis(max_after, darkest[None], 0)[0] - rel.min(axis=0)
    rice_like = rise >= RICE_RISE_DB

    # The smoothing window reaches PIXEL_SMOOTH // 2 px; shrink the cores so no window mixes classes.
    extra = max(0, PIXEL_SMOOTH // 2 - EROSION_PX)
    crop, forest = (binary_erosion(cores[c], iterations=extra) if extra else cores[c] for c in (40, 10))
    frac = lambda cond, region: round(float(cond[region].mean()), 3)
    # Group each field's darkest pass: before, within one pass of, or after the season's darkest paddy pass.
    period = np.where(darkest < low_t - 1, 0, np.where(darkest <= low_t + 1, 1, 2))
    bounds = [(0, low_t - 2), (max(0, low_t - 1), min(len(same) - 1, low_t + 1)), (low_t + 2, len(same) - 1)]
    rgba = np.zeros(darkest.shape + (4,), dtype=np.uint8)
    show = crop & rice_like
    for k, color in enumerate(PERIOD_COLORS):
        hit = show & (period == k)
        rgba[hit, :3] = [int(color[j:j + 2], 16) for j in (1, 3, 5)]
        rgba[hit, 3] = 220
    Image.fromarray(rgba, mode="RGBA").save(out_dir / "timeseries" / "darkest_pass.png")

    # Is timing organised in patches (fields) or random speckle? Compare neighbours COHERENCE_LAG_PX apart,
    # beyond the smoothing window, against the agreement spatially random labels would give.
    lab = np.where(show, period, -1)
    left, right = lab[:, :-COHERENCE_LAG_PX], lab[:, COHERENCE_LAG_PX:]
    both = (left >= 0) & (right >= 0)
    observed = float((left[both] == right[both]).mean())
    shares = np.bincount(period[show], minlength=3) / show.sum()
    chance = float((shares**2).sum())  # agreement expected if labels were spatially random

    return {
        "smoothing_px": PIXEL_SMOOTH,
        "core_erosion_px": EROSION_PX + extra,
        "compared_dates": {"darkest_paddy": dates[same[low_t]]["date"], "brightest_paddy_after": dates[same[peak_t]]["date"]},
        "brightened_over_1db": {"cropland": frac(delta > 1, crop), "forest_control": frac(delta > 1, forest)},
        "darkened_over_1db": {"cropland": frac(delta < -1, crop), "forest_control": frac(delta < -1, forest)},
        "rice_rise_threshold_db": RICE_RISE_DB,
        "dark_then_rise": {"cropland": frac(rice_like, crop), "forest_control": frac(rice_like, forest)},
        "timing_neighbour_agreement": {"lag_m": round(COHERENCE_LAG_PX * px_area**0.5, 1), "observed": round(observed, 3), "if_random": round(chance, 3)},
        "darkest_pass_periods": [
            {
                "from": dates[same[a]]["date"],
                "to": dates[same[b]]["date"],
                "cropland_km2": round(int((show & (period == k)).sum()) * px_area / 1e6, 2),
                "color": PERIOD_COLORS[k],
            }
            for k, (a, b) in enumerate(bounds)
            if a <= b
        ],
        "map_url": f"/data/processed/{event_id}/timeseries/darkest_pass.png",
    }


def add_relative_to_forest(dates: list[dict]) -> None:
    """Every class brightens and darkens together from pass to pass (a scene-wide offset), so
    differences from forest, the largest class, isolate what changed on each surface."""
    for d in dates:
        lc = d["hh_by_landcover"]
        d["relative_to_forest_db"] = {k: round(v["median_db"] - lc[REFERENCE_CLASS]["median_db"], 2) for k, v in lc.items() if k != REFERENCE_CLASS}


def stable_reference(dates: list[dict]) -> dict:
    by_version: dict[str, list[float]] = {}
    for d in dates:
        by_version.setdefault(d["processing_crid"], []).append(d["relative_to_forest_db"][STABLE_CLASS])
    return {
        "class": STABLE_CLASS,
        "relative_to": REFERENCE_CLASS,
        "range_db_by_processing_version": {v: round(max(x) - min(x), 2) for v, x in by_version.items()},
    }


def event_change_masks(out_dir: Path, threshold_db: float) -> dict[str, np.ndarray]:
    """The served event's two-date water loss and gain, recomputed from its own dB arrays."""
    base_water = water_mask(np.load(out_dir / "baseline_db.npy"), threshold_db)
    post_water = water_mask(np.load(out_dir / "post_event_db.npy"), threshold_db)
    return {
        "apparent_water_loss": new_inundation_mask(post_water, base_water),
        "new_inundation_candidate": new_inundation_mask(base_water, post_water),
    }


def event_change_by_landcover(masks: dict[str, np.ndarray], classes: np.ndarray, px_area: float, statistics: dict) -> dict:
    """Where the served event's water loss and gain fall, by WorldCover class."""
    out = {}
    for name, stat in (("apparent_water_loss", "water_loss_pixels"), ("new_inundation_candidate", "new_inundation_pixels")):
        mask = masks[name]
        assert int(mask.sum()) == statistics[stat], f"{name}: {int(mask.sum())} pixels != statistics.json {statistics[stat]}"
        out[name] = {
            "pixels": int(mask.sum()),
            "by_landcover_km2": {n: round(int((mask & (classes == c)).sum()) * px_area / 1e6, 3) for c, n in WORLDCOVER_CLASSES.items()},
        }
    return out


def landcover_map(classes: np.ndarray, water_loss: np.ndarray, out_dir: Path, event_id: str, px_area: float) -> dict:
    """Map layers: the classes behind the finding, and where the two-date water loss fell.

    Only three classes get a colour: on a map every colour must stay distinct from every
    other, and three is what a colourblind-safe palette supports. They keep the colours the
    charts use. Forest, grassland and the rest stay clear, so the radar image shows through.
    """
    rgba = np.zeros((*classes.shape, 4), np.uint8)
    rows = []
    for code, (key, label, color) in LANDCOVER_MAP_CLASSES.items():
        hit = classes == code
        rgba[hit] = (*(int(color[i:i + 2], 16) for i in (1, 3, 5)), 255)
        rows.append({"key": key, "label": label, "color": color, "area_km2": round(int(hit.sum()) * px_area / 1e6, 2)})
    Image.fromarray(rgba, mode="RGBA").save(out_dir / "timeseries" / "landcover.png")
    loss = np.zeros((*classes.shape, 4), np.uint8)
    loss[water_loss] = (255, 255, 255, 255)
    Image.fromarray(loss, mode="RGBA").save(out_dir / "timeseries" / "water_loss.png")
    return {
        "map_url": f"/data/processed/{event_id}/timeseries/landcover.png",
        "water_loss_url": f"/data/processed/{event_id}/timeseries/water_loss.png",
        "classes": rows,
        "uncoloured": "Forest, grassland and other land",
    }


def percentiles(values: np.ndarray) -> dict:
    p25, p50, p75 = np.percentile(values, [25, 50, 75])
    return {"p25_db": round(float(p25), 2), "median_db": round(float(p50), 2), "p75_db": round(float(p75), 2)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--track", type=int, default=40)
    parser.add_argument("--frame", type=int, default=10)
    parser.add_argument("--freq", default="A")
    parser.add_argument("--pol", default="HHHH")
    args = parser.parse_args()

    out_dir = PROCESSED_DIR / args.event_id
    metadata = json.loads((out_dir / "metadata.json").read_text())
    statistics = json.loads((out_dir / "statistics.json").read_text())
    threshold_db = metadata["processing"]["threshold_db"]
    filter_size = metadata["processing"]["speckle_filter_size"]
    display_range = tuple(metadata["tiles"]["display_range_db"])
    lat, lon = metadata["location"]["center"][1], metadata["location"]["center"][0]
    # The event AOI was read with --aoi-lat 17.058 --aoi-lon 96.088 --aoi-half-width-km 7 (real-data-validation.md).
    center_e, center_n, zone_number, _ = utm.from_latlon(17.058, 96.088)
    half_width_m = 7000.0

    granules = track_granules(lat, lon, args.track, args.frame)
    print(f"{len(granules)} Track {args.track} / Frame {args.frame} acquisitions found")
    (out_dir / "timeseries").mkdir(exist_ok=True)

    reference_grid = None
    classes = None
    cores = None
    stack = []
    dates = []
    for g in granules:
        layer, source = read_window(g, center_e, center_n, half_width_m, args.freq, args.pol, _session)
        print(f"{g['date']}  {source}  {g['granule_id']}", flush=True)

        grid = (layer.backscatter.shape, float(layer.x_coords[0]), float(layer.y_coords[0]))
        if reference_grid is None:
            reference_grid = grid
            classes = worldcover_classes(layer.x_coords, layer.y_coords, zone_number)
            # Core pixels only: a 10 m map resampled onto the radar grid mixes classes at their edges.
            cores = {code: binary_erosion(classes == code, iterations=EROSION_PX) for code in WORLDCOVER_CLASSES}
            px_area = pixel_area_m2(layer.x_coords, layer.y_coords)
        assert grid == reference_grid, f"{g['granule_id']} is not on the same grid as the first date: {grid} vs {reference_grid}"

        db = to_db(lee_filter(layer.backscatter, size=filter_size))
        valid = (layer.mask > 0) & (layer.mask < 255) & np.isfinite(layer.backscatter) if layer.mask is not None else np.isfinite(layer.backscatter)
        water = water_mask(db, threshold_db)

        stamp = g["date"][:10].replace("-", "")
        Image.fromarray(_db_to_preview_band(db, *display_range), mode="L").save(out_dir / "timeseries" / f"hh_{stamp}.png")

        by_class, full_mask_median = {}, {}
        for code, name in WORLDCOVER_CLASSES.items():
            region = cores[code] & valid
            if (classes == code).sum() < MIN_CLASS_FRACTION * classes.size:
                continue
            full = (classes == code) & valid
            # Brightness from core pixels; water-like area from the whole class, so areas add up.
            by_class[name] = {**percentiles(db[region]), "core_pixels": int(region.sum()), "pixels": int(full.sum()), "radar_water_fraction": round(float(water[full].mean()), 3)}
            full_mask_median[name] = float(np.median(db[full]))
        stack.append(db.astype(np.float32))

        dates.append({
            "date": g["date"],
            "granule_id": g["granule_id"],
            "collection": g["url"].split("/")[4],
            "processing_crid": (_CRID_RE.search(g["granule_id"]) or [None, None])[1],
            "read": source,
            "_full_mask_median": full_mask_median,
            "valid_fraction": round(float(valid.mean()), 4),
            # Counted over the whole window exactly as pipeline_flood does, so the event dates can be checked below.
            "water_pixels": int(water.sum()),
            "water_area_km2": round(int(water.sum()) * px_area / 1e6, 3),
            "hh_by_landcover": by_class,
            "frame_url": f"/data/processed/{args.event_id}/timeseries/hh_{stamp}.png",
        })

    by_date = {d["date"]: d for d in dates}
    for key, stat in (("baseline", "baseline_water_pixels"), ("post_event", "post_event_water_pixels")):
        got = by_date[metadata["observation_dates"][key]]["water_pixels"]
        assert got == statistics[stat], f"{key} water pixels {got} != statistics.json {statistics[stat]}"

    # Wind and rain at every pass, to test "wind roughens the reservoir" across all dates, not just two.
    whens = [_parse_utc(d["date"]) for d in dates]
    era5, metar_csv = fetch(17.058, 96.088, whens[0] - timedelta(days=1), whens[-1] + timedelta(days=1))
    raw_dir = VALIDATION_DIR / args.event_id / "weather"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "series-era5-open-meteo.json").write_text(json.dumps(era5))
    (raw_dir / "series-metar-vyyy.csv").write_text(metar_csv)
    weather = build_record(args.event_id, 17.058, 96.088, [d["date"] for d in dates], era5, metar_csv)
    for d, w in zip(dates, weather["dates"]):
        d["weather"] = {
            "era5_wind_ms": w["era5"]["wind_speed_ms"],
            "airport_max_wind_ms": w["metar"]["max_wind_ms"],
            "era5_rain_24h_mm": w["era5"]["rain_24h_mm"],
        }

    add_relative_to_forest(dates)
    # How much the forest-relative values move if class edges are kept (no erosion).
    erosion_shift: dict[str, float] = {}
    for d in dates:
        full = d.pop("_full_mask_median")
        for name, value in d["relative_to_forest_db"].items():
            shift = abs((full[name] - full[REFERENCE_CLASS]) - value)
            erosion_shift[name] = round(max(erosion_shift.get(name, 0.0), shift), 2)
    masks = event_change_masks(out_dir, threshold_db)
    record = {
        "event_id": args.event_id,
        "track": args.track,
        "frame": args.frame,
        "polarization": args.pol[:2],
        "inputs": {"threshold_db": threshold_db, "lee_filter_size": filter_size, "display_range_db": list(display_range), "aoi_half_width_km": half_width_m / 1000},
        "landcover_source": "ESA WorldCover 10 m 2021 v200 (tile N15E096), nearest-neighbour onto the radar grid",
        "landcover_fractions": {name: round(float((classes == code).mean()), 3) for code, name in WORLDCOVER_CLASSES.items() if (classes == code).mean() >= MIN_CLASS_FRACTION},
        "grid": {"x0": float(layer.x_coords[0]), "y0": float(layer.y_coords[0]), "shape": list(classes.shape), "epsg": layer.epsg},
        "landcover_mask_erosion_px": EROSION_PX,
        "erosion_sensitivity_max_db": erosion_shift,
        "stable_reference": stable_reference(dates),
        "event_change_by_landcover": event_change_by_landcover(masks, classes, px_area, statistics),
        "landcover_map": landcover_map(classes, masks["apparent_water_loss"], out_dir, args.event_id, px_area),
        "pixel_season": pixel_season(stack, dates, cores, out_dir, args.event_id, px_area),
        "dates": dates,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "timeseries.json").write_text(json.dumps(record, indent=2))
    for d in dates:
        lc = d["hh_by_landcover"]
        print(d["date"][:10], d["processing_crid"], f"wind {d['weather']['era5_wind_ms']:.1f}/{d['weather']['airport_max_wind_ms']}", f"water {d['water_area_km2']:6.3f} km2", "  ".join(f"{k} {v['median_db']:6.2f}" for k, v in lc.items()))
    print("stable reference:", record["stable_reference"])
    print("event change by land cover:", json.dumps(record["event_change_by_landcover"]))
    print("erosion sensitivity (max dB):", erosion_shift)
    print("pixel season:", json.dumps({k: v for k, v in record["pixel_season"].items() if k != "palette"}))


if __name__ == "__main__":
    main()
