"""Request ID propagation middleware."""

import uuid
from collections.abc import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from agent_gateway.config.settings import get_settings


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign or propagate a unique request ID for tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        header = settings.request_id_header
        request_id = request.headers.get(header) or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers[header] = request_id
        return response
