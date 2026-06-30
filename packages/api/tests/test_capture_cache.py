"""Tests for the two-layer capture-parse cache (Epic 27): exact, semantic, degrade."""

from __future__ import annotations

from typing import Any

import pytest

from slate.infrastructure.cache.base import AbstractCache
from slate.infrastructure.embedding import DummyEmbeddingClient
from slate.infrastructure.llm.base import ExtractedGame
from slate.infrastructure.llm.capture_cache import SemanticCaptureCache
from slate.infrastructure.llm.dummy import DummyLLMClient
from tests.conftest import _TestSessionFactory

_GAMES = [ExtractedGame(title="Elden Ring", platform_hint="pc", confidence=0.9)]


class _CountingLLM(DummyLLMClient):
    """Counts parse_capture_text calls and returns a fixed result."""

    def __init__(self, result: list[ExtractedGame]) -> None:
        self.calls = 0
        self._result = result

    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        self.calls += 1
        return self._result


class _DictCache(AbstractCache):
    """In-memory exact cache."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    async def get_json(self, key: str) -> Any | None:
        return self.store.get(key)

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def delete_namespace(self, prefix: str) -> None:
        self.store = {k: v for k, v in self.store.items() if not k.startswith(prefix)}


class _BrokenEmbeddingClient(DummyEmbeddingClient):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding backend down")


def _cache(
    inner: _CountingLLM,
    *,
    embedding: DummyEmbeddingClient | None = None,
    enabled: bool = True,
    threshold: float = 0.7,
) -> SemanticCaptureCache:
    return SemanticCaptureCache(
        inner,
        embedding or DummyEmbeddingClient(),
        _DictCache(),
        _TestSessionFactory,
        model="gemma3:4b",
        ttl_seconds=3600,
        threshold=threshold,
        enabled=enabled,
    )


class TestCaptureCache:
    async def test_exact_hit_skips_the_model(self) -> None:
        inner = _CountingLLM(_GAMES)
        cache = _cache(inner)
        await cache.parse_capture_text("Elden Ring")
        second = await cache.parse_capture_text("Elden Ring")  # identical → exact hit
        assert inner.calls == 1
        assert [g.title for g in second] == ["Elden Ring"]
        assert second[0].platform_hint == "pc" and second[0].confidence == 0.9

    async def test_semantic_hit_on_near_duplicate(self) -> None:
        inner = _CountingLLM(_GAMES)
        cache = _cache(inner)
        await cache.parse_capture_text("Elden Ring")  # stores exact + semantic
        # Different exact key (extra token) but high cosine → semantic hit, no 2nd call.
        result = await cache.parse_capture_text("Elden Ring pc")
        assert inner.calls == 1
        assert [g.title for g in result] == ["Elden Ring"]

    async def test_distinct_input_misses_and_calls_model(self) -> None:
        inner = _CountingLLM(_GAMES)
        cache = _cache(inner)
        await cache.parse_capture_text("Elden Ring")
        await cache.parse_capture_text("Helldivers 2 bug missions railgun")  # unrelated
        assert inner.calls == 2

    async def test_disabled_flag_passes_through(self) -> None:
        inner = _CountingLLM(_GAMES)
        cache = _cache(inner, enabled=False)
        await cache.parse_capture_text("Elden Ring")
        await cache.parse_capture_text("Elden Ring")
        assert inner.calls == 2  # no caching at all

    async def test_degrades_to_live_when_embedding_breaks(self) -> None:
        # A broken embedding backend disables the semantic layer but never the parse.
        inner = _CountingLLM(_GAMES)
        cache = _cache(inner, embedding=_BrokenEmbeddingClient())
        result = await cache.parse_capture_text("Elden Ring")
        assert inner.calls == 1
        assert [g.title for g in result] == ["Elden Ring"]

    async def test_empty_parse_is_not_cached(self) -> None:
        inner = _CountingLLM([])  # model finds no games
        cache = _cache(inner)
        await cache.parse_capture_text("asdf qwer")
        await cache.parse_capture_text("asdf qwer")  # would be an exact hit if cached
        assert inner.calls == 2

    async def test_stats_track_each_layer(self) -> None:
        inner = _CountingLLM(_GAMES)
        cache = _cache(inner)
        await cache.parse_capture_text("Elden Ring")  # miss (live)
        await cache.parse_capture_text("Elden Ring")  # exact hit
        await cache.parse_capture_text("Elden Ring pc")  # semantic hit
        assert cache.stats.misses == 1
        assert cache.stats.exact_hits == 1
        assert cache.stats.semantic_hits == 1
        assert cache.stats.total == 3
        assert cache.stats.hit_rate == pytest.approx(2 / 3)
        assert cache.stats.semantic_gain == pytest.approx(1 / 3)
