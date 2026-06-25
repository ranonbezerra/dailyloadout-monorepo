"""Service-layer cache invalidation (ROADMAP Epic 18).

Maps domain events to the cache keys they invalidate. Keeping this here — rather
than scattering ``cache.delete*`` calls across services — means the event →
busted-keys map lives in one auditable place, and callers express intent
("a mission changed for this user") instead of poking key strings.
"""

from __future__ import annotations

from dailyloadout.infrastructure.cache.base import AbstractCache
from dailyloadout.infrastructure.cache.keys import stats_namespace


async def invalidate_user_stats(cache: AbstractCache, user_id: int) -> None:
    """Bust every cached stats view for *user_id*.

    Called whenever a mission starts, ends, or is debriefed — any of which
    shifts the overview / heatmap / genre / platform / timeline aggregates.
    Best-effort: a no-op cache (tests, caching disabled) simply does nothing.
    """
    await cache.delete_namespace(stats_namespace(user_id))
