"""Output validation, citation checks, and redaction."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from agent_gateway.guardrails.policy import PolicyConfig


class AgentAnswer(BaseModel):
    """Structured final answer from the provider."""

    answer: str
    citations: list[dict[str, str]] = Field(default_factory=list)


def redact_sensitive_text(text: str, policy: PolicyConfig) -> str:
    redacted = text
    for pattern in policy.redaction_patterns.values():
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def validate_citations(
    answer: AgentAnswer,
    *,
    retrieval_used: bool,
    policy: PolicyConfig,
) -> str | None:
    if retrieval_used and policy.require_citations_when_retrieval_used and not answer.citations:
        return "citations_required"
    return None


def validate_output(answer: AgentAnswer, policy: PolicyConfig) -> AgentAnswer:
    """Validate and redact the final answer."""
    cleaned = redact_sensitive_text(answer.answer.strip(), policy)
    if not cleaned:
        msg = "empty_answer"
        raise ValueError(msg)
    return AgentAnswer(answer=cleaned, citations=answer.citations)
