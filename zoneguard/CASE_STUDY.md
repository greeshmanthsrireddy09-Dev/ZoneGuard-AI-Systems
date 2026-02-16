# ZoneGuard Case Study

## Problem
Operations teams react late to zone availability drops, causing order delay spikes and manual firefighting.

## Solution
ZoneGuard provides a multi-agent pipeline that predicts availability risk, detects anomalies, explains likely root causes, and proposes concrete corrective actions.

## Architecture Highlights
- Forecast + anomaly in parallel orchestration
- Reasoning + action triggered by high-priority anomaly events
- Feedback loop for continuous improvement
- Replay evaluation harness for measurable outcomes

## Impact Snapshot (Replay Baseline)
- Forecast quality: MAPE and RMSE tracked per zone
- Incident prevention proxy: anomaly coverage over baseline incidents
- MTTR reduction estimate: derived from accepted actions
- Ops-hours saved estimate: based on anomaly interception and action count

## Production Readiness Additions
- Request tracing (`X-Request-Id`, latency headers)
- Liveness and readiness endpoints (`/health`, `/ready`)
- Docker and CI workflow included

## Demo Script (5 minutes)
1. Trigger `/pipeline/zone` for one zone.
2. Show predicted risk and anomaly ranking.
3. Inspect generated reasoning and action plan.
4. Submit feedback.
5. Run `/evaluate/replay` and present KPI outputs.
