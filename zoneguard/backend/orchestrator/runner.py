"""Async orchestration harness for multi-agent execution."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import pandas as pd

from backend.agents.action_agent import ActionAgent
from backend.agents.anomaly_agent import AnomalyAgent
from backend.agents.forecast_agent import ForecastAgent
from backend.agents.reasoning_agent import ReasoningAgent


@dataclass
class StepTrace:
    """Execution trace for one orchestration step."""

    step: str
    status: str
    latency_ms: float
    details: dict[str, Any]


@dataclass
class PipelineOutput:
    """Pipeline response payload."""

    zone_id: str
    generated_at: str
    traces: list[dict[str, Any]]
    forecast: dict[str, Any]
    anomalies: dict[str, Any]
    reasoning: dict[str, Any] | None
    actions: dict[str, Any] | None


class PipelineOrchestrator:
    """Coordinates forecast, anomaly, reasoning, and action agents."""

    def __init__(
        self,
        forecaster: ForecastAgent,
        anomaly: AnomalyAgent,
        reasoner: ReasoningAgent,
        actor: ActionAgent,
    ) -> None:
        self.forecaster = forecaster
        self.anomaly = anomaly
        self.reasoner = reasoner
        self.actor = actor

    async def run(self, df: pd.DataFrame, zone_id: str, horizon_hours: int = 6, lookback: int = 120) -> PipelineOutput:
        """Run the full pipeline with parallelizable stages."""
        traces: list[StepTrace] = []

        async def run_forecast() -> dict[str, Any]:
            start = perf_counter()
            self.forecaster.train(df)
            result = self.forecaster.predict(df, zone_id=zone_id, horizon_hours=horizon_hours)
            traces.append(
                StepTrace(
                    step="forecast",
                    status="ok",
                    latency_ms=(perf_counter() - start) * 1000,
                    details={"count": len(result.predictions)},
                )
            )
            return {"zone_id": result.zone_id, "horizon_hours": result.horizon_hours, "predictions": result.predictions}

        async def run_anomaly() -> dict[str, Any]:
            start = perf_counter()
            result = self.anomaly.detect(df, zone_id=zone_id, lookback=lookback)
            traces.append(
                StepTrace(
                    step="anomaly",
                    status="ok",
                    latency_ms=(perf_counter() - start) * 1000,
                    details={"events": len(result.events)},
                )
            )
            return {"zone_id": result.zone_id, "events": result.events}

        forecast_payload, anomaly_payload = await asyncio.gather(run_forecast(), run_anomaly())

        reasoning_payload: dict[str, Any] | None = None
        action_payload: dict[str, Any] | None = None

        if anomaly_payload["events"]:
            event = anomaly_payload["events"][0]
            reason_start = perf_counter()
            reasoning_payload = self.reasoner.reason(event)
            traces.append(
                StepTrace(
                    step="reason",
                    status="ok",
                    latency_ms=(perf_counter() - reason_start) * 1000,
                    details={"event_id": reasoning_payload["event_id"]},
                )
            )

            action_start = perf_counter()
            action_payload = self.actor.plan(event, reasoning_payload["explanation"])
            traces.append(
                StepTrace(
                    step="action",
                    status="ok",
                    latency_ms=(perf_counter() - action_start) * 1000,
                    details={"actions": len(action_payload["recommended_actions"])},
                )
            )
        else:
            traces.append(
                StepTrace(
                    step="reason",
                    status="skipped",
                    latency_ms=0.0,
                    details={"reason": "No anomaly events"},
                )
            )
            traces.append(
                StepTrace(
                    step="action",
                    status="skipped",
                    latency_ms=0.0,
                    details={"reason": "No anomaly events"},
                )
            )

        return PipelineOutput(
            zone_id=zone_id,
            generated_at=datetime.now(UTC).isoformat(),
            traces=[asdict(t) for t in traces],
            forecast=forecast_payload,
            anomalies=anomaly_payload,
            reasoning=reasoning_payload,
            actions=action_payload,
        )
