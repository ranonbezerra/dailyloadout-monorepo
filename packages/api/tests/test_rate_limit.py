"""Tests for the pyrate_limiter Redis-backed rate limiter (api/v1/_rate_limit.py).

Rate limiting is disabled globally in the test config (``RATE_LIMIT_ENABLED=false``),
so these tests re-enable it via a ``settings`` patch. No real Redis is started:
``_get_limiter`` is patched to build the same per-identity ``pyrate_limiter``
limiters over an in-memory async bucket (``BucketAsyncWrapper(InMemoryBucket)``),
so the real over-limit logic runs without a Redis backend.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pyrate_limiter import (
    BucketAsyncWrapper,
    Duration,
    InMemoryBucket,
    Limiter,
    Rate,
)

from dailyloadout.api.v1 import _rate_limit
from dailyloadout.api.v1._rate_limit import rate_limit
from dailyloadout.config import settings


@pytest.fixture(autouse=True)
def _enable_rate_limit() -> Any:
    """Enable the limiter for this module only, restoring afterward."""
    original = settings.rate_limit_enabled
    settings.rate_limit_enabled = True
    yield
    settings.rate_limit_enabled = original
    _rate_limit._limiters.clear()


@pytest.fixture
def in_memory_limiter(monkeypatch: pytest.MonkeyPatch) -> dict[str, Limiter]:
    """Patch ``_get_limiter`` to use an in-memory async bucket (no Redis).

    Preserves the per-identity bucket-key memoization, so identity isolation is
    exercised exactly as in production.
    """
    cache: dict[str, Limiter] = {}

    async def _fake_get_limiter(scope: str, identity: str, times: int, seconds: int) -> Limiter:
        cache_key = f"{scope}:{times}:{seconds}:{identity}"
        limiter = cache.get(cache_key)
        if limiter is None:
            rate = Rate(times, Duration.SECOND * seconds)
            limiter = Limiter(BucketAsyncWrapper(InMemoryBucket([rate])))
            cache[cache_key] = limiter
        return limiter

    monkeypatch.setattr(_rate_limit, "_get_limiter", _fake_get_limiter)
    return cache


class _BrokenLimiter:
    async def try_acquire(self, *args: object, **kwargs: object) -> bool:
        raise ConnectionError("redis down")


class _User:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


# ---------------------------------------------------------------------------
# Per-user dependency
# ---------------------------------------------------------------------------


async def test_user_limiter_allows_then_429(
    in_memory_limiter: dict[str, Limiter],
) -> None:
    dep = rate_limit("test_scope", times=3, seconds=60, by="user")
    user = _User(1)

    for _ in range(3):
        await dep(current_user=user)  # type: ignore[call-arg]

    with pytest.raises(HTTPException) as exc:
        await dep(current_user=user)  # type: ignore[call-arg]
    assert exc.value.status_code == 429
    assert exc.value.headers is not None
    assert exc.value.headers["Retry-After"] == "60"


async def test_user_limiter_is_keyed_per_user(
    in_memory_limiter: dict[str, Limiter],
) -> None:
    dep = rate_limit("test_scope", times=2, seconds=60, by="user")
    user_a = _User(1)
    user_b = _User(2)

    await dep(current_user=user_a)  # type: ignore[call-arg]
    await dep(current_user=user_a)  # type: ignore[call-arg]
    with pytest.raises(HTTPException):
        await dep(current_user=user_a)  # type: ignore[call-arg]

    # User B is unaffected — separate identity => separate bucket.
    await dep(current_user=user_b)  # type: ignore[call-arg]
    await dep(current_user=user_b)  # type: ignore[call-arg]


async def test_limiter_fails_open_on_redis_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _broken_get_limiter(*args: object, **kwargs: object) -> _BrokenLimiter:
        return _BrokenLimiter()

    monkeypatch.setattr(_rate_limit, "_get_limiter", _broken_get_limiter)
    dep = rate_limit("test_scope", times=1, seconds=60, by="user")
    user = _User(1)

    # Well past the limit, but the limiter errors => request is allowed.
    for _ in range(5):
        await dep(current_user=user)  # type: ignore[call-arg]


async def test_limiter_disabled_is_noop(
    in_memory_limiter: dict[str, Limiter],
) -> None:
    settings.rate_limit_enabled = False
    dep = rate_limit("test_scope", times=1, seconds=60, by="user")
    user = _User(1)

    for _ in range(10):
        await dep(current_user=user)  # type: ignore[call-arg]
    # Disabled => the limiter is never even built.
    assert in_memory_limiter == {}


# ---------------------------------------------------------------------------
# IP dependency
# ---------------------------------------------------------------------------


async def test_ip_limiter_disabled_is_noop(
    in_memory_limiter: dict[str, Limiter],
) -> None:
    from fastapi import Request

    settings.rate_limit_enabled = False
    dep = rate_limit("ip_scope", times=1, seconds=60, by="ip")
    request = Request({"type": "http", "client": ("1.2.3.4", 1234), "headers": []})

    for _ in range(5):
        await dep(request=request)  # type: ignore[call-arg]
    assert in_memory_limiter == {}


async def test_ip_limiter_through_app(in_memory_limiter: dict[str, Limiter]) -> None:
    app = FastAPI()

    @app.get(
        "/ping",
        dependencies=[Depends(rate_limit("ping_ip", times=2, seconds=60, by="ip"))],
    )
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        assert (await ac.get("/ping")).status_code == 200
        assert (await ac.get("/ping")).status_code == 200
        resp = await ac.get("/ping")
        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "60"


# ---------------------------------------------------------------------------
# Redis-backed limiter construction (the real _get_limiter path is memoised)
# ---------------------------------------------------------------------------


async def test_get_limiter_is_memoized(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real _get_limiter builds one Limiter per (scope, rate, identity)."""
    built: list[str] = []

    class _FakeBucket:
        @classmethod
        async def init(cls, rates: object, redis: object, bucket_key: str) -> _FakeBucket:
            built.append(bucket_key)
            return cls()

    monkeypatch.setattr(_rate_limit, "RedisBucket", _FakeBucket)
    monkeypatch.setattr(_rate_limit, "get_redis_client", lambda: object())
    # Bypass the real Limiter (it validates the bucket type); we only assert that
    # RedisBucket.init is called once per (scope, rate, identity).
    monkeypatch.setattr(_rate_limit, "Limiter", lambda bucket: bucket)
    _rate_limit._limiters.clear()

    first = await _rate_limit._get_limiter("s", "u1", 5, 60)
    second = await _rate_limit._get_limiter("s", "u1", 5, 60)
    assert first is second
    # Distinct identity => distinct bucket.
    await _rate_limit._get_limiter("s", "u2", 5, 60)
    assert built == ["rl:s:u1", "rl:s:u2"]


def test_get_redis_client_is_memoized(monkeypatch: pytest.MonkeyPatch) -> None:
    import dailyloadout.infrastructure.cache.redis_client as rc

    monkeypatch.setattr(rc, "_redis_client", None)
    first = rc.get_redis_client()
    second = rc.get_redis_client()
    assert first is second


# ---------------------------------------------------------------------------
# Auth login/register IP limiter, end-to-end through the real app
# ---------------------------------------------------------------------------


@pytest.fixture
async def limited_auth_client(in_memory_limiter: dict[str, Limiter]) -> Any:
    """Real app client with the auth limiter ACTIVE (no no-op overrides)."""
    from dailyloadout.deps import get_db
    from dailyloadout.deps.capture import (
        get_igdb_client_dep,
        get_llm_client_dep,
        get_stt_client_dep,
    )
    from dailyloadout.infrastructure.llm.dummy import DummyLLMClient
    from dailyloadout.infrastructure.stt.dummy import DummySTTClient
    from dailyloadout.main import app
    from tests.conftest import _override_get_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_client_dep] = lambda: DummyLLMClient()
    app.dependency_overrides[get_igdb_client_dep] = lambda: None
    app.dependency_overrides[get_stt_client_dep] = lambda: DummySTTClient()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def test_login_limiter_429_after_limit(limited_auth_client: AsyncClient) -> None:
    payload = {
        "email": "nobody@example.com",
        "password": "whatever123",  # pragma: allowlist secret`
    }
    statuses = [
        (await limited_auth_client.post("/v1/auth/login", json=payload)).status_code
        for _ in range(settings.rate_limit_login_per_minute + 2)
    ]
    assert 429 in statuses, statuses


async def test_register_limiter_429_after_limit(
    limited_auth_client: AsyncClient,
) -> None:
    statuses = []
    for i in range(settings.rate_limit_register_per_minute + 2):
        resp = await limited_auth_client.post(
            "/v1/auth/register",
            json={
                "email": f"user{i}@example.com",
                "password": "SecurePass1",  # pragma: allowlist secret`
                "display_name": "User",
            },
        )
        statuses.append(resp.status_code)
    assert 429 in statuses, statuses
