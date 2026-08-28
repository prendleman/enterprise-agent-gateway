"""Optional live-provider evaluation tier (credential-dependent)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _settings():
    from agent_gateway.config.settings import Settings, get_settings

    get_settings.cache_clear()
    return Settings(
        demo_mode=False,
        use_fake_providers=False,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        datasets_dir=str(ROOT / "datasets"),
        artifacts_dir=str(ROOT / "artifacts"),
        policies_path=str(ROOT / "config" / "policies.yaml"),
        tool_permissions_path=str(ROOT / "config" / "tool_permissions.yaml"),
        model_pricing_path=str(ROOT / "config" / "model_pricing.example.yaml"),
        models_config_path=str(ROOT / "config" / "models.example.yaml"),
        database_url=f"sqlite+aiosqlite:///{(ROOT / 'artifacts' / 'eval_live.db').as_posix()}",
    )


async def _run() -> int:
    settings = _settings()
    if not settings.openai_api_key and not settings.anthropic_api_key:
        print("Skipping live evaluation: set OPENAI_API_KEY and/or ANTHROPIC_API_KEY")
        return 0

    from agent_gateway.evaluation.report import write_json_report, write_markdown_report
    from agent_gateway.evaluation.runner import EvaluationRunner
    from agent_gateway.storage.database import close_db

    artifacts = Path(settings.artifacts_dir)
    artifacts.mkdir(parents=True, exist_ok=True)

    runner = EvaluationRunner(settings, deterministic=False, max_cases=5)
    report = await runner.run()
    await close_db()

    json_path = artifacts / "evaluation-live-latest.json"
    md_path = artifacts / "evaluation-live-latest.md"
    write_json_report(report, json_path)
    write_markdown_report(report, md_path)

    print(f"Live evaluation: {report.passed_cases}/{report.total_cases} passed")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if report.passed_cases == report.total_cases else 1


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
