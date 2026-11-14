import h5py
import numpy as np
import pytest

from services.processing.io_gcov import GcovLayoutError, find_aoi_window, read_gcov_layer, read_gcov_layer_window


def _write_minimal_gcov(path, with_pol=True):
    with h5py.File(path, "w") as f:
        grp = f.create_group("science/LSAR/GCOV/grids/frequencyA")
        if with_pol:
            grp.create_dataset("HHHH", data=np.ones((4, 4), dtype=np.float32) * 0.05)
        grp.create_dataset("xCoordinates", data=np.arange(4, dtype=np.float64) * 20.0)
        grp.create_dataset("yCoordinates", data=np.arange(4, dtype=np.float64) * -20.0)


def test_read_gcov_layer_reads_documented_paths(tmp_path):
    h5_path = tmp_path / "fake_gcov.h5"
    _write_minimal_gcov(h5_path)

    layer = read_gcov_layer(str(h5_path), granule_id="TEST_GRANULE")

    assert layer.backscatter.shape == (4, 4)
    assert len(layer.x_coords) == 4
    assert layer.granule_id == "TEST_GRANULE"


def test_read_gcov_layer_missing_pol_raises_clear_layout_error(tmp_path):
    h5_path = tmp_path / "missing_pol.h5"
    _write_minimal_gcov(h5_path, with_pol=False)

    with pytest.raises(GcovLayoutError, match="scripts/inspect_nisar_product.py"):
        read_gcov_layer(str(h5_path), granule_id="TEST_GRANULE")


def test_read_gcov_layer_missing_file_raises():
    with pytest.raises(OSError):
        read_gcov_layer("does/not/exist.h5", granule_id="TEST_GRANULE")


def _write_larger_gcov(path, size=100, spacing=10.0, x0=0.0, y0=0.0):
    with h5py.File(path, "w") as f:
        grp = f.create_group("science/LSAR/GCOV/grids/frequencyA")
        data = np.arange(size * size, dtype=np.float32).reshape(size, size) * 0.001 + 0.01
        grp.create_dataset("HHHH", data=data)
        grp.create_dataset("mask", data=np.ones((size, size), dtype=np.uint8))
        grp.create_dataset("xCoordinates", data=x0 + np.arange(size, dtype=np.float64) * spacing)
        grp.create_dataset("yCoordinates", data=y0 - np.arange(size, dtype=np.float64) * spacing)  # north-up, descending
        grp.create_dataset("projection", data=np.uint32(32647))


def test_find_aoi_window_centers_on_requested_point():
    x = np.arange(100, dtype=np.float64) * 10.0  # 0..990
    y = 990.0 - np.arange(100, dtype=np.float64) * 10.0  # 990..0, descending

    row_slice, col_slice = find_aoi_window(x, y, center_x=500.0, center_y=500.0, half_width_m=100.0)

    windowed_x = x[col_slice]
    windowed_y = y[row_slice]
    assert windowed_x.min() >= 400.0 and windowed_x.max() <= 600.0
    assert windowed_y.min() >= 400.0 and windowed_y.max() <= 600.0


def test_find_aoi_window_clips_to_scene_extent():
    x = np.arange(50, dtype=np.float64) * 10.0
    y = 490.0 - np.arange(50, dtype=np.float64) * 10.0

    # center near the corner, with a half-width that would overrun the scene
    row_slice, col_slice = find_aoi_window(x, y, center_x=0.0, center_y=490.0, half_width_m=200.0)

    assert row_slice.start >= 0
    assert col_slice.start >= 0
    assert row_slice.stop <= len(y)
    assert col_slice.stop <= len(x)


def test_read_gcov_layer_window_reads_only_the_aoi_and_preserves_epsg(tmp_path):
    h5_path = tmp_path / "windowed_gcov.h5"
    _write_larger_gcov(h5_path, size=100, spacing=10.0)

    layer = read_gcov_layer_window(
        str(h5_path), granule_id="TEST_GRANULE", center_x=500.0, center_y=500.0, half_width_m=100.0
    )

    assert layer.backscatter.shape[0] < 100 and layer.backscatter.shape[1] < 100  # smaller than the full scene
    assert layer.epsg == 32647
    assert layer.mask is not None
    assert layer.mask.shape == layer.backscatter.shape  # mask windowed identically to backscatter
