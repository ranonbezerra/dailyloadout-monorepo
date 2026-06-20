"""Auto-ignore worker: marks stale pending loadouts as ignored.

A loadout with ``action IS NULL`` and ``created_at`` older than the
configured threshold is considered abandoned.  This worker marks it as
``action='ignored'``.

Intended to be run as a periodic cron job (e.g. hourly).
"""

from __future__ import annotations

import structlog

from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository

logger = structlog.get_logger()


async def auto_ignore_stale_loadouts(
    loadout_repo: LoadoutRepository,
    max_hours: int = 24,
) -> int:
    """Mark all stale loadouts as ignored and return the count."""
    stale = await loadout_repo.get_stale_loadouts(max_hours=max_hours)

    if not stale:
        return 0

    for loadout in stale:
        await loadout_repo.mark_ignored(loadout.id)
        logger.info(
            "loadout_auto_ignored",
            loadout_id=loadout.id,
            user_id=loadout.user_id,
        )

    return len(stale)
