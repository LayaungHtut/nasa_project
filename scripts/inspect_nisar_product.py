"""Inspect a NISAR HDF5 product's real internal structure.

Per the project's rule "do not assume the internal structure of the file,"
this script makes no assumptions -- it walks whatever HDF5 tree the file
actually contains and reports every group/dataset with shape, dtype, and
attributes, then separately checks whether the documented GCOV paths
(services/processing/io_gcov.py) are actually present.

Usage:
    python scripts/inspect_nisar_product.py path/to/granule.h5 [--max-depth N]

As of 2026-09-18 this has not been run against a real granule in this
environment: ASF requires Earthdata Login for all NISAR files, including
sidecar files as small as 27 bytes (confirmed via curl -- see
docs/demo/data-provenance.md). Run this the moment a real .h5 lands in
data/raw/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, so `services.*` imports work when run directly

import h5py

from services.processing.io_gcov import GRID_GROUP_TMPL, MASK_TMPL, POL_DATASET_TMPL, PROJECTION_TMPL, X_COORD_TMPL, Y_COORD_TMPL


def describe_node(name: str, obj) -> dict:
    info: dict = {"path": "/" + name, "type": type(obj).__name__}
    if isinstance(obj, h5py.Dataset):
        info["shape"] = obj.shape
        info["dtype"] = str(obj.dtype)
        if obj.size and obj.size < 1_000_000:
            try:
                info["nan_count"] = None
            except Exception:
                pass
    info["attrs"] = {k: _jsonable(v) for k, v in obj.attrs.items()}
    return info


def _jsonable(v):
    try:
        json.dumps(v)
        return v
    except TypeError:
        if hasattr(v, "tolist"):
            return v.tolist()
        return str(v)


def walk(h5_path: str, max_depth: int | None) -> list[dict]:
    out = []

    def visitor(name, obj):
        if max_depth is not None and name.count("/") > max_depth:
            return
        out.append(describe_node(name, obj))

    with h5py.File(h5_path, "r") as f:
        f.visititems(visitor)
    return out


def check_documented_paths(h5_path: str, freq: str = "A") -> dict:
    checks = {
        "grid_group": GRID_GROUP_TMPL.format(freq=freq),
        "xCoordinates": X_COORD_TMPL.format(freq=freq),
        "yCoordinates": Y_COORD_TMPL.format(freq=freq),
        "projection": PROJECTION_TMPL.format(freq=freq),
        "mask": MASK_TMPL.format(freq=freq),
        "HHHH": POL_DATASET_TMPL.format(freq=freq, pol="HHHH"),
        "HVHV": POL_DATASET_TMPL.format(freq=freq, pol="HVHV"),
    }
    results = {}
    with h5py.File(h5_path, "r") as f:
        for label, path in checks.items():
            results[label] = {"path": path, "present": path in f}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("h5_path")
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--freq", default="A")
    args = parser.parse_args()

    print(f"=== Documented GCOV path check (freq {args.freq}) ===")
    for label, result in check_documented_paths(args.h5_path, args.freq).items():
        mark = "OK" if result["present"] else "MISSING"
        print(f"[{mark}] {label}: {result['path']}")

    print("\n=== Full tree (every group/dataset actually in the file) ===")
    nodes = walk(args.h5_path, args.max_depth)
    for node in nodes:
        line = f"{node['path']}  ({node['type']})"
        if "shape" in node:
            line += f"  shape={node['shape']} dtype={node['dtype']}"
        print(line)
        if node["attrs"]:
            print(f"    attrs: {node['attrs']}")

    print(f"\nTotal nodes: {len(nodes)}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(1)
    main()
