# Simulated provider outage postmortem

> **SIMULATED EXERCISE** — This document records a tabletop / CI failover drill, not a production incident.

## Summary

| Field | Value |
| --- | --- |
| Exercise label | SIMULATED PROVIDER OUTAGE |
| Date | 2026-08-28 |
| Duration | < 5 minutes |
| Customer impact | None (demo environment) |
| Primary provider | fake-openai |
| Fallback provider | fake-anthropic |

## Timeline (simulated)

| Time | Event |
| --- | --- |
| T+0m | Primary provider forced to permanent failure via `scripts/simulate_outage.py` |
| T+1m | Router retries exhausted; circuit breaker opens on primary |
| T+1m | Failover to `fake-anthropic` succeeds |
| T+3m | Golden evaluation fallback bucket verified at 100% |
| T+5m | Exercise closed; artifacts archived under `artifacts/` |

## Root cause

Deliberate injection of `permanent_error()` on the primary fake provider to validate failover paths in CI.

## What went well

- Provider router failed over without raising `AllProvidersFailedError`.
- `agent_provider_failovers_total` counter incremented.
- Agent API continued serving requests with `fallback_used=true` when preferred provider was set.

## What could improve

- Add external OTLP exporter for span visualization in staging.
- Automate runbook verification inside `scripts/verify.py`.

## Action items

| Action | Owner | Status |
| --- | --- | --- |
| Keep fallback cases in golden set | Platform | Done |
| Document mixed load scenario in locust README | Platform | Done |
| Wire OTLP exporter for non-demo environments | Observability | Planned (Phase 4) |

## Artifacts

- `artifacts/outage-simulation.json`
- `artifacts/evaluation-latest.json`
- `artifacts/demo-latest.json`
