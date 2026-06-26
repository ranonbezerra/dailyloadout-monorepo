"""Cache observability endpoint (ROADMAP Epic 18 Phase 4).

Exposes the in-process per-namespace hit/miss counters so TTLs can be tuned
against real hit rates. Counts only (no user data, no secrets), but the
namespace telemetry is internal, so the endpoint requires authentication like
the rest of the API. Counters are per-process and reset on restart.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dailyloadout.api.v1._rate_limit import rate_limit
from dailyloadout.config import settings
from dailyloadout.deps import CurrentUserDep
from dailyloadout.infrastructure.cache.layer import cache_stats

router = APIRouter(prefix="/v1/cache", tags=["cache"])

_read_rate_limit = Depends(
    rate_limit("cache_read", settings.rate_limit_read_per_minute, 60, by="user")
)


class NamespaceStats(BaseModel):
    hit: int
    miss: int
    hit_rate: float


@router.get(
    "/stats",
    response_model=dict[str, NamespaceStats],
    dependencies=[_read_rate_limit],
)
async def get_cache_stats(current_user: CurrentUserDep) -> dict[str, NamespaceStats]:
    """Return per-namespace hit/miss counters and hit rates."""
    out: dict[str, NamespaceStats] = {}
    for namespace, counts in cache_stats().items():
        total = counts["hit"] + counts["miss"]
        rate = counts["hit"] / total if total else 0.0
        out[namespace] = NamespaceStats(
            hit=counts["hit"], miss=counts["miss"], hit_rate=round(rate, 4)
        )
    return out
