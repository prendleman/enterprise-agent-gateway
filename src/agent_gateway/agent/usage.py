"""Request-scoped LLM usage accumulation."""

from __future__ import annotations

from dataclasses import dataclass

from agent_gateway.providers.base import CompletionResponse


@dataclass
class RunUsage:
    """Cumulative token and cost totals for one agent run."""

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    provider_attempts: int = 0

    def add(self, response: CompletionResponse) -> None:
        self.input_tokens += response.input_tokens
        self.output_tokens += response.output_tokens
        self.estimated_cost_usd += response.cost_usd or 0.0
        self.provider_attempts += 1

    def to_usage_info(self) -> dict[str, int | float]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
        }
