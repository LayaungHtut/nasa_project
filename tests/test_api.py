import pytest
from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_list_events_returns_the_fixture_and_hides_ai_field_shape():
    response = client.get("/api/events")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert len(body["events"]) >= 1
    event = body["events"][0]
    assert "ai_explanation" not in event
    assert "has_explanation" in event


def test_get_known_event_matches_contract_shape():
    response = client.get("/api/events/demo-yangon-fixture")
    assert response.status_code == 200
    event = response.json()
    for key in ("id", "phenomenon", "data_status", "location", "observation_dates", "source_products", "processing", "results", "tiles", "change_geometry_url"):
        assert key in event
    # three-tier separation must survive serialization: NASA-observation
    # fields, our-processing fields, and AI fields must stay distinct keys
    assert "granule_id" in event["source_products"][0]
    assert "confidence" in event["results"]
    assert event["ai_explanation"] is None or isinstance(event["ai_explanation"], str)


def test_get_unknown_event_returns_404_with_error_schema():
    response = client.get("/api/events/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "event_not_found"


def test_explain_endpoint_is_grounded_and_cacheable():
    r1 = client.post("/api/events/demo-yangon-fixture/explain")
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["cached"] is False
    assert "1.528" in body1["ai_explanation"] or "km" in body1["ai_explanation"]

    r2 = client.post("/api/events/demo-yangon-fixture/explain")
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
    assert r2.json()["ai_explanation"] == body1["ai_explanation"]


def test_explain_unknown_event_404s_before_calling_ai():
    response = client.post("/api/events/does-not-exist/explain")
    assert response.status_code == 404
