"""Backoffice play_sessions moderation service (Epic 21, Phase 6).

Browse and moderate every user's play_sessions: list/search with per-status tallies,
inspect a play_session, and force-clamp a stuck active play_session (end it now, the
panel counterpart to the periodic ``auto_clamp`` worker). Every mutation is
audited and busts the owner's cached stats. Orchestrates repos only.
"""

from __future__ import annotations

from uuid import UUID

from slate.core.admin.logging import log_admin_event
from slate.core.admin.schemas import (
    AdminPlaySessionDetail,
    AdminPlaySessionList,
    AdminPlaySessionSummary,
    PlaySessionStatusCount,
)
from slate.core.cache.invalidation import invalidate_user_stats
from slate.infrastructure.db.models import PlaySession, User
from slate.infrastructure.db.repositories.admin import AdminAuditRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.db.repositories.user import UserRepository

ACTION_CLAMP = "play_session.clamp"
ENDED_VIA_ADMIN = "admin_clamp"


class PlaySessionNotFoundError(Exception):
    """Raised when a backoffice action targets an unknown play_session public_id."""


class PlaySessionNotActiveError(Exception):
    """Raised when a clamp targets a play_session that has already ended."""


def _status(play_session: PlaySession) -> str:
    return "active" if play_session.ended_at is None else "ended"


class AdminPlaySessionService:
    """PlaySessions moderation for the backoffice."""

    def __init__(
        self,
        play_session_repo: PlaySessionRepository,
        user_repo: UserRepository,
        audit_repo: AdminAuditRepository,
    ) -> None:
        self._play_sessions = play_session_repo
        self._users = user_repo
        self._audit = audit_repo

    async def list_play_sessions(
        self,
        *,
        query: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> AdminPlaySessionList:
        """Return a page of play_sessions (with owner + game) + per-status tallies."""
        rows, total = await self._play_sessions.search_admin(
            query=query, status=status, limit=limit, offset=offset
        )
        counts = await self._play_sessions.status_counts()
        return AdminPlaySessionList(
            items=[_summary(m, email, title) for m, email, title in rows],
            total=total,
            limit=limit,
            offset=offset,
            status_counts=[
                PlaySessionStatusCount(status=s, count=n) for s, n in sorted(counts.items())
            ],
        )

    async def get_play_session(self, public_id: UUID) -> AdminPlaySessionDetail:
        """Return the full backoffice view of one play_session, or raise if unknown."""
        play_session = await self._require_play_session(public_id)
        return await self._detail(play_session)

    async def clamp_play_session(self, actor: User, public_id: UUID) -> AdminPlaySessionDetail:
        """Force-end an active play_session now (audited; busts the owner's stats)."""
        play_session = await self._require_play_session(public_id)
        if play_session.ended_at is not None:
            raise PlaySessionNotActiveError
        await self._play_sessions.end_play_session(play_session.id, ended_via=ENDED_VIA_ADMIN)
        await invalidate_user_stats(play_session.user_id)
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_CLAMP,
            target_user_id=play_session.user_id,
            detail=str(public_id),
        )
        log_admin_event(
            "admin_play_session_clamped",
            actor=actor,
            action=ACTION_CLAMP,
            target_user_id=play_session.user_id,
            resource_type="play_session",
            resource_public_id=public_id,
            play_session_id=play_session.id,
        )
        refreshed = await self._require_play_session(public_id)
        return await self._detail(refreshed)

    # ── Internals ──
    async def _require_play_session(self, public_id: UUID) -> PlaySession:
        play_session = await self._play_sessions.get_by_public_id(public_id)
        if play_session is None:
            raise PlaySessionNotFoundError
        return play_session

    async def _detail(self, play_session: PlaySession) -> AdminPlaySessionDetail:
        user = await self._users.get_by_id(play_session.user_id)
        entry = play_session.library_entry
        return AdminPlaySessionDetail(
            public_id=play_session.public_id,
            user_email=user.email if user is not None else None,
            game_title=entry.game.title if entry is not None and entry.game else None,
            status=_status(play_session),
            play_session_type=play_session.play_session_type,
            ended_via=play_session.ended_via,
            started_at=play_session.started_at,
            ended_at=play_session.ended_at,
            platform_label=(
                entry.platform.label if entry is not None and entry.platform else None
            ),
            recap_text=play_session.recap_text,
            wrap_up_text=play_session.wrap_up_text,
            has_extracted_state=play_session.extracted_state is not None,
        )


def _summary(
    play_session: PlaySession, email: str | None, game_title: str | None
) -> AdminPlaySessionSummary:
    return AdminPlaySessionSummary(
        public_id=play_session.public_id,
        user_email=email,
        game_title=game_title,
        status=_status(play_session),
        play_session_type=play_session.play_session_type,
        ended_via=play_session.ended_via,
        started_at=play_session.started_at,
        ended_at=play_session.ended_at,
    )
