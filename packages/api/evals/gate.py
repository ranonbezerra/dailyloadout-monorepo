"""Baseline + regression gate for the eval harness.

A *baseline* is a flat snapshot of aggregate scores — ``overall``, ``task:<t>``,
``check:<c>`` — committed to ``results/baseline.json``. The gate re-runs the eval
and fails if any metric drops more than a tolerance below the baseline. That is
what turns "I have evals" into "I have a gate that blocks a quality regression":
``run_eval.py --strict`` only catches a *total* deterministic failure, while the
gate catches a *drop* (the judge slipping 0.9→0.6, grounding sinking but still
above the suspicious floor) that would otherwise pass silently.
"""

from __future__ import annotations

from evals.schema import EvalReport


def baseline_from_report(report: EvalReport) -> dict[str, float]:
    """Flatten a report into ``{metric: score}`` (overall + per-task + per-check)."""
    metrics: dict[str, float] = {"overall": round(report.overall_score, 4)}
    for task, score in report.scores_by_task().items():
        metrics[f"task:{task}"] = round(score, 4)
    for check, score in report.scores_by_check().items():
        metrics[f"check:{check}"] = round(score, 4)
    return metrics


def diff_baseline(report: EvalReport, baseline: dict[str, float], tolerance: float) -> list[str]:
    """Return regression messages for metrics that dropped beyond *tolerance*.

    Empty list = no regression. New metrics absent from the baseline are ignored
    (a freshly added task/check is never itself a regression).
    """
    current = baseline_from_report(report)
    regressions: list[str] = []
    for key, base_val in baseline.items():
        cur_val = current.get(key)
        if cur_val is None:
            continue
        if cur_val < base_val - tolerance:
            regressions.append(f"{key}: {cur_val:.3f} < baseline {base_val:.3f}")
    return sorted(regressions)
