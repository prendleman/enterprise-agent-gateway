# Resume Language — Enterprise Agent Gateway

> Copy/adapt bullets for resumes and LinkedIn. Frame as a **portfolio platform** — no production deployment or employer affiliation claims.

## One-liner

Built an enterprise-style **AI agent gateway** for commercial real estate operations with multi-tenant RBAC, policy guardrails, provider failover, golden-set evaluation, and Docker/Kubernetes/ECS deployment scaffolding.

## Bullets (pick 3–5)

- Designed and implemented a **FastAPI agent orchestration layer** with tenant-scoped API keys, YAML policy engine, and RFC 9457 error handling for governed LLM workflows.
- Shipped **CRE domain tools** (work orders, building summaries, policy search, maintenance requests) with role-based permissions and SQLite-backed retrieval.
- Built a **provider routing layer** (OpenAI/Anthropic/fake) with circuit breakers, retries, cost ceilings, and simulated outage failover validated by automated tests.
- Authored a **32-case golden evaluation harness** enforcing 90%+ quality thresholds across safety, tool selection, citations, and fallback categories in CI.
- Exposed **Prometheus metrics** and structured JSON logging; packaged a local **Prometheus + Grafana** observability stack via Docker Compose.
- Delivered **production-style deployment artifacts**: multi-stage non-root Dockerfile, Kustomize manifests (HPA/PDB/NetworkPolicy), and Terraform ECS Fargate example on existing VPC.
- Wrote operational docs: provider outage runbook, simulated postmortem, STRIDE threat model, and ADRs for key architectural decisions.

## Skills tags

`Python` · `FastAPI` · `LLM orchestration` · `Prometheus` · `OpenTelemetry` · `Docker` · `Kubernetes` · `Terraform` · `ECS Fargate` · `CI/CD` · `Agent evaluation` · `Commercial real estate domain modeling`

## What NOT to say

- ❌ "Deployed to production at JLL"
- ❌ "Managed live CRE agent traffic"
- ✅ "Portfolio platform demonstrating patterns used in enterprise agent gateways"
