"""API middleware."""

from __future__ import annotations

import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from agent_gateway.observability.metrics import AGENT_REQUEST_LATENCY_SECONDS, AGENT_REQUESTS_TOTAL


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request latency and status for agent endpoints."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not request.url.path.startswith("/v1/agents"):
            return await call_next(request)

        started = time.perf_counter()
        provider = "unknown"
        status = "success"
        try:
            response = await call_next(request)
            if response.status_code >= 400:
                status = "error"
            return response
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - started
            AGENT_REQUEST_LATENCY_SECONDS.labels(provider=provider).observe(elapsed)
            AGENT_REQUESTS_TOTAL.labels(provider=provider, status=status).inc()
