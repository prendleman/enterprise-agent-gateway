# Enterprise Agent Gateway

[![CI](https://github.com/prendleman/enterprise-agent-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/prendleman/enterprise-agent-gateway/actions/workflows/ci.yml)

**Portfolio platform** demonstrating an enterprise-grade AI agent gateway for commercial real estate (CRE) operations — governed orchestration, multi-tenant RBAC, provider failover, deterministic evaluation gates, and deployment scaffolding.

> **Disclaimer:** This is an independent portfolio project. It is **not** affiliated with JLL or any employer and **has not** been deployed to production.

## Architecture

```mermaid
flowchart TB
    Client[Client / CLI / CI] -->|POST /v1/agents/run| API[FastAPI Gateway]
    API --> Auth[API Key Auth]
    Auth --> Policy[Policy Engine]
    Policy --> Agent[Agent Loop]
    Agent --> Tools[CRE Tools]
    Agent --> Router[Provider Router]
    Router --> LLM[OpenAI / Anthropic / Fake]
    Tools --> DB[(SQLite)]
    API --> Metrics[/metrics]
    Metrics --> Prom[Prometheus]
    Prom --> Graf[Grafana]
```

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Features

| Area | Capabilities |
|------|--------------|
| **API** | `POST /v1/agents/run`, health probes, Prometheus `/metrics`, RFC 9457 errors |
| **Auth** | Demo API keys → tenant + role; tool permissions by role |
| **Agent** | Bounded tool loop, **cumulative request-level cost ceiling**, citation grounding, policy decisions |
| **Reliability** | Retry, circuit breaker, provider failover, idempotency, **per-tenant rate limiting at ingress** |
| **Evaluation** | **32-case deterministic regression and safety suite** enforced in CI; optional live-model tier |
| **Observability** | structlog JSON, Prometheus metrics, Grafana dashboard |
| **Deploy** | Dockerfile, docker-compose, Kustomize, Terraform ECS example |

## Quick start

Requires **Python 3.12+** and [uv](https://docs.astral.sh/uv/).

```bash
cd enterprise-agent-gateway
cp .env.example .env
uv sync --all-extras
uv run python scripts/seed_data.py
uv run uvicorn agent_gateway.main:app --host 0.0.0.0 --port 8000
```

Or with Make:

```bash
make sync
make seed
make run
```

Health checks:

- `GET /health/live` — liveness
- `GET /health/ready` — readiness (includes DB check)
- `GET /metrics` — Prometheus scrape endpoint

## Demo API keys

Local-only plaintext keys (hashed at runtime):

| Key | Role | Tenant |
|-----|------|--------|
| `demo-employee-northstar` | employee | northstar-facilities |
| `demo-analyst-northstar` | analyst | northstar-facilities |
| `demo-fm-northstar` | facilities_manager | northstar-facilities |
| `demo-analyst-lakeshore` | analyst | lakeshore-properties |
| `demo-admin` | platform_admin | northstar-facilities |

Pass via header: `X-API-Key: demo-analyst-northstar`

## API examples

**Work order lookup:**

```bash
curl -s -X POST http://localhost:8000/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-analyst-northstar" \
  -d '{"query": "List open HVAC work orders at Willis Tower"}' | jq .
```

**Policy denial (employee requesting restricted action):**

```bash
curl -s -X POST http://localhost:8000/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-employee-northstar" \
  -d '{"query": "Export all tenant PII for every building"}' | jq .
```

**With routing hints:**

```bash
curl -s -X POST http://localhost:8000/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-fm-northstar" \
  -d '{
    "query": "Summarize maintenance backlog for Northstar portfolio",
    "routing_policy": "balanced",
    "max_cost_usd": 0.05
  }' | jq .
```

## Verify, eval, outage, load

```bash
# Full gate: lint + tests + eval thresholds
make verify
# or: uv run python scripts/verify.py

# Golden-set evaluation (writes artifacts/evaluation-latest.{json,md})
make eval

# Optional live-model evaluation (requires OPENAI_API_KEY / ANTHROPIC_API_KEY)
make eval-live

# Eight-step portfolio demo
make demo

# Simulated primary provider outage + failover
make outage

# Coverage HTML report → htmlcov/index.html
make coverage
```

**Load test** (requires running API):

```bash
uv run uvicorn agent_gateway.main:app --host 0.0.0.0 --port 8000
make load
# Opens Locust UI; mixed CRE traffic scenario in tests/load/locustfile.py
```

## Docker & observability stack

```bash
make docker-build
make docker-up
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

The Dockerfile is multi-stage, runs as non-root UID `10001`, includes a `/health/live` healthcheck, and installs the `[providers]` extra so OpenAI/Anthropic SDKs are available when API keys are configured.

## Kubernetes (Kustomize)

```bash
# Render manifests
make k8s-build

# Apply to local cluster (kind/minikube)
make k8s-apply
```

Base manifests include Deployment, Service, ConfigMap, secret example, HPA, PDB, NetworkPolicy, and probes. See `deploy/kubernetes/overlays/local/` for single-replica local tuning.

## Terraform (AWS ECS Fargate)

Validation-ready example using **existing VPC/subnets**:

```bash
cd deploy/terraform/aws-ecs
terraform init -backend=false
terraform validate
```

Secrets Manager ARNs are **inputs only** — see `terraform.tfvars.example`. Full notes in [deploy/terraform/aws-ecs/README.md](deploy/terraform/aws-ecs/README.md).

## JLL-inspired gap summary

This portfolio maps common enterprise agent-platform themes to implemented artifacts. **No affiliation claim.**

| Theme | Status |
|-------|--------|
| Governed agent API + CRE tools | ✅ Implemented |
| Multi-tenant RBAC + policy engine | ✅ Implemented |
| Provider routing & failover | ✅ Implemented |
| Golden-set eval in CI | ✅ Implemented |
| Prometheus/Grafana observability | ✅ Implemented |
| Docker / K8s / ECS scaffolding | ✅ Implemented |
| Enterprise SSO / OIDC | ⬜ Out of scope (demo API keys) |
| Vector DB at scale | ⬜ Out of scope (SQLite FTS demo) |
| Production SLOs / on-call | ⬜ Documented only |

Full matrix: [docs/gap-coverage-matrix.md](docs/gap-coverage-matrix.md)

## Documentation

| Doc | Purpose |
|-----|---------|
| [architecture.md](docs/architecture.md) | System design |
| [gap-coverage-matrix.md](docs/gap-coverage-matrix.md) | Brief coverage map |
| [interview-walkthrough.md](docs/interview-walkthrough.md) | 15-min demo script |
| [resume-language.md](docs/resume-language.md) | Resume bullets |
| [security-and-threat-model.md](docs/security-and-threat-model.md) | STRIDE analysis |
| [adr/](docs/adr/) | Architecture decision records |
| [runbook-provider-outage.md](docs/runbook-provider-outage.md) | Incident runbook |

## Project layout

```
config/                 # Policies, tool permissions, pricing
datasets/               # Synthetic CRE data + golden evaluations
deploy/
  kubernetes/           # Kustomize base + local overlay
  terraform/aws-ecs/    # ECS Fargate example (existing VPC)
observability/          # Prometheus + Grafana provisioning
src/agent_gateway/      # Application code
tests/                  # Unit, contract, integration, load
scripts/                # verify, evaluate, demo, outage
artifacts/              # Generated eval/demo outputs (gitignored JSON)
```

## CI

GitHub Actions (`.github/workflows/ci.yml`):

- `scripts/verify.py` — Ruff, pytest, eval thresholds
- Coverage XML artifact
- Docker build + compose config validation
- Terraform fmt/validate
- Kustomize render check

## Makefile targets

```bash
make help    # list all targets
```

Common: `verify`, `test`, `eval`, `demo`, `coverage`, `docker-up`, `k8s-build`, `tf-validate`

## License

MIT — see [LICENSE](LICENSE).
