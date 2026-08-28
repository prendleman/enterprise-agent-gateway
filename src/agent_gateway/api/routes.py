"""HTTP API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from agent_gateway.agent.loop import AgentLoop, CostCeilingExceededError, InputBlockedError
from agent_gateway.api.dependencies import enforce_tenant_rate_limit, get_agent_loop
from agent_gateway.api.errors import CostLimitError, PolicyViolationError, ServiceUnavailableError
from agent_gateway.api.models import (
    AgentRunRequest,
    AgentRunResponse,
    Citation,
    ToolCallResponse,
    UsageResponse,
)
from agent_gateway.auth.context import AuthContext
from agent_gateway.errors import problem_response
from agent_gateway.observability.metrics import AGENT_REQUESTS_TOTAL

router = APIRouter()


@router.post("/v1/agents/run", response_model=AgentRunResponse, tags=["agents"])
async def run_agent(
    body: AgentRunRequest,
    request: Request,
    auth: AuthContext = Depends(enforce_tenant_rate_limit),  # noqa: B008
    loop: AgentLoop = Depends(get_agent_loop),  # noqa: B008
) -> AgentRunResponse:
    """Execute a bounded agent run scoped to the authenticated tenant."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    try:
        result = await loop.run(
            query=body.query,
            auth=auth,
            request_id=request_id,
            routing_policy=body.routing_policy,
            preferred_provider=body.preferred_provider,
            max_cost_usd=body.max_cost_usd,
            metadata=body.metadata,
        )
    except InputBlockedError as exc:
        AGENT_REQUESTS_TOTAL.labels(provider="none", status="policy_error").inc()
        raise PolicyViolationError(str(exc)) from exc
    except CostCeilingExceededError as exc:
        AGENT_REQUESTS_TOTAL.labels(provider="none", status="cost_error").inc()
        raise CostLimitError(str(exc)) from exc
    except Exception as exc:
        AGENT_REQUESTS_TOTAL.labels(provider="none", status="error").inc()
        if "All providers failed" in str(exc):
            raise ServiceUnavailableError(str(exc)) from exc
        raise

    AGENT_REQUESTS_TOTAL.labels(provider=result.provider_used, status="success").inc()
    return AgentRunResponse(
        request_id=request_id,
        answer=result.answer,
        citations=[Citation(**c) for c in result.citations],
        tool_calls=[ToolCallResponse(**t.model_dump()) for t in result.tool_calls],
        provider_used=result.provider_used,
        model_used=result.model_used,
        fallback_used=result.fallback_used,
        latency_ms=result.latency_ms,
        usage=UsageResponse(**result.usage.model_dump()),
        policy_decisions=result.policy_decisions,  # type: ignore[arg-type]
        trace_id=result.trace_id,
    )


@router.get("/metrics", tags=["observability"])
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


async def api_error_handler(request: Request, exc: Exception) -> Response:
    from agent_gateway.api.errors import ApiError

    if not isinstance(exc, ApiError):
        raise exc
    return problem_response(
        status=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        type_suffix=exc.type_suffix,
        instance=str(request.url.path),
    )
