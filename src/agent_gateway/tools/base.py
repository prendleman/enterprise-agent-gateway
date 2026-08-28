"""Tool execution protocol and shared models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from agent_gateway.auth.context import AuthContext


class ToolResult(BaseModel):
    """Outcome of a single tool invocation."""

    name: str
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, str]] = Field(default_factory=list)
    error: str | None = None


class ToolContext(BaseModel):
    """Execution context passed to every tool."""

    auth: AuthContext
    request_id: str


class Tool(ABC):
    """Abstract agent tool."""

    name: str

    @abstractmethod
    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        """Run the tool with validated arguments."""

    @abstractmethod
    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize tool arguments."""
