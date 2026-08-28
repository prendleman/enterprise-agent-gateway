"""Input validation and prompt-injection detection."""

from __future__ import annotations

import re

from agent_gateway.guardrails.policy import PolicyConfig, PolicyDecision


def validate_query_length(query: str, policy: PolicyConfig) -> PolicyDecision | None:
    if len(query) > policy.max_query_length:
        return PolicyDecision(
            reason="query_too_long",
            action="validate_input",
            allowed=False,
        )
    return None


def detect_injection(query: str, policy: PolicyConfig) -> PolicyDecision | None:
    for pattern in policy.injection_patterns:
        if re.search(pattern, query):
            return PolicyDecision(
                reason="prompt_injection_detected",
                action="validate_input",
                allowed=False,
            )
    return None


def detect_refusal(query: str, policy: PolicyConfig) -> PolicyDecision | None:
    for pattern in policy.refusal_patterns:
        if re.search(pattern, query):
            return PolicyDecision(
                reason="unsafe_request",
                action="validate_input",
                allowed=False,
            )
    return None


def validate_input(query: str, policy: PolicyConfig) -> list[PolicyDecision]:
    """Return blocking policy decisions for invalid input."""
    checks = [
        validate_query_length(query, policy),
        detect_injection(query, policy),
        detect_refusal(query, policy),
    ]
    return [decision for decision in checks if decision is not None]
