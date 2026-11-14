"""Pure-Python geodesy helpers.

This dev environment's Windows Application Control policy blocks the native
GDAL/PROJ DLLs that rasterio and pyproj ship with (verified 2026-09-18:
`import rasterio` / `import pyproj` both fail with
"An Application Control policy has blocked this file."). Rather than fight
that policy, we use the pure-Python `utm` package for UTM<->WGS84
conversion, since NISAR GCOV grids are UTM-projected and this is the exact
same closed-form transverse-Mercator math PROJ would run for this
projection family -- not an approximation of it.

This also means we don't produce true GDAL-style Cloud-Optimized GeoTIFFs
in this environment. Instead, rasters are served as plain images plus
their 4 corner [lon, lat] coordinates, consumed directly by MapLibre GL's
ImageSource. See docs/architecture/system-architecture.md, "Tiling
decision" section, for the documented tradeoff. A machine without this DLL
block (e.g. a Linux CI runner or another teammate's laptop) can swap in
real rasterio/COG output later without changing the API contract, since
the contract already only promises "a URL to an image" per layer.
"""

from __future__ import annotations

import utm


def utm_zone_from_epsg(epsg: int) -> tuple[int, str]:
    """WGS84/UTM EPSG codes follow 326xx (northern hemisphere) or 327xx
    (southern hemisphere), where xx is the zone number. Verified against
    the real GCOV file: EPSG 32647 -> zone 47, 'N' (matches the file's own
    'PROJCS["WGS 84 / UTM zone 47N"...' spatial_ref attribute)."""
    epsg_str = str(epsg)
    if epsg_str.startswith("326"):
        return int(epsg_str[3:]), "N"
    if epsg_str.startswith("327"):
        return int(epsg_str[3:]), "S"
    raise ValueError(f"EPSG {epsg} is not a recognized WGS84/UTM code (expected 326xx or 327xx).")


def bbox_wgs84(x_coords, y_coords, zone_number: int, zone_letter: str) -> list[float]:
    """Return [min_lon, min_lat, max_lon, max_lat] for a UTM-gridded raster
    given its 1-D x/y coordinate axis arrays (as stored in GCOV's
    xCoordinates/yCoordinates datasets)."""
    xs = [float(x_coords[0]), float(x_coords[-1])]
    ys = [float(y_coords[0]), float(y_coords[-1])]
    lons, lats = [], []
    for x in xs:
        for y in ys:
            lat, lon = utm.to_latlon(x, y, zone_number, zone_letter)
            lons.append(lon)
            lats.append(lat)
    return [min(lons), min(lats), max(lons), max(lats)]


def corner_coordinates(x_coords, y_coords, zone_number: int, zone_letter: str) -> list[list[float]]:
    """Return the 4 image corners as [lon, lat] pairs in
    top-left, top-right, bottom-right, bottom-left order -- the format
    MapLibre GL's ImageSource `coordinates` option expects.

    Assumes y_coords[0] is the northernmost row (standard for a
    north-up raster), matching GCOV's stated grid convention.
    """
    x0, x1 = float(x_coords[0]), float(x_coords[-1])
    y0, y1 = float(y_coords[0]), float(y_coords[-1])

    def to_lonlat(x, y):
        lat, lon = utm.to_latlon(x, y, zone_number, zone_letter)
        return [lon, lat]

    return [
        to_lonlat(x0, y0),  # top-left
        to_lonlat(x1, y0),  # top-right
        to_lonlat(x1, y1),  # bottom-right
        to_lonlat(x0, y1),  # bottom-left
    ]


def pixel_to_lonlat(row: int, col: int, x_coords, y_coords, zone_number: int, zone_letter: str) -> list[float]:
    """Convert a single (row, col) pixel index to [lon, lat], used when
    vectorizing change-mask contours into GeoJSON."""
    x = float(x_coords[min(col, len(x_coords) - 1)])
    y = float(y_coords[min(row, len(y_coords) - 1)])
    lat, lon = utm.to_latlon(x, y, zone_number, zone_letter)
    return [lon, lat]


def pixel_area_m2(x_coords, y_coords) -> float:
    """Ground area of one pixel in square meters, from the UTM grid spacing."""
    dx = abs(float(x_coords[1]) - float(x_coords[0])) if len(x_coords) > 1 else 1.0
    dy = abs(float(y_coords[1]) - float(y_coords[0])) if len(y_coords) > 1 else 1.0
    return dx * dy
