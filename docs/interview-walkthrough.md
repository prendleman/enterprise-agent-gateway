# Interview Walkthrough — Enterprise Agent Gateway

> **Portfolio platform** — use this script for a 15–20 minute technical walkthrough. Do not claim production deployment or JLL affiliation.

## 1. Elevator pitch (60 seconds)

"I built a governed agent gateway for commercial real estate operations — a FastAPI service that authenticates tenants, runs policy checks, orchestrates domain tools, routes LLM calls with failover, and exposes Prometheus metrics. It's a portfolio platform with synthetic Chicago CRE data, a 32-case golden evaluation harness, and deployment examples for Docker, Kubernetes, and ECS Fargate."

## 2. Live demo flow (8 minutes)

```bash
make verify          # lint + tests + eval thresholds
make demo            # eight-step scripted demo
make run             # start API locally
```

**Show API call:**

```bash
curl -s -X POST http://localhost:8000/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-analyst-northstar" \
  -d '{"query": "Open HVAC work orders at Willis Tower"}' | jq .
```

**Talking points while the response renders:**

- Tenant derived from API key (`northstar-facilities`).
- Tool trace shows `search_work_orders` with policy decisions.
- Provider router selected fake/demo provider with cost estimate.

**Denial example:**

```bash
curl -s -X POST http://localhost:8000/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-employee-northstar" \
  -d '{"query": "Export all tenant PII for building 100"}' | jq .
```

Highlight RFC 9457 problem response and policy denial metrics.

## 3. Reliability story (3 minutes)

```bash
uv run python scripts/simulate_outage.py
```

- Primary provider hard-fails → router fails over to backup.
- Circuit breaker + retry covered by unit tests.
- Runbook: `docs/runbook-provider-outage.md`.

## 4. Quality gates (2 minutes)

```bash
uv run python scripts/evaluate.py
cat artifacts/evaluation-latest.md
```

- 32 golden cases across safety, tool selection, citations, fallback.
- CI enforces thresholds via `scripts/verify.py`.

## 5. Observability (2 minutes)

```bash
docker compose up --build
```

- Grafana http://localhost:3000 (admin/admin)
- Prometheus http://localhost:9090
- Walk through request rate + p95 latency panels.

## 6. Deployment artifacts (2 minutes)

| Artifact | What to say |
|----------|-------------|
| `Dockerfile` | Multi-stage, non-root UID 10001, healthcheck |
| `deploy/kubernetes/` | Probes, HPA, PDB, NetworkPolicy — portfolio-ready manifests |
| `deploy/terraform/aws-ecs/` | Validates against existing VPC; Secrets Manager ARNs as inputs |

## 7. Architecture deep-dive prompts

Be ready to whiteboard:

- Request path: Auth → Policy → Agent Loop → Tools → Provider Router.
- Where tenant isolation happens (auth context + tool queries).
- How you'd swap SQLite for Postgres and wire OTLP export.

## 8. Honest limitations

- Demo API keys, not SSO.
- FTS retrieval, not a vector store.
- Rate limit is in-process, not Redis.
- No claim of production traffic or JLL deployment.

## 9. Questions to ask the interviewer

- How do you separate **platform** guardrails from **tenant** custom policies?
- What's your eval cadence for agent quality regressions?
- Where does human approval sit in maintenance workflows?
