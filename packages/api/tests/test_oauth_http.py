"""Tests for the OAuth HTTP exchange (flow) and the Redis state store."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from dailyloadout.config import settings
from dailyloadout.infrastructure.oauth import OAuthError, build_provider, flow
from dailyloadout.infrastructure.oauth import state_store as state_mod
from dailyloadout.infrastructure.oauth.state_store import OAuthState, consume_state, store_state


class _FakeResponse:
    def __init__(self, status: int, payload: dict[str, Any]) -> None:
        self._status = status
        self._payload = payload
        self.request = httpx.Request("GET", "https://provider/x?secret=shh")

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self._status >= 400:
            raise httpx.HTTPStatusError(
                "err",
                request=self.request,
                response=httpx.Response(self._status, request=self.request),
            )


def _client_factory(
    token_payload: dict[str, Any],
    userinfo_payload: dict[str, Any],
    *,
    token_status: int = 200,
    userinfo_status: int = 200,
) -> type:
    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def post(self, url: str, data: Any = None, headers: Any = None) -> _FakeResponse:
            return _FakeResponse(token_status, token_payload)

        async def get(self, url: str, headers: Any = None) -> _FakeResponse:
            return _FakeResponse(userinfo_status, userinfo_payload)

    return _FakeClient


@pytest.fixture
def google_provider(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "google_oauth_client_id", "gid")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "gsecret")
    provider = build_provider("google", settings)
    assert provider is not None
    return provider


# ── flow.exchange_code_for_user ─────────────────────────────────────────


async def test_exchange_happy_path(monkeypatch: pytest.MonkeyPatch, google_provider: Any) -> None:
    fake = _client_factory(
        {"access_token": "at"},
        {"sub": "42", "email": "x@y.com", "email_verified": True, "name": "Xy"},
    )
    monkeypatch.setattr(flow.httpx, "AsyncClient", fake)
    info = await flow.exchange_code_for_user(google_provider, "code", "verifier", "https://api/cb")
    assert info.provider_uid == "42"
    assert info.email == "x@y.com"


async def test_exchange_twitch_userinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "twitch_oauth_client_id", "tid")
    monkeypatch.setattr(settings, "twitch_oauth_client_secret", "tsecret")
    provider = build_provider("twitch", settings)
    assert provider is not None
    fake = _client_factory(
        {"access_token": "at"},
        {"data": [{"id": "7", "login": "g", "display_name": "G", "email": "g@t.tv"}]},
    )
    monkeypatch.setattr(flow.httpx, "AsyncClient", fake)
    info = await flow.exchange_code_for_user(provider, "code", "verifier", "https://api/cb")
    assert info.provider_uid == "7"
    assert info.email_verified is True


async def test_exchange_missing_access_token_raises(
    monkeypatch: pytest.MonkeyPatch, google_provider: Any
) -> None:
    monkeypatch.setattr(flow.httpx, "AsyncClient", _client_factory({}, {}))
    with pytest.raises(OAuthError):
        await flow.exchange_code_for_user(google_provider, "c", "v", "https://api/cb")


async def test_exchange_token_http_error_raises(
    monkeypatch: pytest.MonkeyPatch, google_provider: Any
) -> None:
    fake = _client_factory({"access_token": "at"}, {}, token_status=400)
    monkeypatch.setattr(flow.httpx, "AsyncClient", fake)
    with pytest.raises(OAuthError):
        await flow.exchange_code_for_user(google_provider, "c", "v", "https://api/cb")


async def test_exchange_userinfo_http_error_raises(
    monkeypatch: pytest.MonkeyPatch, google_provider: Any
) -> None:
    fake = _client_factory({"access_token": "at"}, {}, userinfo_status=500)
    monkeypatch.setattr(flow.httpx, "AsyncClient", fake)
    with pytest.raises(OAuthError):
        await flow.exchange_code_for_user(google_provider, "c", "v", "https://api/cb")


# ── state_store ─────────────────────────────────────────────────────────


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def getdel(self, key: str) -> str | None:
        return self.store.pop(key, None)


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(state_mod, "get_redis_client", lambda: fake)
    return fake


async def test_state_round_trip(fake_redis: _FakeRedis) -> None:
    await store_state("st", OAuthState(provider="google", code_verifier="v"))
    out = await consume_state("st")
    assert out is not None
    assert out.provider == "google"
    assert out.code_verifier == "v"
    # Single-use: a second consume misses.
    assert await consume_state("st") is None


async def test_consume_missing_returns_none(fake_redis: _FakeRedis) -> None:
    assert await consume_state("nope") is None


async def test_consume_malformed_returns_none(fake_redis: _FakeRedis) -> None:
    fake_redis.store["oauth:state:bad"] = "{not json"
    assert await consume_state("bad") is None
