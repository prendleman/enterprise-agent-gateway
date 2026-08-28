# ADR 0001: FastAPI as the Agent Gateway Framework

## Status

Accepted

## Context

The portfolio platform needs an async HTTP API with OpenAPI docs, structured validation, middleware hooks, and broad ecosystem support for observability.

## Decision

Use **FastAPI** on **uvicorn** with Pydantic v2 models for request/response contracts.

## Consequences

- **Positive:** Automatic OpenAPI schema, async endpoints, excellent test client support.
- **Positive:** Mature Prometheus and OpenTelemetry integrations.
- **Negative:** Python GIL limits CPU-bound concurrency; acceptable for I/O-bound agent workloads.
- **Neutral:** Team must enforce thin route handlers; business logic stays in services.
