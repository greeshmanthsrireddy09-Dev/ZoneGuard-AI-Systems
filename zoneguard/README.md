# ZoneGuard (Simple Guide)

ZoneGuard is an AI assistant for delivery operations.
It helps answer one practical question:

"Will a delivery zone's availability drop soon, why, and what should we do now?"

## What This Project Does (In Plain English)

Imagine each zone is a small mini-city for deliveries.
ZoneGuard watches signals like demand, drivers, inventory, and weather.
Then it does this:

1. Predicts if availability may drop soon.
2. Flags unusual behavior (anomalies).
3. Explains likely root cause in plain text/JSON.
4. Suggests corrective actions.
5. Learns from feedback.

## What "Availability" Means

Availability is a score between `0` and `1`.
- `1.0` means very healthy operations.
- `0.0` means severe operational stress.

Lower availability usually means customers may face delays, cancellations, or poor service quality.

## How It Works End-to-End

1. App starts.
2. If no data exists, synthetic data is auto-generated.
3. Forecast agent predicts future availability.
4. Anomaly agent finds unusual events.
5. Reasoning agent explains likely cause.
6. Action agent proposes fixes.
7. Feedback is saved for continuous improvement.

## Dashboard Insights (What Each Number Means)

When you open `/ui`, you will see these insights:

- `Risk` chip (`Stable`, `Watch`, `High Risk`):
  Simple traffic-light style alert from forecast + anomaly volume.

- `Forecast Points`:
  Number of future time steps predicted.

- `Anomalies`:
  Count of unusual events found in the selected lookback window.

- `Latest Availability`:
  Most recent predicted availability value.

- `Anomaly Radar` table:
  Shows when unusual events happened and how strong the anomaly score is.

- `Action Board`:
  Suggested steps like rebalancing drivers or inventory.

- `Business Impact Replay`:
  Offline evaluation numbers showing estimated impact.

## Business Impact Metrics (Layman Explanation)

From `/evaluate/replay`, you get:

- `forecast_mape`:
  Forecast average percentage error. Lower is better.

- `forecast_rmse`:
  Forecast error magnitude. Lower is better.

- `anomaly_events`:
  How many unusual events were detected.

- `incident_prevention_rate`:
  Estimated share of incidents the system could catch early.

- `estimated_mttr_reduction_minutes`:
  Estimated minutes saved in resolving incidents.

- `action_acceptance_rate`:
  Estimated ratio of action recommendations likely accepted by ops.

- `estimated_ops_hours_saved`:
  Estimated manual ops hours saved.

## Project Structure

```text
zoneguard/
├── backend/
│   ├── main.py
│   ├── api/
│   ├── agents/
│   └── db.py
├── dashboard/
├── dashboard_web/
├── data/
├── evaluation/
├── tests/
├── requirements.txt
└── README.md
```

## Quick Start (Local, No Cloud Required)

1. Create and activate virtual environment
```bash
python -m venv .venv
. .venv/Scripts/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Start backend
```bash
uvicorn backend.main:app --reload --port 8000
```

4. Open UI
- Main UI: `http://127.0.0.1:8000/ui`
- API docs: `http://127.0.0.1:8000/docs`

## Main API Endpoints

- `GET /predict?zone=zone_01&horizon=6`
- `POST /anomaly`
- `POST /reason`
- `POST /action`
- `POST /feedback`
- `POST /pipeline/zone`
- `POST /evaluate/replay`
- `GET /health`
- `GET /ready`

## Example API Calls

### Predict
```json
GET /predict?zone=zone_01&horizon=6
```

### Full Pipeline
```json
POST /pipeline/zone
{
  "zone": "zone_01",
  "horizon": 6,
  "lookback": 120
}
```

### Replay Evaluation
```json
POST /evaluate/replay
{
  "zone": "zone_01",
  "horizon": 6,
  "lookback": 120
}
```

## Testing

Run all tests:
```bash
pytest -q
```

## Notes

- This project is fully usable locally.
- Synthetic data is used by default.
- You can later connect real data sources if needed.

## Who This Is For

- Ops teams who need fast incident insights.
- AI/ML engineers building multi-agent systems.
- Recruiters/interviewers reviewing production-style AI architecture.
