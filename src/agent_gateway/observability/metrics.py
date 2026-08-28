"""Prometheus metrics for agent gateway."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

AGENT_REQUESTS_TOTAL = Counter(
    "agent_requests_total",
    "Total agent run requests",
    ["provider", "status"],
)

AGENT_REQUEST_LATENCY_SECONDS = Histogram(
    "agent_request_latency_seconds",
    "End-to-end agent request latency",
    ["provider"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

AGENT_PROVIDER_ATTEMPTS_TOTAL = Counter(
    "agent_provider_attempts_total",
    "Provider completion attempts",
    ["provider", "outcome"],
)

AGENT_PROVIDER_FAILOVERS_TOTAL = Counter(
    "agent_provider_failovers_total",
    "Provider failover events",
    ["from_provider", "to_provider"],
)

AGENT_PROVIDER_CIRCUIT_STATE = Gauge(
    "agent_provider_circuit_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["provider", "state"],
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "agent_tool_calls_total",
    "Tool invocation outcomes",
    ["tool", "status"],
)

AGENT_POLICY_DENIALS_TOTAL = Counter(
    "agent_policy_denials_total",
    "Policy denial events",
    ["reason"],
)

AGENT_TOKENS_TOTAL = Counter(
    "agent_tokens_total",
    "Token usage by provider and direction",
    ["provider", "direction"],
)

AGENT_ESTIMATED_COST_USD_TOTAL = Counter(
    "agent_estimated_cost_usd_total",
    "Estimated spend in USD",
    ["provider", "model"],
)

AGENT_RETRIEVAL_RESULTS_COUNT = Histogram(
    "agent_retrieval_results_count",
    "Number of retrieval hits per query",
    buckets=(0, 1, 2, 3, 5, 10, 20),
)
