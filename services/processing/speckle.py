"""Speckle filtering for SAR backscatter.

SAR backscatter has inherent multiplicative speckle noise -- without
filtering, single noisy pixels get misread as "change." We apply a
standard Lee filter (adaptive, edge-preserving) before thresholding.
See docs/science/methodology.md, section 3.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter


def lee_filter(image: np.ndarray, size: int = 5) -> np.ndarray:
    """Adaptive Lee speckle filter. `size` is the square window side in
    pixels; 5 is a common default for moderate-resolution SAR backscatter."""
    img = image.astype(np.float64)
    mean = uniform_filter(img, size)
    sqr_mean = uniform_filter(img * img, size)
    variance = sqr_mean - mean * mean
    variance[variance < 0] = 0
    overall_variance = float(np.nanvar(img))
    if overall_variance == 0:
        return mean
    weight = variance / (variance + overall_variance)
    return mean + weight * (img - mean)
