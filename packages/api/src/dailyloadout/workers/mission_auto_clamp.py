"""Auto-clamp worker: closes stale missions that have been active too long.

A mission with ``ended_at IS NULL`` and ``started_at`` older than the
configured threshold is considered forgotten.  This worker marks it as
``ended_via='auto_clamp'`` and sets ``ended_at = started_at + max_hours``.

Intended to be run as a periodic cron job (e.g. hourly).
"""

from __future__ import annotations

import structlog

from dailyloadout.core.cache.invalidation import invalidate_user_stats
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

logger = structlog.get_logger()


async def auto_clamp_stale_missions(
    mission_repo: MissionRepository,
    max_hours: int = 8,
) -> int:
    """Close all stale missions and return the number clamped.

    A clamp ends a mission, so each affected user's stats are invalidated —
    this is the background counterpart to the REST end/debrief hooks.
    """
    stale = await mission_repo.get_stale_missions(max_hours=max_hours)

    if not stale:
        return 0

    clamped_user_ids: set[int] = set()
    for mission in stale:
        await mission_repo.auto_clamp(mission.id, max_hours=max_hours)
        clamped_user_ids.add(mission.user_id)
        logger.info(
            "mission_auto_clamped",
            mission_id=mission.id,
            user_id=mission.user_id,
            started_at=str(mission.started_at),
        )

    for user_id in clamped_user_ids:
        await invalidate_user_stats(user_id)

    return len(stale)
