"""Eval runner: drive each golden case through the LLM port, then score it.

``produce_output`` dispatches a case to the matching ``AbstractLLMClient`` call
and normalises the result to a string (raw text for recaps, JSON for structured
tasks). ``run_eval`` then applies the deterministic checks and the optional
judge, returning an ``EvalReport``.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import cast

from slate.core.eval.checks import run_checks
from slate.core.eval.judge import AbstractJudge, DummyJudge
from slate.core.eval.schema import CaseResult, EvalCase, EvalReport
from slate.infrastructure.llm.base import AbstractLLMClient


async def produce_output(llm: AbstractLLMClient, case: EvalCase) -> str:
    """Run *case*'s task through *llm* and return the output as a string."""
    inputs = case.inputs
    task = case.task

    if task == "recap":
        return await llm.generate_recap(
            game_title=cast(str, inputs["game_title"]),
            previous_wrap_ups=cast("list[dict[str, object]]", inputs.get("previous_wrap_ups", [])),
            current_next_action=cast("str | None", inputs.get("current_next_action")),
        )

    if task == "wrap_up":
        state = await llm.extract_wrap_up_state(
            game_title=cast(str, inputs["game_title"]),
            wrap_up_text=cast(str, inputs["wrap_up_text"]),
        )
        return json.dumps(asdict(state))

    if task == "capture":
        games = await llm.parse_capture_text(cast(str, inputs["text"]))
        return json.dumps([g.title for g in games])

    if task == "pick":
        selection = await llm.select_game(
            candidates=cast("list[dict[str, object]]", inputs["candidates"]),
            mood=cast(str, inputs["mood"]),
            available_minutes=cast(int, inputs["available_minutes"]),
            mental_energy=cast(str, inputs["mental_energy"]),
            context=cast("str | None", inputs.get("context")),
        )
        return json.dumps(
            {
                "library_entry_public_id": selection.library_entry_public_id,
                "reasoning": selection.reasoning,
            }
        )

    raise ValueError(f"unknown eval task: {task!r}")


async def run_case(llm: AbstractLLMClient, case: EvalCase, judge: AbstractJudge) -> CaseResult:
    """Produce, check, and (optionally) judge a single case."""
    output = await produce_output(llm, case)
    checks = run_checks(output, case)

    judge_score: float | None = None
    judge_reason = ""
    if case.judge:
        judge_score, judge_reason = await judge.score(case, output)

    return CaseResult(
        case_id=case.id,
        task=case.task,
        output=output,
        checks=checks,
        judge_score=judge_score,
        judge_reason=judge_reason,
    )


async def run_eval(
    llm: AbstractLLMClient,
    cases: list[EvalCase],
    judge: AbstractJudge | None = None,
) -> EvalReport:
    """Run every case and aggregate into an ``EvalReport``.

    *judge* defaults to a ``DummyJudge`` (deterministic, model-free) so the
    harness is usable in CI without a real model.
    """
    active_judge = judge or DummyJudge()
    results = [await run_case(llm, case, active_judge) for case in cases]
    return EvalReport(results=results)
