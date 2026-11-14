"""Independent optical check of the radar rice-season signal: Sentinel-2 NDVI over the same fields.

CLI usage (after services.processing.timeseries has written timeseries.json):
    python -m services.processing.ndvi --event-id yangon-track40-frame10

For every Sentinel-2 L2A scene on Element 84 Earth Search over the AOI in the radar season, reads
only the image tiles covering the radar study window (HTTP range reads, no full download):
first the 20 m scene classification (SCL), then the 10 m red and near-infrared bands only when at
least MIN_CLEAR of the paddy fields are cloud-free. NDVI medians use the same eroded ESA WorldCover
cropland and forest cores as the radar series, so both sensors describe the same pixels.

Writes data/validation/<event-id>/ndvi-series.json with each scene's id and band URLs.
NDVI is an optical vegetation index, not ground truth: it rises as a green canopy grows and falls
when fields are flooded, bare or senescent.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import fsspec
import numpy as np
import tifffile
import utm
from scipy.ndimage import binary_erosion

from services.processing.timeseries import EROSION_PX, worldcover_classes

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
VALIDATION_DIR = REPO_ROOT / "data" / "validation"
STAC_SEARCH = "https://earth-search.aws.element84.com/v1/search"
CLEAR_SCL = (4, 5, 6)  # vegetation, not vegetated, water; everything else is cloud, shadow, defect or nodata
MIN_CLEAR = 0.5


def stac_items(lon: float, lat: float, start: str, end: str) -> list[dict]:
    params = {"collections": "sentinel-2-l2a", "intersects": json.dumps({"type": "Point", "coordinates": [lon, lat]}), "datetime": f"{start}/{end}", "limit": 100}
    url, items = f"{STAC_SEARCH}?{urllib.parse.urlencode(params)}", []
    while url:
        page = json.load(urllib.request.urlopen(url, timeout=60))
        items += page["features"]
        url = next((link["href"] for link in page.get("links", []) if link["rel"] == "next"), None)
    return sorted(items, key=lambda item: item["properties"]["datetime"])


def read_at(href: str, rows: np.ndarray, cols: np.ndarray, step_m: float) -> np.ndarray:
    """Values of a tiled GeoTIFF at the given UTM coordinates (nearest pixel), decoding only the tiles hit."""
    with fsspec.open(href, "rb", block_size=2**20) as fh:
        page = tifffile.TiffFile(fh).pages[0]
        x0, y0 = page.tags["ModelTiepointTag"].value[3:5]
        r = ((y0 - rows) / step_m).astype(int)
        c = ((cols - x0) / step_m).astype(int)
        th, tw = page.tilelength, page.tilewidth
        across = -(-page.imagewidth // tw)
        out = np.zeros(r.shape, dtype=page.dtype)
        for tr in range(r.min() // th, r.max() // th + 1):
            for tc in range(c.min() // tw, c.max() // tw + 1):
                hit = (r // th == tr) & (c // tw == tc)
                if not hit.any():
                    continue
                index = tr * across + tc
                fh.seek(page.dataoffsets[index])
                tile = page.decode(fh.read(page.databytecounts[index]), index, jpegtables=page.jpegtables)[0].reshape(th, tw)
                out[hit] = tile[r[hit] - tr * th, c[hit] - tc * tw]
    return out


def reflectance(dn: np.ndarray, band: dict, offset_applied: bool) -> np.ndarray:
    # Earth Search lists the -0.1 BOA offset on the band even when it has already removed it from the pixels.
    scale, offset = band.get("scale", 1.0), 0.0 if offset_applied else band.get("offset", 0.0)
    return np.where(dn == band.get("nodata", 0), np.nan, dn * scale + offset)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True)
    args = parser.parse_args()

    series = json.loads((PROCESSED_DIR / args.event_id / "timeseries.json").read_text())
    grid = series["grid"]
    zone = int(str(grid["epsg"])[3:])
    x = grid["x0"] + 10.0 * np.arange(grid["shape"][1])
    y = grid["y0"] - 10.0 * np.arange(grid["shape"][0])
    classes = worldcover_classes(x, y, zone)
    crop = binary_erosion(classes == 40, iterations=EROSION_PX)
    forest = binary_erosion(classes == 10, iterations=EROSION_PX)
    east, north = np.meshgrid(x, y)
    lat, lon = utm.to_latlon(east, north, zone, northern=True)

    first, last = series["dates"][0]["date"][:10], series["dates"][-1]["date"][:10]
    center_lon, center_lat = json.loads((PROCESSED_DIR / args.event_id / "metadata.json").read_text())["location"]["center"]
    items = stac_items(center_lon, center_lat, f"{first}T00:00:00Z", f"{last}T23:59:59Z")
    print(f"{len(items)} Sentinel-2 scenes {first} to {last}")

    scenes = []
    for item in items:
        epsg = int(item["properties"].get("proj:epsg") or str(item["properties"]["proj:code"]).split(":")[1])
        s2_e, s2_n, _, _ = utm.from_latlon(lat, lon, force_zone_number=epsg % 100)
        scl = read_at(item["assets"]["scl"]["href"], s2_n, s2_e, 20.0)
        clear = np.isin(scl, CLEAR_SCL)
        clear_crop = float(clear[crop].mean())
        row = {"id": item["id"], "datetime": item["properties"]["datetime"], "processing_baseline": item["properties"].get("s2:processing_baseline"), "cropland_clear_fraction": round(clear_crop, 3)}
        if clear_crop >= MIN_CLEAR:
            applied = bool(item["properties"].get("earthsearch:boa_offset_applied"))
            red = reflectance(read_at(item["assets"]["red"]["href"], s2_n, s2_e, 10.0), item["assets"]["red"]["raster:bands"][0], applied)
            nir = reflectance(read_at(item["assets"]["nir"]["href"], s2_n, s2_e, 10.0), item["assets"]["nir"]["raster:bands"][0], applied)
            ndvi = (nir - red) / (nir + red)
            ok = clear & np.isfinite(ndvi)
            row.update({
                "cropland_ndvi_median": round(float(np.median(ndvi[crop & ok])), 3),
                "cropland_ndvi_p25_p75": [round(float(v), 3) for v in np.percentile(ndvi[crop & ok], [25, 75])],
                "cropland_water_fraction": round(float((scl[crop & clear] == 6).mean()), 3),
                "forest_ndvi_median": round(float(np.median(ndvi[forest & ok])), 3) if (forest & ok).sum() > 1000 else None,
                "assets": {k: item["assets"][k]["href"] for k in ("scl", "red", "nir")},
            })
        scenes.append(row)
        print(row["datetime"][:10], f"clear {clear_crop:.2f}", row.get("cropland_ndvi_median", "-"), flush=True)

    record = {
        "event_id": args.event_id,
        "method": "sentinel2_ndvi_on_radar_landcover_v1",
        "source": "Copernicus Sentinel-2 L2A via Element 84 Earth Search (sentinel-2-l2a), modified Copernicus Sentinel data 2026",
        "landcover": series["landcover_source"],
        "landcover_mask_erosion_px": EROSION_PX,
        "clear_scl_classes": list(CLEAR_SCL),
        "min_cropland_clear_fraction": MIN_CLEAR,
        "scenes": scenes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out = VALIDATION_DIR / args.event_id / "ndvi-series.json"
    out.write_text(json.dumps(record, indent=2))
    print(f"wrote {out}: {sum('cropland_ndvi_median' in s for s in scenes)} usable of {len(scenes)} scenes")


if __name__ == "__main__":
    main()
