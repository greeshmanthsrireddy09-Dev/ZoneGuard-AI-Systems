"""Anomaly detection agent for availability and operational signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.ensemble import IsolationForest


@dataclass
class AnomalyResult:
    """Detected anomaly event payload."""

    zone_id: str
    events: list[dict[str, Any]]


class AnomalyAgent:
    """IsolationForest-based anomaly detector per zone."""

    def __init__(self, contamination: float = 0.07) -> None:
        self.contamination = contamination

    def detect(self, df: pd.DataFrame, zone_id: str, lookback: int = 120) -> AnomalyResult:
        """Detect anomalies and return scored events."""
        zone_df = df[df["zone_id"] == zone_id].sort_values("timestamp").tail(lookback).copy()
        if len(zone_df) < 20:
            raise ValueError(f"Insufficient records for anomaly detection in {zone_id}")

        features = zone_df[["demand", "drivers", "inventory", "availability"]]
        model = IsolationForest(
            n_estimators=200,
            contamination=self.contamination,
            random_state=42,
        )

        labels = model.fit_predict(features)
        scores = -model.score_samples(features)
        zone_df["is_anomaly"] = labels == -1
        zone_df["score"] = scores

        events = []
        for row in zone_df[zone_df["is_anomaly"]].itertuples(index=False):
            events.append(
                {
                    "event_id": f"{row.zone_id}:{row.timestamp.isoformat()}",
                    "timestamp": row.timestamp.isoformat(),
                    "zone_id": row.zone_id,
                    "score": round(float(row.score), 4),
                    "snapshot": {
                        "demand": float(row.demand),
                        "drivers": float(row.drivers),
                        "inventory": float(row.inventory),
                        "availability": float(row.availability),
                        "weather": str(row.weather),
                    },
                }
            )

        events.sort(key=lambda x: x["score"], reverse=True)
        return AnomalyResult(zone_id=zone_id, events=events)
