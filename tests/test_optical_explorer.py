"""Ensure displayed candidate boundaries and evidence preserve the archived audit."""
import gzip
import io
import json
from pathlib import Path

import numpy as np
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform_geom
from scipy.ndimage import label

BASE = Path(__file__).resolve().parents[1] / 'data/validation/yangon-track40-frame10'


def test_selectable_polygons_round_trip_to_exact_archived_components():
    manifest = json.loads((BASE / 'map-evidence.json').read_text())
    audit = json.loads((BASE / 'scene-audit.json').read_text())
    mask = np.load(io.BytesIO(gzip.decompress((BASE / 'candidate-mask.npy.gz').read_bytes())))
    expected, count = label(mask)
    features = [(transform_geom('EPSG:4326', audit['target_crs'], feature['geometry']),
                 feature['properties']['component']) for feature in manifest['geometry']['features']]
    actual = rasterize(features, out_shape=mask.shape, transform=Affine(*audit['target_transform']), dtype='int16')
    np.testing.assert_array_equal(actual, expected)
    assert len(manifest['candidates']) == count == 46


def test_per_candidate_reference_counts_cover_every_cell_and_reproduce_audit():
    manifest = json.loads((BASE / 'map-evidence.json').read_text())
    audit = json.loads((BASE / 'comparison.json').read_text())
    for candidate in manifest['candidates']:
        assert candidate['area_m2'] == candidate['candidate_pixels'] * 100
        for ref in candidate['references']:
            assert ref['water_pixels'] + ref['land_pixels'] + ref['unknown_pixels'] == candidate['candidate_pixels']
    for scene in manifest['scenes']:
        row = next(row for row in audit['scenes'] if row['id'] == scene['id'])
        for field in ('water_pixels', 'land_pixels', 'unknown_pixels'):
            assert sum(next(ref[field] for ref in candidate['references'] if ref['scene_id'] == scene['id'])
                       for candidate in manifest['candidates']) == row[field]
        assert (BASE / Path(scene['image_path']).name).is_file()
