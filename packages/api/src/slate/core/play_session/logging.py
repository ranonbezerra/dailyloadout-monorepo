"""Structured domain events for PlaySession flows."""

from __future__ import annotations

import structlog

from slate.infrastructure.db.models import LibraryEntry, PlaySession

logger = structlog.get_logger()


def log_play_session_started(
    *, user_id: int, play_session: PlaySession, entry: LibraryEntry, has_recap: bool
) -> None:
    logger.info(
        "play_session_started",
        user_id=user_id,
        play_session_id=play_session.id,
        play_session_public_id=str(play_session.public_id),
        library_entry_id=entry.id,
        library_entry_public_id=str(entry.public_id),
        game_id=entry.game_id,
        has_recap=has_recap,
    )
