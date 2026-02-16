# ZoneGuard

ZoneGuard is a production-style multi-agent AI system for delivery-zone reliability. It simulates operational data, predicts availability drops, detects anomalies, explains root causes with an LLM interface, proposes corrective actions, and captures operator feedback for continuous improvement.

## Architecture

- Backend API: FastAPI (`backend/main.py`)
- Frontend dashboard: Streamlit (`dashboard/app.py`)
- Database: SQLite via SQLAlchemy async (`backend/db.py`)
- Forecasting agent: XGBoost (`backend/agents/forecast_agent.py`)
- Anomaly agent: IsolationForest (`backend/agents/anomaly_agent.py`)
- Reasoning agent: Ollama + Chroma memory (`backend/agents/reasoning_agent.py`)
- Action agent: Rule-based planner (`backend/agents/action_agent.py`)
- Feedback loop: `/feedback` persists to SQLite + vector memory
- Async orchestrator: `/pipeline/zone` executes full agent chain with step traces
- Replay evaluation: `/evaluate/replay` returns technical and business impact metrics
- Tailwind + Framer Motion UI: `/ui`
- Observability: request ID + latency headers (`X-Request-Id`, `X-Response-Time-Ms`)

## Folder Layout

```text
zoneguard/
+-- backend/
¦   +-- main.py
¦   +-- api/
¦   +-- agents/
¦   ¦   +-- forecast_agent.py
¦   ¦   +-- anomaly_agent.py
¦   ¦   +-- reasoning_agent.py
¦   ¦   +-- action_agent.py
¦   +-- db.py
+-- dashboard/
¦   +-- app.py
¦   +-- components/
+-- data/
¦   +-- simulate.py
¦   +-- loader.py
+-- evaluation/
¦   +-- metrics.py
¦   +-- dashboard.py
+-- tests/
+-- requirements.txt
+-- README.md
+-- deploy/
```

## Quick Start

1. Create environment and install dependencies:

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

2. Run backend API:

```bash
uvicorn backend.main:app --reload --port 8000
```

3. Open web UI:

`http://127.0.0.1:8000/ui`

The backend seeds synthetic data on startup if the database is empty.

## Data Simulation

Generate synthetic data manually:

```bash
python data/simulate.py
```

Fields generated:
- `zone_id`
- `timestamp`
- `demand`
- `drivers`
- `inventory`
- `weather`
- `availability`

## API Contract

### `GET /predict?zone=zone_01&horizon=6`
Response schema:

```json
{
  "zone_id": "zone_01",
  "horizon_hours": 6,
  "predictions": [
    {
      "timestamp": "2026-02-16T12:00:00",
      "predicted_availability": 0.71
    }
  ]
}
```

### `POST /anomaly`
Request schema:

```json
{
  "zone": "zone_01",
  "lookback": 120
}
```

Response schema:

```json
{
  "zone_id": "zone_01",
  "events": [
    {
      "event_id": "zone_01:2026-02-16T11:00:00",
      "timestamp": "2026-02-16T11:00:00",
      "zone_id": "zone_01",
      "score": 0.92,
      "snapshot": {
        "demand": 120.5,
        "drivers": 60.0,
        "inventory": 70.3,
        "availability": 0.44,
        "weather": "rain"
      }
    }
  ]
}
```

### `POST /reason`
Request schema:

```json
{
  "event": {
    "event_id": "zone_01:2026-02-16T11:00:00",
    "snapshot": {
      "demand": 120.5,
      "drivers": 60,
      "inventory": 70.3,
      "availability": 0.44,
      "weather": "rain"
    }
  }
}
```

Response schema:

```json
{
  "event_id": "zone_01:2026-02-16T11:00:00",
  "prompt": "You are ZoneGuard root-cause analyst...",
  "explanation": "{\"root_cause\":\"Demand-driver imbalance...\"}"
}
```

### `POST /action`
Request schema:

```json
{
  "event": {
    "event_id": "zone_01:2026-02-16T11:00:00",
    "snapshot": {
      "demand": 120.5,
      "drivers": 60,
      "inventory": 70.3
    }
  },
  "explanation": "{\"root_cause\":\"Demand-driver imbalance\"}"
}
```

Response schema:

```json
{
  "event_id": "zone_01:2026-02-16T11:00:00",
  "recommended_actions": [
    {
      "action": "Rebalance drivers",
      "detail": "Shift drivers from neighboring zones within next 30 minutes.",
      "priority": "high"
    }
  ],
  "reasoning_reference": "{\"root_cause\":\"Demand-driver imbalance\"}"
}
```

### `POST /feedback`
Request schema:

```json
{
  "event_id": "zone_01:2026-02-16T11:00:00",
  "rating": 5,
  "correction": "Weather impact was underestimated.",
  "metadata": {
    "submitted_by": "ops_lead"
  }
}
```

Response schema:

```json
{
  "status": "ok",
  "stored_at": "2026-02-16T12:12:12.000000"
}
```

### `POST /pipeline/zone`
Request schema:

```json
{
  "zone": "zone_01",
  "horizon": 6,
  "lookback": 120
}
```

### `POST /evaluate/replay`
Request schema:

```json
{
  "zone": "zone_01",
  "horizon": 6,
  "lookback": 120
}
```

Response schema:

```json
{
  "zone_id": "zone_01",
  "forecast_mape": 0.0742,
  "forecast_rmse": 0.0581,
  "anomaly_events": 7,
  "generated_actions": 14,
  "business_impact": {
    "incident_prevention_rate": 1.0,
    "estimated_mttr_reduction_minutes": 34.8,
    "action_acceptance_rate": 0.6,
    "estimated_ops_hours_saved": 5.06
  }
}
```

### `GET /health`
Liveness check: `{\"status\":\"ok\"}`

### `GET /ready`
Readiness check: `{\"status\":\"ready\"}`

Response schema:

```json
{
  "zone_id": "zone_01",
  "generated_at": "2026-02-16T12:45:00+00:00",
  "traces": [
    {"step": "forecast", "status": "ok", "latency_ms": 37.1, "details": {"count": 6}},
    {"step": "anomaly", "status": "ok", "latency_ms": 18.4, "details": {"events": 4}}
  ],
  "forecast": {},
  "anomalies": {},
  "reasoning": {},
  "actions": {}
}
```

## Feedback Loop

- Stores corrections in SQL (`feedback_records`) for auditability.
- Pushes feedback text into Chroma (`reasoning_history`) for future context retrieval.
- Reasoning agent queries prior context by event ID before generating explanations.

## Testing

Run all tests:

```bash
pytest -q
```

Test suite includes:
- Unit tests for simulation
- Integration tests for agents
- API tests for all required endpoints

## Deployment Guide

### Local Dockerless Deployment

1. Install dependencies and ensure Python 3.10+.
2. Start API with Uvicorn on port 8000.
3. Start Streamlit dashboard on port 8501.
4. Configure reverse proxy (Nginx/Caddy) for production HTTPS.

### Production Considerations

- Replace SQLite with Postgres by changing `DATABASE_URL` in `backend/db.py`.
- Run FastAPI with multiple workers behind Gunicorn/Uvicorn.
- Enable structured logging and centralized monitoring.
- Configure Ollama service endpoint and model pre-pull (`llama3.1` or equivalent).
- Use persistent volumes for `zoneguard.db` and `zoneguard_memory`.
- Add authentication/authorization before exposing APIs externally.

### Optional Container Deployment

Create Dockerfiles for backend and dashboard, then orchestrate with Docker Compose or Kubernetes. Keep Chroma and database volumes mounted for durability.

### Included Deployment Files
- `deploy/Dockerfile.backend`
- `deploy/docker-compose.yml`
- `.github/workflows/ci.yml`

