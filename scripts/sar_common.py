"""Helpers shared by the real-NISAR builds (build_hpakant.py, build_slope.py): cleaning, colour ramps, outlines."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from skimage.measure import points_in_poly

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.processing.geo import pixel_to_lonlat  # noqa: E402,F401  (re-exported for the builds)
from services.processing.vectorize import change_mask_to_geojson  # noqa: E402


def clean(mask, min_px):
    """Morphological opening, then drop clusters smaller than min_px."""
    mask = ndimage.binary_opening(mask, iterations=1)
    lab, n = ndimage.label(mask)
    if n == 0:
        return mask
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    return np.isin(lab, 1 + np.flatnonzero(sizes >= min_px))


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


class Grid:
    """A product's UTM pixel-centre coordinates, for turning masks into lon/lat polygons."""

    def __init__(self, x, y, zone, letter):
        self.x, self.y, self.zone, self.letter = x, y, zone, letter

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
