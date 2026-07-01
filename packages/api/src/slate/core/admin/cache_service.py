"""Backoffice cache administration (Epic 18 break-glass flush).

A single audited action: flush every application-cache namespace + the
in-process tier. For incident response (a bad prompt/model shipped, a poisoned
entry, a mass-invalidation need) where waiting out the TTLs isn't acceptable.
The durable rate-limit/cost-guard counters are never touched.
"""

from __future__ import annotations

from slate.core.admin.logging import log_admin_event
from slate.core.cache.invalidation import invalidate_all_cache
from slate.infrastructure.db.models import User
from slate.infrastructure.db.repositories.admin import AdminAuditRepository

ACTION_FLUSH = "cache.flush"


class AdminCacheService:
    """Flush the whole application cache, audited like every backoffice action."""

    def __init__(self, audit: AdminAuditRepository) -> None:
        self._audit = audit

    async def flush(self, actor: User) -> list[str]:
        """Clear every cache namespace + the in-process tier. Returns the cleared list."""
        cleared = await invalidate_all_cache()
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_FLUSH,
            detail=",".join(cleared),
        )
        log_admin_event(
            "admin_cache_flushed",
            actor=actor,
            action=ACTION_FLUSH,
            resource_type="cache",
            namespaces=cleared,
        )
        return cleared
