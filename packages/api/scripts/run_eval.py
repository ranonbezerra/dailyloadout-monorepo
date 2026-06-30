"""Run the LLM evaluation harness and print a report.

Defaults to the deterministic ``DummyLLMClient`` + ``DummyJudge`` — offline and
CI-safe. Pass ``--real`` to evaluate the configured provider (``LLM_PROVIDER``)
with the model-graded ``LLMJudge``. ``--strict`` exits non-zero if any case
fails its deterministic checks (used by the CI gate).

Usage:
    poetry run python scripts/run_eval.py [--real] [--strict]
"""

from __future__ import annotations

import asyncio
import sys

from slate.core.eval import DummyJudge, EvalReport, LLMJudge, golden_cases, run_eval
from slate.infrastructure.llm.dummy import DummyLLMClient


def _print_report(report: EvalReport) -> None:
    print("\nLLM eval report")
    print("=" * 60)
    for r in report.results:
        flag = "PASS" if r.passed else "FAIL"
        judge = "-" if r.judge_score is None else f"{r.judge_score:.2f}"
        checks = ", ".join(f"{c.name}={c.score:.2f}" for c in r.checks) or "(none)"
        print(f"[{flag}] {r.case_id:<22} score={r.score:.3f} judge={judge}  {checks}")
    print("-" * 60)
    for task, score in sorted(report.scores_by_task().items()):
        print(f"  {task:<10} mean={score:.3f}")
    print(f"\nOverall score={report.overall_score:.3f}  pass-rate={report.pass_rate:.0%}\n")


async def _main(real: bool, strict: bool) -> int:
    if real:
        from slate.config import settings
        from slate.infrastructure.llm.factory import get_llm_client

        llm = get_llm_client(settings)
        report = await run_eval(llm, golden_cases(), LLMJudge(llm))
    else:
        llm = DummyLLMClient()
        report = await run_eval(llm, golden_cases(), DummyJudge())

    _print_report(report)
    if strict and report.pass_rate < 1.0:
        print("Strict mode: one or more cases failed their deterministic checks.")
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(_main("--real" in sys.argv, "--strict" in sys.argv))
    raise SystemExit(exit_code)
