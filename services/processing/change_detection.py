"""Deterministic backscatter-threshold water-extent change detection.

Pipeline (see docs/science/methodology.md, section 3):
  speckle-filtered linear backscatter
  -> dB
  -> per-date water mask (backscatter below threshold_db)
  -> change = water present post-event AND NOT present at baseline
  -> drop clusters smaller than min_cluster_pixels (speckle residue)
  -> area + confidence stats

No machine learning. Every number here is traceable to the threshold and
the two input rasters -- see docs/science/limitations.md for what this
method can and cannot detect.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label
from scipy.ndimage import sum as ndi_sum

DEFAULT_WATER_THRESHOLD_DB = -17.0
"""Literature-typical cutoff for open water in L-band HH backscatter.
Tune per-AOI once real data is available -- see limitations.md, this is
NOT claimed to generalize globally without recalibration."""

DEFAULT_MIN_CLUSTER_PIXELS = 8


def to_db(linear_backscatter: np.ndarray) -> np.ndarray:
    safe = np.clip(linear_backscatter, 1e-6, None)
    return 10 * np.log10(safe)


def water_mask(db_image: np.ndarray, threshold_db: float = DEFAULT_WATER_THRESHOLD_DB) -> np.ndarray:
    return db_image < threshold_db


def new_inundation_mask(
    baseline_water: np.ndarray,
    post_event_water: np.ndarray,
    min_cluster_pixels: int = DEFAULT_MIN_CLUSTER_PIXELS,
) -> np.ndarray:
    """Pixels classified as water post-event but not at baseline, with
    small (likely speckle-driven) clusters discarded."""
    candidate = post_event_water & ~baseline_water
    labeled, n = label(candidate)
    if n == 0:
        return candidate
    sizes = ndi_sum(candidate, labeled, index=np.arange(1, n + 1))
    keep = np.zeros(n + 1, dtype=bool)
    keep[1:] = sizes >= min_cluster_pixels
    return keep[labeled]


def change_stats(change_mask: np.ndarray, pixel_area_m2: float, valid_mask: np.ndarray | None = None) -> dict:
    """Deterministic summary stats. `confidence` is NOT a model score --
    it is half data-completeness (fraction of non-nodata pixels in the
    AOI) and half a cluster-size heuristic (small detected areas are more
    likely to be residual speckle than a real event). See
    docs/science/limitations.md for why this is not a calibrated
    probability."""
    if valid_mask is None:
        valid_mask = np.ones_like(change_mask, dtype=bool)

    valid_pixels = int(valid_mask.sum())
    changed_pixels = int((change_mask & valid_mask).sum())
    area_km2 = changed_pixels * pixel_area_m2 / 1e6
    valid_fraction = valid_pixels / change_mask.size if change_mask.size else 0.0
    # Saturation point chosen so a few hundred real detected pixels is a
    # modest, plausible result, not a saturated-confidence one -- the original /200.0
    # divisor hit 1.0 on essentially any real detection, which is exactly
    # the "manufactured probability" failure mode this metric must avoid.
    # /2000.0 keeps small (<100px, likely speckle) clusters near 0 while
    # not pinning every real cluster to a false ceiling.
    size_confidence = min(1.0, changed_pixels / 2000.0) if changed_pixels else 0.0
    confidence = round(0.5 * valid_fraction + 0.5 * size_confidence, 3)

    return {
        "changed_pixels": changed_pixels,
        "valid_pixels": valid_pixels,
        "valid_fraction": round(valid_fraction, 4),
        "change_area_km2": round(area_km2, 3),
        "confidence": confidence,
        "threshold_db": DEFAULT_WATER_THRESHOLD_DB,
        "min_cluster_pixels": DEFAULT_MIN_CLUSTER_PIXELS,
    }
