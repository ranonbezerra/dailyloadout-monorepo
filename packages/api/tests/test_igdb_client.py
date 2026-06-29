"""Unit tests for the raw IGDBClient query sanitization (injection guard)."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from slate.config import Settings
from slate.infrastructure.igdb.client import IGDBClient
from slate.infrastructure.igdb.exceptions import IGDBNotConfiguredError


def _client() -> IGDBClient:
    return IGDBClient(Settings(igdb_client_id="cid", igdb_client_secret="secret"))


def test_requires_credentials() -> None:
    with pytest.raises(IGDBNotConfiguredError):
        IGDBClient(Settings(igdb_client_id="", igdb_client_secret=""))


class _SpyResponse:
    def __init__(self, payload: list[dict[str, Any]]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, Any]]:
        return self._payload


class _SpyAsyncClient:
    """Captures the Apicalypse body sent to the games endpoint."""

    last_body: str = ""
    token_kwargs: ClassVar[dict[str, Any]] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> _SpyAsyncClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> _SpyResponse:
        if url.endswith("/games"):
            _SpyAsyncClient.last_body = kwargs["content"]
            return _SpyResponse([])
        # token endpoint
        _SpyAsyncClient.token_kwargs = kwargs
        return _SpyResponse({"access_token": "tok", "expires_in": 3600})  # type: ignore[arg-type]


async def test_token_sends_secret_in_body_not_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import slate.infrastructure.igdb.client as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", _SpyAsyncClient)
    client = _client()
    await client.search_games("Zelda", limit=1)

    kwargs = _SpyAsyncClient.token_kwargs
    # Credentials go in the POST body, never the query string.
    assert "params" not in kwargs
    assert kwargs["data"]["client_secret"] == "secret"
    assert kwargs["data"]["grant_type"] == "client_credentials"


async def test_token_http_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing token request never surfaces the secret; raises a clean error."""
    import httpx

    import slate.infrastructure.igdb.client as mod
    from slate.infrastructure.igdb.exceptions import IGDBNotConfiguredError

    class _FailingTokenClient(_SpyAsyncClient):
        async def post(self, url: str, **kwargs: Any) -> _SpyResponse:
            request = httpx.Request("POST", url, params={"client_secret": "secret"})
            response = httpx.Response(400, request=request)

            class _Resp:
                def raise_for_status(self) -> None:
                    raise httpx.HTTPStatusError("bad", request=request, response=response)

                def json(self) -> dict[str, Any]:  # pragma: no cover
                    return {}

            return _Resp()  # type: ignore[return-value]

    monkeypatch.setattr(mod.httpx, "AsyncClient", _FailingTokenClient)
    client = _client()
    with pytest.raises(IGDBNotConfiguredError) as exc_info:
        await client.search_games("Zelda", limit=1)
    # The clean error message must not leak the secret.
    assert "secret" not in str(exc_info.value)


async def test_search_sanitizes_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    import slate.infrastructure.igdb.client as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", _SpyAsyncClient)
    client = _client()

    # A malicious title trying to break out of the quoted search term.
    await client.search_games('Zelda"; fields *; where id = 1;', limit=3)

    body = _SpyAsyncClient.last_body
    # The injected quote is stripped, so the search term stays a single token.
    assert '"; fields *' not in body
    assert body.startswith('search "Zelda; fields *; where id = 1;";')


async def test_search_strips_backslashes_and_caps_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import slate.infrastructure.igdb.client as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", _SpyAsyncClient)
    client = _client()

    await client.search_games("a\\b" + "x" * 500, limit=1)

    body = _SpyAsyncClient.last_body
    assert "\\" not in body
    # The interpolated term is capped at 200 chars: "ab" + 198 x's.
    assert 'search "ab' + "x" * 198 + '";' in body
