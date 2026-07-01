"""Repository for the ``capture_candidates`` table.

Split out of ``capture.py`` (which kept the ``captures`` repo) to stay under the
300-line file cap. Still importable from either module for back-compat.
"""

from __future__ import annotations

from datetime import date
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from slate.infrastructure.catalog.base import CatalogMatch
from slate.infrastructure.db.models import CaptureCandidate


class CaptureCandidateRepository:
    """Thin data-access layer around the ``capture_candidates`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        capture_id: int,
        title: str,
        platform_hint: str | None = None,
        confidence: float | None = None,
        igdb_id: int | None = None,
        igdb_title: str | None = None,
        igdb_cover_url: str | None = None,
        igdb_summary: str | None = None,
        igdb_genres: list[str] | None = None,
        igdb_first_release_date: date | None = None,
    ) -> CaptureCandidate:
        """Insert a single capture candidate and return it."""
        candidate = CaptureCandidate(
            capture_id=capture_id,
            title=title,
            platform_hint=platform_hint,
            confidence=confidence,
            igdb_id=igdb_id,
            igdb_title=igdb_title,
            igdb_cover_url=igdb_cover_url,
            igdb_summary=igdb_summary,
            igdb_genres=igdb_genres,
            igdb_first_release_date=igdb_first_release_date,
        )
        self._session.add(candidate)
        await self._session.flush()
        return candidate

    async def create_bulk(
        self,
        capture_id: int,
        candidates: list[dict[str, object]],
    ) -> list[CaptureCandidate]:
        """Insert multiple candidates at once and return them all."""
        results: list[CaptureCandidate] = []
        for data in candidates:
            candidate = CaptureCandidate(capture_id=capture_id, **data)
            self._session.add(candidate)
            results.append(candidate)
        await self._session.flush()
        return results

    async def get_by_public_id(self, public_id: UUID) -> CaptureCandidate | None:
        """Return the candidate with *public_id*, or ``None``."""
        stmt = (
            select(CaptureCandidate)
            .options(joinedload(CaptureCandidate.matched_game))
            .where(CaptureCandidate.public_id == public_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        candidate_id: int,
        status: str,
        matched_game_id: int | None = None,
    ) -> None:
        """Update the status (and optionally matched game) of a candidate."""
        candidate = await self._session.get(CaptureCandidate, candidate_id)
        if candidate is not None:
            candidate.status = status
            if matched_game_id is not None:
                candidate.matched_game_id = matched_game_id
            await self._session.flush()

    async def claim_status(
        self,
        candidate_id: int,
        new_status: str,
        *,
        expected: str = "pending",
    ) -> bool:
        """Atomically move a candidate out of *expected* (default ``pending``).

        Conditional UPDATE so two concurrent confirm/reject calls on the same
        candidate can't both win — the loser's UPDATE matches 0 rows and the
        caller maps it to a 409 (or skips it, in the bulk path). Returns ``True``
        if this call claimed the candidate. The matched game is attached
        afterwards via :meth:`update_status` once it's known.
        """
        result = await self._session.execute(
            update(CaptureCandidate)
            .where(
                CaptureCandidate.id == candidate_id,
                CaptureCandidate.status == expected,
            )
            .values(status=new_status)
        )
        await self._session.flush()
        return (cast("CursorResult[Any]", result).rowcount or 0) > 0

    async def set_title(self, candidate_id: int, title: str) -> None:
        """Override a candidate's title, clearing its stale igdb_* enrichment."""
        candidate = await self._session.get(CaptureCandidate, candidate_id)
        if candidate is not None:
            candidate.title = title
            candidate.igdb_id = None
            candidate.igdb_title = None
            candidate.igdb_cover_url = None
            candidate.igdb_summary = None
            candidate.igdb_genres = None
            candidate.igdb_first_release_date = None
            await self._session.flush()

    async def apply_match(self, candidate_id: int, match: CatalogMatch) -> None:
        """Re-apply a fresh catalog *match* (title + igdb_* fields) after a title
        edit; ``status``/``matched_game_id`` stay untouched so it's still confirmable."""
        candidate = await self._session.get(CaptureCandidate, candidate_id)
        if candidate is not None:
            candidate.title = match.title
            candidate.confidence = match.confidence
            candidate.igdb_id = match.igdb_id
            candidate.igdb_title = match.title if match.matched else None
            candidate.igdb_cover_url = match.cover_url
            candidate.igdb_summary = match.summary
            candidate.igdb_genres = match.genres
            candidate.igdb_first_release_date = match.first_release_date
            await self._session.flush()

    async def delete_for_capture(self, capture_id: int) -> None:
        """Delete every candidate of *capture_id* (clears stale rows before reprocess)."""
        await self._session.execute(
            delete(CaptureCandidate).where(CaptureCandidate.capture_id == capture_id)
        )
        await self._session.flush()

    async def get_all_for_capture(self, capture_id: int) -> list[CaptureCandidate]:
        """Return all candidates belonging to *capture_id*."""
        stmt = (
            select(CaptureCandidate)
            .options(joinedload(CaptureCandidate.matched_game))
            .where(CaptureCandidate.capture_id == capture_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())
