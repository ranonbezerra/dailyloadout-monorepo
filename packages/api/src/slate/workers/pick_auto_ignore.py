"""Auto-ignore worker: marks stale pending picks as ignored.

A pick with ``action IS NULL`` and ``created_at`` older than the
configured threshold is considered abandoned.  This worker marks it as
``action='ignored'``.

Intended to be run as a periodic cron job (e.g. hourly).
"""

from __future__ import annotations

import structlog

from slate.infrastructure.db.repositories.pick import PickRepository

logger = structlog.get_logger()


async def auto_ignore_stale_picks(
    pick_repo: PickRepository,
    max_hours: int = 24,
) -> int:
    """Mark all stale picks as ignored and return the count."""
    stale = await pick_repo.get_stale_picks(max_hours=max_hours)

    if not stale:
        return 0

    for pick in stale:
        await pick_repo.mark_ignored(pick.id)
        logger.info(
            "pick_auto_ignored",
            pick_id=pick.id,
            user_id=pick.user_id,
        )

    return len(stale)
