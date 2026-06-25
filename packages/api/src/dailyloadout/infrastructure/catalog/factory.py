"""Factory for the catalog matcher.

Uses the dummy under tests or when IGDB is unconfigured; otherwise the
IGDB-backed fuzzy matcher.
"""

from __future__ import annotations

from dailyloadout.config import Settings
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient

from .base import AbstractCatalogMatcher


def get_catalog_matcher(
    settings: Settings, igdb_client: IGDBSearchClient | None
) -> AbstractCatalogMatcher:
    """Return the catalog matcher for the current environment.

    Falls back to the dummy when running tests or when no IGDB client is
    configured, so the import path always has a working matcher.
    """
    if settings.app_env == "testing" or igdb_client is None:
        from .dummy import DummyCatalogMatcher

        return DummyCatalogMatcher()

    from .matcher import IGDBCatalogMatcher

    return IGDBCatalogMatcher(igdb_client, min_score=settings.catalog_match_min_score)
