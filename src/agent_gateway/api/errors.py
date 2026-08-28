"""API-specific exceptions."""

from __future__ import annotations


class ApiError(Exception):
    """Base API error with HTTP mapping."""

    status_code: int = 400
    title: str = "Bad Request"
    type_suffix: str = "bad-request"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class UnauthorizedError(ApiError):
    status_code = 401
    title = "Unauthorized"
    type_suffix = "unauthorized"


class ForbiddenError(ApiError):
    status_code = 403
    title = "Forbidden"
    type_suffix = "forbidden"


class RateLimitError(ApiError):
    status_code = 429
    title = "Too Many Requests"
    type_suffix = "rate-limit-exceeded"


class PolicyViolationError(ApiError):
    status_code = 400
    title = "Policy Violation"
    type_suffix = "policy-violation"


class CostLimitError(ApiError):
    status_code = 402
    title = "Cost Limit Exceeded"
    type_suffix = "cost-limit-exceeded"


class ServiceUnavailableError(ApiError):
    status_code = 503
    title = "Service Unavailable"
    type_suffix = "service-unavailable"
