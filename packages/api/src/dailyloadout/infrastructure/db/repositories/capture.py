"""Repositories for the ``captures`` and ``capture_candidates`` tables."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dailyloadout.infrastructure.db.models import Capture, CaptureCandidate, User


class CaptureRepository:
    """Thin data-access layer around the ``captures`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        input_type: str,
        raw_text: str | None = None,
        audio_path: str | None = None,
        image_path: str | None = None,
    ) -> Capture:
        """Insert a new capture and return the persisted instance."""
        capture = Capture(
            user_id=user_id,
            input_type=input_type,
            raw_text=raw_text,
            audio_path=audio_path,
            image_path=image_path,
        )
        self._session.add(capture)
        await self._session.flush()
        return capture

    async def get_by_public_id(
        self,
        public_id: UUID,
        user_id: int | None = None,
    ) -> Capture | None:
        """Return the capture with *public_id*, optionally scoped to *user_id*.

        Eagerly loads candidates and their matched games.
        """
        stmt = (
            select(Capture)
            .options(
                joinedload(Capture.candidates).joinedload(CaptureCandidate.matched_game),
            )
            .where(Capture.public_id == public_id)
        )
        if user_id is not None:
            stmt = stmt.where(Capture.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Capture]:
        """Return captures for *user_id* ordered by newest first."""
        stmt = (
            select(Capture)
            .options(joinedload(Capture.candidates))
            .where(Capture.user_id == user_id)
        )
        if status is not None:
            stmt = stmt.where(Capture.status == status)
        stmt = stmt.order_by(Capture.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: int, status: str | None = None) -> int:
        """Return the total number of captures for *user_id*."""
        stmt = select(func.count(Capture.id)).where(Capture.user_id == user_id)
        if status is not None:
            stmt = stmt.where(Capture.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update_status(
        self,
        capture_id: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update the status (and optionally the error message) of a capture."""
        capture = await self._session.get(Capture, capture_id)
        if capture is not None:
            capture.status = status
            capture.error_message = error_message
            await self._session.flush()

    async def get_queued(self) -> Capture | None:
        """Return the oldest capture still in ``queued`` status, or ``None``."""
        stmt = (
            select(Capture)
            .where(Capture.status == "queued")
            .order_by(Capture.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Backoffice (admin) ──
    async def search_admin(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Capture, str, int]], int]:
        """Return a page of captures (each with owner email + candidate count).

        Unlike the user-facing list, this spans every user's captures. ``query``
        matches the owner's email; ``status`` filters the lifecycle state. The
        candidate count is the review-queue size an admin weighs before purging
        or reprocessing a stuck capture.
        """
        conditions: list[ColumnElement[bool]] = []
        if status:
            conditions.append(Capture.status == status)
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(User.email.ilike(f"%{escaped}%"))

        total = (
            await self._session.scalar(
                select(func.count(Capture.id))
                .join(User, Capture.user_id == User.id)
                .where(*conditions)
            )
        ) or 0
        candidate_count = func.count(CaptureCandidate.id)
        result = await self._session.execute(
            select(Capture, User.email, candidate_count)
            .join(User, Capture.user_id == User.id)
            .outerjoin(CaptureCandidate, CaptureCandidate.capture_id == Capture.id)
            .where(*conditions)
            .group_by(Capture.id, User.email)
            .order_by(Capture.created_at.desc(), Capture.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = [(capture, email, count) for capture, email, count in result.all()]
        return rows, total

    async def get_admin(self, public_id: UUID) -> Capture | None:
        """Return a capture by *public_id* WITHOUT eager-loading candidates.

        The backoffice loads candidates separately (``get_all_for_capture``), so
        keeping this collection unloaded avoids a stale in-memory collection (and
        its delete-orphan cascade) interfering with the reprocess clear+re-insert.
        """
        stmt = select(Capture).where(Capture.public_id == public_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def status_counts(self) -> dict[str, int]:
        """Return ``{status: count}`` across all captures for the admin overview."""
        result = await self._session.execute(
            select(Capture.status, func.count(Capture.id)).group_by(Capture.status)
        )
        return {status: count for status, count in result.all()}

    async def delete(self, capture: Capture) -> None:
        """Hard-delete a capture (its candidates cascade away)."""
        await self._session.delete(capture)
        await self._session.flush()


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

    async def set_title(self, candidate_id: int, title: str) -> None:
        """Override a candidate's title, dropping its stale catalog enrichment.

        A user-corrected title no longer corresponds to the matched IGDB game,
        so the igdb_* fields are cleared and the entry becomes user-authored.
        """
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
