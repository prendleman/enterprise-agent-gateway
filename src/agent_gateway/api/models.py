"""API request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_gateway.providers.base import RoutingPolicy


class AgentRunRequest(BaseModel):
    """POST /v1/agents/run request body (tenant comes from auth)."""

    conversation_id: str
    query: str = Field(min_length=1)
    routing_policy: RoutingPolicy = RoutingPolicy.BALANCED
    preferred_provider: str | None = None
    max_cost_usd: float = Field(default=0.05, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    source_id: str
    title: str


class ToolCallResponse(BaseModel):
    name: str
    status: str


class UsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class PolicyDecisionResponse(BaseModel):
    reason: str
    action: str
    allowed: bool


class AgentRunResponse(BaseModel):
    """POST /v1/agents/run response body."""

    request_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCallResponse] = Field(default_factory=list)
    provider_used: str
    model_used: str
    fallback_used: bool = False
    latency_ms: int
    usage: UsageResponse
    policy_decisions: list[PolicyDecisionResponse] = Field(default_factory=list)
    trace_id: str
