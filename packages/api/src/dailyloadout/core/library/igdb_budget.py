"""Shared per-user/day outbound-IGDB budget (novel-title spam guard).

Each novel title fans out to a live IGDB search, and the IGDB quota is 4 req/s
for the *whole app*. Without a per-user cap, one account spamming new titles
(via create_game / capture parse / bulk import) could exhaust that quota for
everyone. This guard caps outbound IGDB lookups per user per UTC day with a
shared Redis counter (so the same budget spans all three surfaces).

It is intentionally BEST-EFFORT / fail-open: a Redis blip must never block a
library write. When ``settings.rate_limit_enabled`` is False it is a no-op (so
the pytest env never consumes/needs Redis), mirroring the rate-limit dependency.

Callers ask :meth:`allow` BEFORE doing an outbound IGDB search; ``False`` means
the per-day budget is spent and the lookup should be skipped (the local DB path
still resolves the request, just without enrichment).
"""

from __future__ import annotations

import structlog

from dailyloadout.config import settings
from dailyloadout.infrastructure.cache.usage_counter import day_bucket, incr_window

logger = structlog.get_logger()

_DAY_SECONDS = 24 * 3600


async def igdb_budget_allows(user_id: int) -> bool:
    """Return True if *user_id* may make one more outbound IGDB call today.

    Consumes one permit from the per-user/day counter. Fails OPEN: any Redis
    error (or the limiter being disabled) returns True so library writes are
    never blocked by the budget.
    """
    if not settings.rate_limit_enabled:
        return True
    key = f"igdb:budget:{user_id}:{day_bucket()}"
    try:
        count = await incr_window(key, _DAY_SECONDS)
    except Exception:
        logger.warning("igdb_budget_redis_error", user_id=user_id, exc_info=True)
        return True
    if count > settings.igdb_user_budget_per_day:
        logger.warning(
            "igdb_budget_exceeded",
            user_id=user_id,
            count=count,
            limit=settings.igdb_user_budget_per_day,
        )
        return False
    return True
