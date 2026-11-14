import numpy as np

from services.processing.change_detection import change_stats, new_inundation_mask, to_db, water_mask


def test_to_db_monotonic_and_handles_zero():
    linear = np.array([0.0, 0.001, 0.01, 0.1, 1.0])
    db = to_db(linear)
    assert np.all(np.diff(db) > 0)  # higher linear power -> higher dB
    assert np.isfinite(db).all()  # the zero entry must not produce -inf/nan


def test_water_mask_threshold():
    db = np.array([-25.0, -18.0, -17.0, -10.0, 0.0])
    mask = water_mask(db, threshold_db=-17.0)
    assert list(mask) == [True, True, False, False, False]


def test_new_inundation_mask_drops_small_clusters():
    baseline = np.zeros((10, 10), dtype=bool)
    post = np.zeros((10, 10), dtype=bool)
    post[0, 0] = True  # single-pixel speckle blip
    post[4:8, 4:8] = True  # 16-pixel real cluster

    change = new_inundation_mask(baseline, post, min_cluster_pixels=8)

    assert not change[0, 0]  # speckle-sized cluster discarded
    assert change[5, 5]  # real cluster kept
    assert change.sum() == 16


def test_new_inundation_mask_only_flags_new_water():
    baseline = np.zeros((5, 5), dtype=bool)
    baseline[1:4, 1:4] = True  # already water at baseline
    post = baseline.copy()  # unchanged

    change = new_inundation_mask(baseline, post, min_cluster_pixels=1)

    assert change.sum() == 0  # no new water -> no change, even though water exists


def test_change_stats_area_and_confidence_bounds():
    mask = np.zeros((100, 100), dtype=bool)
    mask[:10, :10] = True  # 100 pixels
    stats = change_stats(mask, pixel_area_m2=400.0)  # 20m x 20m pixels

    assert stats["changed_pixels"] == 100
    assert stats["change_area_km2"] == round(100 * 400.0 / 1e6, 3)
    assert 0.0 <= stats["confidence"] <= 1.0


def test_change_stats_respects_valid_mask():
    mask = np.ones((4, 4), dtype=bool)
    valid = np.zeros((4, 4), dtype=bool)
    valid[:2, :2] = True  # only a quarter of the AOI has valid data

    stats = change_stats(mask, pixel_area_m2=1.0, valid_mask=valid)

    assert stats["valid_pixels"] == 4
    assert stats["changed_pixels"] == 4  # change AND valid
