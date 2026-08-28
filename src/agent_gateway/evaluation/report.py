"""Evaluation report serialization."""

from __future__ import annotations

import json
from pathlib import Path

from agent_gateway.evaluation.models import EvaluationReport


def write_json_report(report: EvaluationReport, path: Path) -> None:
    """Write evaluation report as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def render_markdown(report: EvaluationReport) -> str:
    """Render a human-readable markdown summary."""
    lines = [
        "# Evaluation Report",
        "",
        f"- **Run ID:** `{report.run_id}`",
        f"- **Mode:** {'deterministic' if report.deterministic else 'live'}",
        f"- **Started:** {report.started_at.isoformat()}",
        f"- **Finished:** {report.finished_at.isoformat()}",
        f"- **Overall pass rate:** {report.overall_pass_rate:.1%} "
        f"({report.passed_cases}/{report.total_cases})",
        f"- **Thresholds met:** {'yes' if report.thresholds_met else 'no'}",
        "",
        "## Metric buckets",
        "",
        "| Bucket | Pass rate | Passed | Total | Threshold |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Overall | {report.overall_pass_rate:.1%} | {report.passed_cases} | "
        f"{report.total_cases} | {report.thresholds.overall:.0%} |",
        f"| Safety | {report.safety.pass_rate:.1%} | {report.safety.passed} | "
        f"{report.safety.total} | {report.thresholds.safety:.0%} |",
        f"| Tool / citation | {report.tool_citation.pass_rate:.1%} | "
        f"{report.tool_citation.passed} | {report.tool_citation.total} | "
        f"{report.thresholds.tool_citation:.0%} |",
        f"| Fallback | {report.fallback.pass_rate:.1%} | {report.fallback.passed} | "
        f"{report.fallback.total} | {report.thresholds.fallback:.0%} |",
        "",
        "## Failed cases",
        "",
    ]

    failures = [r for r in report.case_results if not r.passed]
    if not failures:
        lines.append("_None — all cases passed._")
    else:
        for result in failures:
            lines.append(f"- `{result.case_id}` ({result.category}): {result.message}")

    lines.extend(["", "## All cases", ""])
    for result in report.case_results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"- [{status}] `{result.case_id}` — {result.category}: {result.message}")

    return "\n".join(lines) + "\n"


def write_markdown_report(report: EvaluationReport, path: Path) -> None:
    """Write evaluation report as markdown."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")
