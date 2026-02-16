"""Database models and session management for ZoneGuard."""

from __future__ import annotations

from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import JSON, Float, Integer, String, Text, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = "sqlite+aiosqlite:///./zoneguard.db"


class Base(DeclarativeBase):
    """Base declarative model for all tables."""


class OperationalRecord(Base):
    """Stores operational observations for each delivery zone and timestamp."""

    __tablename__ = "operational_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    demand: Mapped[float] = mapped_column(Float)
    drivers: Mapped[float] = mapped_column(Float)
    inventory: Mapped[float] = mapped_column(Float)
    weather: Mapped[str] = mapped_column(String(32))
    availability: Mapped[float] = mapped_column(Float)


class ForecastRun(Base):
    """Stores forecasting outputs for traceability."""

    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    horizon_hours: Mapped[int] = mapped_column(Integer)
    predictions: Mapped[dict] = mapped_column(JSON)


class AnomalyEvent(Base):
    """Stores anomaly detection events and associated score."""

    __tablename__ = "anomaly_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(String(64), index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    score: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)


class ReasoningRecord(Base):
    """Stores generated explanations from the reasoning agent."""

    __tablename__ = "reasoning_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    prompt: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)


class FeedbackRecord(Base):
    """Stores user feedback and corrections for continuous improvement."""

    __tablename__ = "feedback_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    rating: Mapped[int] = mapped_column(Integer)
    correction: Mapped[str] = mapped_column(Text)
    meta_json: Mapped[dict] = mapped_column("metadata", JSON)


engine = create_async_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session."""
    async with SessionLocal() as session:
        yield session


async def session_context() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session for non-DI contexts."""
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close()


async def init_db() -> None:
    """Initialize all tables for the application."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

