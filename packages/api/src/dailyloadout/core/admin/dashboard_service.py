"""Backoffice dashboard service (Epic 21, Phase 4).

Aggregates the at-a-glance metrics the admin landing screen shows: user
counts (total / banned / unverified / admins), active missions, catalogue size,
how many config knobs are currently overridden, and the most recent admin
actions. Read-only; orchestrates repositories only.
"""

from __future__ import annotations

from dailyloadout.core.admin.schemas import AdminAuditEntry, DashboardSummary
from dailyloadout.infrastructure.db.repositories.admin import AdminAuditRepository, AdminRepository
from dailyloadout.infrastructure.db.repositories.app_config import AppConfigRepository
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository

_RECENT_ACTIONS = 8


class AdminDashboardService:
    """Builds the dashboard summary from the read-side of each repository."""

    def __init__(
        self,
        user_repo: UserRepository,
        admin_repo: AdminRepository,
        audit_repo: AdminAuditRepository,
        config_repo: AppConfigRepository,
        mission_repo: MissionRepository,
        game_repo: GameRepository,
    ) -> None:
        self._users = user_repo
        self._admins = admin_repo
        self._audit = audit_repo
        self._config = config_repo
        self._missions = mission_repo
        self._games = game_repo

    async def summary(self) -> DashboardSummary:
        """Return the aggregate metrics for the dashboard landing screen."""
        _, total = await self._users.search(limit=1)
        _, banned = await self._users.search(is_banned=True, limit=1)
        _, unverified = await self._users.search(email_verified=False, limit=1)
        admins = await self._admins.count()
        missions_active = await self._missions.count_active()
        catalogue_size = await self._games.count_catalogue()
        overrides = await self._config.list_with_updater()
        rows, _ = await self._audit.list_recent(limit=_RECENT_ACTIONS)

        return DashboardSummary(
            users_total=total,
            users_banned=banned,
            users_unverified=unverified,
            admins=admins,
            missions_active=missions_active,
            catalogue_size=catalogue_size,
            config_overrides=len(overrides),
            recent_actions=[
                AdminAuditEntry(
                    action=r.action,
                    detail=r.detail,
                    created_at=r.created_at,
                    admin_public_id=r.admin_public_id,
                    admin_email=r.admin_email,
                    target_public_id=r.target_public_id,
                    target_email=r.target_email,
                )
                for r in rows
            ],
        )
