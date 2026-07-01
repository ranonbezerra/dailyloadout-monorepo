"""Reference-data reads (genres, platforms) — cached with an in-process tier.

Small, hot, read-mostly lists shown on nearly every library screen. Both go
through the shared cache (``NS_REF``) with a short in-process tier in front of
Redis (ROADMAP Epic 18), so the common case skips the network round-trip. The
platform list is global (one shared key); genres are per-user (the key embeds
``user_id``) so another user's unvalidated private manual genres never leak.
"""

from __future__ import annotations

from slate.core.library.schemas import PlatformResponse
from slate.infrastructure.cache.base import AbstractCache
from slate.infrastructure.cache.keys import NS_REF, reference_key
from slate.infrastructure.cache.layer import cached_call
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.platform import PlatformRepository


async def list_genres(
    game_repo: GameRepository,
    cache: AbstractCache,
    *,
    user_id: int,
    ttl_seconds: int,
    process_ttl_seconds: int,
) -> list[str]:
    """Distinct genre names visible to *user_id* (canonical/shared + own manual)."""
    return await cached_call(
        cache=cache,
        key=reference_key(f"genres:{user_id}"),
        ttl_seconds=ttl_seconds,
        namespace=NS_REF,
        compute=lambda: game_repo.distinct_genres(user_id=user_id),
        process_ttl_seconds=process_ttl_seconds,
    )


async def list_platforms(
    platform_repo: PlatformRepository,
    cache: AbstractCache,
    *,
    ttl_seconds: int,
    process_ttl_seconds: int,
) -> list[PlatformResponse]:
    """All available platforms. Global, tiny, changes ~never — the ideal tier case."""

    async def _compute() -> list[PlatformResponse]:
        rows = await platform_repo.list_all()
        return [PlatformResponse.model_validate(p) for p in rows]

    return await cached_call(
        cache=cache,
        key=reference_key("platforms"),
        ttl_seconds=ttl_seconds,
        namespace=NS_REF,
        compute=_compute,
        loads=lambda raw: [PlatformResponse.model_validate(d) for d in raw],
        dumps=lambda ps: [p.model_dump() for p in ps],
        process_ttl_seconds=process_ttl_seconds,
    )
