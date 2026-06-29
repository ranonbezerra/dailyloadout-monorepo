"""Deterministic catalog matcher for tests and offline development.

Matches OCR lines against a small canned catalog using the same fuzzy scorer as
the real matcher (with a light OCR de-confusion pass), so worker/endpoint tests
get realistic enrichment without a live IGDB call.
"""

from __future__ import annotations

from datetime import date

from slate.infrastructure.igdb.schemas import IGDBGame

from .base import AbstractCatalogMatcher, CatalogMatch
from .matcher import best_match

# A handful of canonical games used to enrich matches deterministically.
_CANNED_CATALOG = [
    IGDBGame(
        igdb_id=1,
        title="Hollow Knight",
        cover_url="https://example.test/hk.jpg",
        summary="A challenging Metroidvania.",
        genres=["Metroidvania", "Platformer"],
        first_release_date=date(2017, 2, 24),
    ),
    IGDBGame(igdb_id=2, title="Celeste", genres=["Platformer"]),
    IGDBGame(igdb_id=3, title="Hades", genres=["Roguelike"]),
    IGDBGame(igdb_id=4, title="Sid Meier's Civilization VI", genres=["Strategy"]),
]

# Common OCR glyph confusions, de-confused before scoring.
_OCR_CONFUSIONS = str.maketrans({"0": "o", "1": "l", "5": "s"})
_DUMMY_MIN_SCORE = 0.55


class DummyCatalogMatcher(AbstractCatalogMatcher):
    def __init__(self, catalog: list[IGDBGame] | None = None) -> None:
        self._catalog = catalog if catalog is not None else _CANNED_CATALOG

    async def match(self, line_text: str) -> CatalogMatch:
        cleaned = line_text.strip()
        deconfused = cleaned.translate(_OCR_CONFUSIONS)
        result = best_match(deconfused, self._catalog, _DUMMY_MIN_SCORE)
        if result is None:
            return CatalogMatch(line_text=cleaned, matched=False, confidence=0.0, title=cleaned)

        game, score = result
        return CatalogMatch(
            line_text=cleaned,
            matched=True,
            confidence=score,
            title=game.title,
            igdb_id=game.igdb_id,
            cover_url=game.cover_url,
            summary=game.summary,
            genres=game.genres,
            first_release_date=game.first_release_date,
        )
