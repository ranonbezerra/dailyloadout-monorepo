"""Tests for the coarse per-user default rate-limit backstop middleware.

A generous safety net so a NEW authenticated route is metered even if its author
forgets an explicit limiter. Identifies the caller by the ``sub`` of a
best-effort-decoded bearer JWT (no DB hit). No-op when rate limiting is disabled
(tests), and fail-open on any limiter error.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from dailyloadout.api import middleware
from dailyloadout.api.middleware import DefaultUserRateLimitMiddleware, _bearer_subject
from dailyloadout.api.v1 import _rate_limit
from dailyloadout.config import settings
from dailyloadout.core.auth.security import create_access_token


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(DefaultUserRateLimitMiddleware, per_minute=2)

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    return app


@pytest.fixture(autouse=True)
def _reset_limiters() -> Any:
    original = settings.rate_limit_enabled
    yield
    settings.rate_limit_enabled = original
    _rate_limit._limiters.clear()


@pytest.fixture
def in_memory_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    from pyrate_limiter import (
        BucketAsyncWrapper,
        Duration,
        InMemoryBucket,
        Limiter,
        Rate,
    )

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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_disabled_is_noop() -> None:
    settings.rate_limit_enabled = False
    app = _build_app()
    token = create_access_token("user-public-id", token_version=0)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for _ in range(10):
            resp = await ac.get("/ping", headers=_auth(token))
            assert resp.status_code == 200


async def test_anonymous_requests_pass_through(in_memory_limiter: None) -> None:
    settings.rate_limit_enabled = True
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # No bearer token => the backstop doesn't meter; route auth handles it.
        for _ in range(10):
            resp = await ac.get("/ping")
            assert resp.status_code == 200


async def test_metered_per_user_429(in_memory_limiter: None) -> None:
    settings.rate_limit_enabled = True
    app = _build_app()
    token = create_access_token("user-aaa", token_version=0)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        assert (await ac.get("/ping", headers=_auth(token))).status_code == 200
        assert (await ac.get("/ping", headers=_auth(token))).status_code == 200
        resp = await ac.get("/ping", headers=_auth(token))
        assert resp.status_code == 429
        assert resp.headers["retry-after"] == "60"


async def test_keyed_per_user(in_memory_limiter: None) -> None:
    settings.rate_limit_enabled = True
    app = _build_app()
    transport = ASGITransport(app=app)
    token_a = create_access_token("user-a", token_version=0)
    token_b = create_access_token("user-b", token_version=0)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/ping", headers=_auth(token_a))
        await ac.get("/ping", headers=_auth(token_a))
        assert (await ac.get("/ping", headers=_auth(token_a))).status_code == 429
        # Distinct identity => unaffected.
        assert (await ac.get("/ping", headers=_auth(token_b))).status_code == 200


async def test_fails_open_on_limiter_error(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.rate_limit_enabled = True

    async def _broken(*args: object, **kwargs: object) -> object:
        raise ConnectionError("redis down")

    monkeypatch.setattr(_rate_limit, "_get_limiter", _broken)
    app = _build_app()
    token = create_access_token("user-err", token_version=0)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Limiter errors => the backstop fails open (request allowed).
        for _ in range(5):
            assert (await ac.get("/ping", headers=_auth(token))).status_code == 200


def test_bearer_subject_extraction() -> None:
    token = create_access_token("abc-123", token_version=0)
    scope = {"headers": [(b"authorization", f"Bearer {token}".encode())]}
    assert _bearer_subject(scope) == "abc-123"


def test_bearer_subject_missing_or_invalid() -> None:
    assert _bearer_subject({"headers": []}) is None
    assert _bearer_subject({"headers": [(b"authorization", b"Basic xyz")]}) is None
    assert _bearer_subject({"headers": [(b"authorization", b"Bearer not-a-jwt")]}) is None


async def test_non_http_scope_passes_through() -> None:
    # A websocket/lifespan scope must not be metered (or crash).
    calls: list[str] = []

    async def _inner_app(scope: Any, receive: Any, send: Any) -> None:
        calls.append(scope["type"])

    mw = DefaultUserRateLimitMiddleware(_inner_app, per_minute=1)
    await mw({"type": "lifespan"}, None, None)  # type: ignore[arg-type]
    assert calls == ["lifespan"]


def test_middleware_module_logger_exists() -> None:
    assert middleware.logger is not None
