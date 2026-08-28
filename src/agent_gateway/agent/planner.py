"""Heuristic and provider-backed planning."""

from __future__ import annotations

import json
import re
from typing import Any

from agent_gateway.agent.models import AgentPlan, PlannedToolStep
from agent_gateway.agent.prompts import PLANNER_SYSTEM_PROMPT
from agent_gateway.agent.usage import RunUsage
from agent_gateway.providers.base import ChatMessage, CompletionRequest, RoutingPolicy
from agent_gateway.providers.router import ProviderRouter


def _keyword_plan(query: str) -> AgentPlan:
    """Deterministic fallback plan based on query keywords."""
    lowered = query.lower()
    steps: list[PlannedToolStep] = []

    if any(token in lowered for token in ("policy", "safety", "compliance", "procedure")):
        steps.append(
            PlannedToolStep(
                tool="search_policy_documents",
                arguments={"query": query, "limit": 5},
                rationale="Policy context requested",
            )
        )

    if any(token in lowered for token in ("work order", "maintenance", "repair", "hvac", "safety")):
        args: dict[str, Any] = {"query": query, "limit": 5}
        if "lakeshore" in lowered:
            args["building_name"] = "Lakeshore Tower"
        if "open" in lowered:
            args["status"] = "open"
        steps.append(
            PlannedToolStep(
                tool="search_work_orders",
                arguments=args,
                rationale="Operational work-order lookup",
            )
        )

    if "building summary" in lowered or "building overview" in lowered:
        args: dict[str, Any] = {}
        summary_match = re.search(r"building summary for\s+(.+)", query, re.I)
        overview_match = re.search(r"building overview for\s+(.+)", query, re.I)
        if summary_match or overview_match:
            match = summary_match or overview_match
            assert match is not None
            args = {"building_name": match.group(1).strip()}
        elif match := re.search(r"building\s+(bldg-\d+)", query, re.I):
            args = {"building_id": match.group(1).strip()}
        steps.append(
            PlannedToolStep(
                tool="get_building_summary",
                arguments=args,
                rationale="Building summary requested",
            )
        )

    if "create maintenance" in lowered or "maintenance request" in lowered:
        idem_key = "agent-generated-key"
        if match := re.search(r"idempotency key\s+([A-Za-z0-9\-_]+)", query, re.I):
            idem_key = match.group(1)
        building_id = "bldg-001"
        if match := re.search(r"building\s+(bldg-\d+)", query, re.I):
            building_id = match.group(1)
        steps.append(
            PlannedToolStep(
                tool="create_maintenance_request",
                arguments={
                    "building_id": building_id,
                    "title": "Agent-created maintenance request",
                    "description": query,
                    "priority": "medium",
                    "idempotency_key": idem_key,
                },
                rationale="Write request requested",
            )
        )

    if not steps:
        steps.append(
            PlannedToolStep(
                tool="search_policy_documents",
                arguments={"query": query, "limit": 3},
                rationale="Default policy lookup",
            )
        )

    return AgentPlan(steps=steps[:3], rationale="Keyword-based plan")


def _parse_plan_json(content: str) -> AgentPlan | None:
    try:
        payload = json.loads(content)
        return AgentPlan.model_validate(payload)
    except (json.JSONDecodeError, ValueError):
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
                return AgentPlan.model_validate(payload)
            except (json.JSONDecodeError, ValueError):
                return None
    return None


async def build_plan(
    *,
    query: str,
    router: ProviderRouter,
    routing_policy: RoutingPolicy,
    preferred_provider: str | None,
    model: str,
    metadata: dict[str, Any] | None,
    run_usage: RunUsage,
) -> tuple[AgentPlan, bool]:
    """Ask routed provider for a structured plan or fall back to heuristics."""
    request = CompletionRequest(
        model=model,
        messages=[
            ChatMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
            ChatMessage(role="user", content=query),
        ],
        metadata={**(metadata or {}), "structured": "plan"},
    )
    response = await router.complete(
        request,
        policy=routing_policy,
        preferred_provider=preferred_provider,
    )
    run_usage.add(response)
    fallback_used = preferred_provider is not None and response.provider != preferred_provider
    parsed = _parse_plan_json(response.content)
    if parsed is not None:
        parsed.steps = parsed.steps[:3]
        return parsed, fallback_used
    return _keyword_plan(query), fallback_used
