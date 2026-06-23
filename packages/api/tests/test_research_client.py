"""Tests for the web research port (dummy, searxng, factory)."""

from __future__ import annotations

import httpx
import pytest

from dailyloadout.config import Settings
from dailyloadout.infrastructure.research.base import (
    ResearchUnavailableError,
    SearchResult,
)
from dailyloadout.infrastructure.research.dummy import (
    DummyResearchClient,
    EmptyResearchClient,
)
from dailyloadout.infrastructure.research.factory import get_research_client
from dailyloadout.infrastructure.research.searxng import SearxngResearchClient


class TestDummyResearchClient:
    async def test_returns_canned_results_for_known_game(self) -> None:
        client = DummyResearchClient()
        results = await client.search("Hollow Knight greenpath next steps")
        assert results
        assert all(isinstance(r, SearchResult) for r in results)
        assert "greenpath" in results[0].url.lower()

    async def test_respects_limit(self) -> None:
        client = DummyResearchClient()
        results = await client.search("Hollow Knight", limit=1)
        assert len(results) == 1

    async def test_unknown_game_returns_fallback(self) -> None:
        client = DummyResearchClient()
        results = await client.search("Some Obscure Indie Title")
        assert len(results) == 1
        assert results[0].title == "General walkthrough"

    async def test_empty_client_returns_nothing(self) -> None:
        results = await EmptyResearchClient().search("Hollow Knight")
        assert results == []


class TestSearxngResearchClient:
    def _client_with_transport(self, handler: object) -> SearxngResearchClient:
        settings = Settings(searxng_base_url="http://searxng.test")
        client = SearxngResearchClient(settings)
        transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
        client._http_client = httpx.AsyncClient(transport=transport)
        return client

    async def test_parses_results(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["format"] == "json"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Guide",
                            "url": "https://x.test/g",
                            "content": "Go west.",
                        },
                        {"title": "Other", "url": "https://x.test/o", "content": "Stuff."},
                    ]
                },
            )

        client = self._client_with_transport(handler)
        results = await client.search("Hollow Knight", limit=5)
        assert len(results) == 2
        assert results[0] == SearchResult("Guide", "https://x.test/g", "Go west.")

    async def test_limit_truncates(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            items = [{"title": f"r{i}", "url": "u", "content": "c"} for i in range(10)]
            return httpx.Response(200, json={"results": items})

        client = self._client_with_transport(handler)
        results = await client.search("q", limit=3)
        assert len(results) == 3

    async def test_http_error_raises_unavailable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        client = self._client_with_transport(handler)
        with pytest.raises(ResearchUnavailableError):
            await client.search("q")

    async def test_malformed_items_skipped(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"results": ["not-a-dict", {"title": "ok"}]})

        client = self._client_with_transport(handler)
        results = await client.search("q")
        assert len(results) == 1
        assert results[0].title == "ok"


class TestResearchFactory:
    def test_dummy_provider(self) -> None:
        client = get_research_client(Settings(research_provider="dummy"))
        assert isinstance(client, DummyResearchClient)

    def test_searxng_provider(self) -> None:
        client = get_research_client(Settings(research_provider="searxng"))
        assert isinstance(client, SearxngResearchClient)

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown research provider"):
            get_research_client(Settings(research_provider="bogus"))
