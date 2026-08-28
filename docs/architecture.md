# Architecture — Enterprise Agent Gateway (Portfolio Platform)

> **Portfolio disclaimer:** This repository is a self-contained demonstration platform inspired by enterprise CRE agent-gateway patterns. It is **not** affiliated with JLL or any employer, and **has not** been deployed to production.

## System context

```mermaid
flowchart TB
    subgraph Clients
        UI[Operator UI / CLI]
        CI[CI / Eval Harness]
    end

    subgraph Gateway["Agent Gateway (FastAPI)"]
        Auth[API Key Auth + Tenant Context]
        Policy[Policy Engine]
        Agent[Agent Loop + Planner]
        Tools[Domain Tools]
        Router[Provider Router]
        Guard[Guardrails]
        Obs[Metrics + Structured Logs]
    end

    subgraph Data
        DB[(SQLite / Postgres-ready)]
        Datasets[Synthetic CRE Datasets]
    end

    subgraph Providers
        OpenAI[OpenAI]
        Anthropic[Anthropic]
        Fake[Fake Providers (demo)]
    end

    subgraph Observability
        Prom[Prometheus]
        Graf[Grafana]
    end

    UI -->|POST /v1/agents/run| Auth
    CI --> Auth
    Auth --> Policy --> Agent
    Agent --> Tools --> DB
    Agent --> Guard
    Agent --> Router
    Router --> OpenAI
    Router --> Anthropic
    Router --> Fake
    Tools --> Datasets
    Obs --> Prom --> Graf
```

## Request lifecycle

1. **Ingress** — Client sends `POST /v1/agents/run` with `X-API-Key` and optional routing hints.
2. **Authentication** — Demo API keys map to tenant + role (SHA-256 hashed at rest in settings).
3. **Input guardrails** — Length limits, blocked patterns, and policy YAML checks.
4. **Planning** — Lightweight planner selects tools based on query intent.
5. **Tool execution** — CRE tools (work orders, buildings, policies, maintenance) with RBAC from `tool_permissions.yaml`.
6. **Provider routing** — Primary/fallback selection with circuit breaker, retry, and cost ceiling.
7. **Output guardrails** — Citation requirements, PII redaction hooks, malformed-output detection.
8. **Response** — Structured answer, tool trace, usage/cost estimate, policy decisions, trace ID.

## Core components

| Layer | Module | Responsibility |
|-------|--------|----------------|
| API | `agent_gateway.api` | HTTP contract, RFC 9457 errors, Prometheus `/metrics` |
| Auth | `agent_gateway.auth` | API key validation, tenant isolation |
| Agent | `agent_gateway.agent` | Orchestration loop, prompts, cost ceiling |
| Tools | `agent_gateway.tools` | CRE domain actions + registry |
| Guardrails | `agent_gateway.guardrails` | Input/output/policy/privacy checks |
| Providers | `agent_gateway.providers` | OpenAI, Anthropic, fake, router, pricing |
| Reliability | `agent_gateway.reliability` | Retry, circuit breaker, idempotency, rate limit |
| Evaluation | `agent_gateway.evaluation` | Golden-set harness with category thresholds |
| Storage | `agent_gateway.storage` | SQLAlchemy models, seed data |

## Deployment topology (portfolio)

Three reference paths ship in `deploy/`:

| Path | Purpose |
|------|---------|
| `Dockerfile` + `docker-compose.yml` | Local stack with API + Prometheus + Grafana |
| `deploy/kubernetes/` | Kustomize base + `overlays/local` for kind/minikube |
| `deploy/terraform/aws-ecs/` | Validation-ready ECS Fargate on **existing** VPC |

None of these paths are wired to a live cloud account in this repo.

## Data & tenancy

- Synthetic Chicago CRE portfolio: buildings, work orders, policy documents.
- Tenant IDs (`northstar-facilities`, `lakeshore-properties`) enforced on tool queries.
- Demo mode uses SQLite; settings accept Postgres-compatible URLs for future migration.

## Observability

- **Logs:** structlog JSON with request ID propagation.
- **Metrics:** Prometheus counters/histograms for requests, latency, tool calls, policy denials, tokens, cost.
- **Tracing:** OpenTelemetry SDK initialized; OTLP export is documented as a follow-on for non-demo environments.

## Security posture (summary)

See [security-and-threat-model.md](security-and-threat-model.md) for STRIDE-style analysis. Highlights:

- API keys are demo-only plaintext keys with hashed lookup.
- NetworkPolicy + non-root containers in Kubernetes manifests.
- Secrets Manager ARNs are **inputs only** in Terraform — no secret values in repo.

## Evaluation & quality gates

- 32-case golden set in `datasets/golden_evaluations.jsonl`.
- Thresholds: 90% overall/tool-citation, 100% safety/fallback.
- `scripts/verify.py` runs lint, tests, and evaluation in CI.

## Related documents

- [Gap coverage matrix](gap-coverage-matrix.md)
- [Interview walkthrough](interview-walkthrough.md)
- [ADRs](adr/)
- [Runbook: provider outage](runbook-provider-outage.md)
