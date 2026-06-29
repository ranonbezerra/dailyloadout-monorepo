"""Base classes for web research clients used by the deep recap agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ResearchUnavailableError(RuntimeError):
    """Raised when the research backend cannot be reached."""


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str


class AbstractResearchClient(ABC):
    """Contract for web search clients (local SearXNG, dummy, ...)."""

    @abstractmethod
    async def search(self, query: str, limit: int = 6) -> list[SearchResult]:
        """Return up to *limit* search results for *query*."""
        ...

    async def fetch(self, url: str) -> str:
        """Return cleaned page text for *url*, for richer recap grounding.

        Optional capability: the default returns an empty string (snippets-only
        grounding). Providers that can scrape override this.
        """
        return ""
