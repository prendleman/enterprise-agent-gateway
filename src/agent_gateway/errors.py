"""RFC 9457 Problem Details for HTTP APIs."""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent_gateway.config.settings import Settings, get_settings


class ProblemDetail(BaseModel):
    """RFC 9457 problem detail object."""

    type: str = Field(
        description="URI reference identifying the problem type.",
    )
    title: str = Field(description="Short, human-readable summary.")
    status: int = Field(description="HTTP status code.")
    detail: str | None = Field(default=None, description="Human-readable explanation.")
    instance: str | None = Field(
        default=None,
        description="URI reference identifying this occurrence.",
    )
    extensions: dict[str, Any] = Field(default_factory=dict, exclude=True)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        data.update(self.extensions)
        return data


def problem_response(
    *,
    status: int,
    title: str,
    detail: str | None = None,
    type_suffix: str = "generic",
    instance: str | None = None,
    settings: Settings | None = None,
    **extensions: Any,
) -> JSONResponse:
    """Build a JSONResponse with RFC 9457 problem details."""
    cfg = settings or get_settings()
    problem = ProblemDetail(
        type=f"{cfg.problem_type_base}/{type_suffix}",
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        extensions=extensions,
    )
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert unhandled exceptions to RFC 9457 responses."""
    settings = get_settings()
    detail = str(exc) if settings.app_debug else "An unexpected error occurred."
    return problem_response(
        status=500,
        title="Internal Server Error",
        detail=detail,
        type_suffix="internal-error",
        instance=str(request.url.path),
        settings=settings,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert HTTPException to RFC 9457 responses."""
    from fastapi import HTTPException

    if not isinstance(exc, HTTPException):
        return await unhandled_exception_handler(request, exc)

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    type_suffix = _status_to_type_suffix(exc.status_code)
    return problem_response(
        status=exc.status_code,
        title=_status_to_title(exc.status_code),
        detail=detail,
        type_suffix=type_suffix,
        instance=str(request.url.path),
    )


def _status_to_title(status: int) -> str:
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }
    return titles.get(status, "Error")


def _status_to_type_suffix(status: int) -> str:
    suffixes = {
        400: "bad-request",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        405: "method-not-allowed",
        409: "conflict",
        422: "validation-error",
        429: "rate-limit-exceeded",
        500: "internal-error",
        503: "service-unavailable",
    }
    return suffixes.get(status, "generic")
