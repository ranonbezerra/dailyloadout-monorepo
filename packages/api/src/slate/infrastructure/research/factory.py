"""Factory for research client selection."""

from __future__ import annotations

from slate.config import Settings

from .base import AbstractResearchClient


def get_research_client(settings: Settings) -> AbstractResearchClient:
    """Return the research client based on the configured provider."""
    provider = settings.research_provider

    if provider == "dummy":
        from slate.infrastructure.research.dummy import DummyResearchClient

        return DummyResearchClient()

    if provider == "searxng":
        from slate.infrastructure.research.searxng import SearxngResearchClient

        return SearxngResearchClient(settings)

    msg = f"Unknown research provider: {provider}"
    raise ValueError(msg)
