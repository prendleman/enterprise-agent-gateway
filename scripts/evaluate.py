"""Run golden-set evaluation and write CI artifacts."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _settings():
    from agent_gateway.config.settings import Settings, get_settings

    get_settings.cache_clear()
    return Settings(
        demo_mode=True,
        use_fake_providers=True,
        datasets_dir=str(ROOT / "datasets"),
        artifacts_dir=str(ROOT / "artifacts"),
        policies_path=str(ROOT / "config" / "policies.yaml"),
        tool_permissions_path=str(ROOT / "config" / "tool_permissions.yaml"),
        model_pricing_path=str(ROOT / "config" / "model_pricing.example.yaml"),
        database_url=f"sqlite+aiosqlite:///{(ROOT / 'artifacts' / 'eval.db').as_posix()}",
    )


async def _run() -> int:
    from agent_gateway.evaluation.report import write_json_report, write_markdown_report
    from agent_gateway.evaluation.runner import EvaluationRunner
    from agent_gateway.storage.database import close_db

    settings = _settings()
    artifacts = Path(settings.artifacts_dir)
    artifacts.mkdir(parents=True, exist_ok=True)

    runner = EvaluationRunner(settings, deterministic=True)
    report = await runner.run()
    await close_db()

    json_path = artifacts / "evaluation-latest.json"
    md_path = artifacts / "evaluation-latest.md"
    write_json_report(report, json_path)
    write_markdown_report(report, md_path)

    print(f"Evaluation complete: {report.passed_cases}/{report.total_cases} passed")
    print(f"Overall pass rate: {report.overall_pass_rate:.1%}")
    print(f"Safety: {report.safety.pass_rate:.1%} ({report.safety.passed}/{report.safety.total})")
    print(
        f"Tool/citation: {report.tool_citation.pass_rate:.1%} "
        f"({report.tool_citation.passed}/{report.tool_citation.total})"
    )
    print(
        f"Fallback: {report.fallback.pass_rate:.1%} "
        f"({report.fallback.passed}/{report.fallback.total})"
    )
    print(f"Thresholds met: {report.thresholds_met}")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")

    return 0 if report.thresholds_met else 1


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
