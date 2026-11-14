"""Build browser previews and selectable evidence from the archived optical audit.

Uses cached crops only. Does not rerun or tune detection or reference classification.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer
import rasterio
from rasterio.features import shapes
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject, transform_geom
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/validation/yangon-track40-frame10'


def build():
    report = json.loads((OUT / 'comparison.json').read_text())
    audit = json.loads((OUT / 'scene-audit.json').read_text())
    raw = gzip.decompress((OUT / 'candidate-mask.npy.gz').read_bytes())
    if hashlib.sha256(raw).hexdigest() != report['candidate_mask_sha256']:
        raise ValueError('Archived mask does not match the optical audit.')
    mask = np.load(io.BytesIO(raw)).astype(bool)
    components, n = label(mask)
    if n != len(report['components']):
        raise ValueError('Component labeling differs from the audit.')
    transform = Affine(*audit['target_transform'])
    to_geo = Transformer.from_crs(audit['target_crs'], 4326, always_xy=True)
    height, width = mask.shape
    corners = [list(to_geo.transform(*(transform * point)))
               for point in [(0, 0), (width, 0), (width, height), (0, height)]]
    features = []
    for geom, value in shapes(components.astype('int16'), mask=mask, transform=transform, connectivity=4):
        features.append({'type': 'Feature', 'properties': {'component': int(value)},
                         'geometry': transform_geom(audit['target_crs'], 'EPSG:4326', geom, precision=9)})
    visual_assets = json.loads((OUT / 'visual-assets.json').read_text())
    scenes = []
    classifications = {}
    for asset in visual_assets:
        source = ROOT / asset['crop']
        if hashlib.sha256(source.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError(f'Optical crop changed: {source}')
        row = next(scene for scene in report['scenes'] if scene['id'] == asset['id'])
        with rasterio.open(source) as src:
            rgb = np.zeros((3, height, width), dtype='uint8')
            for band in range(3):
                reproject(src.read(band+1), rgb[band], src_transform=src.transform,
                          src_crs=src.crs, dst_transform=transform, dst_crs=audit['target_crs'],
                          src_nodata=0, dst_nodata=0, resampling=Resampling.bilinear)
        name = f"{row['id']}_true-color.png"
        Image.fromarray(np.moveaxis(rgb, 0, -1)).save(OUT / name, optimize=True)
        with np.load(OUT / 'crops' / f"{row['id']}_aligned.npz") as arrays:
            classifications[row['id']] = (arrays['scl'], arrays['clear'])
        scenes.append({key: row[key] for key in ('id', 'datetime', 'baseline_offset_days', 'repeat_offset_days')}
                      | {'image_path': f"validation/{report['event_id']}/{name}",
                         'source_url': asset['asset'], 'scl_source_url': row['scl_asset']})
    candidates = []
    for component in report['components']:
        selected = components == component['component']
        if int(selected.sum()) != component['candidate_pixels']:
            raise ValueError('Component footprint does not match the audit.')
        reference = []
        for scene in scenes:
            scl, clear = classifications[scene['id']]
            usable = selected & clear
            reference.append({'scene_id': scene['id'], 'water_pixels': int((usable & (scl == 6)).sum()),
                              'land_pixels': int((usable & (scl != 6)).sum()),
                              'unknown_pixels': int((selected & ~clear).sum())})
        candidates.append({**component, 'area_m2': component['candidate_pixels'] * 100,
                           'references': reference})
    manifest = {
        'event_id': report['event_id'], 'candidate_mask_sha256': report['candidate_mask_sha256'],
        'nisar_dates': report['nisar_dates'], 'corner_coordinates': corners,
        'geometry_note': 'Exact pixel-edge footprints of four-connected candidate components; IDs match comparison.json.',
        'reference_note': '20 m Sentinel-2 SCL on the 10 m radar grid. Unknown includes clouds, shadows, unclassified cells and the exclusion buffer.',
        'scenes': scenes, 'candidates': candidates,
        'geometry': {'type': 'FeatureCollection', 'features': features},
    }
    (OUT / 'map-evidence.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f"Built {len(scenes)} optical previews and {len(candidates)} selectable candidates ({int(mask.sum())} cells).")


if __name__ == '__main__':
    build()
