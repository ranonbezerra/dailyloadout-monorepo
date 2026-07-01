"""Reference-tier caching tests (genres, platforms) — ROADMAP Epic 18.

The ``/internal/v1/cache/stats`` + ``/cache/flush`` endpoint tests live in
``test_admin_cache.py`` (they're backoffice, admin-gated).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from slate.core.library.service import LibraryService
from slate.infrastructure.cache.keys import reference_key
from tests.test_cache_layer import FakeCache

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
