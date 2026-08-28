# Provider outage runbook (simulated exercise)

> **SIMULATED EXERCISE** — This runbook supports portfolio demos and CI drills. It does not describe a live production incident.

## Scope

Primary LLM provider (`fake-openai` in demo mode) becomes unavailable. The gateway must route to the secondary provider (`fake-anthropic`) without user-visible failure.

## Detection

1. Alert on rising `agent_provider_failovers_total{from_provider="fake-openai"}`.
2. Alert on `agent_provider_attempts_total{outcome="failed"}` for the primary provider.
3. Check `/metrics` for circuit breaker gauges: `agent_provider_circuit_state`.

## Immediate response

1. Confirm scope — single provider vs regional outage.
2. Run the simulated drill:

   ```bash
   uv run python scripts/simulate_outage.py
   ```

3. Inspect `artifacts/outage-simulation.json` for `failover_succeeded: true`.
4. Verify agent requests still return HTTP 200 via `scripts/demo.py`.

## Mitigation

- Set routing policy to prefer the healthy secondary provider.
- Keep primary registered but disabled until recovery.
- Monitor estimated cost drift after failover (secondary may differ in pricing).

## Recovery

1. Re-enable primary provider in configuration.
2. Confirm circuit breaker transitions to `closed`.
3. Run golden evaluation:

   ```bash
   uv run python scripts/evaluate.py
   ```

4. Confirm fallback bucket remains at 100% pass rate.

## Communication

- Status page: degraded → monitoring (simulated exercise label only).
- Internal channel: include trace IDs from failed primary attempts.

## References

- Post-incident review template: [postmortem-simulated-provider-outage.md](./postmortem-simulated-provider-outage.md)
- Failover unit tests: `tests/unit/test_failover.py`
