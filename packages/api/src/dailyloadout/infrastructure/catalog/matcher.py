"""IGDB-backed catalog matcher: fuzzy-match OCR lines to canonical games.

Each line is searched against IGDB (reusing the Epic 3 client) and the best
candidate is chosen by token-sort similarity. No LLM is involved — this is the
deterministic post-correction step that repairs OCR swaps (``l``/``I``) and
punctuation noise (``Sid Meier's Civ VI`` -> ``Sid Meier's Civilization VI``).
"""

from __future__ import annotations

import re

import structlog
from rapidfuzz import fuzz

from dailyloadout.infrastructure.igdb.base import IGDBSearchClient
from dailyloadout.infrastructure.igdb.schemas import IGDBGame

from .base import AbstractCatalogMatcher, CatalogMatch

logger = structlog.get_logger()

_DEFAULT_MIN_SCORE = 0.6
_SEARCH_LIMIT = 5


def _normalize(text: str) -> str:
    """Lowercase and reduce to alphanumeric tokens for comparison."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def best_match(
    line_text: str, candidates: list[IGDBGame], min_score: float
) -> tuple[IGDBGame, float] | None:
    """Return the best (candidate, score) above *min_score*, or ``None``.

    Pure function over a candidate list so the scoring is unit-testable without
    a live IGDB call.
    """
    norm_line = _normalize(line_text)
    if not norm_line:
        return None

    best: IGDBGame | None = None
    best_score = 0.0
    for candidate in candidates:
        score = fuzz.token_sort_ratio(norm_line, _normalize(candidate.title)) / 100.0
        if score > best_score:
            best_score = score
            best = candidate

    if best is not None and best_score >= min_score:
        return best, best_score
    return None


class IGDBCatalogMatcher(AbstractCatalogMatcher):
    def __init__(
        self, igdb_client: IGDBSearchClient, min_score: float = _DEFAULT_MIN_SCORE
    ) -> None:
        self._igdb_client = igdb_client
        self._min_score = min_score

    async def match(self, line_text: str) -> CatalogMatch:
        cleaned = line_text.strip()
        try:
            candidates = await self._igdb_client.search_games(cleaned, limit=_SEARCH_LIMIT)
        except Exception:
            logger.warning("catalog_igdb_search_failed", exc_info=True)
            candidates = []

        result = best_match(cleaned, candidates, self._min_score)
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
