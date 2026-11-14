import numpy as np
import pytest

from services.processing.geo import bbox_wgs84, corner_coordinates, pixel_area_m2, pixel_to_lonlat, utm_zone_from_epsg


def _yangon_grid():
    # Roughly matches the fixture's synthetic UTM zone 46N grid.
    x = 680000.0 + np.arange(256) * 20.0
    y = 1860000.0 - np.arange(256) * 20.0
    return x, y


def test_bbox_wgs84_is_near_myanmar_and_well_ordered():
    x, y = _yangon_grid()
    bbox = bbox_wgs84(x, y, zone_number=46, zone_letter="N")

    min_lon, min_lat, max_lon, max_lat = bbox
    assert min_lon < max_lon
    assert min_lat < max_lat
    # Myanmar roughly spans 92-101E, 9-29N -- sanity bound, not precision check
    assert 90 < min_lon < 102
    assert 5 < min_lat < 30


def test_corner_coordinates_returns_four_lonlat_pairs():
    x, y = _yangon_grid()
    corners = corner_coordinates(x, y, zone_number=46, zone_letter="N")

    assert len(corners) == 4
    for lon, lat in corners:
        assert 90 < lon < 102
        assert 5 < lat < 30


def test_pixel_to_lonlat_within_bbox():
    x, y = _yangon_grid()
    bbox = bbox_wgs84(x, y, zone_number=46, zone_letter="N")
    lon, lat = pixel_to_lonlat(0, 0, x, y, zone_number=46, zone_letter="N")

    assert bbox[0] - 0.01 <= lon <= bbox[2] + 0.01
    assert bbox[1] - 0.01 <= lat <= bbox[3] + 0.01


def test_pixel_area_m2_from_grid_spacing():
    x, y = _yangon_grid()
    assert pixel_area_m2(x, y) == 400.0  # 20m x 20m


def test_utm_zone_from_epsg_matches_real_yangon_granule():
    # EPSG 32647 is the real projection read from the downloaded Track
    # 40/Frame 10 GCOV granule (see docs/science/real-data-validation.md) --
    # the file's own spatial_ref attribute confirms "UTM zone 47N".
    assert utm_zone_from_epsg(32647) == (47, "N")


def test_utm_zone_from_epsg_southern_hemisphere():
    assert utm_zone_from_epsg(32747) == (47, "S")


def test_utm_zone_from_epsg_rejects_non_utm_code():
    with pytest.raises(ValueError):
        utm_zone_from_epsg(4326)
