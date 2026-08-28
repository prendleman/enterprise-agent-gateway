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


def _citation_source_id(citation: dict[str, str]) -> str | None:
    return citation.get("source_id") or citation.get("id")


def ground_citations(
    answer: AgentAnswer,
    *,
    allowed_source_ids: set[str],
    retrieval_used: bool,
    policy: PolicyConfig,
) -> tuple[AgentAnswer, str | None]:
    """Keep only citations whose source IDs came from executed tools."""
    grounded: list[dict[str, str]] = []
    for citation in answer.citations:
        source_id = _citation_source_id(citation)
        if source_id and source_id in allowed_source_ids:
            grounded.append(citation)

    grounded_answer = AgentAnswer(answer=answer.answer, citations=grounded)
    if answer.citations and not grounded and allowed_source_ids:
        return grounded_answer, "citation_not_grounded"
    if retrieval_used and policy.require_citations_when_retrieval_used and not grounded:
        return grounded_answer, "citations_required"
    return grounded_answer, None


def validate_citations(
    answer: AgentAnswer,
    *,
    retrieval_used: bool,
    policy: PolicyConfig,
    allowed_source_ids: set[str] | None = None,
) -> str | None:
    if allowed_source_ids is not None:
        _, violation = ground_citations(
            answer,
            allowed_source_ids=allowed_source_ids,
            retrieval_used=retrieval_used,
            policy=policy,
        )
        return violation
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
