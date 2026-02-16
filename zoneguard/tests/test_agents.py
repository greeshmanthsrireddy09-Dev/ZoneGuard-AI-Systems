from backend.agents.action_agent import ActionAgent
from backend.agents.anomaly_agent import AnomalyAgent
from backend.agents.forecast_agent import ForecastAgent
from backend.agents.reasoning_agent import ReasoningAgent
from data.simulate import generate_synthetic_data


def test_forecast_agent_training_and_prediction() -> None:
    df = generate_synthetic_data(n_zones=2, hours=24 * 8, seed=1)
    agent = ForecastAgent()
    agent.train(df)
    result = agent.predict(df, zone_id="zone_01", horizon_hours=4)
    assert result.zone_id == "zone_01"
    assert len(result.predictions) == 4


def test_anomaly_agent_detects_events() -> None:
    df = generate_synthetic_data(n_zones=1, hours=24 * 6, seed=2)
    agent = AnomalyAgent(contamination=0.10)
    result = agent.detect(df, zone_id="zone_01", lookback=100)
    assert result.zone_id == "zone_01"
    assert isinstance(result.events, list)


def test_action_agent_returns_actions() -> None:
    action_agent = ActionAgent()
    event = {
        "event_id": "zone_01:2026-01-01T00:00:00",
        "snapshot": {"demand": 100, "drivers": 60, "inventory": 70},
    }
    plan = action_agent.plan(event, explanation="{}")
    assert plan["event_id"] == event["event_id"]
    assert len(plan["recommended_actions"]) >= 2


def test_reasoning_agent_returns_payload(tmp_path) -> None:
    reasoner = ReasoningAgent(persist_dir=str(tmp_path / "chroma_test"))
    event = {
        "event_id": "zone_01:test_event",
        "snapshot": {"demand": 90, "drivers": 65, "inventory": 75, "weather": "rain"},
    }
    res = reasoner.reason(event)
    assert res["event_id"] == event["event_id"]
    assert "explanation" in res
