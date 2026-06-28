"""Backoffice captures moderation service (Epic 21, Phase 6).

Browse and moderate every user's captures: list/search with per-status tallies,
inspect a capture's review queue, reprocess a stuck/failed text capture (re-runs
the inline pipeline after clearing its stale candidates), and purge one outright.
Every mutation is audited. Orchestrates repos + the worker pipeline only.
"""

from __future__ import annotations

from uuid import UUID

from dailyloadout.core.admin.schemas import (
    AdminCaptureCandidate,
    AdminCaptureDetail,
    AdminCaptureList,
    AdminCaptureSummary,
    CaptureStatusCount,
)
from dailyloadout.core.capture.ports import CaptureProcessor
from dailyloadout.infrastructure.db.models import Capture, CaptureCandidate, User
from dailyloadout.infrastructure.db.repositories.admin import AdminAuditRepository
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.db.repositories.user import UserRepository
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

ACTION_REPROCESS = "capture.reprocess"
ACTION_PURGE = "capture.purge"


class CaptureNotFoundError(Exception):
    """Raised when a backoffice action targets an unknown capture public_id."""


class CaptureNotReprocessableError(Exception):
    """Raised when a capture has no re-runnable source (e.g. a photo whose temp
    upload was already discarded after the first pass)."""


class AdminCaptureService:
    """Captures moderation for the backoffice."""

    def __init__(
        self,
        capture_repo: CaptureRepository,
        candidate_repo: CaptureCandidateRepository,
        audit_repo: AdminAuditRepository,
        user_repo: UserRepository,
        *,
        llm_client: AbstractLLMClient,
        igdb_client: IGDBSearchClient | None,
        process_capture: CaptureProcessor,
    ) -> None:
        self._captures = capture_repo
        self._candidates = candidate_repo
        self._audit = audit_repo
        self._users = user_repo
        self._llm = llm_client
        self._igdb = igdb_client
        self._process_capture = process_capture

    async def list_captures(
        self,
        *,
        query: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> AdminCaptureList:
        """Return a page of captures (with candidate counts) + status tallies."""
        rows, total = await self._captures.search_admin(
            query=query, status=status, limit=limit, offset=offset
        )
        counts = await self._captures.status_counts()
        return AdminCaptureList(
            items=[_summary(c, email, n) for c, email, n in rows],
            total=total,
            limit=limit,
            offset=offset,
            status_counts=[
                CaptureStatusCount(status=s, count=n) for s, n in sorted(counts.items())
            ],
        )

    async def get_capture(self, public_id: UUID) -> AdminCaptureDetail:
        """Return the full backoffice view of one capture, or raise if unknown."""
        capture = await self._require_capture(public_id)
        candidates = await self._candidates.get_all_for_capture(capture.id)
        return await self._detail(capture, candidates)

    async def reprocess_capture(self, actor: User, public_id: UUID) -> AdminCaptureDetail:
        """Re-run the pipeline for a text/voice capture (clears stale candidates)."""
        capture = await self._require_capture(public_id)
        if not capture.raw_text:
            raise CaptureNotReprocessableError
        await self._candidates.delete_for_capture(capture.id)
        await self._process_capture(
            capture=capture,
            capture_repo=self._captures,
            candidate_repo=self._candidates,
            llm_client=self._llm,
            igdb_client=self._igdb,
        )
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_REPROCESS,
            target_user_id=capture.user_id,
            detail=str(public_id),
        )
        # Re-fetch: the pipeline's flushes expire server-default columns (e.g.
        # ``updated_at``) on the in-memory row, so a fresh SELECT repopulates
        # them; candidates are likewise read fresh after the clear + re-insert.
        refreshed = await self._require_capture(public_id)
        candidates = await self._candidates.get_all_for_capture(refreshed.id)
        return await self._detail(refreshed, candidates)

    async def purge_capture(self, actor: User, public_id: UUID) -> None:
        """Hard-delete a capture and its candidates, audited."""
        capture = await self._require_capture(public_id)
        target_user_id = capture.user_id
        await self._captures.delete(capture)
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_PURGE,
            target_user_id=target_user_id,
            detail=str(public_id),
        )

    # ── Internals ──
    async def _require_capture(self, public_id: UUID) -> Capture:
        capture = await self._captures.get_admin(public_id)
        if capture is None:
            raise CaptureNotFoundError
        return capture

    async def _detail(
        self, capture: Capture, candidates: list[CaptureCandidate]
    ) -> AdminCaptureDetail:
        user = await self._users.get_by_id(capture.user_id)
        return AdminCaptureDetail(
            public_id=capture.public_id,
            user_email=user.email if user is not None else None,
            input_type=capture.input_type,
            status=capture.status,
            candidate_count=len(candidates),
            error_message=capture.error_message,
            created_at=capture.created_at,
            updated_at=capture.updated_at,
            raw_text=capture.raw_text,
            reprocessable=bool(capture.raw_text),
            candidates=[_candidate(c) for c in candidates],
        )


def _summary(capture: Capture, email: str | None, candidate_count: int) -> AdminCaptureSummary:
    return AdminCaptureSummary(
        public_id=capture.public_id,
        user_email=email,
        input_type=capture.input_type,
        status=capture.status,
        candidate_count=candidate_count,
        error_message=capture.error_message,
        created_at=capture.created_at,
        updated_at=capture.updated_at,
    )


def _candidate(candidate: CaptureCandidate) -> AdminCaptureCandidate:
    return AdminCaptureCandidate(
        public_id=candidate.public_id,
        title=candidate.title,
        status=candidate.status,
        confidence=candidate.confidence,
        igdb_id=candidate.igdb_id,
        matched_game_title=(
            candidate.matched_game.title if candidate.matched_game is not None else None
        ),
    )
