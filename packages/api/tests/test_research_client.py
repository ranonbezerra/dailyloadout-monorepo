"""Tests for the web research port (dummy, searxng, factory)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from dailyloadout.config import Settings
from dailyloadout.infrastructure.research._html import extract_text
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

    async def test_dummy_fetch_returns_canned_page_text(self) -> None:
        text = await DummyResearchClient().fetch("https://x.test/guide")
        assert "locked door past the fountain" in text

    async def test_base_fetch_defaults_to_empty(self) -> None:
        # EmptyResearchClient doesn't override fetch — inherits the empty default.
        assert await EmptyResearchClient().fetch("https://x.test") == ""


class TestHtmlExtraction:
    def test_strips_scripts_styles_and_tags(self) -> None:
        html = (
            "<html><head><style>.x{color:red}</style></head>"
            "<body><script>alert(1)</script>"
            "<h1>Greenpath</h1><p>Head <b>west</b> to the station.</p></body></html>"
        )
        text = extract_text(html)
        assert "Greenpath" in text
        assert "Head west to the station." in text
        assert "alert" not in text
        assert "color:red" not in text

    def test_truncates_to_max_chars(self) -> None:
        html = "<p>" + ("word " * 5000) + "</p>"
        assert len(extract_text(html, max_chars=500)) <= 500


@pytest.fixture
def make_searxng_client():
    """Build SearxngResearchClients backed by a MockTransport, closed on teardown."""
    created: list[SearxngResearchClient] = []

    def _make(handler: object) -> SearxngResearchClient:
        client = SearxngResearchClient(Settings(searxng_base_url="http://searxng.test"))
        client._http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
        created.append(client)
        return client

    yield _make

    async def _close() -> None:
        for c in created:
            if c._http_client is not None:
                await c._http_client.aclose()

    asyncio.run(_close())


class TestSearxngResearchClient:
    async def test_parses_results(self, make_searxng_client) -> None:
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

        client = make_searxng_client(handler)
        results = await client.search("Hollow Knight", limit=5)
        assert len(results) == 2
        assert results[0] == SearchResult("Guide", "https://x.test/g", "Go west.")

    async def test_limit_truncates(self, make_searxng_client) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            items = [{"title": f"r{i}", "url": "u", "content": "c"} for i in range(10)]
            return httpx.Response(200, json={"results": items})

        client = make_searxng_client(handler)
        results = await client.search("q", limit=3)
        assert len(results) == 3

    async def test_http_error_raises_unavailable(self, make_searxng_client) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        client = make_searxng_client(handler)
        with pytest.raises(ResearchUnavailableError):
            await client.search("q")

    async def test_malformed_items_skipped(self, make_searxng_client) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"results": ["not-a-dict", {"title": "ok"}]})

        client = make_searxng_client(handler)
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
