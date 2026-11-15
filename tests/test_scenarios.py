"""The simulated scenarios: their storyline must come out of the detection, and the
committed JSON must be exactly what the generator produces."""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_scenarios", REPO / "scripts" / "build_scenarios.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("scenarios")
    bs.STATIC_DIR, bs.DATA_DIR = tmp / "static", tmp / "data"
    return {"mining": bs.build_mining(), "landslide": bs.build_landslide()}


def test_mining_moves_from_compliant_to_watch_to_breach(built):
    s = built["mining"]
    limit = s["thresholds"]["breach_outside_m2"]
    beyond = [m["outside_beyond_tolerance_m2"] for m in s["metrics"]]
    assert beyond[:2] == [0, 0]
    assert 0 < beyond[2] < limit  # a nibble past the line: watch, not breach
    assert beyond[3] >= limit and beyond[4] > beyond[3]
    for m in s["metrics"]:
        assert m["inside_m2"] + m["outside_m2"] == m["new_clearing_m2"]
    assert s["metrics"][-1]["max_subsidence_outside_cm"] >= s["thresholds"]["subsidence_watch_cm"]
    assert s["validation"]["recall"] > 0.9 and s["validation"]["precision"] > 0.9


def test_landslide_precedes_and_explains_the_diversion(built):
    s = built["landslide"]
    m, t = s["metrics"], s["thresholds"]
    slide = [x["landslide_m2"] >= t["landslide_min_m2"] for x in m]
    diverted = [x["channel_shift_m"] >= t["channel_shift_m"] and x["new_channel_m2"] >= t["new_channel_min_m2"] for x in m]
    assert slide == [False, False, True, True]
    assert diverted == [False, False, False, True]
    assert m[2]["coherence_at_slide"] < t["coherence_min"]  # the slide destroyed coherence
    assert m[2]["impoundment_m2"] > 0 and m[3]["impoundment_m2"] > m[2]["impoundment_m2"]
    assert all(abs(x["control_reach_water_change_pct"]) < 10 for x in m)  # no basin-wide flood
    assert s["linkage"]["slide_is_upstream"] and 0 < s["linkage"]["river_distance_km"] < t["link_max_km"]
    assert s["linkage"]["precursor_creep_cm"] > 0.5
    assert s["validation"]["precision"] > 0.8 and s["validation"]["recall"] > 0.6


def test_committed_scenarios_match_the_generator(built):
    for s in built.values():
        committed = json.loads((REPO / "src" / "lib" / "data" / "scenarios" / f"{s['id']}.json").read_text(encoding="utf-8"))
        assert committed == json.loads(json.dumps(s)), f"{s['id']}: rerun python scripts/build_scenarios.py"


def test_every_scenario_is_labelled_simulated(built):
    for s in built.values():
        assert s["data_status"] == "SIMULATED"
        assert "fictional" in json.dumps(s).lower() or "illustrative" in s["location"]["name"].lower()
