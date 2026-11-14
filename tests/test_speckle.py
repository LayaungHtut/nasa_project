import numpy as np

from services.processing.speckle import lee_filter


def test_lee_filter_reduces_variance_on_noisy_flat_field():
    rng = np.random.default_rng(0)
    flat_truth = np.full((50, 50), 1.0)
    noisy = flat_truth * rng.gamma(shape=4, scale=0.25, size=flat_truth.shape)

    filtered = lee_filter(noisy, size=5)

    assert filtered.var() < noisy.var()
    assert abs(filtered.mean() - 1.0) < 0.1


def test_lee_filter_handles_constant_input_without_nan():
    constant = np.full((10, 10), 5.0)
    filtered = lee_filter(constant)
    assert np.allclose(filtered, 5.0)
    assert not np.isnan(filtered).any()
