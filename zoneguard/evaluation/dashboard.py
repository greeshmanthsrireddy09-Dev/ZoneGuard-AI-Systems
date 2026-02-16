"""Simple CLI summary dashboard for evaluation outputs."""

from __future__ import annotations

from evaluation.metrics import mape, rmse


def print_metrics(y_true: list[float], y_pred: list[float]) -> None:
    """Print core model metrics for quick checks."""
    print(f"MAPE: {mape(y_true, y_pred):.4f}")
    print(f"RMSE: {rmse(y_true, y_pred):.4f}")


if __name__ == "__main__":
    print_metrics([0.8, 0.7, 0.9], [0.78, 0.72, 0.86])
