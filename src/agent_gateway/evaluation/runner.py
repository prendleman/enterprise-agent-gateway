"""Golden-set evaluation runner."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_gateway.agent.loop import AgentLoop, CostCeilingExceededError, InputBlockedError
from agent_gateway.auth.service import AuthService
from agent_gateway.config.settings import Settings
from agent_gateway.evaluation.metrics import finalize_report
from agent_gateway.evaluation.models import (
    CaseResult,
    EvaluationReport,
    EvaluationThresholds,
    GoldenEvaluationCase,
)
from agent_gateway.providers.base import RoutingPolicy
from agent_gateway.providers.fake import FakeProvider, permanent_error
from agent_gateway.providers.pricing import PricingCatalog
from agent_gateway.providers.registry import ProviderRegistry
from agent_gateway.providers.router import ProviderRouter
from agent_gateway.storage.database import close_db, init_db
from agent_gateway.storage.seed import seed_database


def load_golden_cases(path: Path) -> list[GoldenEvaluationCase]:
    """Load golden evaluation cases from JSONL."""
    cases: list[GoldenEvaluationCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        cases.append(GoldenEvaluationCase.model_validate(json.loads(stripped)))
    return cases


def _build_router(settings: Settings, *, force_primary_failure: bool) -> ProviderRouter:
    pricing_path = Path(settings.model_pricing_path)
    pricing = PricingCatalog.from_yaml(pricing_path) if pricing_path.exists() else None
    shared_model = "shared-eval-model"

    primary = FakeProvider(
        name="fake-openai",
        display_name="Fake OpenAI",
        models=[shared_model],
        default_model=shared_model,
        quality_score=0.72,
        failure_mode=permanent_error() if force_primary_failure else None,
    )
    backup = FakeProvider(
        name="fake-anthropic",
        display_name="Fake Anthropic",
        models=[shared_model],
        default_model=shared_model,
        quality_score=0.78,
    )
    registry = ProviderRegistry(
        {
            primary.capabilities.name: primary,
            backup.capabilities.name: backup,
        },
        pricing=pricing,
    )
    return ProviderRouter(registry)


class EvaluationRunner:
    """Execute golden evaluations against the agent loop."""

    def __init__(
        self,
        settings: Settings,
        *,
        dataset_path: Path | None = None,
        thresholds: EvaluationThresholds | None = None,
        deterministic: bool = True,
    ) -> None:
        self._settings = settings
        self._dataset_path = (
            dataset_path or Path(settings.datasets_dir) / "golden_evaluations.jsonl"
        )
        self._thresholds = thresholds or EvaluationThresholds()
        self._deterministic = deterministic
        self._auth = AuthService(settings)

    async def run(self) -> EvaluationReport:
        """Run all golden cases and return an aggregated report."""
        run_id = uuid.uuid4().hex[:12]
        started_at = datetime.now(tz=UTC)
        cases = load_golden_cases(self._dataset_path)

        await close_db()
        await init_db(self._settings)
        if self._settings.is_demo:
            await seed_database(self._settings)

        case_results: list[CaseResult] = []
        for case in cases:
            case_results.append(await self._run_case(case))

        finished_at = datetime.now(tz=UTC)
        return finalize_report(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            deterministic=self._deterministic,
            case_results=case_results,
            thresholds=self._thresholds,
        )

    async def _run_case(self, case: GoldenEvaluationCase) -> CaseResult:
        auth = self._auth.authenticate(case.api_key)
        if auth is None:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message="Invalid api_key in golden case",
                tags=case.tags,
            )

        router = _build_router(
            self._settings,
            force_primary_failure=case.force_primary_failure,
        )
        loop = AgentLoop(router=router)
        routing = RoutingPolicy(case.routing_policy)

        try:
            result = await loop.run(
                query=case.query,
                auth=auth,
                request_id=f"eval-{case.id}",
                routing_policy=routing,
                preferred_provider=case.preferred_provider,
                max_cost_usd=case.max_cost_usd,
                metadata={"evaluation_id": case.id, "deterministic": self._deterministic},
            )
        except InputBlockedError as exc:
            return self._score_blocked(case, str(exc))
        except CostCeilingExceededError as exc:
            return self._score_cost_error(case, str(exc))
        except Exception as exc:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message=f"Unexpected error: {exc}",
                tags=case.tags,
            )

        return self._score_success(case, result.model_dump())

    def _score_blocked(self, case: GoldenEvaluationCase, reason: str) -> CaseResult:
        if not case.expect_blocked:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message=f"Unexpected input block: {reason}",
                tags=case.tags,
            )
        if case.expect_block_reason and case.expect_block_reason not in reason:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message=f"Blocked with wrong reason: {reason}",
                tags=case.tags,
                details={"reason": reason},
            )
        return CaseResult(
            case_id=case.id,
            category=case.category,
            passed=True,
            message="Input blocked as expected",
            tags=case.tags,
            details={"reason": reason},
        )

    def _score_cost_error(self, case: GoldenEvaluationCase, reason: str) -> CaseResult:
        if not case.expect_cost_error:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message=f"Unexpected cost error: {reason}",
                tags=case.tags,
            )
        return CaseResult(
            case_id=case.id,
            category=case.category,
            passed=True,
            message="Cost ceiling enforced as expected",
            tags=case.tags,
            details={"reason": reason},
        )

    def _score_success(self, case: GoldenEvaluationCase, result: dict[str, Any]) -> CaseResult:
        if case.expect_blocked:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message="Expected blocked request but agent succeeded",
                tags=case.tags,
            )
        if case.expect_cost_error:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message="Expected cost ceiling error but agent succeeded",
                tags=case.tags,
            )

        tool_calls = {call["name"]: call["status"] for call in result.get("tool_calls", [])}
        answer = result.get("answer", "")
        citations = result.get("citations", [])
        fallback_used = bool(result.get("fallback_used"))
        details: dict[str, Any] = {
            "tool_calls": tool_calls,
            "provider_used": result.get("provider_used"),
            "fallback_used": fallback_used,
        }

        if case.expected_tools:
            missing = [tool for tool in case.expected_tools if tool not in tool_calls]
            if missing:
                return CaseResult(
                    case_id=case.id,
                    category=case.category,
                    passed=False,
                    message=f"Missing expected tools: {missing}",
                    tags=case.tags,
                    details=details,
                )

        if case.expected_tool_status:
            for tool, status in case.expected_tool_status.items():
                actual = tool_calls.get(tool)
                if actual != status:
                    return CaseResult(
                        case_id=case.id,
                        category=case.category,
                        passed=False,
                        message=f"Tool {tool} status {actual!r} != expected {status!r}",
                        tags=case.tags,
                        details=details,
                    )

        if case.expect_denial_reason:
            decisions = result.get("policy_decisions", [])
            if not any(d.get("reason") == case.expect_denial_reason for d in decisions):
                return CaseResult(
                    case_id=case.id,
                    category=case.category,
                    passed=False,
                    message=f"Expected denial reason {case.expect_denial_reason!r}",
                    tags=case.tags,
                    details=details,
                )

        if case.expected_answer_contains:
            lowered = answer.lower()
            missing_terms = [
                term for term in case.expected_answer_contains if term.lower() not in lowered
            ]
            if missing_terms:
                return CaseResult(
                    case_id=case.id,
                    category=case.category,
                    passed=False,
                    message=f"Answer missing terms: {missing_terms}",
                    tags=case.tags,
                    details=details,
                )

        if case.expected_answer_not_contains:
            lowered = answer.lower()
            forbidden = [
                term for term in case.expected_answer_not_contains if term.lower() in lowered
            ]
            if forbidden:
                return CaseResult(
                    case_id=case.id,
                    category=case.category,
                    passed=False,
                    message=f"Answer contained forbidden terms: {forbidden}",
                    tags=case.tags,
                    details=details,
                )

        if case.expect_citations is True and not citations:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message="Expected citations but none returned",
                tags=case.tags,
                details=details,
            )

        if case.expect_fallback and not fallback_used:
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message="Expected provider fallback but fallback_used=false",
                tags=case.tags,
                details=details,
            )

        if case.expect_no_results and (
            "no matching" not in answer.lower() and "found 0" not in answer.lower()
        ):
            return CaseResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                message="Expected no-result style answer",
                tags=case.tags,
                details=details,
            )

        return CaseResult(
            case_id=case.id,
            category=case.category,
            passed=True,
            message="All expectations met",
            tags=case.tags,
            details=details,
        )
