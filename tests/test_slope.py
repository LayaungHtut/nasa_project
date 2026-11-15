"""The real Hpakant slope-motion record must be exactly what build_slope.py makes from the cached NISAR windows."""

import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
INSAR = REPO / "data" / "raw" / "hpakant" / "insar"
COMMITTED = REPO / "src" / "lib" / "data" / "scenarios" / "hpakant-slopes.json"

spec = importlib.util.spec_from_file_location("build_slope", REPO / "scripts" / "build_slope.py")
bsl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bsl)


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    if not any(INSAR.glob("*.npz")):
        pytest.skip("GUNW windows not cached; run scripts/fetch_hpakant_insar.py (needs Earthdata Login)")
    out = tmp_path_factory.mktemp("slopes")
    bsl.OUT_JSON, bsl.OUT_STATIC = out / "hpakant-slopes.json", out / "img"
    bsl.main()
    return json.loads(bsl.OUT_JSON.read_text(encoding="utf-8"))


def test_committed_record_matches_a_rebuild(rebuilt):
    assert json.loads(COMMITTED.read_text(encoding="utf-8")) == rebuilt


def test_positive_phase_is_motion_toward_the_satellite():
    lam = 0.2439
    # A full 2 pi cycle is half a wavelength of range change; ionosphere is removed before converting.
    assert bsl.los_cm(np.array([2 * np.pi]), np.array([0.0]), lam)[0] == pytest.approx(lam / 2 * 100)
    assert bsl.los_cm(np.array([1.0]), np.array([1.0]), lam)[0] == 0


def test_candidates_are_steep_beyond_noise_and_traceable(rebuilt):
    t, u = rebuilt["thresholds"], rebuilt["uncertainty"]
    for c in rebuilt["candidates"]:
        assert abs(c["rate_cm_yr"]) > 0.9 * t["sigma_k"] * u["rate_sigma_cm_yr"]
        assert c["sign_agreement"] >= t["sign_agreement_min"] - 0.05  # patch median of per-pixel agreement
    for e in rebuilt["epochs"]:
        assert e["gunw_granule_id"].startswith("NISAR_L2_PR_GUNW_") and "_062_D_075_" in e["gunw_granule_id"]
    assert rebuilt["data_status"] == "REAL"


def test_wording_never_confirms_a_landslide_or_calls_it_elevation():
    s = COMMITTED.read_text(encoding="utf-8").lower()
    assert "landslide detected" not in s
    # Every mention of a confirmed landslide must be a denial ("not a confirmed landslide").
    assert all(re.search(r"not (a )?$", s[: m.start()]) for m in re.finditer("confirmed landslide", s))
    assert "line of sight" in s or "line-of-sight" in s
