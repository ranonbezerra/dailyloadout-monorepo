"""Caching decorator for web-research clients (ROADMAP Epic 18).

Wraps an ``AbstractResearchClient`` so identical queries — common across deep
recaps that ground on the same game — skip the network hop. A cache
miss/outage falls through to the live client; empty result sets are not cached
(a transient SearXNG hiccup shouldn't be remembered for hours).
"""

from __future__ import annotations

from dataclasses import asdict

from slate.infrastructure.cache.base import AbstractCache
from slate.infrastructure.cache.keys import NS_RESEARCH, research_key
from slate.infrastructure.cache.layer import cached_call

from .base import AbstractResearchClient, SearchResult


class CachedResearchClient(AbstractResearchClient):
    """An ``AbstractResearchClient`` that caches search results."""

    def __init__(
        self, inner: AbstractResearchClient, cache: AbstractCache, ttl_seconds: int
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds

    async def search(self, query: str, limit: int = 6) -> list[SearchResult]:
        return await cached_call(
            cache=self._cache,
            key=research_key(query, limit),
            ttl_seconds=self._ttl,
            namespace=NS_RESEARCH,
            compute=lambda: self._inner.search(query, limit),
            loads=lambda data: [SearchResult(**item) for item in data],
            dumps=lambda results: [asdict(r) for r in results],
            cache_if=bool,  # don't cache an empty result set
        )

    async def fetch(self, url: str) -> str:
        # Page bodies are large and rarely re-fetched; pass through uncached.
        return await self._inner.fetch(url)
