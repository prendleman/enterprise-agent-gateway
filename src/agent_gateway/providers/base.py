"""Typed provider interface for LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProviderHealthStatus(StrEnum):
    """Health state reported by a provider adapter."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class RoutingPolicy(StrEnum):
    """Request routing strategies."""

    BALANCED = "balanced"
    QUALITY = "quality"
    COST = "cost"
    PREFERRED = "preferred"


class ChatMessage(BaseModel):
    """Single chat turn."""

    role: str
    content: str


class CompletionRequest(BaseModel):
    """Normalized completion request across providers."""

    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompletionResponse(BaseModel):
    """Normalized completion response."""

    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    finish_reason: str = "stop"
    cost_usd: float | None = None


class ProviderCapabilities(BaseModel):
    """Static metadata used for routing decisions."""

    name: str
    display_name: str
    models: list[str]
    default_model: str
    quality_score: float = Field(ge=0.0, le=1.0)
    enabled: bool = True


class ProviderError(Exception):
    """Base error raised by provider adapters."""

    transient: bool = False

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class TransientProviderError(ProviderError):
    """Retryable provider failure (timeouts, 5xx, rate limits)."""

    transient = True


class PermanentProviderError(ProviderError):
    """Non-retryable provider failure (bad request, auth)."""

    transient = False


class CircuitOpenError(ProviderError):
    """Circuit breaker is open for this provider."""

    transient = True


class LLMProvider(ABC):
    """Abstract LLM provider adapter."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return provider metadata."""

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a chat completion."""

    @abstractmethod
    async def health_check(self) -> ProviderHealthStatus:
        """Probe provider availability."""

    def is_configured(self) -> bool:
        """True when credentials/config required for live calls are present."""
        return True
