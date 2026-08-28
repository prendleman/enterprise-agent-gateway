# ADR 0004: Golden-Set Evaluation as CI Gate

## Status

Accepted

## Context

Agent systems regress silently when prompts, tools, or policies change. Manual QA does not scale for 32+ scenarios spanning safety, tools, citations, and failover.

## Decision

Maintain `datasets/golden_evaluations.jsonl` and run **EvaluationRunner** in CI via `scripts/evaluate.py` with category thresholds:

| Category | Threshold |
|----------|-----------|
| Overall | ≥ 90% |
| Safety | 100% |
| Tool/citation | ≥ 90% |
| Fallback | 100% |

Use **fake providers** for deterministic runs in demo/CI.

## Consequences

- **Positive:** Objective quality gate on every PR.
- **Positive:** Markdown + JSON artifacts for review.
- **Negative:** Golden set requires curation as features grow.
- **Follow-on:** Add LLM-as-judge scoring and production trace replay.
