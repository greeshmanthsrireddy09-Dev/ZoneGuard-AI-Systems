"""Business impact metrics for operational AI decisions."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class BusinessImpact:
    """Business-oriented KPI summary."""

    incident_prevention_rate: float
    estimated_mttr_reduction_minutes: float
    action_acceptance_rate: float
    estimated_ops_hours_saved: float

    def to_dict(self) -> dict[str, float]:
        """Serialize KPI payload."""
        return asdict(self)


def estimate_impact(
    anomalies_detected: int,
    corrective_actions: int,
    acknowledged_actions: int,
    baseline_incidents: int,
) -> BusinessImpact:
    """Estimate practical business impact from replay results.

    The formulas are intentionally simple and transparent for portfolio/demo use.
    """
    if baseline_incidents <= 0:
        baseline_incidents = 1

    incident_prevention_rate = min(1.0, anomalies_detected / baseline_incidents)
    action_acceptance_rate = 0.0 if corrective_actions == 0 else min(1.0, acknowledged_actions / corrective_actions)

    # Heuristic estimates for demonstration and benchmarking.
    estimated_mttr_reduction_minutes = round(12.0 + 38.0 * action_acceptance_rate, 2)
    estimated_ops_hours_saved = round((anomalies_detected * 0.35) + (acknowledged_actions * 0.22), 2)

    return BusinessImpact(
        incident_prevention_rate=round(incident_prevention_rate, 4),
        estimated_mttr_reduction_minutes=estimated_mttr_reduction_minutes,
        action_acceptance_rate=round(action_acceptance_rate, 4),
        estimated_ops_hours_saved=estimated_ops_hours_saved,
    )
