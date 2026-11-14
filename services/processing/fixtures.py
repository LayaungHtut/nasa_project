"""Synthetic GCOV-shaped fixture for pipeline development.

THIS IS NOT REAL NISAR DATA. It exists only so the rest of the pipeline
(speckle filter -> threshold -> change mask -> stats -> GeoJSON) can be
built, run, and tested end-to-end before Earthdata Login access is
available (see docs/demo/data-provenance.md for the exact blocker).

Every consumer of this fixture MUST propagate `data_status:
"SYNTHETIC_PLACEHOLDER"` into any output record -- never let a
fixture-derived ChangeEvent claim to be real. See
docs/handoff/demo-data.md.

The synthetic scene models a river with a floodplain: baseline has a
narrow river (low backscatter) through mostly land (higher backscatter);
post-event adds a wider flooded region next to the river, plus random
speckle multiplicative noise on both, so the pipeline's speckle filter
and thresholding are meaningfully exercised.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FIXTURE_SIZE = 256
FIXTURE_GRANULE_ID_BASELINE = "SYNTHETIC_FIXTURE_baseline_no_real_granule"
FIXTURE_GRANULE_ID_POST = "SYNTHETIC_FIXTURE_post_event_no_real_granule"

# Placeholder UTM grid roughly matching the Yangon AOI's real zone (46N),
# spaced at GCOV's documented ~20 m grid, purely so downstream geo math
# (geo.py) has plausible-shaped inputs to run against.
_ZONE_NUMBER = 46
_ZONE_LETTER = "N"
_PIXEL_SPACING_M = 20.0
_ORIGIN_EASTING = 680000.0
_ORIGIN_NORTHING = 1860000.0


def _speckled(base: np.ndarray, rng: np.random.Generator, looks: int = 4) -> np.ndarray:
    """Multiply by a Gamma-distributed speckle field (mean 1) -- the
    standard multiplicative noise model for multi-look SAR intensity."""
    speckle = rng.gamma(shape=looks, scale=1.0 / looks, size=base.shape)
    return base * speckle


def _make_scene(rng: np.random.Generator, flood: bool) -> np.ndarray:
    n = FIXTURE_SIZE
    land = np.full((n, n), 0.08, dtype=np.float64)  # ~ -11 dB, typical vegetated/bare land
    yy, xx = np.mgrid[0:n, 0:n]

    river = np.abs(xx - (n // 2 + (yy - n // 2) * 0.15)) < 6
    land[river] = 0.006  # ~ -22 dB, open water

    if flood:
        floodplain = (np.abs(xx - (n // 2 + (yy - n // 2) * 0.15)) < 26) & (yy > n * 0.35) & (yy < n * 0.75)
        land[floodplain & ~river] = 0.010  # ~ -20 dB, new standing water

    return _speckled(land, rng)


@dataclass
class FixturePair:
    baseline: np.ndarray
    post_event: np.ndarray
    x_coords: np.ndarray
    y_coords: np.ndarray
    zone_number: int
    zone_letter: str
    baseline_granule_id: str
    post_event_granule_id: str


def make_fixture_pair(seed: int = 42) -> FixturePair:
    rng = np.random.default_rng(seed)
    baseline = _make_scene(rng, flood=False)
    post_event = _make_scene(rng, flood=True)
    n = FIXTURE_SIZE
    x_coords = _ORIGIN_EASTING + np.arange(n) * _PIXEL_SPACING_M
    y_coords = _ORIGIN_NORTHING - np.arange(n) * _PIXEL_SPACING_M  # north-up: decreasing northing downward
    return FixturePair(
        baseline=baseline,
        post_event=post_event,
        x_coords=x_coords,
        y_coords=y_coords,
        zone_number=_ZONE_NUMBER,
        zone_letter=_ZONE_LETTER,
        baseline_granule_id=FIXTURE_GRANULE_ID_BASELINE,
        post_event_granule_id=FIXTURE_GRANULE_ID_POST,
    )
