"""Backoffice picks read-only service (Epic 21, Phase 6).

Browse every user's pick suggestions: list/search with per-action tallies
and inspect one. Read-only by design — picks decay on their own via the
``auto_ignore`` worker, so the backoffice only reads (no mutations, no audit).
Orchestrates repos only.
"""

from __future__ import annotations

from uuid import UUID

from slate.core.admin.picks_schemas import (
    AdminPickDetail,
    AdminPickList,
    AdminPickSummary,
    PickActionCount,
)
from slate.infrastructure.db.models import Pick
from slate.infrastructure.db.repositories.pick import PickRepository
from slate.infrastructure.db.repositories.user import UserRepository


class PickNotFoundError(Exception):
    """Raised when a backoffice lookup targets an unknown pick public_id."""


def _action(pick: Pick) -> str:
    return pick.action or "pending"


class AdminPickService:
    """Read-only picks browse for the backoffice."""

    def __init__(self, pick_repo: PickRepository, user_repo: UserRepository) -> None:
        self._picks = pick_repo
        self._users = user_repo

    async def list_picks(
        self,
        *,
        query: str | None,
        action: str | None,
        limit: int,
        offset: int,
    ) -> AdminPickList:
        """Return a page of picks (with owner + game) + per-action tallies."""
        rows, total = await self._picks.search_admin(
            query=query, action=action, limit=limit, offset=offset
        )
        counts = await self._picks.action_counts()
        return AdminPickList(
            items=[_summary(pick, email, title) for pick, email, title in rows],
            total=total,
            limit=limit,
            offset=offset,
            action_counts=[PickActionCount(action=a, count=n) for a, n in sorted(counts.items())],
        )

    async def get_pick(self, public_id: UUID) -> AdminPickDetail:
        """Return the full backoffice view of one pick, or raise if unknown."""
        pick = await self._picks.get_by_public_id(public_id)
        if pick is None:
            raise PickNotFoundError
        user = await self._users.get_by_id(pick.user_id)
        entry = pick.library_entry
        return AdminPickDetail(
            public_id=pick.public_id,
            user_email=user.email if user is not None else None,
            game_title=entry.game.title if entry is not None and entry.game else None,
            action=_action(pick),
            mood=pick.mood,
            available_minutes=pick.available_minutes,
            mental_energy=pick.mental_energy,
            created_at=pick.created_at,
            platform_label=(
                entry.platform.label if entry is not None and entry.platform else None
            ),
            context=pick.context,
            reasoning=pick.reasoning,
            led_to_play_session=pick.play_session_id is not None,
        )


def _summary(pick: Pick, email: str | None, game_title: str | None) -> AdminPickSummary:
    return AdminPickSummary(
        public_id=pick.public_id,
        user_email=email,
        game_title=game_title,
        action=_action(pick),
        mood=pick.mood,
        available_minutes=pick.available_minutes,
        mental_energy=pick.mental_energy,
        created_at=pick.created_at,
    )
