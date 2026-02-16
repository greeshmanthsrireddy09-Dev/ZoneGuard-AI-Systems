"""Offline replay harness for evaluating ZoneGuard pipeline quality."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

from backend.agents.action_agent import ActionAgent
from backend.agents.anomaly_agent import AnomalyAgent
from backend.agents.forecast_agent import ForecastAgent
from backend.agents.reasoning_agent import ReasoningAgent
from evaluation.business_metrics import estimate_impact
from evaluation.metrics import mape, rmse


@dataclass
class ReplayReport:
    """Evaluation report for one zone replay."""

    zone_id: str
    forecast_mape: float
    forecast_rmse: float
    anomaly_events: int
    generated_actions: int
    business_impact: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Serialize replay report."""
        return asdict(self)


class ReplayHarness:
    """Runs deterministic replay evaluation over historical data."""

    def __init__(self) -> None:
        self.forecaster = ForecastAgent()
        self.anomaly = AnomalyAgent()
        self.reasoner = ReasoningAgent()
        self.actor = ActionAgent()

    def run(self, df: pd.DataFrame, zone_id: str, horizon_hours: int = 6, lookback: int = 120) -> ReplayReport:
        """Execute replay and compute technical + business metrics."""
        zone_df = df[df["zone_id"] == zone_id].sort_values("timestamp").copy()
        if len(zone_df) < max(40, lookback // 2):
            raise ValueError(f"Insufficient records for replay on {zone_id}")

        self.forecaster.train(df)
        forecast = self.forecaster.predict(df, zone_id=zone_id, horizon_hours=horizon_hours)

        y_pred = [float(row["predicted_availability"]) for row in forecast.predictions]
        y_true = [float(v) for v in zone_df["availability"].tail(horizon_hours).to_list()]

        anomaly_result = self.anomaly.detect(df, zone_id=zone_id, lookback=lookback)

        generated_actions = 0
        acknowledged_actions = 0
        for event in anomaly_result.events[:5]:
            reason = self.reasoner.reason(event)
            action = self.actor.plan(event, reason["explanation"])
            count = len(action.get("recommended_actions", []))
            generated_actions += count
            # Portfolio assumption: ~60% operator acknowledgment for viable plans.
            acknowledged_actions += int(round(count * 0.6))

        impact = estimate_impact(
            anomalies_detected=len(anomaly_result.events),
            corrective_actions=generated_actions,
            acknowledged_actions=acknowledged_actions,
            baseline_incidents=max(1, lookback // 24),
        )

        return ReplayReport(
            zone_id=zone_id,
            forecast_mape=round(mape(y_true, y_pred), 4),
            forecast_rmse=round(rmse(y_true, y_pred), 4),
            anomaly_events=len(anomaly_result.events),
            generated_actions=generated_actions,
            business_impact=impact.to_dict(),
        )
