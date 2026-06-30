"""LLM-as-judge for the eval harness.

The judge scores qualities the deterministic checks can't — faithfulness,
helpfulness, tone — on a ``[0, 1]`` scale. ``LLMJudge`` renders a rubric and
calls the existing ``AbstractLLMClient`` (the ``smart`` role); ``DummyJudge``
returns a fixed score so CI is deterministic and model-free.

The judge runs in **free-text** mode (no forced JSON) so reasoning models can
think before answering — forcing ``format=json`` cuts their reasoning short and
yields snap, unreliable verdicts. The ``{score, reason}`` object is then extracted
from the reply (tolerating ``<think>`` blocks, fences, and surrounding prose), so
any judge model works: thinking (qwen3) or instruction-tuned (qwen2.5).
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from evals.schema import EvalCase
from slate.infrastructure.llm.base import AbstractLLMClient

# Per-task rubric: what "good" means for the judge to grade against.
_RUBRICS: dict[str, str] = {
    "recap": (
        "Grade a video-game session recap ('previously on...'). It may rely ONLY on "
        "the player's notes (reference.context). Score high when it faithfully "
        "summarises where they left off, suggests a concrete next step grounded in "
        "the notes, and keeps a neutral, blame-free tone (no 'you haven't played in "
        "X days', no streaks). HARD RULE: any named entity (place, boss, item, "
        "character) NOT present in the notes — or any beat from unplayed content — "
        "is a hallucination/spoiler and caps the score low, however well-written. "
        "Follow the expected behavior given for the case."
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


# A flat JSON object that carries a "score" key (the verdict). Tolerates anything
# around it — reasoning, <think> blocks, markdown fences.
_VERDICT_RE = re.compile(r'\{[^{}]*"score"[^{}]*\}', re.DOTALL)


def _extract_verdict(raw: str) -> tuple[float, str]:
    """Pull ``(score, reason)`` from a free-text judge reply.

    Scans for the LAST JSON object containing a ``score`` key — the verdict usually
    follows any reasoning. Falls back to a bare ``score: <0..1>`` number, then to a
    clearly-labelled failure (so a parse miss is never silently a 0.0 verdict).
    """
    for block in reversed(_VERDICT_RE.findall(raw)):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "score" in data:
            return _clamp(data.get("score")), str(data.get("reason", ""))
    bare = re.search(r"score\b[^0-9]*([01](?:\.\d+)?)", raw, re.IGNORECASE)
    if bare:
        return _clamp(bare.group(1)), raw.strip()[:200]
    return 0.0, f"unparseable judge output: {raw.strip()[:120]}"


class LLMJudge(AbstractJudge):
    """Model-graded judge backed by the project's LLM port."""

    def __init__(self, llm: AbstractLLMClient) -> None:
        self._llm = llm

    def _build_prompt(self, case: EvalCase, output: str) -> str:
        rubric = _RUBRICS.get(case.task, "Grade the output for correctness and helpfulness.")
        # Only the grounding context + expected behavior — NOT the answer key
        # (mentions/forbidden). Showing the must-mention list would let the judge
        # reward shallow keyword presence; showing the spoiler list leaks it.
        notes = str(case.reference.get("context") or "")
        behavior = str(case.reference.get("behavior") or "")
        return (
            "You are a strict evaluator scoring an AI assistant's output.\n"
            f"Task: {case.task}\n"
            f"Rubric: {rubric}\n"
            f"Player's notes (the ONLY source of truth): {notes}\n"
            f"Expected behavior for this case: {behavior}\n"
            f"Output to grade:\n{output}\n\n"
            "Reason briefly if you need to, then END with a single JSON object on "
            'its own line: {"score": <float 0..1>, "reason": "<one sentence>"}.'
        )

    async def score(self, case: EvalCase, output: str) -> tuple[float, str]:
        # Free-text (no json=True): let reasoning models think, then extract the
        # verdict from the reply. Forcing JSON suppresses the reasoning that makes
        # a judge accurate.
        try:
            raw = await self._llm.complete(self._build_prompt(case, output), role="smart")
            return _extract_verdict(raw)
        except Exception as exc:
            return 0.0, f"judge error: {exc}"


class DummyJudge(AbstractJudge):
    """Deterministic judge for CI: returns *fixed_score* with no model call."""

    def __init__(self, fixed_score: float = 1.0) -> None:
        self._fixed = _clamp(fixed_score)

    async def score(self, case: EvalCase, output: str) -> tuple[float, str]:
        return self._fixed, "dummy"
