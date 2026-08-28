"""Agent structured models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlannedToolStep(BaseModel):
    """Single tool invocation proposed by the planner."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class AgentPlan(BaseModel):
    """Structured plan returned by the provider."""

    steps: list[PlannedToolStep] = Field(default_factory=list)
    rationale: str = ""


class ToolCallRecord(BaseModel):
    """Tool execution record returned in API responses."""

    name: str
    status: str


class UsageInfo(BaseModel):
    """Token and cost usage summary."""

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class AgentRunResult(BaseModel):
    """Internal agent loop result."""

    answer: str
    citations: list[dict[str, str]] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    provider_used: str
    model_used: str
    fallback_used: bool = False
    latency_ms: int = 0
    usage: UsageInfo = Field(default_factory=UsageInfo)
    policy_decisions: list[dict[str, str | bool]] = Field(default_factory=list)
    trace_id: str
    retrieval_used: bool = False
