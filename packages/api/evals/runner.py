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
from uuid import uuid4

from evals.checks import run_checks
from evals.judge import AbstractJudge, DummyJudge
from evals.schema import CaseResult, EvalCase, EvalReport
from slate.infrastructure.agent.base import AbstractRecapAgent, DeepRecapRequest
from slate.infrastructure.agent.graph.state import PlaySessionContext
from slate.infrastructure.llm.base import AbstractLLMClient


async def produce_output(
    llm: AbstractLLMClient,
    case: EvalCase,
    agent: AbstractRecapAgent | None = None,
) -> str:
    """Run *case*'s task through the LLM (or the deep-recap *agent*) and return text."""
    inputs = case.inputs
    task = case.task

    if task == "recap":
        return await llm.generate_recap(
            game_title=cast(str, inputs["game_title"]),
            previous_wrap_ups=cast("list[dict[str, object]]", inputs.get("previous_wrap_ups", [])),
            current_next_action=cast("str | None", inputs.get("current_next_action")),
        )

    if task == "deep_recap":
        # Exercises the LangGraph deep-research graph (search → grade → refine →
        # synthesize → spoiler-aware → anti-hallucination), not the quick path.
        if agent is None:
            raise ValueError("deep_recap task requires a recap agent")
        context: PlaySessionContext = {
            "game_title": cast(str, inputs["game_title"]),
            "previous_wrap_ups": cast(
                "list[dict[str, object]]", inputs.get("previous_wrap_ups", [])
            ),
            "location": cast("str | None", inputs.get("location")),
            "current_quest": cast("str | None", inputs.get("current_quest")),
            "next_action": cast("str | None", inputs.get("current_next_action")),
            "level": cast("str | None", inputs.get("level")),
        }
        result = await agent.deep_recap(
            DeepRecapRequest(context=context, thread_id=uuid4().hex, force_refresh=True)
        )
        return result.text

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


async def run_case(
    llm: AbstractLLMClient,
    case: EvalCase,
    judge: AbstractJudge,
    agent: AbstractRecapAgent | None = None,
) -> CaseResult:
    """Produce, check, and (optionally) judge a single case."""
    output = await produce_output(llm, case, agent)
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
    agent: AbstractRecapAgent | None = None,
) -> EvalReport:
    """Run every case and aggregate into an ``EvalReport``.

    *judge* defaults to a ``DummyJudge`` (deterministic, model-free); *agent* is
    the deep-recap agent (required only when the set has ``deep_recap`` cases).
    """
    active_judge = judge or DummyJudge()
    results = [await run_case(llm, case, active_judge, agent) for case in cases]
    return EvalReport(results=results)
