"""Action planning agent that proposes operational mitigations."""

from __future__ import annotations

from typing import Any


class ActionAgent:
    """Create actionable recommendations from event and explanation payloads."""

    @staticmethod
    def plan(event: dict[str, Any], explanation: str | dict[str, Any]) -> dict[str, Any]:
        """Generate prioritized action plan."""
        snapshot = event.get("snapshot", {})
        demand = float(snapshot.get("demand", 0.0))
        drivers = float(snapshot.get("drivers", 0.0))
        inventory = float(snapshot.get("inventory", 0.0))

        actions: list[dict[str, Any]] = []

        if drivers < demand * 0.9:
            actions.append(
                {
                    "action": "Rebalance drivers",
                    "detail": "Shift drivers from neighboring zones within next 30 minutes.",
                    "priority": "high",
                }
            )

        if inventory < demand * 0.8:
            actions.append(
                {
                    "action": "Expedite inventory transfer",
                    "detail": "Move hot-selling inventory from closest micro-fulfillment center.",
                    "priority": "high",
                }
            )

        actions.append(
            {
                "action": "Enable surge controls",
                "detail": "Temporarily throttle low-priority orders and adjust promised ETA windows.",
                "priority": "medium",
            }
        )

        actions.append(
            {
                "action": "Monitor zone stability",
                "detail": "Track availability every 15 minutes for the next 2 hours.",
                "priority": "medium",
            }
        )

        return {
            "event_id": event.get("event_id", "unknown-event"),
            "recommended_actions": actions,
            "reasoning_reference": explanation,
        }
