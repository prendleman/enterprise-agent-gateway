"""Policy configuration loader."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from agent_gateway.auth.context import AuthContext, Role
from agent_gateway.config.settings import Settings, get_settings


class PolicyDecision(BaseModel):
    """Recorded authorization or guardrail decision."""

    reason: str
    action: str
    allowed: bool


class PolicyConfig(BaseModel):
    """Runtime guardrail configuration."""

    max_query_length: int = 2000
    max_tool_steps: int = 3
    default_max_cost_usd: float = 0.05
    provider_timeout_seconds: float = 30.0
    require_citations_when_retrieval_used: bool = True
    injection_patterns: list[str] = Field(default_factory=list)
    refusal_patterns: list[str] = Field(default_factory=list)
    redaction_patterns: dict[str, str] = Field(default_factory=dict)


def load_policy_config(settings: Settings | None = None) -> PolicyConfig:
    """Load guardrail policy from YAML."""
    cfg = settings or get_settings()
    path = Path(cfg.policies_path)
    if not path.exists():
        return PolicyConfig(
            max_query_length=cfg.max_query_length,
            max_tool_steps=cfg.max_tool_steps,
            default_max_cost_usd=cfg.default_max_cost_usd,
            provider_timeout_seconds=cfg.provider_timeout_seconds,
        )
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return PolicyConfig.model_validate(raw)


class ToolPermissions(BaseModel):
    """Role-based tool allowlist."""

    permissions: dict[str, dict[str, bool]]


def load_tool_permissions(settings: Settings | None = None) -> ToolPermissions:
    cfg = settings or get_settings()
    path = Path(cfg.tool_permissions_path)
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return ToolPermissions.model_validate(raw)


def is_tool_allowed(tool_name: str, auth: AuthContext, permissions: ToolPermissions) -> bool:
    tool_rules = permissions.permissions.get(tool_name, {})
    return bool(tool_rules.get(auth.role.value, False))


def authorize_tool(
    tool_name: str,
    auth: AuthContext,
    permissions: ToolPermissions,
) -> PolicyDecision:
    allowed = is_tool_allowed(tool_name, auth, permissions)
    if allowed:
        return PolicyDecision(reason="tool_allowed", action=tool_name, allowed=True)
    return PolicyDecision(
        reason="tool_denied_role",
        action=tool_name,
        allowed=False,
    )


def role_is_admin(auth: AuthContext) -> bool:
    return auth.role == Role.PLATFORM_ADMIN
