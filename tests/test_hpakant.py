"""The real-data Hpakant record must be exactly what build_hpakant.py makes from the cached NISAR windows."""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "raw" / "hpakant" / "manifest.json"
COMMITTED = REPO / "src" / "lib" / "data" / "scenarios" / "hpakant-observed.json"

spec = importlib.util.spec_from_file_location("build_hpakant", REPO / "scripts" / "build_hpakant.py")
bh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bh)


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    if not CACHE.exists():
        pytest.skip("NISAR windows not cached; run scripts/fetch_hpakant.py (needs Earthdata Login)")
    out = tmp_path_factory.mktemp("hpakant")
    bh.OUT_JSON, bh.OUT_STATIC = out / "hpakant-observed.json", out / "img"
    bh.main()
    return json.loads(bh.OUT_JSON.read_text(encoding="utf-8"))


def test_committed_record_matches_a_rebuild(rebuilt):
    assert json.loads(COMMITTED.read_text(encoding="utf-8")) == rebuilt


def test_only_consistent_passes_of_one_mode_are_compared(rebuilt):
    p = rebuilt["provenance"]
    assert all("_QPDH_" in g and "_P05023_" in g for g in p["gcov_granules"])
    assert any("calibration not consistent" in x["reason"] for x in p["excluded"])
    assert rebuilt["data_status"] == "REAL"


def test_wording_never_claims_mining_or_illegality():
    s = json.loads(COMMITTED.read_text(encoding="utf-8"))
    text = json.dumps(s["story"]) + json.dumps(s["uncertainty"])
    assert "illegal" not in text.lower()
    assert s["validation"]["precision"] is None  # no independent reference, so no accuracy is claimed


def test_patch_areas_add_up_to_each_pass_total(rebuilt):
    for k, m in enumerate(rebuilt["metrics"]):
        patches = {f["properties"]["patch_id"]: f["properties"] for f in rebuilt["geojson"]["features"] if f["properties"]["epoch"] == k}
        if m is None:
            assert not patches
            continue
        for kind, key in (("disturbed", "disturbed_m2"), ("new_water", "new_water_m2")):
            assert sum(p["area_m2"] for p in patches.values() if p["kind"] == kind) == m[key]
        assert sum(p["kind"] == "disturbed" for p in patches.values()) == m["clusters"]


def test_patch_properties_cover_every_pass(rebuilt):
    n = len(rebuilt["epochs"])
    for f in rebuilt["geojson"]["features"]:
        p = f["properties"]
        assert len(p["hv_db"]) == len(p["hh_db"]) == n
        assert p["area_m2"] >= rebuilt["thresholds"]["min_cluster_m2"]
        assert p["epoch"] in p["seen_on"]
        w, s, e, nn = p["bbox"]
        assert w <= p["centroid"][0] <= e and s <= p["centroid"][1] <= nn
        if p["kind"] == "disturbed":
            assert p["drop_db_median"] >= rebuilt["thresholds"]["drop_db"]
        else:
            assert p["drop_db_median"] is None


def test_hv_series_follows_latest_change_and_reference(rebuilt):
    s = rebuilt["hv_series"]
    n = len(rebuilt["epochs"])
    assert len(s["reference"]) == len(s["disturbed"]) == n
    assert s["disturbed_m2"] == rebuilt["metrics"][-1]["disturbed_m2"]
    # The per-pass offset holds the reference median at its latest-pass level.
    assert len({r["median"] for r in s["reference"]}) == 1
    for r in s["reference"] + s["disturbed"]:
        assert r["p25"] <= r["median"] <= r["p75"]
