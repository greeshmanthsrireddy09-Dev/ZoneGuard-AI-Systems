"""Pydantic schemas for ZoneGuard API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PredictResponse(BaseModel):
    """Forecast API response schema."""

    zone_id: str
    horizon_hours: int
    predictions: list[dict[str, Any]]


class AnomalyRequest(BaseModel):
    """Anomaly detection request payload."""

    zone: str = Field(..., description="Zone identifier")
    lookback: int = Field(120, ge=24, le=720)


class AnomalyResponse(BaseModel):
    """Anomaly detection response schema."""

    zone_id: str
    events: list[dict[str, Any]]


class ReasonRequest(BaseModel):
    """Reasoning request payload."""

    event: dict[str, Any]


class ReasonResponse(BaseModel):
    """Reasoning response schema."""

    event_id: str
    prompt: str
    explanation: str


class ActionRequest(BaseModel):
    """Action planning request payload."""

    event: dict[str, Any]
    explanation: str | dict[str, Any]


class ActionResponse(BaseModel):
    """Action planning response schema."""

    event_id: str
    recommended_actions: list[dict[str, Any]]
    reasoning_reference: str | dict[str, Any]


class FeedbackRequest(BaseModel):
    """Feedback ingestion payload."""

    event_id: str
    rating: int = Field(..., ge=1, le=5)
    correction: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    """Feedback response schema."""

    status: str
    stored_at: datetime


class PipelineRequest(BaseModel):
    """Unified pipeline execution request."""

    zone: str
    horizon: int = Field(6, ge=1, le=48)
    lookback: int = Field(120, ge=24, le=720)


class PipelineResponse(BaseModel):
    """Unified pipeline execution response."""

    zone_id: str
    generated_at: str
    traces: list[dict[str, Any]]
    forecast: dict[str, Any]
    anomalies: dict[str, Any]
    reasoning: dict[str, Any] | None
    actions: dict[str, Any] | None


class ReplayRequest(BaseModel):
    """Replay evaluation request payload."""

    zone: str
    horizon: int = Field(6, ge=1, le=48)
    lookback: int = Field(120, ge=24, le=720)


class ReplayResponse(BaseModel):
    """Replay evaluation response payload."""

    zone_id: str
    forecast_mape: float
    forecast_rmse: float
    anomaly_events: int
    generated_actions: int
    business_impact: dict[str, float]
