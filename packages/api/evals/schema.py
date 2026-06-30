"""Data model for the LLM evaluation harness.

A golden ``EvalCase`` declares an input for one LLM task and the deterministic
checks (and optional model-graded judge) to apply to the output. Running a case
yields a ``CaseResult``; a run yields an ``EvalReport`` with per-task and overall
means that a CI gate can diff against a committed baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The LLM tasks the harness can evaluate (each maps to an AbstractLLMClient call).
EvalTask = str  # "recap" | "capture" | "pick" | "wrap_up"


@dataclass
class EvalCase:
    """One golden case: an input for *task* plus how to score the output."""

    id: str
    task: EvalTask
    inputs: dict[str, object]
    # Ground-truth fragments a deterministic check can compare against (e.g. the
    # context text for grounding, or the candidate ids for a pick).
    reference: dict[str, object] = field(default_factory=dict)
    # Names of deterministic checks to run (see ``checks.REGISTRY``).
    checks: list[str] = field(default_factory=list)
    # Run the LLM-as-judge rubric on the output?
    judge: bool = True


@dataclass
class CheckResult:
    """Outcome of one deterministic check (score in ``[0, 1]``)."""

    name: str
    passed: bool
    score: float
    detail: str = ""


@dataclass
class CaseResult:
    """The scored result of running one ``EvalCase``."""

    case_id: str
    task: EvalTask
    output: str
    checks: list[CheckResult]
    judge_score: float | None = None
    judge_reason: str = ""

    @property
    def deterministic_score(self) -> float:
        """Mean of the deterministic check scores (1.0 when there are none)."""
        if not self.checks:
            return 1.0
        return sum(c.score for c in self.checks) / len(self.checks)

    @property
    def passed(self) -> bool:
        """True when every deterministic check passed (the judge is advisory)."""
        return all(c.passed for c in self.checks)

    @property
    def score(self) -> float:
        """Overall case score: deterministic mean, blended with the judge if present."""
        if self.judge_score is None:
            return self.deterministic_score
        return (self.deterministic_score + self.judge_score) / 2


@dataclass
class EvalReport:
    """Aggregate of a harness run."""

    results: list[CaseResult]

    @property
    def overall_score(self) -> float:
        if not self.results:
            return 1.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 1.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    def scores_by_task(self) -> dict[str, float]:
        """Mean score per task, for the CI baseline diff."""
        by_task: dict[str, list[float]] = {}
        for r in self.results:
            by_task.setdefault(r.task, []).append(r.score)
        return {task: sum(s) / len(s) for task, s in by_task.items()}

    def scores_by_check(self) -> dict[str, float]:
        """Mean score per deterministic check (spoiler_free, grounding, …).

        This is what the gate watches most closely: the deterministic checks are
        stable across runs (unlike the judge), so a drop here is a real regression.
        """
        by_check: dict[str, list[float]] = {}
        for r in self.results:
            for c in r.checks:
                by_check.setdefault(c.name, []).append(c.score)
        return {name: sum(s) / len(s) for name, s in by_check.items()}
