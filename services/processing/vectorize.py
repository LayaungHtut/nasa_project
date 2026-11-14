"""Vectorize a boolean change mask into WGS84 GeoJSON polygons.

Uses scikit-image's marching-squares contour finder (pure Python/NumPy,
no GDAL/OGR dependency -- see geo.py's module docstring for why GDAL isn't
available in this dev environment) instead of rasterio/fiona's usual
`rasterio.features.shapes`. This produces contour lines, not
topologically-clean polygons with holes, which is a real simplification:
adjacent same-value regions and donut-shaped holes are not modeled as
precisely as a proper polygonize would. Documented as a known limitation
-- acceptable for a hackathon visualization layer, not for GIS analysis.
"""

from __future__ import annotations

import numpy as np
from skimage import measure

from services.processing.geo import pixel_to_lonlat


def change_mask_to_geojson(
    change_mask: np.ndarray,
    x_coords,
    y_coords,
    zone_number: int,
    zone_letter: str,
    min_contour_points: int = 3,
) -> dict:
    contours = measure.find_contours(change_mask.astype(np.uint8), level=0.5)
    features = []
    for i, contour in enumerate(contours):
        if len(contour) < min_contour_points:
            continue
        ring = [
            pixel_to_lonlat(int(round(r)), int(round(c)), x_coords, y_coords, zone_number, zone_letter)
            for r, c in contour
        ]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        features.append(
            {
                "type": "Feature",
                "properties": {"feature_id": i},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        )
    return {"type": "FeatureCollection", "features": features}
