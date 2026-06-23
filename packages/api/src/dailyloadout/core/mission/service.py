"""Mission service: lifecycle management, briefing, and debrief orchestration."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from dailyloadout.core.mission.briefing import (
    build_preview,
    generate_briefing,
)
from dailyloadout.infrastructure.db.models import Mission
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()


class MissionService:
    """Orchestrates mission lifecycle: start, briefing, debrief, and end."""

    def __init__(
        self,
        mission_repo: MissionRepository,
        library_repo: LibraryRepository,
        llm_client: AbstractLLMClient,
    ) -> None:
        self._mission_repo = mission_repo
        self._library_repo = library_repo
        self._llm_client = llm_client

    # -- Start mission ---------------------------------------------------

    async def start_mission(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        briefing_text: str | None = None,
    ) -> Mission:
        """Start a new mission for a library entry.

        If *briefing_text* is provided (from a previous preview call), the
        LLM briefing generation step is skipped.
        """
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library entry not found",
            )

        active = await self._mission_repo.get_active_for_user(user_id)
        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active mission. End it first.",
            )

        if briefing_text is None:
            briefing_text = await generate_briefing(
                self._mission_repo,
                self._library_repo,
                self._llm_client,
                entry.id,
                entry.game.title,
                entry.mission_next_action,
            )

        try:
            mission = await self._mission_repo.create(
                user_id=user_id,
                library_entry_id=entry.id,
                briefing_text=briefing_text or None,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active mission. End it first.",
            ) from None

        mission.library_entry = entry
        await self._library_repo.update(entry, last_played_at=mission.started_at)

        return mission

    # -- Preview briefing ------------------------------------------------

    async def preview_briefing(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        position_override: str | None = None,
    ) -> dict[str, object]:
        """Generate a briefing preview without creating a mission.

        Returns a dict with ``library_entry``, ``briefing_text``, and
        ``last_session_context`` for the frontend confirmation step.
        """
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library entry not found",
            )

        active = await self._mission_repo.get_active_for_user(user_id)
        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active mission. End it first.",
            )

        return await build_preview(
            self._mission_repo,
            self._library_repo,
            self._llm_client,
            entry,
            position_override=position_override,
        )

    # -- Retroactive debrief ---------------------------------------------

    async def submit_retroactive_debrief(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        debrief_text: str,
    ) -> dict[str, object]:
        """Record a debrief for a play session that wasn't tracked.

        Creates a pre-ended mission with ``mission_type="retroactive"``,
        runs LLM extraction synchronously, and returns a fresh briefing
        preview.
        """
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library entry not found",
            )

        extracted_state = None
        try:
            extracted = await self._llm_client.extract_debrief_state(
                game_title=entry.game.title,
                debrief_text=debrief_text,
            )
            extracted_state = {
                "location": extracted.location,
                "next_action": extracted.next_action,
                "level": extracted.level,
                "current_quest": extracted.current_quest,
            }
            if extracted.next_action:
                await self._library_repo.update(entry, mission_next_action=extracted.next_action)
        except Exception:
            logger.warning("retroactive_extraction_failed", exc_info=True)

        await self._mission_repo.create_retroactive(
            user_id=user_id,
            library_entry_id=entry.id,
            debrief_text=debrief_text,
            extracted_state=extracted_state,
        )

        return await build_preview(
            self._mission_repo,
            self._library_repo,
            self._llm_client,
            entry,
        )

    # -- Query -----------------------------------------------------------

    async def get_mission(self, user_id: int, mission_public_id: UUID) -> Mission:
        """Return a mission scoped to *user_id*, or raise 404."""
        mission = await self._mission_repo.get_by_public_id(mission_public_id, user_id=user_id)
        if mission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mission not found",
            )
        return mission

    async def get_active_mission(self, user_id: int) -> Mission | None:
        """Return the user's active mission, or None."""
        return await self._mission_repo.get_active_for_user(user_id)

    async def list_missions(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Mission], int]:
        """Return the user's missions along with the total count."""
        missions = await self._mission_repo.list_for_user(user_id, limit=limit, offset=offset)
        total = await self._mission_repo.count_for_user(user_id)
        return missions, total

    # -- Debrief ---------------------------------------------------------

    async def submit_debrief(
        self,
        user_id: int,
        mission_public_id: UUID,
        debrief_text: str,
    ) -> Mission:
        """Submit a debrief for a mission and end it.

        Saves the debrief text, ends the mission immediately, and dispatches
        the LLM extraction to a background Taskiq worker.
        """
        mission = await self.get_mission(user_id, mission_public_id)
        if mission.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mission is already ended",
            )

        await self._mission_repo.set_debrief(mission.id, debrief_text)
        await self._mission_repo.end_mission(mission.id, ended_via="debrief_completed")

        game_title = mission.library_entry.game.title
        try:
            from dailyloadout.infrastructure.tasks.debrief_extraction import (
                extract_debrief_state_task,
            )

            await extract_debrief_state_task.kiq(mission.id, game_title, debrief_text)
            logger.info("debrief_extraction_dispatched", mission_id=mission.id)
        except Exception:
            logger.warning(
                "debrief_extraction_dispatch_failed",
                mission_id=mission.id,
                exc_info=True,
            )

        return await self.get_mission(user_id, mission_public_id)

    # -- End mission (no debrief) ----------------------------------------

    async def end_mission(
        self,
        user_id: int,
        mission_public_id: UUID,
        ended_via: str = "paused_app",
    ) -> Mission:
        """End a mission without a debrief."""
        mission = await self.get_mission(user_id, mission_public_id)
        if mission.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mission is already ended",
            )

        await self._mission_repo.end_mission(mission.id, ended_via=ended_via)
        return await self.get_mission(user_id, mission_public_id)

    # -- Regenerate briefing ---------------------------------------------

    async def regenerate_briefing(
        self,
        user_id: int,
        mission_public_id: UUID,
        position_override: str | None = None,
    ) -> Mission:
        """Regenerate the briefing for an active mission.

        If *position_override* is provided, it replaces the stored session
        context for suggestion generation.
        """
        mission = await self.get_mission(user_id, mission_public_id)
        if mission.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot regenerate briefing for an ended mission",
            )

        entry = mission.library_entry
        briefing_text = await generate_briefing(
            self._mission_repo,
            self._library_repo,
            self._llm_client,
            entry.id,
            entry.game.title,
            entry.mission_next_action,
            position_override=position_override,
        )
        if briefing_text:
            await self._mission_repo.set_briefing(mission.id, briefing_text)

        return await self.get_mission(user_id, mission_public_id)
