"""Evaluation metric aggregation and threshold checks."""

from __future__ import annotations

from agent_gateway.evaluation.models import (
    FALLBACK_CATEGORIES,
    SAFETY_CATEGORIES,
    TOOL_CITATION_CATEGORIES,
    CaseResult,
    CategoryMetrics,
    EvaluationReport,
    EvaluationThresholds,
)


def aggregate_metrics(
    case_results: list[CaseResult],
) -> tuple[CategoryMetrics, CategoryMetrics, CategoryMetrics]:
    """Compute safety, tool/citation, and fallback metric buckets."""
    safety = CategoryMetrics()
    tool_citation = CategoryMetrics()
    fallback = CategoryMetrics()

    for result in case_results:
        category = result.category
        if category in SAFETY_CATEGORIES:
            safety.total += 1
            if result.passed:
                safety.passed += 1
        if category in TOOL_CITATION_CATEGORIES:
            tool_citation.total += 1
            if result.passed:
                tool_citation.passed += 1
        if category in FALLBACK_CATEGORIES:
            fallback.total += 1
            if result.passed:
                fallback.passed += 1

    return safety, tool_citation, fallback


def thresholds_met(
    report: EvaluationReport,
    thresholds: EvaluationThresholds | None = None,
) -> bool:
    """Return True when all configured thresholds are satisfied."""
    cfg = thresholds or report.thresholds
    return (
        report.overall_pass_rate >= cfg.overall
        and report.safety.pass_rate >= cfg.safety
        and (report.tool_citation.total == 0 or report.tool_citation.pass_rate >= cfg.tool_citation)
        and (report.fallback.total == 0 or report.fallback.pass_rate >= cfg.fallback)
    )


def finalize_report(
    *,
    run_id: str,
    started_at,
    finished_at,
    deterministic: bool,
    case_results: list[CaseResult],
    thresholds: EvaluationThresholds,
) -> EvaluationReport:
    """Build a complete report with aggregated metrics."""
    passed = sum(1 for r in case_results if r.passed)
    total = len(case_results)
    safety, tool_citation, fallback = aggregate_metrics(case_results)
    report = EvaluationReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        deterministic=deterministic,
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        overall_pass_rate=(passed / total) if total else 1.0,
        safety=safety,
        tool_citation=tool_citation,
        fallback=fallback,
        thresholds=thresholds,
        thresholds_met=False,
        case_results=case_results,
    )
    report.thresholds_met = thresholds_met(report, thresholds)
    return report
