"""Run the LLM evaluation harness and print a report.

Defaults to the deterministic ``DummyLLMClient`` + ``DummyJudge`` + ``DummyRecapAgent``
— offline and CI-safe. Pass ``--real`` to evaluate the configured provider
(``LLM_PROVIDER`` / ``AGENT_PROVIDER``) with the model-graded ``LLMJudge`` and the
real deep-recap agent.

The real quality gate is ``--real --gate`` (wired into ``make quality`` as
``make api-eval-gate``): the heavy, meaningful regression check runs **locally**
before push/PR because the judge needs Ollama and is non-deterministic. Hosted CI
keeps only the cheap deterministic redundancy — the dummy golden-pipeline test and
harness unit tests in ``api-test`` — so a structural break still fails the PR
without spending real-model CI minutes.

The judge defaults to ``qwen2.5:14b-instruct`` — a different, instruction-tuned
model at least as large as the generator, so it can't grade itself leniently. An
A/B vs ``qwen3:8b`` picked it: the thinking model's reasoning overruns the output
budget before it emits the verdict JSON (empty, unparsable scores), while the
instruct model returns a calibrated 0.5-1.0 range. Override with ``JUDGE_MODEL``.

Every run writes its scores to results/latest.json. Use that to commit the run
you actually inspected, instead of re-rolling a fresh one:

    --promote  copy results/latest.json → baseline.json (NO eval, NO model)
    --save     run, then write the current run's scores to baseline.json
    --gate     re-run and FAIL (exit 1) if any metric dropped vs the baseline
    --tolerance N   allowed drop before --gate fails (default 0.05)
    --strict   exit 1 if any case fails its deterministic checks (total-failure guard)
    --calibrate     grade the frozen human-labelled set and report judge↔human kappa
    --retrieval     A/B recall@k of recent vs semantic recap retrieval (Epic 24)
    --no-cache      force the gate even if no eval-relevant file changed since last pass

The gate is content-cached: if nothing that can move a recap score changed since it
last passed (prompts, LLM client, agent graph, recap service, models, the harness),
it is skipped — so a web/auth/docs-only push pays no Ollama cost and needs no SSD.

Usage:
    poetry run python scripts/run_eval.py --real            # run + inspect
    poetry run python scripts/run_eval.py --promote         # commit THAT run as baseline
    poetry run python scripts/run_eval.py --real --gate     # block a regression
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
from evals.calibration import (
    BUCKET_NAMES,
    N_CLASSES,
    bucket,
    calibration_cases,
    interpret_kappa,
    quadratic_weighted_kappa,
)
from evals.gate import baseline_from_report, diff_baseline
from evals.gate_cache import is_cached_pass, record_pass
from evals.retrieval import RetrievalReport, evaluate_retrieval
from slate.infrastructure.agent.dummy import DummyRecapAgent
from slate.infrastructure.llm.dummy import DummyLLMClient

_RESULTS = Path(__file__).resolve().parent.parent / "evals" / "results"
_BASELINE = _RESULTS / "baseline.json"  # committed contract the gate defends
_LATEST = _RESULTS / "latest.json"  # the most recent run (gitignored, transient)


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

        # Self-eval guard: judge on a DIFFERENT model than the one being graded so
        # the judge can't favour its own output. Defaults to the A/B-winning instruct
        # model (qwen2.5:14b-instruct); JUDGE_MODEL overrides. Instruct > thinking
        # here: a thinking judge truncates its verdict before emitting the score.
        judge_settings = settings.model_copy(update={"ollama_smart_model": _judge_model()})
        return await run_eval(llm, golden_cases(), LLMJudge(get_llm_client(judge_settings)), agent)

    return await run_eval(DummyLLMClient(), golden_cases(), DummyJudge(), DummyRecapAgent())


def _judge_model() -> str:
    """The judge model: JUDGE_MODEL if set, else the A/B-winning instruct default."""
    return os.getenv("JUDGE_MODEL", "qwen2.5:14b-instruct")


def _required_models() -> set[str]:
    """Ollama models a --real / --calibrate run must be able to load."""
    from slate.config import settings

    return {settings.ollama_fast_model, settings.ollama_smart_model, _judge_model()}


def _available_models() -> set[str] | None:
    """Model names Ollama can serve now, or None if the daemon can't be reached.

    The models live on an external SSD; when it's disconnected Ollama's blobs
    vanish and ``/api/tags`` stops listing them — so a 'missing' required model
    here is really the SSD-not-connected signal, not a config error.
    """
    import httpx

    from slate.config import settings

    try:
        resp = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=5.0)
        resp.raise_for_status()
        return {m.get("name", "") for m in resp.json().get("models", [])}
    except Exception:
        return None


def _models_status() -> tuple[bool, str]:
    """(ok, detail): whether the required Ollama models are loadable right now."""
    available = _available_models()
    if available is None:
        return False, "Ollama is unreachable — daemon down or external model SSD not connected?"
    missing = sorted(m for m in _required_models() if m and m not in available)
    if missing:
        return False, f"Ollama is missing models {missing} — external model SSD not connected?"
    return True, ""


async def _calibrate() -> int:
    """Grade the frozen, human-labelled set with the judge and report agreement.

    Calibration always needs a real judge (a dummy verdict has nothing to agree
    with), so this ignores --real and builds the LLM judge directly.
    """
    from slate.config import settings
    from slate.infrastructure.llm.factory import get_llm_client

    model = _judge_model()
    judge_settings = settings.model_copy(update={"ollama_smart_model": model})
    judge = LLMJudge(get_llm_client(judge_settings))
    rows = []
    for case in calibration_cases():
        score, reason = await judge.score(case.to_eval_case(), case.output)
        rows.append((case, score, reason))
    _print_calibration(rows, model)
    return 0


def _print_calibration(rows: list[tuple[object, float, str]], model: str) -> None:
    human_b = [bucket(c.human_score) for c, _, _ in rows]  # type: ignore[attr-defined]
    judge_b = [bucket(s) for _, s, _ in rows]
    kappa = quadratic_weighted_kappa(human_b, judge_b, N_CLASSES)
    exact = sum(1 for h, j in zip(human_b, judge_b, strict=True) if h == j)

    print(f"\nJudge calibration  (judge model: {model})")
    print("=" * 72)
    print(f"{'case':<28}{'human':>13}{'judge':>13}  agree")
    print("-" * 72)
    for (case, score, reason), h, j in zip(rows, human_b, judge_b, strict=True):
        mark = "ok" if h == j else ("~" if abs(h - j) == 1 else "XX")
        human = f"{case.human_score:.2f} {BUCKET_NAMES[h]}"  # type: ignore[attr-defined]
        judge = f"{score:.2f} {BUCKET_NAMES[j]}"
        print(f"{case.id:<28}{human:>13}{judge:>13}  {mark}")  # type: ignore[attr-defined]
        if h != j:
            print(f"        ↳ judge: {reason}")
    print("-" * 72)
    # Confusion matrix: rows = human bucket, cols = judge bucket.
    matrix = [[0] * N_CLASSES for _ in range(N_CLASSES)]
    for h, j in zip(human_b, judge_b, strict=True):
        matrix[h][j] += 1
    print("confusion (row=human, col=judge):  " + "  ".join(f"{n:>4}" for n in BUCKET_NAMES))
    for i, name in enumerate(BUCKET_NAMES):
        cells = "  ".join(f"{matrix[i][k]:>4}" for k in range(N_CLASSES))
        print(f"  {name:<6}                          {cells}")
    print("-" * 72)
    n = len(rows)
    print(f"exact-bucket agreement: {exact}/{n} ({exact / n:.0%})")
    print(f"quadratic-weighted kappa: {kappa:.3f}  — {interpret_kappa(kappa)}\n")


async def _retrieval_ab() -> int:
    """Retrieval A/B: recall@k of recent vs semantic over the buried-context cases.

    Deterministic on the DummyEmbeddingClient by default (offline/CI-safe); --real
    uses the configured embedding provider (needs the embedding model in Ollama).
    """
    if "--real" in sys.argv:
        from slate.config import settings
        from slate.infrastructure.embedding.factory import get_embedding_client

        client = get_embedding_client(settings)
    else:
        from slate.infrastructure.embedding.dummy import DummyEmbeddingClient

        client = DummyEmbeddingClient()
    _print_retrieval(await evaluate_retrieval(client))
    return 0


def _print_retrieval(report: RetrievalReport) -> None:
    print("\nRetrieval A/B  (recall@k: recent vs semantic)")
    print("=" * 60)
    for row in report.rows:
        recent, semantic = float(row["recent"]), float(row["semantic"])
        mark = "win" if semantic > recent else ("--" if semantic == recent else "REGRESS")
        print(f"  {row['id']!s:<22} recent={recent:.2f}  semantic={semantic:.2f}  {mark}")
    print("-" * 60)
    print(f"  mean recent   recall = {report.recent_recall:.3f}")
    print(f"  mean semantic recall = {report.semantic_recall:.3f}")
    print(f"  delta (semantic - recent) = {report.delta:+.3f}\n")


def _rel(path: Path) -> str:
    return str(path.relative_to(path.parents[2]))


def _promote() -> int:
    """Copy the last run (results/latest.json) to the baseline — no eval, no model."""
    if not _LATEST.exists():
        print("Promote: no run to promote yet — run the eval first.")
        return 1
    _BASELINE.write_text(_LATEST.read_text())
    print(f"Promoted last run → {_rel(_BASELINE)}")
    return 0


def _preflight_or_exit() -> int | None:
    """Model preflight for --real/--calibrate. Returns an exit code, or None to go on.

    The Ollama models live on an external SSD. When it's gone, fail hard in the push
    gate (SLATE_EVAL_STRICT, set by `make quality`) but only warn-and-skip for a
    manual run — a disconnected SSD must not masquerade as a quality regression.
    """
    if "--real" not in sys.argv and "--calibrate" not in sys.argv:
        return None
    ok, detail = _models_status()
    if ok:
        return None
    if os.getenv("SLATE_EVAL_STRICT"):
        print(f"\033[31m✗ Eval gate FAILED\033[0m — {detail}")
        return 1
    print(f"\033[33m⚠  Eval skipped\033[0m — {detail}")
    return 0


def _gate(report: EvalReport) -> int:
    """Diff the run against the committed baseline; record a pass for the cache."""
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
    record_pass()  # remember this content passed, so an unchanged push skips the gate
    return 0


async def _main() -> int:
    if "--promote" in sys.argv:
        return _promote()

    if "--retrieval" in sys.argv:
        return await _retrieval_ab()

    # Cache: skip the slow real gate when nothing that can change a recap score has
    # changed since it last passed. A push touching only web/auth/docs can't regress
    # quality, so it shouldn't pay the Ollama cost — or need the model SSD connected.
    # (--no-cache forces a fresh run.) Runs before the model preflight on purpose.
    if "--gate" in sys.argv and "--no-cache" not in sys.argv and is_cached_pass():
        print("Eval gate: no eval-relevant changes since last pass — skipping (cached).")
        return 0

    preflight = _preflight_or_exit()
    if preflight is not None:
        return preflight

    if "--calibrate" in sys.argv:
        return await _calibrate()

    report = await _run()
    _print_report(report)

    # Persist every run so it can be promoted to baseline later WITHOUT re-running
    # (recaps are regenerated each run, so --save would otherwise snapshot a fresh,
    # different run than the one you just inspected).
    _RESULTS.mkdir(parents=True, exist_ok=True)
    _LATEST.write_text(json.dumps(baseline_from_report(report), indent=2) + "\n")

    if "--save" in sys.argv:
        _BASELINE.write_text(_LATEST.read_text())
        print(f"Saved baseline → {_rel(_BASELINE)}")

    if "--gate" in sys.argv:
        code = _gate(report)
        if code != 0:
            return code

    if "--strict" in sys.argv and report.pass_rate < 1.0:
        print("Strict mode: one or more cases failed their deterministic checks.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
