"""Deterministic research client for tests and offline development.

Returns canned, spoiler-light results keyed off the game title in the query
so graph integration tests are fully deterministic and need no network.
"""

from __future__ import annotations

from .base import AbstractResearchClient, SearchResult

# A small bank of canned results keyed by a lowercase substring of the query.
_CANNED: dict[str, list[SearchResult]] = {
    "hollow knight": [
        SearchResult(
            title="Hollow Knight — Greenpath walkthrough",
            url="https://example.test/hollow-knight/greenpath",
            snippet=(
                "From Greenpath, head west to reach the Queen's Station and the "
                "tram. Stock up on charms before exploring deeper areas."
            ),
        ),
        SearchResult(
            title="Hollow Knight map progression guide",
            url="https://example.test/hollow-knight/map",
            snippet=(
                "Buy the map from Cornifer in each region. The northwest passage "
                "from Greenpath opens once you have the Mantis Claw."
            ),
        ),
    ],
    "elden ring": [
        SearchResult(
            title="Elden Ring — Limgrave early routes",
            url="https://example.test/elden-ring/limgrave",
            snippet=(
                "From the first grace, ride north along the road toward the "
                "Gatefront ruins. Several caves to the east are worth exploring."
            ),
        ),
    ],
}

_FALLBACK = [
    SearchResult(
        title="General walkthrough",
        url="https://example.test/walkthrough",
        snippet="Continue exploring the current area and finish your active objective.",
    ),
]


class DummyResearchClient(AbstractResearchClient):
    """Canned web-search results for deterministic tests."""

    async def search(self, query: str, limit: int = 6) -> list[SearchResult]:
        """Return canned results matched by game title substring."""
        lowered = query.lower()
        for key, results in _CANNED.items():
            if key in lowered:
                return results[:limit]
        return _FALLBACK[:limit]

    async def fetch(self, url: str) -> str:
        """Return canned page text so scrape-enriched synthesis is deterministic."""
        return (
            "Walkthrough page. From your current area, head through the eastern "
            "passage and look for the locked door past the fountain; the lever for "
            "it is on the ledge above. Stock up on consumables before continuing."
        )


class EmptyResearchClient(AbstractResearchClient):
    """Research client that always returns nothing — exercises the empty/fallback path."""

    async def search(self, query: str, limit: int = 6) -> list[SearchResult]:
        """Return no results regardless of *query*."""
        return []
