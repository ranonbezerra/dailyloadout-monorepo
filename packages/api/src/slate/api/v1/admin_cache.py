"""Backoffice cache administration API (Epic 18 break-glass flush).

Served under ``/internal/v1/cache`` — a separate module from ``admin.py`` to keep
each router within the 300-line budget. Admin-gated and audited like the rest of
the backoffice. The flush is rate-limited fail-closed: repeatedly clearing the
cache forces a thundering-herd recompute, so a leaked admin token can't loop it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from slate.api.v1._rate_limit import rate_limit
from slate.deps.admin import AdminCacheServiceDep
from slate.deps.auth import AdminUserDep

router = APIRouter(prefix="/internal/v1", tags=["internal"])

_flush_rate_limit = Depends(rate_limit("admin_cache_flush", 5, 60, by="user", fail_closed=True))


class CacheFlushResponse(BaseModel):
    """The namespaces cleared by a flush (for the operator's confirmation)."""

    cleared_namespaces: list[str]


@router.post(
    "/cache/flush",
    response_model=CacheFlushResponse,
    dependencies=[_flush_rate_limit],
)
async def flush_cache(
    admin: AdminUserDep,
    service: AdminCacheServiceDep,
) -> CacheFlushResponse:
    """Flush every application-cache namespace + the in-process tier (audited).

    Break-glass only: durable rate-limit/cost-guard counters are untouched; every
    cleared key simply recomputes live on its next read.
    """
    cleared = await service.flush(admin)
    return CacheFlushResponse(cleared_namespaces=cleared)
