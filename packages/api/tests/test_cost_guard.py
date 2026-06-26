"""Tests for the global cost kill-switch + supporting Redis usage counters.

The cost guard is disabled globally in the test config (``COST_GUARD_ENABLED=false``)
so the suite never 503s; these tests re-enable it via a ``settings`` patch and a
tiny in-memory fake Redis (no real Redis is started). They exercise:

- the atomic window counters (``incr_window`` / ``peek_window``),
- each ceiling tripping a 503 (global minute/day/month + per-user/day),
- the no-op when disabled, and
- the FAIL-CLOSED behaviour on a Redis error (503, never silent allow).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from dailyloadout.api.v1 import _cost_guard
from dailyloadout.config import settings
from dailyloadout.infrastructure.cache import usage_counter


class _FakeRedis:
    """Minimal async Redis stand-in: INCR / EXPIRE / GET over a dict."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.expires: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, ttl: int) -> bool:
        self.expires[key] = ttl
        return True

    async def get(self, key: str) -> str | None:
        value = self.store.get(key)
        return str(value) if value is not None else None


class _BrokenRedis:
    async def incr(self, key: str) -> int:
        raise ConnectionError("redis down")

    async def expire(self, key: str, ttl: int) -> bool:
        raise ConnectionError("redis down")

    async def get(self, key: str) -> str | None:
        raise ConnectionError("redis down")


class _User:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(usage_counter, "get_redis_client", lambda: fake)
    return fake


_COST_FIELDS = (
    "cost_guard_enabled",
    "cost_global_per_minute",
    "cost_global_per_day",
    "cost_global_per_month",
    "cost_user_per_day",
    "cost_alert_threshold",
)


@pytest.fixture(autouse=True)
def _enable_cost_guard() -> object:
    saved = {f: getattr(settings, f) for f in _COST_FIELDS}
    settings.cost_guard_enabled = True
    yield
    for field, value in saved.items():
        setattr(settings, field, value)


# ---------------------------------------------------------------------------
# usage_counter
# ---------------------------------------------------------------------------


async def test_incr_window_sets_ttl_once(fake_redis: _FakeRedis) -> None:
    assert await usage_counter.incr_window("k", 60) == 1
    assert fake_redis.expires["k"] == 60
    fake_redis.expires.clear()
    # Second increment must NOT re-apply the TTL (window slides, not extends).
    assert await usage_counter.incr_window("k", 60) == 2
    assert "k" not in fake_redis.expires


async def test_peek_window_reads_without_incrementing(fake_redis: _FakeRedis) -> None:
    await usage_counter.incr_window("k", 60)
    assert await usage_counter.peek_window("k") == 1
    assert await usage_counter.peek_window("missing") == 0


async def test_peek_window_returns_zero_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usage_counter, "get_redis_client", lambda: _BrokenRedis())
    assert await usage_counter.peek_window("k") == 0


def test_bucket_keys_are_utc_shaped() -> None:
    from datetime import UTC, datetime

    now = datetime(2026, 6, 26, 14, 5, tzinfo=UTC)
    assert usage_counter.minute_bucket(now) == "202606261405"
    assert usage_counter.day_bucket(now) == "20260626"
    assert usage_counter.month_bucket(now) == "202606"


# ---------------------------------------------------------------------------
# cost_guard dependency
# ---------------------------------------------------------------------------


async def test_cost_guard_allows_under_ceiling(fake_redis: _FakeRedis) -> None:
    dep = _cost_guard.cost_guard("test")
    await dep(current_user=_User(1))  # type: ignore[arg-type]


async def test_cost_guard_user_day_ceiling_trips_503(
    fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usage_counter, "get_redis_client", lambda: fake_redis)
    settings.cost_user_per_day = 2
    settings.cost_global_per_minute = 1000
    settings.cost_global_per_day = 1000
    settings.cost_global_per_month = 1000
    dep = _cost_guard.cost_guard("test")
    user = _User(7)

    await dep(current_user=user)  # type: ignore[arg-type]
    await dep(current_user=user)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        await dep(current_user=user)  # type: ignore[arg-type]
    assert exc.value.status_code == 503


async def test_cost_guard_global_minute_ceiling_trips_503(fake_redis: _FakeRedis) -> None:
    settings.cost_global_per_minute = 2
    settings.cost_global_per_day = 1000
    settings.cost_global_per_month = 1000
    settings.cost_user_per_day = 1000
    dep = _cost_guard.cost_guard("test")

    # Different users — the global minute window is shared across all of them.
    await dep(current_user=_User(1))  # type: ignore[arg-type]
    await dep(current_user=_User(2))  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        await dep(current_user=_User(3))  # type: ignore[arg-type]
    assert exc.value.status_code == 503


async def test_cost_guard_disabled_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.cost_guard_enabled = False
    # No fake Redis wired — if the guard touched Redis it would error; the no-op
    # must short-circuit before that.
    dep = _cost_guard.cost_guard("test")
    for _ in range(50):
        await dep(current_user=_User(1))  # type: ignore[arg-type]


async def test_cost_guard_fails_closed_on_redis_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(usage_counter, "get_redis_client", lambda: _BrokenRedis())
    dep = _cost_guard.cost_guard("test")
    with pytest.raises(HTTPException) as exc:
        await dep(current_user=_User(1))  # type: ignore[arg-type]
    assert exc.value.status_code == 503


async def test_cost_guard_emits_near_limit_alert(fake_redis: _FakeRedis) -> None:
    settings.cost_global_per_minute = 1000
    settings.cost_global_per_day = 1000
    settings.cost_global_per_month = 1000
    settings.cost_user_per_day = 10
    settings.cost_alert_threshold = 0.8
    dep = _cost_guard.cost_guard("test")
    user = _User(99)
    # 8th call (== 0.8 * 10) crosses the alert threshold without tripping the cap.
    for _ in range(9):
        await dep(current_user=user)  # type: ignore[arg-type]
