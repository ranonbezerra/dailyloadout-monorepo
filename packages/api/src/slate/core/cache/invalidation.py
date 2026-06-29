"""Service-layer cache invalidation (ROADMAP Epic 18).

Maps domain events to the cache keys they invalidate. Keeping this here — rather
than scattering ``cache.delete*`` calls across services — means the event →
busted-keys map lives in one auditable place, and callers express intent
("a play_session changed for this user") instead of poking key strings.

Invalidation is **ambient**, like ``structlog``'s logger: callers just say
``await invalidate_user_stats(user_id)`` and this module resolves the process
cache itself (memoised singleton; ``NullCache`` under tests / when disabled). No
service needs to hold or thread a cache for the write side. The optional *cache*
argument exists only so the function can be unit-tested with a fake.
"""

from __future__ import annotations

from slate.config import settings
from slate.infrastructure.cache.base import AbstractCache
from slate.infrastructure.cache.factory import get_cache
from slate.infrastructure.cache.keys import stats_namespace


async def invalidate_user_stats(user_id: int, cache: AbstractCache | None = None) -> None:
    """Bust every cached stats view for *user_id*.

    Called whenever a play_session starts, ends, or is wrapped up, or the library
    changes — any of which shifts the overview / heatmap / genre / platform /
    timeline aggregates. Best-effort: a no-op cache (tests, caching disabled)
    simply does nothing.
    """
    target = cache if cache is not None else get_cache(settings)
    await target.delete_namespace(stats_namespace(user_id))
