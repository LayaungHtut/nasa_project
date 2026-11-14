"""Scientific safeguards: missing evidence cannot become change confirmation."""
import numpy as np

from scripts.validate_hlawga_optical import compare_pair, choose_scene, quality_mask, target_grid
from pyproj import Transformer


def test_cloud_and_shadow_are_unknown_not_dry_land():
    before = np.array([[4, 5, 6, 6, 9, 3, 7, 0]])
    after = np.array([[6, 4, 6, 5, 6, 6, 6, 6]])
    candidate = np.ones_like(before, dtype=bool)
    result = compare_pair(candidate, before, quality_mask(before, 0), after, quality_mask(after, 0))
    assert result == dict(candidate_pixels=8, joint_clear_pixels=4, land_to_water_pixels=1,
                          land_to_land_pixels=1, water_to_water_pixels=1, water_to_land_pixels=1,
                          unknown_pixels=4)


def test_shadow_buffer_excludes_neighboring_clear_cells():
    scl = np.full((9, 9), 4)
    scl[4, 4] = 3
    clear = quality_mask(scl)
    assert not clear[4, 4] and not clear[4, 3] and not clear[3, 4]
    assert clear[2, 4]
    assert not clear[0, 0]


def test_selection_uses_coverage_and_time_not_water_agreement():
    rows = [dict(id='cloudy', baseline_offset_days=1, candidate_clear_pixels_buffered=0),
            dict(id='clear', baseline_offset_days=-2, candidate_clear_pixels_buffered=20),
            dict(id='too-far', baseline_offset_days=4, candidate_clear_pixels_buffered=100)]
    assert choose_scene(rows, 'baseline', 3)['id'] == 'clear'
    assert choose_scene(rows, 'baseline', .5) is None


def test_grid_uses_pixel_edges_not_stored_centers():
    to_geo = Transformer.from_crs(32647, 4326, always_xy=True)
    corners = [to_geo.transform(x, y) for x, y in [(183025, 1895275), (183045, 1895275),
                                                   (183045, 1895255), (183025, 1895255)]]
    grid = target_grid({'tiles': {'corner_coordinates': corners}}, (3, 3))
    assert grid * (0.5, 0.5) == (183025, 1895275)
    assert grid * (3, 3) == (183050, 1895250)
