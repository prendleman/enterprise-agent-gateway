"""Citation grounding validation tests."""

from __future__ import annotations

from agent_gateway.guardrails.output import AgentAnswer, ground_citations
from agent_gateway.guardrails.policy import PolicyConfig


def test_rejects_ungrounded_citation_ids() -> None:
    answer = AgentAnswer(
        answer="Safety issue noted.",
        citations=[{"source_id": "invented-id", "title": "Fake"}],
    )
    grounded, violation = ground_citations(
        answer,
        allowed_source_ids={"policy-doc-001"},
        retrieval_used=True,
        policy=PolicyConfig(require_citations_when_retrieval_used=True),
    )
    assert violation == "citation_not_grounded"
    assert grounded.citations == []


def test_keeps_grounded_citations() -> None:
    answer = AgentAnswer(
        answer="Safety issue noted.",
        citations=[{"source_id": "policy-doc-001", "title": "Fire Safety"}],
    )
    grounded, violation = ground_citations(
        answer,
        allowed_source_ids={"policy-doc-001"},
        retrieval_used=True,
        policy=PolicyConfig(require_citations_when_retrieval_used=True),
    )
    assert violation is None
    assert len(grounded.citations) == 1
