"""Cache observability + reference-tier tests (ROADMAP Epic 18 Phase 4)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from httpx import AsyncClient

from slate.core.library.service import LibraryService
from slate.infrastructure.cache.keys import reference_key
from slate.infrastructure.cache.layer import cached_call, reset_cache_stats
from tests.test_cache_layer import FakeCache

# ── /v1/cache/stats endpoint ─────────────────────────────────────────────


async def test_cache_stats_endpoint_reports_counters(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    reset_cache_stats()
    cache = FakeCache()

    async def compute() -> int:
        return 1

    # One miss then one hit under a known namespace.
    await cached_call(cache=cache, key="k", ttl_seconds=10, namespace="probe", compute=compute)
    await cached_call(cache=cache, key="k", ttl_seconds=10, namespace="probe", compute=compute)

    resp = await async_client.get("/v1/cache/stats", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["probe"] == {"hit": 1, "miss": 1, "hit_rate": 0.5}


async def test_cache_stats_endpoint_requires_auth(async_client: AsyncClient) -> None:
    """The namespace telemetry is internal — unauthenticated calls are rejected."""
    resp = await async_client.get("/v1/cache/stats")
    assert resp.status_code == 401


# ── Reference tier: list_genres ──────────────────────────────────────────


class _GenreRepo:
    def __init__(self) -> None:
        self.calls = 0

    async def distinct_genres(self, *, user_id: int) -> list[str]:
        self.calls += 1
        return ["action", "metroidvania"]


def _service(repo: _GenreRepo, cache: Any) -> LibraryService:
    return LibraryService(repo, None, None, cache=cache, reference_ttl_seconds=100)  # type: ignore[arg-type]


async def test_genres_served_from_cache_on_repeat() -> None:
    repo = _GenreRepo()
    cache = FakeCache()
    service = _service(repo, cache)

    first = await service.list_genres(user_id=7)
    second = await service.list_genres(user_id=7)

    assert first == second == ["action", "metroidvania"]
    assert repo.calls == 1  # second read hit the reference cache
    # The genre cache is namespaced per user (private rows are user-scoped).
    assert reference_key("genres:7") in cache.store


# ── Reference tier: list_platforms (global, shared) ──────────────────────


class _PlatformRepo:
    def __init__(self) -> None:
        self.calls = 0

    async def list_all(self) -> list[SimpleNamespace]:
        self.calls += 1
        return [SimpleNamespace(id=1, slug="pc", label="PC", family="pc")]


async def test_platforms_cached_and_tiered_on_repeat() -> None:
    repo = _PlatformRepo()
    cache = FakeCache()
    service = LibraryService(None, None, repo, cache=cache, reference_ttl_seconds=100)  # type: ignore[arg-type]

    first = await service.list_platforms()
    second = await service.list_platforms()

    assert [p.slug for p in first] == [p.slug for p in second] == ["pc"]
    assert repo.calls == 1  # second read served from cache (tier/Redis), not the DB
    # Platforms are global, so the key is un-scoped (one shared entry).
    assert reference_key("platforms") in cache.store
