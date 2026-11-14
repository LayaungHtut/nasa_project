"""Independent Sentinel-2 reference audit for the existing Hlawga NISAR result.

Does not tune or rewrite the NISAR classification. Optical SCL is a reference
classification, not ground truth. All areas use the original NISAR pixel mask.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import gzip
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.warp import reproject, transform_bounds, Resampling
from rasterio.windows import Window, from_bounds
from pyproj import Transformer
from scipy.ndimage import binary_dilation, label, shift

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / 'data/processed/yangon-track40-frame10'
OUT = ROOT / 'data/validation/yangon-track40-frame10'
PRIMARY_DAYS = 3
EXPLORATORY_DAYS = 7
CLEAR_CLASSES = (4, 5, 6)  # vegetation, bare/non-vegetated, water
SCL_NAMES = {0: 'nodata', 1: 'defective', 2: 'cast_shadow', 3: 'cloud_shadow',
             4: 'vegetation', 5: 'not_vegetated', 6: 'water', 7: 'unclassified',
             8: 'medium_cloud', 9: 'high_cloud', 10: 'cirrus', 11: 'snow_ice'}


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry_digest(path):
    # Parsed JSON, compact: line endings and reformatting must not break the audit link.
    return hashlib.sha256(json.dumps(json.loads(path.read_text()), separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def candidate_bytes():
    """Preserve the exact input in a tiny archive so the audit is reproducible."""
    source = EVENT / 'change_mask.npy'
    archive = OUT / 'candidate-mask.npy.gz'
    if source.exists():
        content = source.read_bytes()
        OUT.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(gzip.compress(content, mtime=0))
        return content
    return gzip.decompress(archive.read_bytes())


def candidate_mask():
    return np.load(io.BytesIO(candidate_bytes())).astype(bool)


def target_grid(metadata, shape):
    """Stored image corners are pixel CENTERS, so offset half a pixel for GDAL."""
    transform = Transformer.from_crs('EPSG:4326', 'EPSG:32647', always_xy=True)
    xy = [transform.transform(*corner) for corner in metadata['tiles']['corner_coordinates']]
    dx = (xy[1][0] - xy[0][0]) / (shape[1] - 1)
    dy = (xy[3][1] - xy[0][1]) / (shape[0] - 1)
    if not np.allclose([dx, dy], [10, -10], atol=0.002):
        raise ValueError(f'Unexpected grid spacing: {dx}, {dy}')
    return Affine(10, 0, round(xy[0][0], 3) - 5, 0, -10, round(xy[0][1], 3) + 5)


def read_crop(item, asset_key, bbox):
    """Cache a small georeferenced AOI crop, never the whole 100 km tile."""
    path = OUT / 'crops' / f"{item['id']}_{asset_key}.tif"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with rasterio.open(path) as src:
            return src.read(), src.transform, src.crs, path
    href = item['assets'][asset_key]['href']
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_TIMEOUT='45',
                      GDAL_HTTP_MAX_RETRY='2', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
        with rasterio.open(href) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox, densify_pts=21)
            # A 60 m margin lets the cloud/shadow buffer extend outside the AOI.
            window = from_bounds(left-60, bottom-60, right+60, top+60, src.transform)
            col0, row0 = int(np.floor(window.col_off)), int(np.floor(window.row_off))
            col1, row1 = int(np.ceil(window.col_off+window.width)), int(np.ceil(window.row_off+window.height))
            window = Window(col0, row0, col1-col0, row1-row0).intersection(Window(0, 0, src.width, src.height))
            array = src.read(window=window)
            affine = src.window_transform(window)
            crs = src.crs
            profile = dict(driver='GTiff', width=array.shape[2], height=array.shape[1],
                           count=array.shape[0], dtype=array.dtype, crs=crs,
                           transform=affine, nodata=0, compress='deflate')
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(array)
    return array, affine, crs, path


def project(array, affine, crs, shape, target, resampling=Resampling.nearest):
    result = np.zeros(shape, dtype=array.dtype)
    reproject(array, result, src_transform=affine, src_crs=crs,
              dst_transform=target, dst_crs='EPSG:32647', resampling=resampling,
              src_nodata=0, dst_nodata=0)
    return result


def quality_mask(scl, buffer_pixels=1):
    # Unclassified, shadow, cloud, snow, nodata and defective cells stay unknown.
    bad = ~np.isin(scl, CLEAR_CLASSES)
    return ~binary_dilation(bad, iterations=buffer_pixels, border_value=1) if buffer_pixels else ~bad


def compare_pair(candidate, before_scl, before_clear, after_scl, after_clear):
    """Partition candidates; unknown reference cells must never become dry land."""
    usable = candidate & before_clear & after_clear
    before_water, after_water = before_scl == 6, after_scl == 6
    counts = {
        'candidate_pixels': int(candidate.sum()),
        'joint_clear_pixels': int(usable.sum()),
        'land_to_water_pixels': int((usable & ~before_water & after_water).sum()),
        'land_to_land_pixels': int((usable & ~before_water & ~after_water).sum()),
        'water_to_water_pixels': int((usable & before_water & after_water).sum()),
        'water_to_land_pixels': int((usable & before_water & ~after_water).sum()),
        'unknown_pixels': int((candidate & ~usable).sum()),
    }
    assert sum(counts[k] for k in ('land_to_water_pixels', 'land_to_land_pixels',
                                 'water_to_water_pixels', 'water_to_land_pixels', 'unknown_pixels')) == counts['candidate_pixels']
    return counts


def choose_scene(rows, phase, window_days):
    eligible = [row for row in rows if abs(row[f'{phase}_offset_days']) <= window_days]
    return min(eligible, key=lambda row: (-row['candidate_clear_pixels_buffered'],
                                        abs(row[f'{phase}_offset_days']), row['id'])) if eligible else None


def aligned(row):
    with np.load(OUT / 'crops' / f"{row['id']}_aligned.npz") as arrays:
        return arrays['scl'], arrays['clear']


def compare_references(audit):
    candidate = candidate_mask()
    report = {key: audit[key] for key in ('event_id', 'generated_at', 'candidate_mask_sha256',
                                        'candidate_geometry_sha256', 'nisar_dates', 'selection_rule', 'quality_rule')}
    metadata = json.loads((EVENT / 'metadata.json').read_text())
    report.update(status='unconfirmed', reference='Copernicus Sentinel-2 L2A scene classification (SCL)',
                  processing_snapshot=metadata['processing'], results_snapshot=metadata['results'],
                  pixel_area_m2=100, reference_pixel_spacing_m=20,
                  candidate_pixels=int(candidate.sum()), candidate_area_km2=float(candidate.sum()/10000))
    report['scenes'] = []
    for row in audit['scenes']:
        scl, clear = aligned(row)
        usable = candidate & clear
        report['scenes'].append({**row, 'water_pixels': int((usable & (scl == 6)).sum()),
                                'land_pixels': int((usable & (scl != 6)).sum()),
                                'unknown_pixels': int((candidate & ~clear).sum())})
    for name, days in [('primary', PRIMARY_DAYS), ('exploratory', EXPLORATORY_DAYS)]:
        before = choose_scene(audit['scenes'], 'baseline', days)
        after = choose_scene(audit['scenes'], 'repeat', days)
        if before is None or after is None:
            raise ValueError(f'No scene within {name} window; explicitly handle missing reference.')
        bs, bc = aligned(before)
        ps, pc = aligned(after)
        report[name] = {'window_days': days, 'baseline_scene': before['id'], 'repeat_scene': after['id'],
                        'baseline_offset_days': before['baseline_offset_days'],
                        'repeat_offset_days': after['repeat_offset_days'],
                        **compare_pair(candidate, bs, bc, ps, pc)}
    # Translate both optical references together relative to radar: diagnostic,
    # not measured registration uncertainty or a statistical confidence interval.
    before = choose_scene(audit['scenes'], 'baseline', EXPLORATORY_DAYS)
    after = choose_scene(audit['scenes'], 'repeat', EXPLORATORY_DAYS)
    bs, bc = aligned(before)
    ps, pc = aligned(after)
    sensitivity = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            arrays = [shift(a, (dy, dx), order=0, mode='constant', cval=0, prefilter=False) for a in (bs, bc, ps, pc)]
            sensitivity.append({'row_shift_m': dy*10, 'col_shift_m': dx*10,
                                **compare_pair(candidate, *arrays)})
    report['registration_sensitivity'] = sensitivity
    # Per-component review table covers every original mask cell, without assuming
    # that rounded visualization contours reproduce the raster's area exactly.
    components, n = label(candidate)
    to_geo = Transformer.from_crs('EPSG:32647', 'EPSG:4326', always_xy=True)
    target = Affine(*audit['target_transform'])
    report['components'] = []
    for number in range(1, n+1):
        mask = components == number
        rows, cols = np.where(mask)
        x, y = target * (float(cols.mean())+.5, float(rows.mean())+.5)
        report['components'].append({'component': number, 'centroid_lon_lat': list(to_geo.transform(x, y)),
                                     **compare_pair(mask, bs, bc, ps, pc)})
    report['limitations'] = audit['limitations'] + [
        'Agreement is restricted to candidate pixels; no recall, specificity or whole-map accuracy is estimated.',
        'Optical scenes are temporally displaced. Land at the optical date is not proof of a radar false positive.',
        'Primary +/-3 day window and exploratory +/-7 day window are analyst choices, not a preregistered protocol.',
        'Candidate contours use rounded pixel centers. Areas and counts use the original raster mask, not polygon area.',
        'No surveyed registration control, field observations or reservoir records were used.',
        'An optical land-to-water match does not establish flood cause or exact timing.'
    ]
    report['summary'] = (
        f"{report['primary']['joint_clear_pixels']} paired clear candidate cells within +/-{PRIMARY_DAYS} days of both radar dates. "
        f"Exploratory +/-{EXPLORATORY_DAYS} day comparison: {report['exploratory']['land_to_water_pixels']} "
        f"land-to-water cells, {report['exploratory']['land_to_land_pixels']} land-to-land cells, "
        f"{report['exploratory']['unknown_pixels']} unknown out of {int(candidate.sum())}. "
        'Water-change interpretation remains unconfirmed.'
    )
    (OUT / 'comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(report['summary'], flush=True)
    return report


def render_reference_figure(audit, report):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.colors import ListedColormap

    metadata = json.loads((EVENT / 'metadata.json').read_text())
    catalog = json.loads((OUT / 'earth-search-sentinel2-initial.json').read_text())['response']['features']
    items = {item['id']: item for item in catalog}
    candidate = candidate_mask()
    target = Affine(*audit['target_transform'])
    ids = [report['exploratory']['baseline_scene'], report['primary']['repeat_scene'], report['exploratory']['repeat_scene']]
    rows = {row['id']: row for row in audit['scenes']}
    extent = [target.c/1000, (target.c+candidate.shape[1]*10)/1000,
              (target.f-candidate.shape[0]*10)/1000, target.f/1000]
    geometries = json.loads((EVENT / 'change.geojson').read_text())['features']
    tx = Transformer.from_crs('EPSG:4326', 'EPSG:32647', always_xy=True)
    outlines = []
    for feature in geometries:
        geom = feature['geometry']
        polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
        for poly in polys:
            for ring in poly:
                xs, ys = tx.transform(*np.array(ring).T)
                outlines.append((np.array(xs)/1000, np.array(ys)/1000))
    # Largest component sets the zoom independently of optical agreement.
    comp, _ = label(candidate)
    sizes = np.bincount(comp.ravel()); sizes[0] = 0
    rr, cc = np.where(comp == sizes.argmax())
    cx, cy = target * (float(cc.mean())+.5, float(rr.mean())+.5)
    supporting = max(report['components'], key=lambda c: c['land_to_water_pixels'])
    support_x, support_y = tx.transform(*supporting['centroid_lon_lat'])
    fig, axes = plt.subplots(3, 3, figsize=(15, 14))
    assets = []
    for column, item_id in enumerate(ids):
        print(f'Reading true color: {item_id}', flush=True)
        array, affine, crs, path = read_crop(items[item_id], 'visual', metadata['location']['bbox'])
        rgb = np.stack([project(band, affine, crs, candidate.shape, target,
                                Resampling.bilinear) for band in array[:3]], axis=-1)
        scl, clear = aligned(rows[item_id])
        overlay = np.zeros(candidate.shape, dtype='uint8')
        overlay[candidate & clear & (scl == 6)] = 1
        overlay[candidate & clear & (scl != 6)] = 2
        overlay[candidate & ~clear] = 3
        cmap = ListedColormap(['#00000000', '#00e5ff', '#ff3d75', '#ffd740'])
        offset_key = 'baseline_offset_days' if column == 0 else 'repeat_offset_days'
        for i in range(3):
            ax = axes[i, column]
            ax.imshow(rgb, extent=extent)
            if i == 0:
                for xs, ys in outlines:
                    ax.plot(xs, ys, color='#ffd740', lw=.65)
            else:
                ax.imshow(overlay, extent=extent, cmap=cmap, vmin=0, vmax=3, interpolation='nearest')
                for xs, ys in outlines:
                    ax.plot(xs, ys, color='white', lw=.55, alpha=.8)
                zx, zy = (cx, cy) if i == 1 else (support_x, support_y)
                ax.set_xlim(zx/1000-.35, zx/1000+.35)
                ax.set_ylim(zy/1000-.35, zy/1000+.35)
            ax.set_xlabel('Easting (km, UTM 47N)')
            if column == 0:
                ax.set_ylabel('Northing (km, UTM 47N)')
            ax.tick_params(labelsize=8)
            ax.ticklabel_format(useOffset=False, style='plain')
        axes[0, column].set_title(f"{rows[item_id]['datetime'][:10]} optical\n{rows[item_id][offset_key]:+.2f} days from {'baseline' if column == 0 else 'repeat'} radar", fontsize=11)
        r = next(row for row in report['scenes'] if row['id'] == item_id)
        axes[1, column].set_title(f"Largest candidate component (same 700 m view)\nAll candidates: {r['water_pixels']} water / {r['land_pixels']} land / {r['unknown_pixels']} unknown", fontsize=9)
        axes[2, column].set_title(f"Component {supporting['component']}: {supporting['land_to_water_pixels']} land-to-water matches\nSelected to inspect the limited supporting evidence", fontsize=9)
        assets.append({'id': item_id, 'asset': items[item_id]['assets']['visual']['href'],
                       'crop': str(path.relative_to(ROOT)).replace('\\', '/'), 'sha256': digest(path)})
    handles = [Line2D([0], [0], color='#ffd740', lw=1, label='Overview: original candidate outlines')]
    handles += [Line2D([0], [0], marker='s', color='none', markerfacecolor=color, markersize=8, label=label_)
                for color, label_ in [('#00e5ff', 'Zoom: optical water'), ('#ff3d75', 'Zoom: optical land'), ('#ffd740', 'Zoom: unknown/excluded')]]
    fig.legend(handles=handles, loc='lower center', ncol=2, bbox_to_anchor=(.5, .037), fontsize=10)
    fig.suptitle('Hlawga independent optical check: water change remains unconfirmed', fontsize=16, y=.985)
    fig.text(.5, .015, 'Contains modified Copernicus Sentinel data (2026), via Earth Search. SCL is a 20 m algorithmic reference; time offsets prevent exact-date confirmation.', ha='center', fontsize=9)
    fig.tight_layout(rect=[0, .105, 1, .945])
    fig.savefig(OUT / 'optical-comparison.png', dpi=160)
    plt.close(fig)
    (OUT / 'visual-assets.json').write_text(json.dumps(assets, indent=2), encoding='utf-8')


def audit_scenes():
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((EVENT / 'metadata.json').read_text())
    candidate = candidate_mask()
    target = target_grid(metadata, candidate.shape)
    catalog_path = OUT / 'earth-search-sentinel2-initial.json'
    if not catalog_path.exists():
        params = {'collections': 'sentinel-2-l2a', 'bbox': ','.join(map(str, metadata['location']['bbox'])),
                  'datetime': '2026-08-20T00:00:00Z/2026-09-16T23:59:59Z', 'limit': 100}
        url = 'https://earth-search.aws.element84.com/v1/search?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=45) as response:
            catalog = json.load(response)
        catalog_path.write_text(json.dumps({'query_url': url, 'response': catalog}, indent=2))
    catalog = json.loads(catalog_path.read_text())['response']
    if len(catalog['features']) != catalog.get('numberMatched'):
        raise ValueError('Search is incomplete; retrieve all pages before ranking scenes.')
    # Tile 46QHD covers the whole AOI. Neighboring 46QHE overlaps its northern edge;
    # duplicate tiles of the same acquisition are not independent observations.
    items = sorted([f for f in catalog['features'] if f['properties'].get('grid:code') == 'MGRS-46QHD'],
                   key=lambda f: f['properties']['datetime'])
    rows = []
    for item in items:
        print(f"Reading SCL: {item['id']}", flush=True)
        array, affine, crs, path = read_crop(item, 'scl', metadata['location']['bbox'])
        native_scl = array[0]
        scl = project(native_scl, affine, crs, candidate.shape, target)
        clear = project(quality_mask(native_scl).astype('uint8'), affine, crs, candidate.shape, target).astype(bool)
        counts = {SCL_NAMES[int(k)]: int(n) for k, n in zip(*np.unique(scl[candidate], return_counts=True))}
        row = {
            'id': item['id'], 'datetime': item['properties']['datetime'],
            'scene_cloud_percent': item['properties']['eo:cloud_cover'],
            'baseline_offset_days': (utc(item['properties']['datetime'])-utc(metadata['observation_dates']['baseline'])).total_seconds()/86400,
            'repeat_offset_days': (utc(item['properties']['datetime'])-utc(metadata['observation_dates']['post_event'])).total_seconds()/86400,
            'aoi_covered_fraction': float(np.mean(scl != 0)),
            'aoi_clear_fraction_buffered': float(np.mean(clear)),
            'candidate_pixels': int(candidate.sum()),
            'candidate_clear_pixels_buffered': int((clear & candidate).sum()),
            'candidate_scl_counts_unbuffered': counts,
            'scl_asset': item['assets']['scl']['href'],
            'crop_sha256': digest(path),
            'crop': str(path.relative_to(ROOT)).replace('\\', '/')
        }
        np.savez_compressed(OUT / 'crops' / f"{item['id']}_aligned.npz", scl=scl, clear=clear)
        rows.append(row)
        print(json.dumps(row), flush=True)
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'event_id': metadata['id'], 'candidate_mask_sha256': hashlib.sha256(candidate_bytes()).hexdigest(),
        'candidate_geometry_sha256': geometry_digest(EVENT/'change.geojson'),
        'nisar_dates': metadata['observation_dates'],
        'target_crs': 'EPSG:32647', 'target_transform': list(target)[:6],
        'target_shape': list(candidate.shape),
        'primary_window_days': PRIMARY_DAYS, 'exploratory_window_days': EXPLORATORY_DAYS,
        'selection_rule': 'Rank by usable candidate coverage, then absolute time offset; never by agreement with NISAR.',
        'quality_rule': 'SCL 4/5/6 only; exclude one native pixel (20 m, four-connected neighbors) around every other class. Nearest-neighbor reprojection.',
        'scenes': rows,
        'limitations': ['SCL is an independent algorithmic reference, not field ground truth.',
                        '20 m SCL resampled to a 10 m grid does not create independent 10 m reference information.',
                        'A temporally displaced optical observation cannot confirm the exact timing of change.']
    }
    (OUT/'scene-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true', help='Download/cache true-color crops and render the overlay figure')
    args = parser.parse_args()
    audit = audit_scenes()
    comparison = compare_references(audit)
    if args.figures:
        render_reference_figure(audit, comparison)
