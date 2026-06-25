"""Cache observability + reference-tier tests (ROADMAP Epic 18 Phase 4)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from dailyloadout.core.library.service import LibraryService
from dailyloadout.infrastructure.cache.keys import reference_key
from dailyloadout.infrastructure.cache.layer import cached_call, reset_cache_stats
from tests.test_cache_layer import FakeCache

# ── /v1/cache/stats endpoint ─────────────────────────────────────────────


async def test_cache_stats_endpoint_reports_counters(async_client: AsyncClient) -> None:
    reset_cache_stats()
    cache = FakeCache()

    async def compute() -> int:
        return 1

    # One miss then one hit under a known namespace.
    await cached_call(cache=cache, key="k", ttl_seconds=10, namespace="probe", compute=compute)
    await cached_call(cache=cache, key="k", ttl_seconds=10, namespace="probe", compute=compute)

    resp = await async_client.get("/v1/cache/stats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["probe"] == {"hit": 1, "miss": 1, "hit_rate": 0.5}


# ── Reference tier: list_genres ──────────────────────────────────────────


class _GenreRepo:
    def __init__(self) -> None:
        self.calls = 0

    async def distinct_genres(self) -> list[str]:
        self.calls += 1
        return ["action", "metroidvania"]


def _service(repo: _GenreRepo, cache: Any) -> LibraryService:
    return LibraryService(repo, None, None, cache=cache, reference_ttl_seconds=100)  # type: ignore[arg-type]


async def test_genres_served_from_cache_on_repeat() -> None:
    repo = _GenreRepo()
    cache = FakeCache()
    service = _service(repo, cache)

    first = await service.list_genres()
    second = await service.list_genres()

    assert first == second == ["action", "metroidvania"]
    assert repo.calls == 1  # second read hit the reference cache
    assert reference_key("genres") in cache.store
