from fastapi.testclient import TestClient
import pytest

from backend.main import app


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ZoneGuard API online"
    assert response.json()["ui"] == "/ui"
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers


def test_health_and_ready_endpoints(client: TestClient) -> None:
    liveness = client.get("/health")
    readiness = client.get("/ready")
    assert liveness.status_code == 200
    assert readiness.status_code == 200
    assert liveness.json()["status"] == "ok"
    assert readiness.json()["status"] == "ready"


def test_predict_and_anomaly_routes(client: TestClient) -> None:
    p = client.get("/predict", params={"zone": "zone_01", "horizon": 3})
    assert p.status_code == 200
    assert p.json()["zone_id"] == "zone_01"

    a = client.post("/anomaly", json={"zone": "zone_01", "lookback": 72})
    assert a.status_code == 200
    assert "events" in a.json()


def test_reason_action_feedback_routes(client: TestClient) -> None:
    anomaly = client.post("/anomaly", json={"zone": "zone_01", "lookback": 72}).json()
    event = anomaly["events"][0] if anomaly["events"] else {
        "event_id": "zone_01:fallback",
        "snapshot": {"demand": 80, "drivers": 60, "inventory": 65, "weather": "clear", "availability": 0.6},
    }

    r = client.post("/reason", json={"event": event})
    assert r.status_code == 200

    act = client.post("/action", json={"event": event, "explanation": r.json()["explanation"]})
    assert act.status_code == 200

    fb = client.post(
        "/feedback",
        json={
            "event_id": event["event_id"],
            "rating": 4,
            "correction": "Reasoning largely correct.",
            "metadata": {"from": "api-test"},
        },
    )
    assert fb.status_code == 200
    assert fb.json()["status"] == "ok"


def test_pipeline_route(client: TestClient) -> None:
    response = client.post("/pipeline/zone", json={"zone": "zone_01", "horizon": 4, "lookback": 72})
    assert response.status_code == 200
    payload = response.json()
    assert payload["zone_id"] == "zone_01"
    assert "traces" in payload
    assert "forecast" in payload
    assert "anomalies" in payload


def test_replay_evaluation_route(client: TestClient) -> None:
    response = client.post("/evaluate/replay", json={"zone": "zone_01", "horizon": 4, "lookback": 72})
    assert response.status_code == 200
    payload = response.json()
    assert payload["zone_id"] == "zone_01"
    assert "forecast_mape" in payload
    assert "business_impact" in payload
