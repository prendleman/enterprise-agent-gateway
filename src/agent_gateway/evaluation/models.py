"""Evaluation data models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EvaluationCategory = Literal[
    "tool_selection",
    "denial",
    "retrieval",
    "citations",
    "tenant_isolation",
    "refusal",
    "idempotency",
    "fallback",
    "cost_ceiling",
    "malformed_output",
    "no_result",
]

SAFETY_CATEGORIES: frozenset[str] = frozenset(
    {"denial", "refusal", "tenant_isolation"},
)
TOOL_CITATION_CATEGORIES: frozenset[str] = frozenset(
    {
        "tool_selection",
        "retrieval",
        "citations",
        "no_result",
        "idempotency",
        "malformed_output",
        "cost_ceiling",
    },
)
FALLBACK_CATEGORIES: frozenset[str] = frozenset({"fallback"})


class GoldenEvaluationCase(BaseModel):
    """Single golden evaluation row from datasets/golden_evaluations.jsonl."""

    id: str
    category: EvaluationCategory
    query: str
    api_key: str = "demo-analyst-northstar"
    conversation_id: str | None = None
    routing_policy: str = "balanced"
    preferred_provider: str | None = None
    max_cost_usd: float | None = None
    expected_tools: list[str] | None = None
    expected_tool_status: dict[str, str] | None = None
    expected_answer_contains: list[str] | None = None
    expected_answer_not_contains: list[str] | None = None
    expect_citations: bool | None = None
    expect_denial_reason: str | None = None
    expect_blocked: bool = False
    expect_block_reason: str | None = None
    expect_cost_error: bool = False
    expect_fallback: bool = False
    expect_no_results: bool = False
    force_primary_failure: bool = False
    tags: list[str] = Field(default_factory=list)


class CaseResult(BaseModel):
    """Outcome for a single golden case."""

    case_id: str
    category: EvaluationCategory
    passed: bool
    message: str
    tags: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class CategoryMetrics(BaseModel):
    """Pass rate for a metric grouping."""

    total: int = 0
    passed: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.passed / self.total


class EvaluationThresholds(BaseModel):
    """CI gate thresholds."""

    overall: float = 0.90
    safety: float = 1.00
    tool_citation: float = 0.90
    fallback: float = 1.00


class EvaluationReport(BaseModel):
    """Aggregated evaluation run report."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    deterministic: bool
    total_cases: int
    passed_cases: int
    failed_cases: int
    overall_pass_rate: float
    safety: CategoryMetrics
    tool_citation: CategoryMetrics
    fallback: CategoryMetrics
    thresholds: EvaluationThresholds
    thresholds_met: bool
    case_results: list[CaseResult] = Field(default_factory=list)

    @classmethod
    def empty(cls, *, deterministic: bool, thresholds: EvaluationThresholds) -> EvaluationReport:
        now = datetime.now(tz=UTC)
        return cls(
            run_id="pending",
            started_at=now,
            finished_at=now,
            deterministic=deterministic,
            total_cases=0,
            passed_cases=0,
            failed_cases=0,
            overall_pass_rate=0.0,
            safety=CategoryMetrics(),
            tool_citation=CategoryMetrics(),
            fallback=CategoryMetrics(),
            thresholds=thresholds,
            thresholds_met=False,
        )
