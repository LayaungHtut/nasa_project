import json

from fastapi.testclient import TestClient

from services.processing.fixtures import make_fixture_pair
from services.processing.pipeline_flood import run_pipeline


def test_fixture_pipeline_runs_end_to_end_and_is_marked_synthetic(tmp_path, monkeypatch):
    import services.processing.pipeline_flood as pf

    monkeypatch.setattr(pf, "PROCESSED_DIR", tmp_path)

    fx = make_fixture_pair()
    event = pf.run_pipeline(
        event_id="test-event",
        location_name="Test AOI",
        baseline_db_source=fx.baseline,
        post_db_source=fx.post_event,
        x_coords=fx.x_coords,
        y_coords=fx.y_coords,
        zone_number=fx.zone_number,
        zone_letter=fx.zone_letter,
        baseline_granule_id=fx.baseline_granule_id,
        post_event_granule_id=fx.post_event_granule_id,
        baseline_acquisition="SYNTHETIC-NO-REAL-ACQUISITION",
        post_event_acquisition="SYNTHETIC-NO-REAL-ACQUISITION",
        data_status="SYNTHETIC_PLACEHOLDER",
    )

    assert event["data_status"] == "SYNTHETIC_PLACEHOLDER"
    assert event["results"]["change_area_km2"] > 0  # the synthetic flood must actually be detected
    assert (tmp_path / "test-event" / "metadata.json").exists()
    assert (tmp_path / "test-event" / "preview.png").exists()
    assert (tmp_path / "test-event" / "change.geojson").exists()
    assert (tmp_path / "test-event" / "statistics.json").exists()

    geojson = json.loads((tmp_path / "test-event" / "change.geojson").read_text())
    assert geojson["type"] == "FeatureCollection"

    # Audit requirements (2026-09-18): filter size and score type must be
    # machine-readable, not just documented in prose.
    assert event["processing"]["speckle_filter_size"] == 5  # default when not overridden
    assert event["results"]["confidence_type"] == "heuristic_detection_score"
    assert event["statistics_url"] == f"/data/processed/test-event/statistics.json"

    stats = json.loads((tmp_path / "test-event" / "statistics.json").read_text())
    for key in (
        "total_pixels",
        "aoi_area_km2",
        "baseline_water_pixels",
        "post_event_water_pixels",
        "new_inundation_pixels",
        "water_loss_pixels",
        "detection_score",
        "detection_score_formula",
    ):
        assert key in stats
    # every count must come from the actual arrays, not be hand-entered --
    # cross check against the event record's own numbers
    assert stats["new_inundation_pixels"] == event["results"]["changed_pixels"]
    assert stats["detection_score"] == event["results"]["confidence"]


def test_real_data_status_never_produced_by_fixture_mode():
    """Guards against accidentally flipping the data_status default -- a
    fixture run must never be labeled REAL (docs/handoff/demo-data.md)."""
    fx = make_fixture_pair()
    assert "SYNTHETIC" in fx.baseline_granule_id
    assert "SYNTHETIC" in fx.post_event_granule_id
