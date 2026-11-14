import numpy as np

import services.processing.timeseries as ts
from services.processing.ndvi import reflectance


def _season(n_dates=8, low_west=2, low_east=5):
    """60x60 scene: top half forest (flat 0 dB), bottom half paddy. The west paddy is darkest on
    date low_west, the east paddy on low_east; both then rise 3 dB above their earlier level."""
    rng = np.random.default_rng(1)
    stack = []
    for t in range(n_dates):
        img = rng.normal(0, 0.2, (60, 60))
        for cols, low in ((slice(0, 30), low_west), (slice(30, 60), low_east)):
            img[30:, cols] += -6.0 if t == low else (-4.0 if t < low else -1.0)
        stack.append(img)
    forest = np.zeros((60, 60), bool)
    forest[:30] = True
    crop = ~forest
    dates = [
        {
            "date": f"2026-08-{t + 1:02d}T00:00:00Z",
            "processing_crid": "P1",
            "hh_by_landcover": {"tree_cover": {"median_db": 0.0}},
            "relative_to_forest_db": {"cropland": float(np.median(s[crop]))},
        }
        for t, s in enumerate(stack)
    ]
    erode = lambda m: ts.binary_erosion(m, iterations=ts.EROSION_PX)  # as the pipeline's cores are
    return stack, dates, {40: erode(crop), 10: erode(forest)}


def test_pixel_season_separates_paddy_from_the_forest_control(tmp_path):
    (tmp_path / "timeseries").mkdir()
    stack, dates, cores = _season()
    out = ts.pixel_season(stack, dates, cores, tmp_path, "test", px_area=100.0)
    assert out["dark_then_rise"]["cropland"] > 0.95
    assert out["dark_then_rise"]["forest_control"] < 0.05
    assert out["brightened_over_1db"]["forest_control"] < 0.05
    assert (tmp_path / "timeseries" / "darkest_pass.png").exists()
    # Two half-blocks with different timing: neighbours agree far more often than random labels would.
    t = out["timing_neighbour_agreement"]
    assert t["lag_m"] == 150.0
    assert t["observed"] > 0.6 and t["if_random"] < 0.6


def test_pixel_season_ignores_dates_from_other_processing(tmp_path):
    (tmp_path / "timeseries").mkdir()
    stack, dates, cores = _season()
    dates[-1]["processing_crid"] = "P2"
    stack[-1] = stack[-1] + 10  # a big version shift must not create a "rise"
    out = ts.pixel_season(stack, dates, cores, tmp_path, "test", px_area=100.0)
    assert out["dark_then_rise"]["forest_control"] < 0.05
    assert out["brightened_over_1db"]["forest_control"] < 0.05


def test_reflectance_does_not_reapply_an_offset_already_removed():
    band = {"scale": 1e-4, "offset": -0.1, "nodata": 0}
    assert np.isclose(reflectance(np.array([459]), band, True)[0], 0.0459)
    assert np.isclose(reflectance(np.array([1459]), band, False)[0], 0.0459)
    assert np.isnan(reflectance(np.array([0]), band, True)[0])


def test_tiff_window_matches_full_read(tmp_path):
    import tifffile

    full = np.random.default_rng(2).integers(0, 255, (100, 90), dtype=np.uint8)
    path = tmp_path / "tiled.tif"
    tifffile.imwrite(path, full, tile=(32, 32), compression="zlib")
    # Windows that start, end and cross tile edges, including partial edge tiles.
    for r0, r1, c0, c1 in ((0, 100, 0, 90), (5, 70, 30, 33), (31, 33, 63, 90), (96, 100, 0, 1)):
        assert np.array_equal(ts.read_tiff_window(path, r0, r1, c0, c1), full[r0:r1, c0:c1])


def test_landcover_map_colours_only_the_finding_classes(tmp_path):
    from PIL import Image

    (tmp_path / "timeseries").mkdir()
    classes = np.array([[40, 80, 50, 10], [30, 40, 40, 0]], np.uint8)
    loss = np.zeros(classes.shape, bool)
    loss[1, 1] = True
    out = ts.landcover_map(classes, loss, tmp_path, "e", px_area=100.0)
    rgba = np.array(Image.open(tmp_path / "timeseries" / "landcover.png"))
    assert tuple(rgba[0, 0]) == (0x19, 0x9E, 0x70, 255)  # paddy
    assert tuple(rgba[0, 1]) == (0x39, 0x87, 0xE5, 255)  # reservoir
    assert rgba[0, 3, 3] == 0 and rgba[1, 0, 3] == 0  # forest and grassland stay clear
    assert {c["key"]: c["area_km2"] for c in out["classes"]}["cropland"] == 0.0  # 3 px x 100 m2
    lossimg = np.array(Image.open(tmp_path / "timeseries" / "water_loss.png"))
    assert lossimg[1, 1, 3] == 255 and lossimg[..., 3].sum() == 255
