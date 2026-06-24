"""Loadout game-pick helper: one LLM call with a reroll + UUID-existence guard.

Extracted from the service so the pick can back any DECIDE=AI entrance to the
mission pipeline (ROADMAP Epic 12), not only the loadout-suggestion flow.
"""

from __future__ import annotations

import structlog

from dailyloadout.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()

MAX_REROLLS = 1


async def pick_one(
    llm_client: AbstractLLMClient,
    candidates: list[dict[str, object]],
    valid_ids: set[str],
    mood: str,
    available_minutes: int,
    mental_energy: str,
    context: str | None = None,
) -> tuple[str, str] | None:
    """Call the LLM once (with one reroll) and return ``(public_id, reasoning)``.

    Returns ``None`` if the LLM fails or keeps returning a game outside the
    candidate set after the reroll — the deterministic UUID-existence guard.
    """
    for attempt in range(1 + MAX_REROLLS):
        try:
            pick = await llm_client.pick_loadout_game(
                candidates=candidates,
                mood=mood,
                available_minutes=available_minutes,
                mental_energy=mental_energy,
                context=context,
            )
        except Exception:
            logger.warning("loadout_llm_pick_failed", exc_info=True, attempt=attempt)
            continue

        if pick.library_entry_public_id in valid_ids:
            return pick.library_entry_public_id, pick.reasoning

        logger.warning(
            "loadout_invalid_uuid",
            returned_id=pick.library_entry_public_id,
            attempt=attempt,
        )

    return None
