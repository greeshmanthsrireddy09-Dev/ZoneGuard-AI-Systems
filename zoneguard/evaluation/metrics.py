"""Evaluation metrics for ZoneGuard outputs."""

from __future__ import annotations

from typing import Iterable

import numpy as np


def mape(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """Compute mean absolute percentage error with safe denominator."""
    yt = np.array(list(y_true), dtype=float)
    yp = np.array(list(y_pred), dtype=float)
    denom = np.clip(np.abs(yt), 1e-6, None)
    return float(np.mean(np.abs((yt - yp) / denom)))


def rmse(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """Compute root mean squared error."""
    yt = np.array(list(y_true), dtype=float)
    yp = np.array(list(y_pred), dtype=float)
    return float(np.sqrt(np.mean((yt - yp) ** 2)))
