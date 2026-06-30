"""Auto-clamp worker: closes stale play_sessions that have been active too long.

A play_session with ``ended_at IS NULL`` and ``started_at`` older than the
configured threshold is considered forgotten.  This worker marks it as
``ended_via='auto_clamp'`` and sets ``ended_at = started_at + max_hours``.

Intended to be run as a periodic cron job (e.g. hourly).
"""

from __future__ import annotations

import structlog

from slate.core.cache.invalidation import invalidate_user_stats
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.observability import job_context

logger = structlog.get_logger()


async def auto_clamp_stale_play_sessions(
    play_session_repo: PlaySessionRepository,
    max_hours: int = 8,
) -> int:
    """Close all stale play_sessions and return the number clamped.

    A clamp ends a play_session, so each affected user's stats are invalidated —
    this is the background counterpart to the REST end/wrap_up hooks.
    """
    with job_context("play_session_auto_clamp", max_hours=max_hours):
        stale = await play_session_repo.get_stale_play_sessions(max_hours=max_hours)

        if not stale:
            return 0

        clamped_user_ids: set[int] = set()
        for play_session in stale:
            await play_session_repo.auto_clamp(play_session.id, max_hours=max_hours)
            clamped_user_ids.add(play_session.user_id)
            logger.info(
                "play_session_auto_clamped",
                play_session_id=play_session.id,
                user_id=play_session.user_id,
                started_at=str(play_session.started_at),
            )

        for user_id in clamped_user_ids:
            await invalidate_user_stats(user_id)

        return len(stale)
