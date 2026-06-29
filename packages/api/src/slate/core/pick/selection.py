"""Pick game-selection helper: one LLM call with a reroll + UUID-existence guard.

Extracted from the service so the selection can back any DECIDE=AI entrance to the
play_session pipeline (ROADMAP Epic 12), not only the Pick flow.
"""

from __future__ import annotations

import structlog

from slate.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()

MAX_REROLLS = 1


async def select_one(
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
            selection = await llm_client.select_game(
                candidates=candidates,
                mood=mood,
                available_minutes=available_minutes,
                mental_energy=mental_energy,
                context=context,
            )
        except Exception:
            logger.warning("pick_selection_failed", exc_info=True, attempt=attempt)
            continue

        if selection.library_entry_public_id in valid_ids:
            return selection.library_entry_public_id, selection.reasoning

        logger.warning(
            "pick_invalid_uuid",
            returned_id=selection.library_entry_public_id,
            attempt=attempt,
        )

    return None
