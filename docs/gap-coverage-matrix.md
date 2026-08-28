# Gap Coverage Matrix — JLL-Inspired Build Brief

> **Portfolio disclaimer:** This matrix maps **demonstrated capabilities** in this repo to themes commonly found in enterprise CRE / agent-platform job descriptions (including JLL-style AI platform roles). It does **not** imply JLL endorsement, employment, or production deployment.

Legend: ✅ Implemented in repo · 🟡 Partial / demo-scoped · ⬜ Out of scope for portfolio

| Theme | Brief expectation | Status | Evidence |
|-------|-------------------|--------|----------|
| Governed agent API | REST endpoint for bounded agent runs | ✅ | `POST /v1/agents/run` |
| Multi-tenant isolation | Tenant-scoped tools & data | ✅ | API keys → tenant; eval cases `tenant_isolation` |
| RBAC / tool permissions | Role-based tool access | ✅ | `config/tool_permissions.yaml`, auth roles |
| Policy engine | YAML-driven allow/deny rules | ✅ | `config/policies.yaml`, guardrails |
| Provider abstraction | Pluggable LLM backends | ✅ | OpenAI, Anthropic, fake providers |
| Routing & failover | Primary/fallback with health | ✅ | `ProviderRouter`, outage simulation |
| Circuit breaker & retry | Resilience patterns | ✅ | `reliability/` module + unit tests |
| Cost controls | Per-request spend ceiling | ✅ | `max_cost_usd`, pricing catalog |
| Idempotency | Safe retries for mutations | ✅ | `reliability/idempotency.py` + tests |
| Rate limiting | Abuse protection | 🟡 | In-memory token bucket (demo scale) |
| Structured logging | JSON logs + request ID | ✅ | structlog middleware |
| Prometheus metrics | RED + domain metrics | ✅ | `/metrics`, docker-compose stack |
| OpenTelemetry tracing | Distributed traces | 🟡 | SDK wired; OTLP export planned |
| Golden-set evaluation | Automated quality gates | ✅ | 32 cases, thresholds in CI |
| Load testing | Mixed traffic scenario | ✅ | `tests/load/locustfile.py` |
| Incident runbook | Provider outage playbook | ✅ | `docs/runbook-provider-outage.md` |
| Postmortem template | Blameless review artifact | ✅ | `docs/postmortem-simulated-provider-outage.md` |
| Container packaging | Multi-stage, non-root | ✅ | `Dockerfile` |
| Local observability stack | Prometheus + Grafana | ✅ | `docker-compose.yml` |
| Kubernetes manifests | Probes, HPA, PDB, NetPol | ✅ | `deploy/kubernetes/` |
| IaC example (AWS ECS) | Fargate on existing VPC | ✅ | `deploy/terraform/aws-ecs/` |
| Secrets management | No secrets in repo | ✅ | `.env.example`, K8s secret example, TF ARNs |
| CRE domain tools | Buildings, WOs, policies | ✅ | `agent_gateway/tools/` |
| Retrieval / search | Policy & work-order search | ✅ | SQLite FTS retrieval |
| AuthN (enterprise SSO) | OIDC / SAML | ⬜ | Demo API keys only |
| AuthZ (central IAM) | External policy store | ⬜ | File-based policies |
| Vector DB / embeddings | Semantic search at scale | ⬜ | FTS demo |
| Human-in-the-loop | Approval workflows | ⬜ | — |
| Production SLOs / on-call | Live paging | ⬜ | Documented only |
| Multi-region DR | Active/active | ⬜ | — |
| WAF / mTLS edge | Perimeter hardening | ⬜ | NetworkPolicy example only |

## Summary

Phases 0–4 of this portfolio platform cover the **full agent stack**, **evaluation harness**, **reliability patterns**, and **deployment scaffolding** called out in the build brief. Enterprise gaps (SSO, vector search at scale, live SLOs) are explicitly labeled out-of-scope or partial to keep the project honest and interview-ready.
