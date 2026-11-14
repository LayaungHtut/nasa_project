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
