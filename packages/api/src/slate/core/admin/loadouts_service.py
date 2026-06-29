"""Backoffice loadouts read-only service (Epic 21, Phase 6).

Browse every user's loadout suggestions: list/search with per-action tallies
and inspect one. Read-only by design — loadouts decay on their own via the
``auto_ignore`` worker, so the backoffice only reads (no mutations, no audit).
Orchestrates repos only.
"""

from __future__ import annotations

from uuid import UUID

from slate.core.admin.loadouts_schemas import (
    AdminLoadoutDetail,
    AdminLoadoutList,
    AdminLoadoutSummary,
    LoadoutActionCount,
)
from slate.infrastructure.db.models import Loadout
from slate.infrastructure.db.repositories.loadout import LoadoutRepository
from slate.infrastructure.db.repositories.user import UserRepository


class LoadoutNotFoundError(Exception):
    """Raised when a backoffice lookup targets an unknown loadout public_id."""


def _action(loadout: Loadout) -> str:
    return loadout.action or "pending"


class AdminLoadoutService:
    """Read-only loadouts browse for the backoffice."""

    def __init__(self, loadout_repo: LoadoutRepository, user_repo: UserRepository) -> None:
        self._loadouts = loadout_repo
        self._users = user_repo

    async def list_loadouts(
        self,
        *,
        query: str | None,
        action: str | None,
        limit: int,
        offset: int,
    ) -> AdminLoadoutList:
        """Return a page of loadouts (with owner + game) + per-action tallies."""
        rows, total = await self._loadouts.search_admin(
            query=query, action=action, limit=limit, offset=offset
        )
        counts = await self._loadouts.action_counts()
        return AdminLoadoutList(
            items=[_summary(loadout, email, title) for loadout, email, title in rows],
            total=total,
            limit=limit,
            offset=offset,
            action_counts=[
                LoadoutActionCount(action=a, count=n) for a, n in sorted(counts.items())
            ],
        )

    async def get_loadout(self, public_id: UUID) -> AdminLoadoutDetail:
        """Return the full backoffice view of one loadout, or raise if unknown."""
        loadout = await self._loadouts.get_by_public_id(public_id)
        if loadout is None:
            raise LoadoutNotFoundError
        user = await self._users.get_by_id(loadout.user_id)
        entry = loadout.library_entry
        return AdminLoadoutDetail(
            public_id=loadout.public_id,
            user_email=user.email if user is not None else None,
            game_title=entry.game.title if entry is not None and entry.game else None,
            action=_action(loadout),
            mood=loadout.mood,
            available_minutes=loadout.available_minutes,
            mental_energy=loadout.mental_energy,
            created_at=loadout.created_at,
            platform_label=(
                entry.platform.label if entry is not None and entry.platform else None
            ),
            context=loadout.context,
            reasoning=loadout.reasoning,
            led_to_play_session=loadout.play_session_id is not None,
        )


def _summary(loadout: Loadout, email: str | None, game_title: str | None) -> AdminLoadoutSummary:
    return AdminLoadoutSummary(
        public_id=loadout.public_id,
        user_email=email,
        game_title=game_title,
        action=_action(loadout),
        mood=loadout.mood,
        available_minutes=loadout.available_minutes,
        mental_energy=loadout.mental_energy,
        created_at=loadout.created_at,
    )
