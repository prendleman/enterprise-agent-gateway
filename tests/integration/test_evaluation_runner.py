"""Integration tests for the golden evaluation runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_gateway.config.settings import Settings
from agent_gateway.evaluation.runner import EvaluationRunner, load_golden_cases
from agent_gateway.storage.database import close_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def eval_settings(tmp_path) -> Settings:
    db_path = tmp_path / "eval-test.db"
    return Settings(
        database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        demo_mode=True,
        use_fake_providers=True,
        datasets_dir=str(PROJECT_ROOT / "datasets"),
        artifacts_dir=str(tmp_path / "artifacts"),
        policies_path=str(PROJECT_ROOT / "config" / "policies.yaml"),
        tool_permissions_path=str(PROJECT_ROOT / "config" / "tool_permissions.yaml"),
        model_pricing_path=str(PROJECT_ROOT / "config" / "model_pricing.example.yaml"),
    )


def test_golden_dataset_has_minimum_cases() -> None:
    cases = load_golden_cases(PROJECT_ROOT / "datasets" / "golden_evaluations.jsonl")
    assert len(cases) >= 30
    categories = {case.category for case in cases}
    for expected in (
        "tool_selection",
        "denial",
        "retrieval",
        "citations",
        "tenant_isolation",
        "refusal",
        "idempotency",
        "fallback",
        "cost_ceiling",
        "malformed_output",
        "no_result",
    ):
        assert expected in categories


@pytest.mark.asyncio
async def test_evaluation_runner_deterministic_passes_thresholds(eval_settings: Settings) -> None:
    runner = EvaluationRunner(eval_settings, deterministic=True)
    report = await runner.run()
    await close_db()

    assert report.deterministic is True
    assert report.total_cases >= 30
    assert report.overall_pass_rate >= 0.90
    assert report.safety.pass_rate >= 1.0
    assert report.tool_citation.pass_rate >= 0.90
    assert report.fallback.pass_rate >= 1.0
    assert report.thresholds_met is True


@pytest.mark.asyncio
async def test_evaluation_runner_is_repeatable(eval_settings: Settings) -> None:
    runner = EvaluationRunner(eval_settings, deterministic=True)
    first = await runner.run()
    second = await runner.run()
    await close_db()

    assert first.passed_cases == second.passed_cases
    assert first.overall_pass_rate == second.overall_pass_rate
