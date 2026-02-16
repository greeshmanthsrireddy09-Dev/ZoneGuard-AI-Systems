"""Dataset loading and optional database ingestion utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import OperationalRecord


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV dataset with parsed timestamps."""
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


async def ingest_dataframe(df: pd.DataFrame, session: AsyncSession) -> int:
    """Insert dataframe rows into operational_records table."""
    rows = [
        OperationalRecord(
            zone_id=row.zone_id,
            timestamp=row.timestamp.to_pydatetime(),
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
    return len(rows)
