"""Run the LLM evaluation harness and print a report.

Defaults to the deterministic ``DummyLLMClient`` + ``DummyJudge`` + ``DummyRecapAgent``
— offline and CI-safe. Pass ``--real`` to evaluate the configured provider
(``LLM_PROVIDER`` / ``AGENT_PROVIDER``) with the model-graded ``LLMJudge`` and the
real deep-recap agent.

Set ``JUDGE_MODEL`` (e.g. ``qwen3:8b``) to judge on a different model than the one
being graded — avoids the self-evaluation leniency of a model scoring itself.

Quality gate (against a committed baseline):
    --save     write the current aggregate scores to results/baseline.json
    --gate     re-run and FAIL (exit 1) if any metric dropped vs the baseline
    --tolerance N   allowed drop before --gate fails (default 0.05)
    --strict   exit 1 if any case fails its deterministic checks (total-failure guard)

Usage:
    poetry run python scripts/run_eval.py --real --save      # snapshot a baseline
    poetry run python scripts/run_eval.py --real --gate      # block a regression
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Make the package-local ``evals`` harness importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals import DummyJudge, EvalReport, LLMJudge, golden_cases, run_eval
from evals.gate import baseline_from_report, diff_baseline
from slate.infrastructure.agent.dummy import DummyRecapAgent
from slate.infrastructure.llm.dummy import DummyLLMClient

_BASELINE = Path(__file__).resolve().parent.parent / "evals" / "results" / "baseline.json"


def _print_report(report: EvalReport) -> None:
    print("\nLLM eval report")
    print("=" * 60)
    for r in report.results:
        flag = "PASS" if r.passed else "FAIL"
        judge = "-" if r.judge_score is None else f"{r.judge_score:.2f}"
        checks = ", ".join(f"{c.name}={c.score:.2f}" for c in r.checks) or "(none)"
        print(f"[{flag}] {r.case_id:<34} score={r.score:.3f} judge={judge}  {checks}")
        # Diagnostics: the judge's reason (why that score) + the detail of any
        # deterministic check that did NOT pass (missing tokens / leaked spoilers).
        if r.judge_reason and r.judge_reason != "dummy":
            print(f"        ↳ judge: {r.judge_reason}")
        for c in r.checks:
            if not c.passed and c.detail:
                print(f"        ↳ {c.name}: {c.detail}")
    print("-" * 60)
    for task, score in sorted(report.scores_by_task().items()):
        print(f"  {task:<12} mean={score:.3f}")
    print(f"\nOverall score={report.overall_score:.3f}  pass-rate={report.pass_rate:.0%}\n")


def _arg_value(name: str, default: float) -> float:
    if name in sys.argv:
        try:
            return float(sys.argv[sys.argv.index(name) + 1])
        except (IndexError, ValueError):
            pass
    return default


async def _run() -> EvalReport:
    if "--real" in sys.argv:
        from slate.config import settings
        from slate.infrastructure.agent.factory import get_recap_agent
        from slate.infrastructure.llm.factory import get_llm_client
        from slate.infrastructure.llm.traced import TracedLLMClient

        base = get_llm_client(settings)
        llm = TracedLLMClient(base) if settings.tracing_enabled else base
        agent = get_recap_agent(settings, base)

        # Self-eval guard: judge on a DIFFERENT model than the one being graded
        # (set JUDGE_MODEL, e.g. qwen3:8b) so the judge can't favour its own output.
        judge_model = os.getenv("JUDGE_MODEL")
        if judge_model:
            judge_llm = get_llm_client(
                settings.model_copy(update={"ollama_smart_model": judge_model})
            )
        else:
            judge_llm = base
        return await run_eval(llm, golden_cases(), LLMJudge(judge_llm), agent)

    return await run_eval(DummyLLMClient(), golden_cases(), DummyJudge(), DummyRecapAgent())


async def _main() -> int:
    report = await _run()
    _print_report(report)

    if "--save" in sys.argv:
        _BASELINE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE.write_text(json.dumps(baseline_from_report(report), indent=2) + "\n")
        print(f"Saved baseline → {_BASELINE.relative_to(_BASELINE.parents[2])}")

    if "--gate" in sys.argv:
        if not _BASELINE.exists():
            print("Gate: no baseline yet — run with --save first.")
            return 1
        baseline = json.loads(_BASELINE.read_text())
        regressions = diff_baseline(report, baseline, _arg_value("--tolerance", 0.05))
        if regressions:
            print("Gate FAILED — metrics regressed vs baseline:")
            for line in regressions:
                print(f"  ✗ {line}")
            return 1
        print("Gate passed — no metric regressed vs baseline.")

    if "--strict" in sys.argv and report.pass_rate < 1.0:
        print("Strict mode: one or more cases failed their deterministic checks.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
