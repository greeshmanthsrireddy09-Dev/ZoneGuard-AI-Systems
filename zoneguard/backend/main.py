"""FastAPI application entrypoint for ZoneGuard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router
from backend.db import OperationalRecord, SessionLocal, init_db
from backend.observability import RequestTraceMiddleware, configure_logging
from data.simulate import generate_synthetic_data

app = FastAPI(title="ZoneGuard", version="1.0.0")
app.include_router(router)
configure_logging()
app.add_middleware(RequestTraceMiddleware)
ui_dir = Path(__file__).resolve().parents[1] / "dashboard_web"
if ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database and seed synthetic data if empty."""
    await init_db()
    async with SessionLocal() as session:
        from sqlalchemy import func, select

        count = (await session.execute(select(func.count(OperationalRecord.id)))).scalar_one()
        if count == 0:
            df = generate_synthetic_data(n_zones=6, hours=24 * 14)
            rows = [
                OperationalRecord(
                    zone_id=row.zone_id,
                    timestamp=pd.Timestamp(row.timestamp).to_pydatetime(),
                    demand=float(row.demand),
                    drivers=float(row.drivers),
                    inventory=float(row.inventory),
                    weather=str(row.weather),
                    availability=float(row.availability),
                )
                for row in df.itertuples(index=False)
            ]
            session.add_all(rows)
            await session.commit()


@app.get("/")
async def root() -> dict[str, str]:
    """Health route."""
    return {"status": "ZoneGuard API online", "docs": "/docs", "ui": "/ui"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Lightweight liveness check."""
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness endpoint for deployments/load balancers."""
    return {"status": "ready"}
