"""Mission service: lifecycle management, briefing, and debrief orchestration."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status

from dailyloadout.core.mission.anti_hallucination import validate_briefing
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

    # ------------------------------------------------------------------
    # Start mission
    # ------------------------------------------------------------------

    async def start_mission(
        self,
        user_id: int,
        library_entry_public_id: UUID,
    ) -> Mission:
        """Start a new mission for a library entry.

        Generates a briefing from previous debriefs and creates the mission.

        Raises:
            HTTPException: If the library entry is not found, or the user
                already has an active mission.
        """
        # Validate library entry exists and belongs to user.
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library entry not found",
            )

        # Check for existing active mission.
        active = await self._mission_repo.get_active_for_user(user_id)
        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active mission. End it first.",
            )

        # Fetch last session context for the frontend confirmation step.
        recent_missions = await self._mission_repo.get_recent_for_entry(entry.id, limit=1)
        last_context = None
        if recent_missions and recent_missions[0].extracted_state:
            last_context = recent_missions[0].extracted_state

        # Generate briefing from previous debriefs.
        briefing_text = await self._generate_briefing(
            entry.id, entry.game.title, entry.mission_next_action
        )

        mission = await self._mission_repo.create(
            user_id=user_id,
            library_entry_id=entry.id,
            briefing_text=briefing_text or None,
        )

        # Attach the library entry for response serialisation.
        mission.library_entry = entry
        # Attach last session context as transient attribute for the response.
        mission.last_session_context = last_context  # type: ignore[attr-defined]

        # Update last_played_at on the library entry.
        await self._library_repo.update(entry, last_played_at=mission.started_at)

        return mission

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Debrief
    # ------------------------------------------------------------------

    async def submit_debrief(
        self,
        user_id: int,
        mission_public_id: UUID,
        debrief_text: str,
    ) -> Mission:
        """Submit a debrief for a mission and end it.

        Extracts structured state from the debrief text and updates
        the library entry's ``mission_next_action``.

        Raises:
            HTTPException: If the mission is not found, not active, or
                not owned by the user.
        """
        mission = await self.get_mission(user_id, mission_public_id)
        if mission.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mission is already ended",
            )

        # Save debrief text.
        await self._mission_repo.set_debrief(mission.id, debrief_text)

        # Extract structured state.
        game_title = mission.library_entry.game.title
        extracted = await self._llm_client.extract_debrief_state(
            game_title=game_title,
            debrief_text=debrief_text,
        )

        state_dict = {
            "location": extracted.location,
            "next_action": extracted.next_action,
            "level": extracted.level,
            "current_quest": extracted.current_quest,
        }
        await self._mission_repo.set_extracted_state(mission.id, state_dict)

        # Update the denormalised next action on the library entry.
        if extracted.next_action:
            entry = mission.library_entry
            await self._library_repo.update(entry, mission_next_action=extracted.next_action)

        # End the mission.
        await self._mission_repo.end_mission(mission.id, ended_via="debrief_completed")

        # Re-fetch for response.
        return await self.get_mission(user_id, mission_public_id)

    # ------------------------------------------------------------------
    # End mission (no debrief)
    # ------------------------------------------------------------------

    async def end_mission(
        self,
        user_id: int,
        mission_public_id: UUID,
        ended_via: str = "paused_app",
    ) -> Mission:
        """End a mission without a debrief.

        Raises:
            HTTPException: If the mission is not found, not active, or
                not owned by the user.
        """
        mission = await self.get_mission(user_id, mission_public_id)
        if mission.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mission is already ended",
            )

        await self._mission_repo.end_mission(mission.id, ended_via=ended_via)
        return await self.get_mission(user_id, mission_public_id)

    # ------------------------------------------------------------------
    # Regenerate briefing
    # ------------------------------------------------------------------

    async def regenerate_briefing(
        self,
        user_id: int,
        mission_public_id: UUID,
        position_override: str | None = None,
    ) -> Mission:
        """Regenerate the briefing for an active mission.

        If *position_override* is provided, it replaces the stored session
        context for suggestion generation (the player corrected their position).

        Raises:
            HTTPException: If the mission is not found, not active, or
                not owned by the user.
        """
        mission = await self.get_mission(user_id, mission_public_id)
        if mission.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot regenerate briefing for an ended mission",
            )

        entry = mission.library_entry
        briefing_text = await self._generate_briefing(
            entry.id,
            entry.game.title,
            entry.mission_next_action,
            position_override=position_override,
        )
        if briefing_text:
            await self._mission_repo.set_briefing(mission.id, briefing_text)

        return await self.get_mission(user_id, mission_public_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _generate_briefing(
        self,
        library_entry_id: int,
        game_title: str,
        current_next_action: str | None,
        position_override: str | None = None,
    ) -> str:
        """Generate a briefing from the last 3 debriefs.

        If *position_override* is provided, it's passed to the LLM as the
        player's corrected current position.

        Runs anti-hallucination validation on the output. If suspicious,
        appends a disclaimer.
        """
        recent_missions = await self._mission_repo.get_recent_for_entry(library_entry_id, limit=3)

        previous_debriefs: list[dict[str, object]] = []
        for m in recent_missions:
            debrief_data: dict[str, object] = {}
            if m.extracted_state:
                debrief_data.update(m.extracted_state)
            if m.debrief_text:
                debrief_data["raw_text"] = m.debrief_text
            if debrief_data:
                previous_debriefs.append(debrief_data)

        try:
            briefing = await self._llm_client.generate_briefing(
                game_title=game_title,
                previous_debriefs=previous_debriefs,
                current_next_action=current_next_action,
                position_override=position_override,
            )
        except Exception:
            logger.warning("briefing_generation_failed", exc_info=True)
            return ""

        if not briefing:
            return ""

        # Anti-hallucination check.
        if previous_debriefs:
            context_parts = [game_title]
            for d in previous_debriefs:
                context_parts.extend(str(v) for v in d.values() if v is not None)
            if current_next_action:
                context_parts.append(current_next_action)
            if position_override:
                context_parts.append(position_override)
            context_text = " ".join(context_parts)

            result = validate_briefing(briefing, context_text)
            if result.is_suspicious:
                briefing += (
                    "\n\n⚠️ Note: This briefing may contain inaccuracies. "
                    "Some details could not be verified against your session notes."
                )

        return briefing
