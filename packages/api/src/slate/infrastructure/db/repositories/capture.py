"""Repository for the ``captures`` table.

The ``capture_candidates`` repo lives in ``capture_candidate.py`` (kept separate
for the 300-line cap) and is re-exported here so existing
``from ...repositories.capture import CaptureCandidateRepository`` imports keep
working.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from slate.infrastructure.db.like import LIKE_ESCAPE, escape_like
from slate.infrastructure.db.models import Capture, CaptureCandidate, User
from slate.infrastructure.db.repositories.capture_candidate import CaptureCandidateRepository

__all__ = ["CaptureCandidateRepository", "CaptureRepository"]


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
            conditions.append(User.email.ilike(f"%{escape_like(query)}%", escape=LIKE_ESCAPE))

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
