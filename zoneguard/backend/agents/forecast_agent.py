"""Forecasting agent powered by XGBoost for availability prediction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover - environment-dependent optional dependency
    XGBRegressor = None  # type: ignore[assignment]


@dataclass
class ForecastResult:
    """Container for forecast outputs."""

    zone_id: str
    horizon_hours: int
    predictions: list[dict[str, Any]]


class ForecastAgent:
    """Train and infer availability forecasts per zone."""

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._feature_cols = ["hour", "dayofweek", "demand", "drivers", "inventory", "weather_idx", "availability_lag_1", "availability_roll_3"]

    @staticmethod
    def _encode_weather(df: pd.DataFrame) -> pd.Series:
        mapping = {"clear": 0, "rain": 1, "storm": 2, "snow": 3}
        return df["weather"].map(mapping).fillna(0).astype(float)

    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        ordered = df.sort_values("timestamp").copy()
        ordered["hour"] = ordered["timestamp"].dt.hour.astype(float)
        ordered["dayofweek"] = ordered["timestamp"].dt.dayofweek.astype(float)
        ordered["weather_idx"] = self._encode_weather(ordered)
        ordered["availability_lag_1"] = ordered["availability"].shift(1)
        ordered["availability_roll_3"] = ordered["availability"].rolling(window=3, min_periods=1).mean().shift(1)
        ordered = ordered.dropna().reset_index(drop=True)
        return ordered

    def train(self, df: pd.DataFrame) -> None:
        """Train one model per zone for availability regression."""
        for zone, zone_df in df.groupby("zone_id"):
            feats = self._build_features(zone_df)
            if len(feats) < 30:
                continue
            X = feats[self._feature_cols]
            y = feats["availability"]
            if XGBRegressor is not None:
                model = XGBRegressor(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=4,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="reg:squarederror",
                    random_state=42,
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=300,
                    max_depth=8,
                    random_state=42,
                )
            model.fit(X, y)
            self._models[zone] = model

    def predict(self, df: pd.DataFrame, zone_id: str, horizon_hours: int = 6) -> ForecastResult:
        """Predict near-future availability for a zone using recursive updates."""
        if zone_id not in self._models:
            raise ValueError(f"No model trained for {zone_id}")

        model = self._models[zone_id]
        zone_df = df[df["zone_id"] == zone_id].sort_values("timestamp").copy()
        feats_df = self._build_features(zone_df)
        if feats_df.empty:
            raise ValueError(f"Insufficient feature history for {zone_id}")

        current_row = feats_df.iloc[-1].copy()
        current_ts = pd.Timestamp(feats_df.iloc[-1]["timestamp"])
        preds: list[dict[str, Any]] = []

        for _ in range(horizon_hours):
            current_ts = current_ts + timedelta(hours=1)
            current_row["hour"] = float(current_ts.hour)
            current_row["dayofweek"] = float(current_ts.dayofweek)

            x = np.array([[float(current_row[col]) for col in self._feature_cols]])
            yhat = float(np.clip(model.predict(x)[0], 0.0, 1.0))

            current_row["availability_lag_1"] = yhat
            current_row["availability_roll_3"] = float((current_row["availability_roll_3"] * 2 + yhat) / 3)

            preds.append({"timestamp": current_ts.isoformat(), "predicted_availability": round(yhat, 4)})

        return ForecastResult(zone_id=zone_id, horizon_hours=horizon_hours, predictions=preds)
