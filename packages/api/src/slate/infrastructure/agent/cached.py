"""Caching decorator for the deep-research recap agent (ROADMAP Epic 18).

Caches the *entire* graph run (~4 LLM calls + web research), addressed by a
digest of the grounding ``PlaySessionContext``. Because that context includes the
session's wrap_ups, a new wrap_up changes the digest and yields a fresh key — so
"bust on new wrap_up" is structural, no explicit invalidation needed.

Only genuine deep-research results are cached; a quick-fallback (the deep path
timed out or research was down) is left uncached so the next attempt can try the
deep path again.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from slate.infrastructure.cache.base import AbstractCache
from slate.infrastructure.cache.keys import NS_RECAP, recap_key
from slate.infrastructure.cache.layer import cached_call

from .base import AbstractRecapAgent, DeepRecapRequest, RecapResult


class CachedRecapAgent(AbstractRecapAgent):
    """An ``AbstractRecapAgent`` that caches results around an inner agent."""

    def __init__(self, inner: AbstractRecapAgent, cache: AbstractCache, ttl_seconds: int) -> None:
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds

    async def deep_recap(self, req: DeepRecapRequest) -> RecapResult:
        return await cached_call(
            cache=self._cache,
            key=recap_key("deep", req.context),
            ttl_seconds=self._ttl,
            namespace=NS_RECAP,
            compute=lambda: self._inner.deep_recap(req),
            loads=lambda d: RecapResult(**d),
            dumps=_to_dict,
            cache_if=lambda r: r.source == "deep_research" and bool(r.text),
            skip_cache=req.force_refresh,
        )


def _to_dict(result: RecapResult) -> dict[str, Any]:
    return asdict(result)
