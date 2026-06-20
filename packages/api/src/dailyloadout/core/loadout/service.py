"""Loadout service: daily game suggestion with UUID validation."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status

from dailyloadout.infrastructure.db.models import Loadout
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()

MAX_REROLLS = 1


class LoadoutService:
    """Orchestrates daily loadout: question → LLM pick → accept/reject."""

    def __init__(
        self,
        loadout_repo: LoadoutRepository,
        library_repo: LibraryRepository,
        mission_repo: MissionRepository,
        llm_client: AbstractLLMClient,
    ) -> None:
        self._loadout_repo = loadout_repo
        self._library_repo = library_repo
        self._mission_repo = mission_repo
        self._llm_client = llm_client

    # ------------------------------------------------------------------
    # Create loadout
    # ------------------------------------------------------------------

    async def create_loadout(
        self,
        user_id: int,
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
        cooldown_hours: int = 12,
    ) -> Loadout:
        """Create a single loadout suggestion."""
        results = await self.create_loadouts(
            user_id=user_id,
            mood=mood,
            available_minutes=available_minutes,
            mental_energy=mental_energy,
            context=context,
            count=1,
            cooldown_hours=cooldown_hours,
        )
        return results[0]

    async def create_loadouts(
        self,
        user_id: int,
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
        count: int = 1,
        cooldown_hours: int = 12,
    ) -> list[Loadout]:
        """Create up to *count* loadout suggestions with distinct games.

        Raises:
            HTTPException 422: If no eligible games or LLM fails.
        """
        entries = await self._library_repo.list_eligible_for_loadout(
            user_id, cooldown_hours=cooldown_hours
        )

        if not entries:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No eligible games in your library. "
                "Add games first or wait for the cooldown.",
            )

        # Build candidate list for the LLM.
        entry_by_pid: dict[str, object] = {}
        all_candidates: list[dict[str, object]] = []
        for entry in entries:
            pid = str(entry.public_id)
            entry_by_pid[pid] = entry
            all_candidates.append(
                {
                    "public_id": pid,
                    "game_title": entry.game.title,
                    "platform": entry.platform.label,
                    "status": entry.status,
                    "last_played_at": (
                        str(entry.last_played_at) if entry.last_played_at else None
                    ),
                    "mission_next_action": entry.mission_next_action,
                    "genres": entry.game.genres or [],
                    "summary": entry.game.summary,
                }
            )

        # Cap count to available candidates.
        count = min(count, len(all_candidates))

        results: list[Loadout] = []
        picked_ids: set[str] = set()
        remaining = list(all_candidates)

        for _ in range(count):
            if not remaining:
                break

            valid_ids = {str(c["public_id"]) for c in remaining}
            picked = await self._pick_one(
                remaining, valid_ids, mood, available_minutes, mental_energy, context
            )

            if picked is None:
                break

            picked_id, reasoning = picked
            picked_ids.add(picked_id)

            # Find the matching entry.
            from dailyloadout.infrastructure.db.models import LibraryEntry

            chosen_entry: LibraryEntry = entry_by_pid[picked_id]  # type: ignore[assignment]

            loadout = await self._loadout_repo.create(
                user_id=user_id,
                library_entry_id=chosen_entry.id,
                mood=mood,
                available_minutes=available_minutes,
                mental_energy=mental_energy,
                reasoning=reasoning,
                context=context,
            )
            loadout.library_entry = chosen_entry
            results.append(loadout)

            # Remove picked entry from remaining candidates.
            remaining = [c for c in remaining if str(c["public_id"]) != picked_id]

        if not results:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not pick a valid game. Please try again.",
            )

        return results

    async def _pick_one(
        self,
        candidates: list[dict[str, object]],
        valid_ids: set[str],
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
    ) -> tuple[str, str] | None:
        """Call LLM once (with reroll) and return (public_id, reasoning)."""
        for attempt in range(1 + MAX_REROLLS):
            try:
                pick = await self._llm_client.pick_loadout_game(
                    candidates=candidates,
                    mood=mood,
                    available_minutes=available_minutes,
                    mental_energy=mental_energy,
                    context=context,
                )
            except Exception:
                logger.warning(
                    "loadout_llm_pick_failed",
                    exc_info=True,
                    attempt=attempt,
                )
                continue

            if pick.library_entry_public_id in valid_ids:
                return pick.library_entry_public_id, pick.reasoning

            logger.warning(
                "loadout_invalid_uuid",
                returned_id=pick.library_entry_public_id,
                attempt=attempt,
            )

        return None

    # ------------------------------------------------------------------
    # Accept loadout → creates a mission
    # ------------------------------------------------------------------

    async def accept_loadout(
        self,
        user_id: int,
        loadout_public_id: UUID,
    ) -> Loadout:
        """Accept a loadout suggestion and start a mission.

        Raises:
            HTTPException 404: Loadout not found.
            HTTPException 409: Loadout already actioned or active mission exists.
        """
        loadout = await self._loadout_repo.get_by_public_id(loadout_public_id, user_id=user_id)
        if loadout is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loadout not found",
            )

        if loadout.action is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Loadout already {loadout.action}",
            )

        # Check for active mission.
        active = await self._mission_repo.get_active_for_user(user_id)
        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active mission. End it first.",
            )

        # Create the mission.
        mission = await self._mission_repo.create(
            user_id=user_id,
            library_entry_id=loadout.library_entry_id,  # type: ignore[arg-type]
        )

        # Update loadout.
        await self._loadout_repo.set_action(loadout.id, "accepted")
        await self._loadout_repo.set_mission(loadout.id, mission.id)

        # Re-fetch for response.
        return await self._get_loadout(user_id, loadout_public_id)

    # ------------------------------------------------------------------
    # Reject loadout
    # ------------------------------------------------------------------

    async def reject_loadout(
        self,
        user_id: int,
        loadout_public_id: UUID,
    ) -> Loadout:
        """Reject a loadout suggestion.

        Raises:
            HTTPException 404: Loadout not found.
            HTTPException 409: Loadout already actioned.
        """
        loadout = await self._loadout_repo.get_by_public_id(loadout_public_id, user_id=user_id)
        if loadout is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loadout not found",
            )

        if loadout.action is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Loadout already {loadout.action}",
            )

        await self._loadout_repo.set_action(loadout.id, "rejected")

        # Re-fetch for response.
        return await self._get_loadout(user_id, loadout_public_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_latest_pending(self, user_id: int) -> Loadout | None:
        """Return the latest pending loadout, or None."""
        return await self._loadout_repo.get_pending_for_user(user_id)

    async def list_loadouts(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Loadout], int]:
        """Return the user's loadouts along with the total count."""
        loadouts = await self._loadout_repo.list_for_user(user_id, limit=limit, offset=offset)
        total = await self._loadout_repo.count_for_user(user_id)
        return loadouts, total

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_loadout(self, user_id: int, loadout_public_id: UUID) -> Loadout:
        """Fetch a loadout or raise 404."""
        loadout = await self._loadout_repo.get_by_public_id(loadout_public_id, user_id=user_id)
        if loadout is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loadout not found",
            )
        return loadout
