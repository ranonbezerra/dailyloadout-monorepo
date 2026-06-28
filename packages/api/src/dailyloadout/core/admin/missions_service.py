"""Backoffice missions moderation service (Epic 21, Phase 6).

Browse and moderate every user's missions: list/search with per-status tallies,
inspect a mission, and force-clamp a stuck active mission (end it now, the
panel counterpart to the periodic ``auto_clamp`` worker). Every mutation is
audited and busts the owner's cached stats. Orchestrates repos only.
"""

from __future__ import annotations

from uuid import UUID

from dailyloadout.core.admin.schemas import (
    AdminMissionDetail,
    AdminMissionList,
    AdminMissionSummary,
    MissionStatusCount,
)
from dailyloadout.core.cache.invalidation import invalidate_user_stats
from dailyloadout.infrastructure.db.models import Mission, User
from dailyloadout.infrastructure.db.repositories.admin import AdminAuditRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository

ACTION_CLAMP = "mission.clamp"
ENDED_VIA_ADMIN = "admin_clamp"


class MissionNotFoundError(Exception):
    """Raised when a backoffice action targets an unknown mission public_id."""


class MissionNotActiveError(Exception):
    """Raised when a clamp targets a mission that has already ended."""


def _status(mission: Mission) -> str:
    return "active" if mission.ended_at is None else "ended"


class AdminMissionService:
    """Missions moderation for the backoffice."""

    def __init__(
        self,
        mission_repo: MissionRepository,
        user_repo: UserRepository,
        audit_repo: AdminAuditRepository,
    ) -> None:
        self._missions = mission_repo
        self._users = user_repo
        self._audit = audit_repo

    async def list_missions(
        self,
        *,
        query: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> AdminMissionList:
        """Return a page of missions (with owner + game) + per-status tallies."""
        rows, total = await self._missions.search_admin(
            query=query, status=status, limit=limit, offset=offset
        )
        counts = await self._missions.status_counts()
        return AdminMissionList(
            items=[_summary(m, email, title) for m, email, title in rows],
            total=total,
            limit=limit,
            offset=offset,
            status_counts=[
                MissionStatusCount(status=s, count=n) for s, n in sorted(counts.items())
            ],
        )

    async def get_mission(self, public_id: UUID) -> AdminMissionDetail:
        """Return the full backoffice view of one mission, or raise if unknown."""
        mission = await self._require_mission(public_id)
        return await self._detail(mission)

    async def clamp_mission(self, actor: User, public_id: UUID) -> AdminMissionDetail:
        """Force-end an active mission now (audited; busts the owner's stats)."""
        mission = await self._require_mission(public_id)
        if mission.ended_at is not None:
            raise MissionNotActiveError
        await self._missions.end_mission(mission.id, ended_via=ENDED_VIA_ADMIN)
        await invalidate_user_stats(mission.user_id)
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_CLAMP,
            target_user_id=mission.user_id,
            detail=str(public_id),
        )
        refreshed = await self._require_mission(public_id)
        return await self._detail(refreshed)

    # ── Internals ──
    async def _require_mission(self, public_id: UUID) -> Mission:
        mission = await self._missions.get_by_public_id(public_id)
        if mission is None:
            raise MissionNotFoundError
        return mission

    async def _detail(self, mission: Mission) -> AdminMissionDetail:
        user = await self._users.get_by_id(mission.user_id)
        entry = mission.library_entry
        return AdminMissionDetail(
            public_id=mission.public_id,
            user_email=user.email if user is not None else None,
            game_title=entry.game.title if entry is not None and entry.game else None,
            status=_status(mission),
            mission_type=mission.mission_type,
            ended_via=mission.ended_via,
            started_at=mission.started_at,
            ended_at=mission.ended_at,
            platform_label=(
                entry.platform.label if entry is not None and entry.platform else None
            ),
            briefing_text=mission.briefing_text,
            debrief_text=mission.debrief_text,
            has_extracted_state=mission.extracted_state is not None,
        )


def _summary(mission: Mission, email: str | None, game_title: str | None) -> AdminMissionSummary:
    return AdminMissionSummary(
        public_id=mission.public_id,
        user_email=email,
        game_title=game_title,
        status=_status(mission),
        mission_type=mission.mission_type,
        ended_via=mission.ended_via,
        started_at=mission.started_at,
        ended_at=mission.ended_at,
    )
