"""Unit tests for the raw IGDBClient query sanitization (injection guard)."""

from __future__ import annotations

from typing import Any

import pytest

from dailyloadout.config import Settings
from dailyloadout.infrastructure.igdb.client import IGDBClient
from dailyloadout.infrastructure.igdb.exceptions import IGDBNotConfiguredError


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
        return _SpyResponse({"access_token": "tok", "expires_in": 3600})  # type: ignore[arg-type]


async def test_search_sanitizes_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    import dailyloadout.infrastructure.igdb.client as mod

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
    import dailyloadout.infrastructure.igdb.client as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", _SpyAsyncClient)
    client = _client()

    await client.search_games("a\\b" + "x" * 500, limit=1)

    body = _SpyAsyncClient.last_body
    assert "\\" not in body
    # The interpolated term is capped at 200 chars: "ab" + 198 x's.
    assert 'search "ab' + "x" * 198 + '";' in body
