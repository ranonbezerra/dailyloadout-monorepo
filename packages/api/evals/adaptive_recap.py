"""Adaptive-RAG A/B: does relevance-gated routing beat always-quick and always-deep? (Epic 29)

The adaptive router (Epic 29) picks the cheap local-RAG recap when the player's retrieved
history is rich enough to ground it, and escalates to the expensive web-research recap when
it's thin. This measures that choice against the two fixed policies:

- **always-quick** under-grounds the sparse cases (no web to fill the gap).
- **always-deep** grounds everything but pays the deep cost on every recap.

The adaptive router should match always-deep's grounding while paying deep only on the
sparse cases — a faithfulness win over always-quick and a cost win over always-deep.

Deterministic and model-free: the evaluator's verdict is a token-count over stand-in
sessions, so the A/B runs offline with no LLM or DB, exactly like the rerank/retrieval A/Bs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import cast

from slate.config import Settings
from slate.core.play_session.adaptive import (
    RecapPath,
    evaluate_local_relevance,
    route_recap,
)

# Grounding quality of each path on a case, by whether local history is sufficient.
# quick grounds a rich case fully but under-grounds a sparse one; deep grounds both.
_QUICK_GROUNDING_RICH = 1.0
_QUICK_GROUNDING_SPARSE = 0.4
_DEEP_GROUNDING = 1.0
# Relative cost: the deep path fires ~4 LLM calls + web research vs one for quick.
_QUICK_COST = 1.0
_DEEP_COST = 5.0


@dataclass(frozen=True)
class AdaptiveCase:
    """Retrieved-history scenario + the path that best serves it."""

    id: str
    # (wrap_up_text, extracted_state) per retrieved session.
    sessions: tuple[tuple[str, dict[str, object] | None], ...]
    ideal_path: RecapPath  # "quick" when local is sufficient, "deep" when it isn't


@dataclass
class AdaptiveReport:
    rows: list[dict[str, object]] = field(default_factory=list)

    @property
    def router_accuracy(self) -> float:
        return _mean([float(r["chosen"] == r["ideal"]) for r in self.rows])

    @property
    def adaptive_grounding(self) -> float:
        return _mean([cast(float, r["adaptive_grounding"]) for r in self.rows])

    @property
    def always_quick_grounding(self) -> float:
        return _mean([cast(float, r["quick_grounding"]) for r in self.rows])

    @property
    def always_deep_grounding(self) -> float:
        return _mean([cast(float, r["deep_grounding"]) for r in self.rows])

    @property
    def adaptive_cost(self) -> float:
        return sum(cast(float, r["adaptive_cost"]) for r in self.rows)

    @property
    def always_quick_cost(self) -> float:
        return _QUICK_COST * len(self.rows)

    @property
    def always_deep_cost(self) -> float:
        return _DEEP_COST * len(self.rows)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _grounding(path: RecapPath, ideal: RecapPath) -> float:
    """How well *path* grounds a case whose ideal path is *ideal*."""
    if path == "deep":
        return _DEEP_GROUNDING
    return _QUICK_GROUNDING_RICH if ideal == "quick" else _QUICK_GROUNDING_SPARSE


def _cost(path: RecapPath) -> float:
    return _DEEP_COST if path == "deep" else _QUICK_COST


def adaptive_cases() -> list[AdaptiveCase]:
    """Cases spanning rich (quick is enough) and thin (escalate) local histories."""
    return [
        # Rich: two sessions dense with proper nouns → the local recap grounds fine.
        AdaptiveCase(
            id="rich_two_sessions",
            sessions=(
                (
                    "Cleared Stormveil Castle and beat Godrick the Grafted",
                    {"location": "Limgrave"},
                ),
                ("Explored Liurnia, found Rennala at Raya Lucaria Academy", {"level": "42"}),
            ),
            ideal_path="quick",
        ),
        # Rich: single very dense session still clears the bar.
        AdaptiveCase(
            id="rich_dense_pair",
            sessions=(
                ("Konpeki Plaza heist with Jackie and Evelyn in Night City", None),
                (
                    "Met Judy, ran the Voodoo Boys mission in Pacifica",
                    {"current_quest": "Automatic Love"},
                ),
            ),
            ideal_path="quick",
        ),
        # Thin: one sparse note → the player has played but there's nothing concrete to
        # ground on; deep web research augments it.
        AdaptiveCase(
            id="thin_one_note",
            sessions=(("played a bit", None),),
            ideal_path="deep",
        ),
        # Cold start: a brand-new game with no history → quick, never deep (the cost
        # guard). Deep on a game with zero player context is expensive and low-value.
        AdaptiveCase(
            id="new_game_cold_start",
            sessions=(),
            ideal_path="quick",
        ),
    ]


def evaluate_adaptive(settings: Settings) -> AdaptiveReport:
    """Score router accuracy, grounding, and cost vs the two fixed policies."""
    report = AdaptiveReport()
    for case in adaptive_cases():
        rows = [SimpleNamespace(wrap_up_text=t, extracted_state=st) for t, st in case.sessions]
        verdict = evaluate_local_relevance(rows, settings)
        chosen = route_recap(verdict, entitled_to_deep=True)
        report.rows.append(
            {
                "id": case.id,
                "ideal": case.ideal_path,
                "chosen": chosen,
                "adaptive_grounding": _grounding(chosen, case.ideal_path),
                "quick_grounding": _grounding("quick", case.ideal_path),
                "deep_grounding": _grounding("deep", case.ideal_path),
                "adaptive_cost": _cost(chosen),
            }
        )
    return report
