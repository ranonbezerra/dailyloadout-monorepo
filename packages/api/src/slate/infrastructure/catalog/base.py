"""Catalog matching port (ROADMAP Epic 14).

Turns a dirty OCR line into a canonical game by fuzzy-matching against a
reference catalog (IGDB). This is deterministic string work — no LLM call —
which is where most "wrong title" errors die for free.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class CatalogMatch:
    """The result of matching one OCR line against the canonical catalog."""

    line_text: str
    matched: bool
    confidence: float  # 0.0 - 1.0
    title: str  # canonical title when matched, else the cleaned line text
    igdb_id: int | None = None
    cover_url: str | None = None
    summary: str | None = None
    genres: list[str] | None = None
    first_release_date: date | None = None


class AbstractCatalogMatcher(ABC):
    """Contract for matching OCR lines to canonical games."""

    @abstractmethod
    async def match(self, line_text: str) -> CatalogMatch:
        """Match a single line; ``matched=False`` keeps the cleaned text."""
        ...

    async def match_many(self, lines: list[str]) -> list[CatalogMatch]:
        """Match several lines. Default: sequential ``match`` calls."""
        return [await self.match(line) for line in lines]
