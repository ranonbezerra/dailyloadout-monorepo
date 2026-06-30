"""LLM-as-judge for the eval harness.

The judge scores qualities the deterministic checks can't — faithfulness,
helpfulness, tone — on a ``[0, 1]`` scale. ``LLMJudge`` renders a rubric and
calls the existing ``AbstractLLMClient`` (the ``smart`` role); ``DummyJudge``
returns a fixed score so CI is deterministic and model-free.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from slate.core.eval.schema import EvalCase
from slate.infrastructure.llm.base import AbstractLLMClient

# Per-task rubric: what "good" means for the judge to grade against.
_RUBRICS: dict[str, str] = {
    "recap": (
        "A good recap faithfully summarises where the player left off using ONLY "
        "their notes, suggests a concrete next step, and never reveals unseen "
        "spoilers. Penalise invented facts and spoilers heavily."
    ),
    "wrap_up": "Good extraction captures location, next action, level, and quest accurately.",
    "capture": "Good extraction lists exactly the game titles present in the input, no extras.",
    "pick": "A good pick is justified by the player's mood/time/energy and the game's fit.",
}


class AbstractJudge(ABC):
    """Scores an output for an ``EvalCase`` on ``[0, 1]`` with a short reason."""

    @abstractmethod
    async def score(self, case: EvalCase, output: str) -> tuple[float, str]:
        """Return ``(score in [0, 1], reason)``."""
        ...


def _clamp(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


class LLMJudge(AbstractJudge):
    """Model-graded judge backed by the project's LLM port."""

    def __init__(self, llm: AbstractLLMClient) -> None:
        self._llm = llm

    def _build_prompt(self, case: EvalCase, output: str) -> str:
        rubric = _RUBRICS.get(case.task, "Grade the output for correctness and helpfulness.")
        reference = json.dumps(case.reference, default=str, ensure_ascii=False)
        return (
            "You are a strict evaluator scoring an AI assistant's output.\n"
            f"Task: {case.task}\n"
            f"Rubric: {rubric}\n"
            f"Reference/context (JSON): {reference}\n"
            f"Output to grade:\n{output}\n\n"
            'Respond with ONLY JSON: {"score": <float 0..1>, "reason": "<one sentence>"}.'
        )

    async def score(self, case: EvalCase, output: str) -> tuple[float, str]:
        try:
            raw = await self._llm.complete(
                self._build_prompt(case, output), role="smart", json=True
            )
            parsed = json.loads(raw)
            return _clamp(parsed.get("score")), str(parsed.get("reason", ""))
        except Exception as exc:
            return 0.0, f"judge error: {exc}"


class DummyJudge(AbstractJudge):
    """Deterministic judge for CI: returns *fixed_score* with no model call."""

    def __init__(self, fixed_score: float = 1.0) -> None:
        self._fixed = _clamp(fixed_score)

    async def score(self, case: EvalCase, output: str) -> tuple[float, str]:
        return self._fixed, "dummy"
