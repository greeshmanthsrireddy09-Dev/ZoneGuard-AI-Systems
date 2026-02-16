"""Streamlit dashboard for ZoneGuard operations."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import requests
import streamlit as st

try:
    API_BASE = st.secrets.get("api_base", "http://localhost:8000")
except Exception:
    API_BASE = "http://localhost:8000"

st.set_page_config(page_title="ZoneGuard", layout="wide")

st.markdown(
    """
<style>
:root {
  --bg-soft: #f3f5f8;
  --card: #ffffff;
  --ink: #0f172a;
  --muted: #475569;
  --accent: #0b84ff;
  --success: #16a34a;
  --warn: #ea580c;
  --border: #dbe3ea;
}
.main {background: linear-gradient(180deg, #f8fafc 0%, #f3f5f8 100%);}
.block-container {padding-top: 1.5rem;}
.hero {
  background: radial-gradient(circle at 0% 0%, #dbeafe, #ffffff 42%, #eef6ff 100%);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 1.2rem 1.4rem;
  margin-bottom: 1rem;
}
.hero h1 {
  font-size: 1.8rem;
  color: var(--ink);
  margin: 0;
  font-weight: 700;
}
.hero p {margin: 0.3rem 0 0; color: var(--muted);}
.hero-wrap {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}
.chip {
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.76rem;
  font-weight: 700;
  border: 1px solid var(--border);
  background: #ffffffbf;
}
.chip-safe {color: #065f46; border-color: #a7f3d0; background: #ecfdf5;}
.chip-watch {color: #92400e; border-color: #fde68a; background: #fffbeb;}
.chip-risk {color: #991b1b; border-color: #fecaca; background: #fef2f2;}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 1rem;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}
.card-title {
  color: var(--ink);
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}
.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.7rem;
  margin: 0.8rem 0 0.2rem;
}
.metric-pill {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.7rem;
}
.metric-pill .k {
  color: var(--muted);
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.metric-pill .v {
  color: var(--ink);
  font-size: 1.1rem;
  font-weight: 700;
}
.action-card {
  border: 1px solid var(--border);
  background: #f8fbff;
  border-radius: 12px;
  padding: 0.75rem 0.8rem;
  margin: 0.5rem 0;
}
.action-title {
  color: var(--ink);
  font-weight: 700;
  font-size: 0.92rem;
}
.priority {
  font-size: 0.7rem;
  padding: 0.16rem 0.45rem;
  border-radius: 999px;
  margin-left: 0.35rem;
  border: 1px solid var(--border);
}
.priority-high {background: #fee2e2; color: #991b1b; border-color: #fecaca;}
.priority-medium {background: #fef9c3; color: #854d0e; border-color: #fde68a;}
.priority-low {background: #dcfce7; color: #166534; border-color: #bbf7d0;}
.status-ok {color: var(--success); font-weight: 700;}
.status-warn {color: var(--warn); font-weight: 700;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <h1>ZoneGuard Control Center</h1>
  <p>Predict zone availability, detect operational anomalies, explain root causes, and trigger corrective actions.</p>
</div>
""",
    unsafe_allow_html=True,
)


if "forecast_payload" not in st.session_state:
    st.session_state.forecast_payload = None
if "anomaly_payload" not in st.session_state:
    st.session_state.anomaly_payload = None
if "reason_payload" not in st.session_state:
    st.session_state.reason_payload = None
if "action_payload" not in st.session_state:
    st.session_state.action_payload = None
if "pipeline_payload" not in st.session_state:
    st.session_state.pipeline_payload = None


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any] | None:
    """Perform API request and return parsed payload when successful."""
    url = f"{API_BASE}{path}"
    try:
        resp = requests.request(method=method, url=url, timeout=30, **kwargs)
    except requests.RequestException as exc:
        st.error(f"Connection error: {exc}")
        return None

    if not resp.ok:
        st.error(f"API error {resp.status_code}: {resp.text}")
        return None

    return resp.json()


def _extract_top_event(anomaly_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return highest-priority anomaly event if available."""
    if not anomaly_payload:
        return None
    events = anomaly_payload.get("events", [])
    if not events:
        return None
    return events[0]


def _risk_state(latest_pred: float | None, anomaly_count: int) -> tuple[str, str]:
    """Classify current zone risk for quick visual cue."""
    if latest_pred is not None and (latest_pred < 0.55 or anomaly_count >= 5):
        return ("High Risk", "chip-risk")
    if latest_pred is not None and (latest_pred < 0.72 or anomaly_count >= 2):
        return ("Watch", "chip-watch")
    return ("Stable", "chip-safe")


st.sidebar.header("Controls")
zone = st.sidebar.text_input("Zone ID", value="zone_01")
horizon = st.sidebar.slider("Forecast Horizon (hours)", min_value=1, max_value=24, value=6)
lookback = st.sidebar.slider("Anomaly Lookback", min_value=24, max_value=240, value=120)
st.sidebar.caption(f"Backend: {API_BASE}")

c1, c2, c3 = st.columns([1.1, 1.1, 1.8])

with c1:
    run_pipeline = st.button("Run Full Pipeline", width="stretch", type="primary")

with c2:
    run_forecast = st.button("Forecast Only", width="stretch")

with c3:
    run_anomaly = st.button("Detect + Explain + Action", width="stretch")

if run_pipeline:
    payload = _request("POST", "/pipeline/zone", json={"zone": zone, "horizon": horizon, "lookback": lookback})
    if payload:
        st.session_state.pipeline_payload = payload
        st.session_state.forecast_payload = payload.get("forecast")
        st.session_state.anomaly_payload = payload.get("anomalies")
        st.session_state.reason_payload = payload.get("reasoning")
        st.session_state.action_payload = payload.get("actions")

if run_forecast:
    payload = _request("GET", "/predict", params={"zone": zone, "horizon": horizon})
    if payload:
        st.session_state.forecast_payload = payload

if run_anomaly:
    anomaly_payload = _request("POST", "/anomaly", json={"zone": zone, "lookback": lookback})
    if anomaly_payload:
        st.session_state.anomaly_payload = anomaly_payload
        top_event = _extract_top_event(anomaly_payload)
        if top_event:
            reason_payload = _request("POST", "/reason", json={"event": top_event})
            if reason_payload:
                st.session_state.reason_payload = reason_payload
                action_payload = _request(
                    "POST",
                    "/action",
                    json={"event": top_event, "explanation": reason_payload.get("explanation", "")},
                )
                if action_payload:
                    st.session_state.action_payload = action_payload

pipeline_payload = st.session_state.pipeline_payload
forecast_payload = st.session_state.forecast_payload
anomaly_payload = st.session_state.anomaly_payload
reason_payload = st.session_state.reason_payload
action_payload = st.session_state.action_payload

forecast_count = len((forecast_payload or {}).get("predictions", []))
anomaly_count = len((anomaly_payload or {}).get("events", []))
actions_count = len((action_payload or {}).get("recommended_actions", []))
latest_prediction_value: float | None = None

if forecast_count > 0:
    latest_prediction_value = float((forecast_payload or {}).get("predictions", [])[-1].get("predicted_availability", 0))

latest_prediction_label = "-" if latest_prediction_value is None else f"{latest_prediction_value:.3f}"
risk_label, risk_class = _risk_state(latest_prediction_value, anomaly_count)

st.markdown(
    f"""
<div class="hero">
  <div class="hero-wrap">
    <div>
      <div class="card-title" style="margin: 0;">Live Zone Summary</div>
      <p style="margin: 0.2rem 0 0; color: var(--muted);">Latest posture for <b>{zone}</b> based on forecast and anomaly signals.</p>
    </div>
    <div class="chip {risk_class}">{risk_label}</div>
  </div>
  <div class="metric-row">
    <div class="metric-pill"><div class="k">Zone</div><div class="v">{zone}</div></div>
    <div class="metric-pill"><div class="k">Forecast Points</div><div class="v">{forecast_count}</div></div>
    <div class="metric-pill"><div class="k">Anomalies</div><div class="v">{anomaly_count}</div></div>
    <div class="metric-pill"><div class="k">Action Items</div><div class="v">{actions_count}</div></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

tab_overview, tab_investigate, tab_payloads = st.tabs(["Overview", "Investigation", "Payloads"])

with tab_overview:
    col_left, col_mid, col_right = st.columns([1.2, 1.1, 1.5])

    with col_left:
        st.markdown('<div class="card"><div class="card-title">Forecast Curve</div>', unsafe_allow_html=True)
        st.caption(f"Latest predicted availability: {latest_prediction_label}")
        if forecast_payload and forecast_payload.get("predictions"):
            fdf = pd.DataFrame(forecast_payload["predictions"])
            st.line_chart(fdf.set_index("timestamp")["predicted_availability"], height=250)
        else:
            st.info("Run forecast to view predicted availability trend.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_mid:
        st.markdown('<div class="card"><div class="card-title">Anomaly Radar</div>', unsafe_allow_html=True)
        if anomaly_payload:
            events = anomaly_payload.get("events", [])
            if events:
                events_df = pd.DataFrame(
                    [{"timestamp": e["timestamp"], "score": e["score"], "zone_id": e["zone_id"]} for e in events[:12]]
                )
                st.dataframe(events_df, width="stretch", height=250)
            else:
                st.success("No anomalies detected for selected window.")
        else:
            st.info("Run anomaly detection to populate event list.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="card"><div class="card-title">Action Board</div>', unsafe_allow_html=True)
        if action_payload and action_payload.get("recommended_actions"):
            for action in action_payload["recommended_actions"]:
                priority = str(action.get("priority", "medium")).lower()
                priority_class = "priority-medium"
                if priority == "high":
                    priority_class = "priority-high"
                elif priority == "low":
                    priority_class = "priority-low"

                st.markdown(
                    f"""
<div class="action-card">
  <span class="action-title">{action.get("action", "Action")}</span>
  <span class="priority {priority_class}">{priority.title()}</span>
  <div style="color:#475569; margin-top:0.35rem; font-size:0.88rem;">{action.get("detail", "")}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Run pipeline or anomaly flow to generate corrective actions.")
        st.markdown("</div>", unsafe_allow_html=True)

with tab_investigate:
    col_reason, col_feedback = st.columns([1.6, 1])
    with col_reason:
        st.markdown('<div class="card"><div class="card-title">Root Cause Narrative</div>', unsafe_allow_html=True)
        if reason_payload:
            try:
                parsed = json.loads(reason_payload.get("explanation", "{}"))
                st.json(parsed)
            except Exception:
                st.code(reason_payload.get("explanation", ""), language="json")
        else:
            st.info("Reasoning appears after anomaly detection.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_feedback:
        st.markdown('<div class="card"><div class="card-title">Feedback Loop</div>', unsafe_allow_html=True)
        top_event = _extract_top_event(anomaly_payload)
        disable_feedback = top_event is None
        st.caption("Confirm whether recommended actions helped operations.")
        if st.button("Submit Positive Feedback", disabled=disable_feedback, width="stretch"):
            fb_payload = _request(
                "POST",
                "/feedback",
                json={
                    "event_id": top_event["event_id"],
                    "rating": 5,
                    "correction": "Recommended action reduced availability risk.",
                    "metadata": {"source": "dashboard"},
                },
            )
            if fb_payload:
                st.success("Feedback stored successfully.")
        st.markdown("</div>", unsafe_allow_html=True)

with tab_payloads:
    if pipeline_payload:
        st.markdown("**Pipeline Traces**")
        traces = pd.DataFrame(pipeline_payload.get("traces", []))
        if not traces.empty:
            st.dataframe(traces, width="stretch")
    st.markdown("**Raw Objects**")
    st.json({"forecast": forecast_payload, "anomaly": anomaly_payload, "reason": reason_payload, "action": action_payload})

st.caption("ZoneGuard: detect, predict, explain, and optimize zone availability.")
