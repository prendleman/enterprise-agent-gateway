"""Bounded agent execution loop."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import structlog

from agent_gateway.agent.models import AgentPlan, AgentRunResult, ToolCallRecord, UsageInfo
from agent_gateway.agent.planner import build_plan
from agent_gateway.agent.prompts import ANSWER_SYSTEM_PROMPT
from agent_gateway.agent.usage import RunUsage
from agent_gateway.auth.context import AuthContext
from agent_gateway.guardrails.input import validate_input
from agent_gateway.guardrails.output import AgentAnswer, ground_citations, validate_output
from agent_gateway.guardrails.policy import (
    PolicyConfig,
    PolicyDecision,
    ToolPermissions,
    authorize_tool,
    load_policy_config,
    load_tool_permissions,
)
from agent_gateway.observability.metrics import (
    AGENT_ESTIMATED_COST_USD_TOTAL,
    AGENT_POLICY_DENIALS_TOTAL,
    AGENT_PROVIDER_ATTEMPTS_TOTAL,
    AGENT_RETRIEVAL_RESULTS_COUNT,
    AGENT_TOKENS_TOTAL,
    AGENT_TOOL_CALLS_TOTAL,
)
from agent_gateway.providers.base import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    RoutingPolicy,
)
from agent_gateway.providers.router import AllProvidersFailedError, ProviderRouter
from agent_gateway.tools.base import ToolContext
from agent_gateway.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


class AgentLoopError(Exception):
    """Base agent loop failure."""


class InputBlockedError(AgentLoopError):
    """Input failed guardrail validation."""


class CostCeilingExceededError(AgentLoopError):
    """Estimated cost exceeds request ceiling."""


class AgentLoop:
    """Execute validate -> plan -> authorize tools -> answer."""

    def __init__(
        self,
        *,
        router: ProviderRouter,
        tools: ToolRegistry | None = None,
        policy: PolicyConfig | None = None,
        permissions: ToolPermissions | None = None,
    ) -> None:
        self._router = router
        self._tools = tools or ToolRegistry()
        self._policy = policy or load_policy_config()
        self._permissions = permissions or load_tool_permissions()

    async def run(
        self,
        *,
        query: str,
        auth: AuthContext,
        request_id: str,
        routing_policy: RoutingPolicy = RoutingPolicy.BALANCED,
        preferred_provider: str | None = None,
        max_cost_usd: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        started = time.perf_counter()
        trace_id = uuid.uuid4().hex
        policy_decisions: list[dict[str, str | bool]] = []
        cost_ceiling = (
            max_cost_usd if max_cost_usd is not None else self._policy.default_max_cost_usd
        )
        run_usage = RunUsage()
        fallback_used = False
        primary_provider = ""
        primary_model = ""

        blocked = validate_input(query, self._policy)
        if blocked:
            for decision in blocked:
                policy_decisions.append(decision.model_dump())
                AGENT_POLICY_DENIALS_TOTAL.labels(reason=decision.reason).inc()
            raise InputBlockedError(blocked[0].reason)

        initial_response = await self._routed_completion(
            query=query,
            routing_policy=routing_policy,
            preferred_provider=preferred_provider,
            metadata=metadata,
            run_usage=run_usage,
            cost_ceiling=cost_ceiling,
        )
        primary_provider = initial_response.provider
        primary_model = initial_response.model
        if preferred_provider and initial_response.provider != preferred_provider:
            fallback_used = True

        plan, planner_fallback = await build_plan(
            query=query,
            router=self._router,
            routing_policy=routing_policy,
            preferred_provider=preferred_provider,
            model=self._default_model(),
            metadata=metadata,
            run_usage=run_usage,
        )
        self._enforce_cost_ceiling(run_usage.estimated_cost_usd, cost_ceiling)
        if planner_fallback:
            fallback_used = True

        tool_records: list[ToolCallRecord] = []
        tool_context = ToolContext(auth=auth, request_id=request_id)
        collected_citations: list[dict[str, str]] = []
        allowed_source_ids: set[str] = set()
        tool_outputs: list[dict[str, Any]] = []
        retrieval_used = False

        for step in plan.steps[: self._policy.max_tool_steps]:
            authz = authorize_tool(step.tool, auth, self._permissions)
            policy_decisions.append(authz.model_dump())
            if not authz.allowed:
                AGENT_POLICY_DENIALS_TOTAL.labels(reason=authz.reason).inc()
                AGENT_TOOL_CALLS_TOTAL.labels(tool=step.tool, status="denied").inc()
                tool_records.append(ToolCallRecord(name=step.tool, status="denied"))
                continue

            tool = self._tools.get(step.tool)
            if tool is None:
                tool_records.append(ToolCallRecord(name=step.tool, status="failed"))
                AGENT_TOOL_CALLS_TOTAL.labels(tool=step.tool, status="failed").inc()
                continue

            try:
                validated_args = tool.validate_arguments(step.arguments)
                result = await tool.execute(validated_args, tool_context)
            except ValueError:
                tool_records.append(ToolCallRecord(name=step.tool, status="failed"))
                AGENT_TOOL_CALLS_TOTAL.labels(tool=step.tool, status="failed").inc()
                continue

            tool_records.append(ToolCallRecord(name=step.tool, status=result.status))
            AGENT_TOOL_CALLS_TOTAL.labels(tool=step.tool, status=result.status).inc()
            if result.status == "succeeded":
                tool_outputs.append({"tool": step.tool, "data": result.data})
                collected_citations.extend(result.citations)
                for citation in result.citations:
                    source_id = citation.get("source_id") or citation.get("id")
                    if source_id:
                        allowed_source_ids.add(source_id)
                if step.tool.startswith("search_"):
                    retrieval_used = True
                    count = int(result.data.get("count", 0))
                    AGENT_RETRIEVAL_RESULTS_COUNT.observe(count)

        answer, answer_fallback = await self._build_answer(
            query=query,
            plan=plan,
            tool_outputs=tool_outputs,
            citations=collected_citations,
            routing_policy=routing_policy,
            preferred_provider=preferred_provider,
            metadata=metadata,
            run_usage=run_usage,
            cost_ceiling=cost_ceiling,
        )
        if answer_fallback:
            fallback_used = True

        grounded_answer, citation_error = ground_citations(
            answer,
            allowed_source_ids=allowed_source_ids,
            retrieval_used=retrieval_used,
            policy=self._policy,
        )
        if citation_error:
            policy_decisions.append(
                PolicyDecision(
                    reason=citation_error,
                    action="validate_output",
                    allowed=False,
                ).model_dump()
            )
            AGENT_POLICY_DENIALS_TOTAL.labels(reason=citation_error).inc()

        validated = validate_output(grounded_answer, self._policy)
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = UsageInfo(**run_usage.to_usage_info())
        self._record_usage(primary_provider or "unknown", primary_model or "unknown", usage)

        return AgentRunResult(
            answer=validated.answer,
            citations=validated.citations or grounded_answer.citations,
            tool_calls=tool_records,
            provider_used=primary_provider,
            model_used=primary_model,
            fallback_used=fallback_used,
            latency_ms=latency_ms,
            usage=usage,
            policy_decisions=policy_decisions,
            trace_id=trace_id,
            retrieval_used=retrieval_used,
        )

    async def _routed_completion(
        self,
        *,
        query: str | None = None,
        request: CompletionRequest | None = None,
        routing_policy: RoutingPolicy,
        preferred_provider: str | None,
        metadata: dict[str, Any] | None,
        run_usage: RunUsage,
        cost_ceiling: float,
    ) -> CompletionResponse:
        completion_request = request or CompletionRequest(
            model=self._default_model(),
            messages=[ChatMessage(role="user", content=query or "")],
            metadata=metadata or {},
        )
        try:
            response = await self._router.complete(
                completion_request,
                policy=routing_policy,
                preferred_provider=preferred_provider,
            )
            AGENT_PROVIDER_ATTEMPTS_TOTAL.labels(
                provider=response.provider,
                outcome="success",
            ).inc()
        except AllProvidersFailedError as exc:
            AGENT_PROVIDER_ATTEMPTS_TOTAL.labels(provider="none", outcome="failed").inc()
            raise AgentLoopError(str(exc)) from exc

        run_usage.add(response)
        self._enforce_cost_ceiling(run_usage.estimated_cost_usd, cost_ceiling)
        return response

    async def _build_answer(
        self,
        *,
        query: str,
        plan: AgentPlan,
        tool_outputs: list[dict[str, Any]],
        citations: list[dict[str, str]],
        routing_policy: RoutingPolicy,
        preferred_provider: str | None,
        metadata: dict[str, Any] | None,
        run_usage: RunUsage,
        cost_ceiling: float,
    ) -> tuple[AgentAnswer, bool]:
        payload = {
            "query": query,
            "plan": plan.model_dump(),
            "tool_outputs": tool_outputs,
            "citations": citations,
        }
        request = CompletionRequest(
            model=self._default_model(),
            messages=[
                ChatMessage(role="system", content=ANSWER_SYSTEM_PROMPT),
                ChatMessage(role="user", content=json.dumps(payload)),
            ],
            metadata={**(metadata or {}), "structured": "answer"},
        )
        response = await self._router.complete(
            request,
            policy=routing_policy,
            preferred_provider=preferred_provider,
        )
        run_usage.add(response)
        self._enforce_cost_ceiling(run_usage.estimated_cost_usd, cost_ceiling)
        answer_fallback = preferred_provider is not None and response.provider != preferred_provider
        parsed = self._parse_answer(response.content)
        if parsed is not None:
            if not parsed.citations and citations:
                parsed.citations = citations
            return parsed, answer_fallback
        summary = self._fallback_answer(query, tool_outputs, citations)
        return AgentAnswer(answer=summary, citations=citations), answer_fallback

    @staticmethod
    def _parse_answer(content: str) -> AgentAnswer | None:
        try:
            payload = json.loads(content)
            return AgentAnswer.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def _fallback_answer(
        query: str,
        tool_outputs: list[dict[str, Any]],
        citations: list[dict[str, str]],
    ) -> str:
        if not tool_outputs:
            return f"No matching operational records were found for: {query}"
        first = tool_outputs[0]
        count = first.get("data", {}).get("count")
        if count is not None:
            return f"Found {count} relevant records for your request."
        return "Completed the requested lookup with available tenant-scoped records."

    def _default_model(self) -> str:
        return self._router.default_provider().capabilities.default_model

    @staticmethod
    def _enforce_cost_ceiling(cumulative_cost: float, ceiling: float) -> None:
        if cumulative_cost > ceiling:
            raise CostCeilingExceededError(
                f"Estimated cumulative cost {cumulative_cost:.4f} exceeds ceiling {ceiling:.4f}"
            )

    @staticmethod
    def _record_usage(provider: str, model: str, usage: UsageInfo) -> None:
        AGENT_TOKENS_TOTAL.labels(provider=provider, direction="input").inc(usage.input_tokens)
        AGENT_TOKENS_TOTAL.labels(provider=provider, direction="output").inc(usage.output_tokens)
        AGENT_ESTIMATED_COST_USD_TOTAL.labels(provider=provider, model=model).inc(
            usage.estimated_cost_usd
        )
