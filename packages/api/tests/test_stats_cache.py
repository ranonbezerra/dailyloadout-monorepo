"""StatsService caching tests (ROADMAP Epic 18).

Verifies the service serves repeat reads from cache, isolates users, and
recomputes after a play_session-event invalidation — using a fake repo (call
counting) and the in-memory fake cache, so no DB or Redis is involved.
"""

from __future__ import annotations

from datetime import UTC, datetime

from slate.core.cache.invalidation import invalidate_user_stats
from slate.core.stats.service import StatsService
from tests.test_cache_layer import FakeCache


class FakeStatsRepo:
    """Counts overview-supporting repo calls; returns canned aggregates."""

    def __init__(self) -> None:
        self.overview_calls = 0

    async def total_games(self, user_id: int) -> int:
        self.overview_calls += 1
        return 3

    async def status_counts(self, user_id: int) -> dict[str, int]:
        return {"playing": 1}

    async def play_sessions_last_30d(self, user_id: int) -> int:
        return 2

    async def avg_play_session_duration_minutes(self, user_id: int) -> float | None:
        return 45.0


def _service(repo: FakeStatsRepo, cache: FakeCache) -> StatsService:
    return StatsService(repo, cache=cache, ttl_seconds=300)  # type: ignore[arg-type]


_NOW = datetime(2026, 1, 1, tzinfo=UTC)


async def test_overview_served_from_cache_on_repeat() -> None:
    repo = FakeStatsRepo()
    cache = FakeCache()
    service = _service(repo, cache)

    first = await service.get_overview(1, _NOW)
    second = await service.get_overview(1, _NOW)

    assert first == second
    assert first.total_games == 3
    assert repo.overview_calls == 1  # second read hit the cache


async def test_overview_cache_is_per_user() -> None:
    repo = FakeStatsRepo()
    cache = FakeCache()
    service = _service(repo, cache)

    await service.get_overview(1, _NOW)
    await service.get_overview(2, _NOW)

    # Distinct users → distinct keys → two computes (no cross-user reuse).
    assert repo.overview_calls == 2


async def test_overview_recomputes_after_invalidation() -> None:
    repo = FakeStatsRepo()
    cache = FakeCache()
    service = _service(repo, cache)

    await service.get_overview(1, _NOW)
    await invalidate_user_stats(1, cache=cache)  # e.g. a play_session just ended
    await service.get_overview(1, _NOW)

    assert repo.overview_calls == 2


async def test_null_cache_recomputes_every_time() -> None:
    from slate.infrastructure.cache.base import NullCache

    repo = FakeStatsRepo()
    service = StatsService(repo, cache=NullCache(), ttl_seconds=300)  # type: ignore[arg-type]

    await service.get_overview(1, _NOW)
    await service.get_overview(1, _NOW)

    assert repo.overview_calls == 2  # caching disabled → always recompute
