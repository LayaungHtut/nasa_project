import json

import numpy as np
import pytest

import services.processing.polarimetry as pm


def _quality(hv_rfi=1.0):
    return {
        "rfi_likelihood": {"HH": 1.0, "HV": hv_rfi},
        "noise_equivalent_backscatter_db": {"HH": -22.0, "HV": -21.0},
        "flags": {"noise_correction_applied": False, "rfi_mitigation_applied": False},
    }


def _scene(hv_offset_db, hv_repeat_shift_db=0.0):
    """HH: land at -5 dB with a dark 'reservoir' block at -12 dB that brightens
    to -8 dB on the repeat date. HV: HH + offset, optionally shifted on the repeat date."""
    hh_b = np.full((40, 40), -5.0)
    hh_b[10:20, 10:20] = -12.0
    hh_r = hh_b.copy()
    hh_r[10:20, 10:20] = -8.0
    return {"baseline": hh_b, "repeat": hh_r}, {
        "baseline": hh_b + hv_offset_db,
        "repeat": hh_r + hv_offset_db + hv_repeat_shift_db,
    }


def _run(tmp_path, monkeypatch, hh, hv):
    monkeypatch.setattr(pm, "PROCESSED_DIR", tmp_path)
    return pm.run_polarimetry(
        event_id="t",
        hh=hh,
        hv=hv,
        quality={"baseline": _quality(), "repeat": _quality()},
        granules={"baseline": "B", "repeat": "R"},
        threshold_db=-9.54,
        lee_filter_size=3,
        aoi={"lat": 0, "lon": 0, "half_width_km": 1},
    )


def test_healthy_hv_is_accepted_and_classes_follow_hh(tmp_path, monkeypatch):
    hh, hv = _scene(hv_offset_db=-7.0)
    record = _run(tmp_path, monkeypatch, hh, hv)

    assert record["hv_assessment"] == {"hv_usable_for_interpretation": True, "reasons": []}
    assert record["classes"]["apparent_water_loss"]["pixels"] == 100
    assert record["classes"]["apparent_water_loss"]["HH"] == {"baseline": -12.0, "repeat": -8.0}
    assert record["hh_difference_db"]["apparent_water_loss_median"] == 4.0
    for name in ("baseline_hv.png", "post_event_hv.png", "difference_hh.png", "polarization.json"):
        assert (tmp_path / "t" / name).exists()


def test_hv_brighter_than_hh_and_unstable_over_land_is_rejected(tmp_path, monkeypatch):
    hh, hv = _scene(hv_offset_db=+2.0, hv_repeat_shift_db=-1.5)
    record = _run(tmp_path, monkeypatch, hh, hv)

    assessment = record["hv_assessment"]
    assert assessment["hv_usable_for_interpretation"] is False
    assert len(assessment["reasons"]) == 2
    assert "HV shifts 1.50 dB" in assessment["reasons"][1]


def test_mismatch_with_statistics_json_is_refused(tmp_path, monkeypatch):
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "statistics.json").write_text(json.dumps({"water_loss_pixels": 1, "new_inundation_pixels": 0}))
    hh, hv = _scene(hv_offset_db=-7.0)
    with pytest.raises(ValueError, match="do not match statistics.json"):
        _run(tmp_path, monkeypatch, hh, hv)


def test_difference_map_hides_small_changes_and_colours_by_sign():
    rgba = pm.difference_rgba(np.array([[0.5, -3.0, 3.0, np.nan]]))
    assert rgba[0, 0, 3] == 0 and rgba[0, 3, 3] == 0
    assert tuple(rgba[0, 1, :3]) == (59, 130, 246) and rgba[0, 1, 3] == 230
    assert tuple(rgba[0, 2, :3]) == (249, 115, 22)
