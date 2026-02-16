"""Application API router for ZoneGuard."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.action_agent import ActionAgent
from backend.agents.anomaly_agent import AnomalyAgent
from backend.agents.forecast_agent import ForecastAgent
from backend.agents.reasoning_agent import ReasoningAgent
from backend.api.schemas import (
    ActionRequest,
    ActionResponse,
    AnomalyRequest,
    AnomalyResponse,
    FeedbackRequest,
    FeedbackResponse,
    PipelineRequest,
    PipelineResponse,
    PredictResponse,
    ReplayRequest,
    ReplayResponse,
    ReasonRequest,
    ReasonResponse,
)
from backend.db import AnomalyEvent, FeedbackRecord, ForecastRun, OperationalRecord, ReasoningRecord, get_session
from backend.orchestrator.runner import PipelineOrchestrator
from evaluation.harness import ReplayHarness

router = APIRouter()

_forecaster = ForecastAgent()
_anomaly = AnomalyAgent()
_reasoner = ReasoningAgent()
_actor = ActionAgent()
_orchestrator = PipelineOrchestrator(_forecaster, _anomaly, _reasoner, _actor)
_replay = ReplayHarness()


async def _load_dataframe(session: AsyncSession):
    import pandas as pd

    rows = (await session.execute(select(OperationalRecord))).scalars().all()
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        [
            {
                "zone_id": r.zone_id,
                "timestamp": r.timestamp,
                "demand": r.demand,
                "drivers": r.drivers,
                "inventory": r.inventory,
                "weather": r.weather,
                "availability": r.availability,
            }
            for r in rows
        ]
    )


@router.get("/predict", response_model=PredictResponse)
async def predict(zone: str, horizon: int = 6, session: AsyncSession = Depends(get_session)) -> PredictResponse:
    """GET /predict?zone=... endpoint for availability forecasting."""
    df = await _load_dataframe(session)
    if df.empty:
        raise HTTPException(status_code=404, detail="No operational data loaded")

    _forecaster.train(df)
    result = _forecaster.predict(df, zone_id=zone, horizon_hours=horizon)

    session.add(ForecastRun(zone_id=zone, horizon_hours=horizon, predictions=result.predictions))
    await session.commit()
    return PredictResponse(zone_id=result.zone_id, horizon_hours=result.horizon_hours, predictions=result.predictions)


@router.post("/anomaly", response_model=AnomalyResponse)
async def anomaly(payload: AnomalyRequest, session: AsyncSession = Depends(get_session)) -> AnomalyResponse:
    """POST /anomaly endpoint for outlier event detection."""
    df = await _load_dataframe(session)
    if df.empty:
        raise HTTPException(status_code=404, detail="No operational data loaded")

    result = _anomaly.detect(df, zone_id=payload.zone, lookback=payload.lookback)
    for event in result.events:
        session.add(AnomalyEvent(zone_id=payload.zone, score=event["score"], payload=event))
    await session.commit()

    return AnomalyResponse(zone_id=result.zone_id, events=result.events)


@router.post("/reason", response_model=ReasonResponse)
async def reason(payload: ReasonRequest, session: AsyncSession = Depends(get_session)) -> ReasonResponse:
    """POST /reason endpoint for root-cause explanation."""
    res = _reasoner.reason(payload.event)
    session.add(
        ReasoningRecord(
            event_id=res["event_id"],
            prompt=res["prompt"],
            explanation=res["explanation"],
        )
    )
    await session.commit()

    return ReasonResponse(**res)


@router.post("/action", response_model=ActionResponse)
async def action(payload: ActionRequest) -> ActionResponse:
    """POST /action endpoint for corrective action planning."""
    plan = _actor.plan(payload.event, payload.explanation)
    return ActionResponse(**plan)


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(payload: FeedbackRequest, session: AsyncSession = Depends(get_session)) -> FeedbackResponse:
    """POST /feedback endpoint for storing operator corrections."""
    _reasoner.ingest_feedback(payload.event_id, payload.correction, payload.rating)

    session.add(
        FeedbackRecord(
            event_id=payload.event_id,
            rating=payload.rating,
            correction=payload.correction,
            meta_json=payload.metadata,
        )
    )
    await session.commit()

    return FeedbackResponse(status="ok", stored_at=datetime.now(UTC).replace(tzinfo=None))


@router.post("/pipeline/zone", response_model=PipelineResponse)
async def run_pipeline(payload: PipelineRequest, session: AsyncSession = Depends(get_session)) -> PipelineResponse:
    """Execute full multi-agent pipeline for one zone."""
    df = await _load_dataframe(session)
    if df.empty:
        raise HTTPException(status_code=404, detail="No operational data loaded")

    out = await _orchestrator.run(df=df, zone_id=payload.zone, horizon_hours=payload.horizon, lookback=payload.lookback)
    return PipelineResponse(**out.__dict__)


@router.post("/evaluate/replay", response_model=ReplayResponse)
async def evaluate_replay(payload: ReplayRequest, session: AsyncSession = Depends(get_session)) -> ReplayResponse:
    """Run offline replay evaluation over stored historical records."""
    df = await _load_dataframe(session)
    if df.empty:
        raise HTTPException(status_code=404, detail="No operational data loaded")

    report = _replay.run(df=df, zone_id=payload.zone, horizon_hours=payload.horizon, lookback=payload.lookback)
    return ReplayResponse(**report.to_dict())

