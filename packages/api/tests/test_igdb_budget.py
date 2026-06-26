"""Tests for the shared per-user/day outbound-IGDB budget.

Best-effort/fail-open guard: it caps outbound IGDB lookups per user per UTC day,
but a Redis error (or the limiter being disabled) must never block a library
write. Uses a tiny in-memory fake Redis, no real Redis is started.
"""

from __future__ import annotations

import pytest

from dailyloadout.config import settings
from dailyloadout.core.library import igdb_budget
from dailyloadout.infrastructure.cache import usage_counter


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, ttl: int) -> bool:
        return True


class _BrokenRedis:
    async def incr(self, key: str) -> int:
        raise ConnectionError("redis down")


@pytest.fixture(autouse=True)
def _enable_limiter() -> object:
    original_enabled = settings.rate_limit_enabled
    original_budget = settings.igdb_user_budget_per_day
    settings.rate_limit_enabled = True
    yield
    settings.rate_limit_enabled = original_enabled
    settings.igdb_user_budget_per_day = original_budget


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(usage_counter, "get_redis_client", lambda: fake)
    return fake


async def test_budget_allows_until_exhausted(fake_redis: _FakeRedis) -> None:
    settings.igdb_user_budget_per_day = 3
    assert await igdb_budget.igdb_budget_allows(1) is True
    assert await igdb_budget.igdb_budget_allows(1) is True
    assert await igdb_budget.igdb_budget_allows(1) is True
    # 4th lookup is over the per-day budget.
    assert await igdb_budget.igdb_budget_allows(1) is False


async def test_budget_is_per_user(fake_redis: _FakeRedis) -> None:
    settings.igdb_user_budget_per_day = 1
    assert await igdb_budget.igdb_budget_allows(1) is True
    assert await igdb_budget.igdb_budget_allows(1) is False
    # Separate user — separate budget.
    assert await igdb_budget.igdb_budget_allows(2) is True


async def test_budget_noop_when_rate_limiting_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.rate_limit_enabled = False
    settings.igdb_user_budget_per_day = 0

    def _boom() -> object:
        raise AssertionError("Redis must not be touched when disabled")

    monkeypatch.setattr(usage_counter, "get_redis_client", _boom)
    assert await igdb_budget.igdb_budget_allows(1) is True


async def test_budget_fails_open_on_redis_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usage_counter, "get_redis_client", lambda: _BrokenRedis())
    settings.igdb_user_budget_per_day = 1
    # Redis is down — the budget must fail OPEN (allow), never block writes.
    assert await igdb_budget.igdb_budget_allows(1) is True
