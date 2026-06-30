"""Structured domain events for Pick flows."""

from __future__ import annotations

import structlog

from slate.infrastructure.db.models import Pick

logger = structlog.get_logger()


def log_pick_requested(
    *,
    user_id: int,
    eligible_count: int,
    requested_count: int,
    mood: str,
    available_minutes: int,
    mental_energy: str,
    has_context: bool,
) -> None:
    logger.info(
        "pick_requested",
        user_id=user_id,
        eligible_count=eligible_count,
        requested_count=requested_count,
        mood=mood,
        available_minutes=available_minutes,
        mental_energy=mental_energy,
        has_context=has_context,
    )


def log_pick_created(*, user_id: int, pick: Pick) -> None:
    logger.info(
        "pick_created",
        user_id=user_id,
        pick_id=pick.id,
        pick_public_id=str(pick.public_id),
        library_entry_id=pick.library_entry_id,
    )


def log_pick_actioned(*, user_id: int, pick: Pick, action: str) -> None:
    logger.info(
        "pick_actioned",
        user_id=user_id,
        pick_id=pick.id,
        pick_public_id=str(pick.public_id),
        library_entry_id=pick.library_entry_id,
        action=action,
    )
