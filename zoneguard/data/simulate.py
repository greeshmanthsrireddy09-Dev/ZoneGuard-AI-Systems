"""Data simulation utilities for ZoneGuard."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

WEATHER_STATES = ("clear", "rain", "storm", "snow")


def _weather_to_multiplier(weather: str) -> float:
    """Translate weather condition into availability pressure multiplier."""
    if weather == "clear":
        return 1.0
    if weather == "rain":
        return 0.93
    if weather == "snow":
        return 0.88
    return 0.80


def generate_synthetic_data(
    n_zones: int = 6,
    hours: int = 24 * 30,
    seed: int = 7,
    freq: Literal["h", "H"] = "h",
) -> pd.DataFrame:
    """Generate synthetic operational data for delivery zones.

    Returns a DataFrame with:
    zone_id, timestamp, demand, drivers, inventory, weather, availability.
    """
    rng = np.random.default_rng(seed)
    start = datetime.utcnow() - timedelta(hours=hours)
    timestamps = pd.date_range(start=start, periods=hours, freq=freq)

    records: list[dict] = []
    for z in range(1, n_zones + 1):
        zone = f"zone_{z:02d}"
        base_demand = rng.uniform(50, 120)
        base_drivers = rng.uniform(45, 110)
        base_inventory = rng.uniform(60, 140)

        for i, ts in enumerate(timestamps):
            hour_cycle = 1.0 + 0.35 * np.sin((2 * np.pi * (i % 24)) / 24)
            day_cycle = 1.0 + 0.15 * np.cos((2 * np.pi * (i % (24 * 7))) / (24 * 7))

            weather = rng.choice(WEATHER_STATES, p=[0.68, 0.18, 0.08, 0.06])
            demand = max(5.0, base_demand * hour_cycle * day_cycle + rng.normal(0, 6))
            drivers = max(3.0, base_drivers * (1 + rng.normal(0, 0.08)))
            inventory = max(4.0, base_inventory * (1 + rng.normal(0, 0.10)))

            pressure = demand / max(1.0, drivers)
            inv_factor = min(1.2, inventory / max(1.0, demand))
            weather_mult = _weather_to_multiplier(str(weather))
            availability = np.clip(
                1.1 - 0.38 * pressure + 0.24 * inv_factor,
                0.05,
                1.0,
            ) * weather_mult
            availability = float(np.clip(availability + rng.normal(0, 0.03), 0.0, 1.0))

            # Inject occasional operational shock events.
            if rng.random() < 0.018:
                availability = float(np.clip(availability - rng.uniform(0.2, 0.4), 0.0, 1.0))

            records.append(
                {
                    "zone_id": zone,
                    "timestamp": ts,
                    "demand": round(float(demand), 3),
                    "drivers": round(float(drivers), 3),
                    "inventory": round(float(inventory), 3),
                    "weather": str(weather),
                    "availability": round(availability, 4),
                }
            )

    return pd.DataFrame.from_records(records)


def save_dataset(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Persist generated synthetic data to CSV."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return output


if __name__ == "__main__":
    generated = generate_synthetic_data(n_zones=8, hours=24 * 45)
    path = save_dataset(generated, Path(__file__).resolve().parent / "synthetic_zoneguard.csv")
    print(f"Synthetic data saved to {path}")
