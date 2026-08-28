# ADR 0003: Provider Router with Circuit Breaker Failover

## Status

Accepted

## Context

LLM providers exhibit latency spikes, rate limits, and hard outages. The gateway must continue serving governed agent runs when the primary provider fails.

## Decision

Implement a **ProviderRouter** with:

- Registry of provider adapters (OpenAI, Anthropic, fake)
- Routing policies (`balanced`, `cost`, `quality`)
- **Retry** with backoff for transient errors
- **Circuit breaker** per provider
- Automatic **failover** to backup provider

## Consequences

- **Positive:** Validated by unit tests and `scripts/simulate_outage.py`.
- **Positive:** Metrics expose failovers and circuit state for dashboards.
- **Negative:** Failover may change model behavior; callers see `fallback_used` flag.
- **Follow-on:** Add health-weighted routing and budget-aware provider selection.
