"""Reader for real NISAR GCOV HDF5 products.

VERIFIED 2026-09-18 against the real, downloaded Track 40/Frame 10
granules (both baseline 2026-08-27 and post-event 2026-09-08) using
scripts/inspect_nisar_product.py: every path template below matched
exactly ([OK] on all 7 documented paths), confirming
https://nisar-docs.asf.alaska.edu/gcov/'s documented structure is
correct for this collection (NISAR_L2_GCOV_PROVISIONAL_V1). Real
observed shape: HHHH/HVHV/mask all (33192, 33912) float32/uint8, 10 m
pixel spacing, EPSG 32647 (WGS84 / UTM zone 47N), both dates on the
identical coordinate grid (repeat-pass geocoding).

Full HHHH is ~4.5 GB in memory as float32 -- read_gcov_layer_window()
below reads only an AOI-sized slice directly from disk via h5py dataset
slicing (h5py only pulls the requested hyperslab, not the full array),
which is what the pipeline actually uses.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import h5py
except ImportError:  # Windows Application Control can block h5py's DLLs; pyfive is pure Python with the same read API
    import pyfive as h5py

GRID_GROUP_TMPL = "/science/LSAR/GCOV/grids/frequency{freq}"
POL_DATASET_TMPL = GRID_GROUP_TMPL + "/{pol}"
X_COORD_TMPL = GRID_GROUP_TMPL + "/xCoordinates"
Y_COORD_TMPL = GRID_GROUP_TMPL + "/yCoordinates"
PROJECTION_TMPL = GRID_GROUP_TMPL + "/projection"
MASK_TMPL = GRID_GROUP_TMPL + "/mask"


@dataclass
class GcovLayer:
    backscatter: np.ndarray  # linear power, one diagonal covariance term (e.g. HHHH)
    x_coords: np.ndarray  # 1-D UTM easting axis, meters
    y_coords: np.ndarray  # 1-D UTM northing axis, meters
    epsg: int | None  # EPSG code read from the file's projection dataset, if present
    mask: np.ndarray | None  # GCOV's own per-pixel quality mask, if present
    granule_id: str
    source_path: str


class GcovLayoutError(KeyError):
    """Raised when a real .h5 file doesn't match the documented GCOV layout.
    See this module's docstring: fix the path templates above and re-run
    scripts/inspect_nisar_product.py to confirm before trusting results."""


def _read_epsg(f: h5py.File, freq: str) -> int | None:
    proj_path = PROJECTION_TMPL.format(freq=freq)
    if proj_path not in f:
        return None
    try:
        return int(f[proj_path][()])
    except (TypeError, ValueError):
        return None


def find_aoi_window(
    x_coords: np.ndarray, y_coords: np.ndarray, center_x: float, center_y: float, half_width_m: float
) -> tuple[slice, slice]:
    """Given the full-scene 1-D coordinate axes and a UTM center point,
    return (row_slice, col_slice) for an AOI of side 2*half_width_m,
    clipped to the scene extent. y_coords is assumed descending
    (north-up raster, as confirmed for real GCOV products)."""
    col_idx = np.searchsorted(x_coords, [center_x - half_width_m, center_x + half_width_m])
    # y_coords descends, so searchsorted needs the reversed comparison
    row_idx = np.searchsorted(-y_coords, [-(center_y + half_width_m), -(center_y - half_width_m)])
    col_slice = slice(max(0, int(col_idx[0])), min(len(x_coords), int(col_idx[1])))
    row_slice = slice(max(0, int(row_idx[0])), min(len(y_coords), int(row_idx[1])))
    return row_slice, col_slice


def read_gcov_layer(
    h5_path: str,
    granule_id: str,
    freq: str = "A",
    pol: str = "HHHH",
    *,
    row_slice: slice | None = None,
    col_slice: slice | None = None,
    stride: int = 1,
    bbox_wgs84: tuple[float, float, float, float] | None = None,
) -> GcovLayer:
    """Read a single GCOV polarization layer, optionally windowed or strided.

    If bbox_wgs84 is provided as (min_lon, min_lat, max_lon, max_lat), row_slice
    and col_slice are automatically computed using the file's UTM coordinates.
    With no window or stride this reads the FULL scene (~4.5 GB for a real
    granule) -- prefer read_gcov_layer_window() for an AOI.
    """
    with h5py.File(h5_path, "r") as f:
        pol_path = POL_DATASET_TMPL.format(freq=freq, pol=pol)
        if pol_path not in f:
            raise GcovLayoutError(
                f"{pol_path} not found in {h5_path}. Run "
                "scripts/inspect_nisar_product.py on this file and update "
                "services/processing/io_gcov.py's path templates."
            )
        epsg = _read_epsg(f, freq)

        x_ds = f[X_COORD_TMPL.format(freq=freq)]
        y_ds = f[Y_COORD_TMPL.format(freq=freq)]

        if bbox_wgs84 is not None:
            import utm
            min_lon, min_lat, max_lon, max_lat = bbox_wgs84
            # Determine zone from epsg (e.g. 32647 -> 47, 'N') or coordinate bounds
            if epsg and str(epsg).startswith("326"):
                z_num, z_let = int(str(epsg)[3:]), "N"
            elif epsg and str(epsg).startswith("327"):
                z_num, z_let = int(str(epsg)[3:]), "S"
            else:
                z_num, z_let = 47, "N"
            
            x_min_utm, y_min_utm = utm.from_latlon(min_lat, min_lon, z_num)[:2]
            x_max_utm, y_max_utm = utm.from_latlon(max_lat, max_lon, z_num)[:2]

            x0, dx = float(x_ds[0]), float(x_ds[1] - x_ds[0])
            y0, dy = float(y_ds[0]), float(y_ds[1] - y_ds[0])

            c_min = max(0, int((min(x_min_utm, x_max_utm) - x0) / dx))
            c_max = min(len(x_ds), int((max(x_min_utm, x_max_utm) - x0) / dx))
            r_min = max(0, int((max(y_min_utm, y_max_utm) - y0) / dy))
            r_max = min(len(y_ds), int((min(y_min_utm, y_max_utm) - y0) / dy))

            row_slice = slice(r_min, r_max, stride)
            col_slice = slice(c_min, c_max, stride)
        elif stride > 1 and row_slice is None and col_slice is None:
            row_slice = slice(None, None, stride)
            col_slice = slice(None, None, stride)

        if row_slice is not None and col_slice is not None:
            backscatter = f[pol_path][row_slice, col_slice]
            x_coords = x_ds[col_slice]
            y_coords = y_ds[row_slice]
        else:
            backscatter = f[pol_path][()]
            x_coords = x_ds[()]
            y_coords = y_ds[()]

        mask = None
        mask_path = MASK_TMPL.format(freq=freq)
        if mask_path in f:
            if row_slice is not None and col_slice is not None:
                mask = f[mask_path][row_slice, col_slice]
            else:
                mask = f[mask_path][()]

    return GcovLayer(
        backscatter=backscatter,
        x_coords=x_coords,
        y_coords=y_coords,
        epsg=epsg,
        mask=mask,
        granule_id=granule_id,
        source_path=h5_path,
    )


def read_gcov_layer_window(
    h5_path: str,
    granule_id: str,
    center_x: float,
    center_y: float,
    half_width_m: float,
    freq: str = "A",
    pol: str = "HHHH",
) -> GcovLayer:
    """Reads only an AOI-sized window around (center_x, center_y) (UTM
    meters, same projection as the file). h5py slices a dataset lazily,
    so only the requested hyperslab is read from disk -- the full ~4.5 GB
    array is never materialized in memory."""
    with h5py.File(h5_path, "r") as f:
        pol_path = POL_DATASET_TMPL.format(freq=freq, pol=pol)
        if pol_path not in f:
            raise GcovLayoutError(
                f"{pol_path} not found in {h5_path}. Run "
                "scripts/inspect_nisar_product.py on this file and update "
                "services/processing/io_gcov.py's path templates."
            )
        x_coords_full = f[X_COORD_TMPL.format(freq=freq)][()]
        y_coords_full = f[Y_COORD_TMPL.format(freq=freq)][()]
        row_slice, col_slice = find_aoi_window(x_coords_full, y_coords_full, center_x, center_y, half_width_m)

        backscatter = f[pol_path][row_slice, col_slice]
        x_coords = x_coords_full[col_slice]
        y_coords = y_coords_full[row_slice]
        epsg = _read_epsg(f, freq)

        mask = None
        mask_path = MASK_TMPL.format(freq=freq)
        if mask_path in f:
            mask = f[mask_path][row_slice, col_slice]

    return GcovLayer(
        backscatter=backscatter,
        x_coords=x_coords,
        y_coords=y_coords,
        epsg=epsg,
        mask=mask,
        granule_id=granule_id,
        source_path=h5_path,
    )
