"""Golden dataset for the eval harness.

A small, curated set of cases per LLM task. Inputs are crafted so the scores are
**deterministic under ``DummyLLMClient``** (CI) while remaining meaningful against
a real model — the same cases score quality, not plumbing, when run with Ollama.
Keep this list small and reviewed; it is the contract the CI gate diffs against.
"""

from __future__ import annotations

from slate.core.eval.schema import EvalCase


def golden_cases() -> list[EvalCase]:
    """Return the curated golden cases (the set the CI baseline tracks)."""
    return [
        EvalCase(
            id="recap-with-context",
            task="recap",
            inputs={
                "game_title": "Hollow Knight",
                "previous_wrap_ups": [
                    {
                        "next_action": "reach Greenpath and find the Hornet arena",
                        "location": "Forgotten Crossroads near the Stagway",
                    }
                ],
                "current_next_action": "reach Greenpath",
            },
            reference={
                "context": (
                    "Hollow Knight reach Greenpath and find the Hornet arena "
                    "Forgotten Crossroads near the Stagway"
                ),
                "forbidden": ["final boss", "ending"],
            },
            checks=["non_empty", "grounding", "spoiler_free"],
        ),
        EvalCase(
            id="recap-first-session",
            task="recap",
            inputs={"game_title": "Celeste", "previous_wrap_ups": []},
            reference={"forbidden": ["Badeline", "summit ending"]},
            checks=["non_empty", "spoiler_free"],
        ),
        EvalCase(
            id="wrap-up-extract",
            task="wrap_up",
            inputs={
                "game_title": "Elden Ring",
                "wrap_up_text": "Beat Margit and reached Stormveil Castle, on to Godrick.",
            },
            reference={},
            checks=["json_valid"],
        ),
        EvalCase(
            id="capture-two-games",
            task="capture",
            inputs={"text": "got Hollow Knight and Hades on the Switch"},
            reference={"expected_titles": ["Hollow Knight", "Hades"]},
            checks=["json_valid"],
        ),
        EvalCase(
            id="pick-valid",
            task="pick",
            inputs={
                "candidates": [
                    {"public_id": "11111111-1111-4111-8111-111111111111", "game_title": "Hades"},
                    {"public_id": "22222222-2222-4222-8222-222222222222", "game_title": "Celeste"},
                ],
                "mood": "chill",
                "available_minutes": 30,
                "mental_energy": "low",
            },
            reference={
                "candidate_ids": [
                    "11111111-1111-4111-8111-111111111111",
                    "22222222-2222-4222-8222-222222222222",
                ]
            },
            checks=["json_valid", "uuid_in_candidates"],
        ),
    ]
