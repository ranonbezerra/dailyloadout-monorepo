"""Shared play_session-start orchestration (ROADMAP Epic 12 — Unified PlaySession Pipeline).

The single place a PlaySession is created, regardless of how the game was chosen —
a direct start, an accepted Pick, or (later) the Concierge. Centralising it
keeps the "one active play_session per user" constraint mapping and the
``last_played_at`` stamp consistent across every entrance to the play loop.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from slate.core.cache.invalidation import invalidate_user_stats
from slate.infrastructure.db.models import LibraryEntry, PlaySession
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import (
    PlaySessionRepository,
)

_ACTIVE_PLAY_SESSION_DETAIL = "You already have an active play session. End it first."


async def create_play_session_for_entry(
    *,
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    user_id: int,
    entry: LibraryEntry,
    recap_text: str | None = None,
) -> PlaySession:
    """Create an active play_session for *entry*, with an optional recap.

    Maps the one-active-play_session DB constraint to a clean 409 and stamps the
    entry's ``last_played_at``. Callers load the entry and run any pre-checks
    (e.g. an early active-play_session check to avoid wasting an LLM recap call).

    This is the single seam every start path funnels through (direct start,
    accepted Pick, Concierge), so invalidating the user's stats here covers
    them all.
    """
    try:
        play_session = await play_session_repo.create(
            user_id=user_id,
            library_entry_id=entry.id,
            recap_text=recap_text or None,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_ACTIVE_PLAY_SESSION_DETAIL,
        ) from None

    play_session.library_entry = entry
    await library_repo.update(entry, last_played_at=play_session.started_at)
    await invalidate_user_stats(user_id)
    return play_session
