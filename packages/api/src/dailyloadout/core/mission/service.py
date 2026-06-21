"""Mission service: lifecycle management, briefing, and debrief orchestration."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status

from dailyloadout.core.mission.anti_hallucination import validate_briefing
from dailyloadout.infrastructure.db.models import LibraryEntry, Mission
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
        briefing_text: str | None = None,
    ) -> Mission:
        """Start a new mission for a library entry.

        If *briefing_text* is provided (from a previous preview call), the
        LLM briefing generation step is skipped.

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

        # Generate briefing only if not pre-supplied from a preview.
        if briefing_text is None:
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

        # Update last_played_at on the library entry.
        await self._library_repo.update(entry, last_played_at=mission.started_at)

        return mission

    # ------------------------------------------------------------------
    # Preview briefing (without creating a mission)
    # ------------------------------------------------------------------

    async def preview_briefing(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        position_override: str | None = None,
    ) -> dict[str, object]:
        """Generate a briefing preview without creating a mission.

        Returns a dict with ``library_entry``, ``briefing_text``, and
        ``last_session_context`` for the frontend confirmation step.

        Raises:
            HTTPException: If the library entry is not found, or the user
                already has an active mission.
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

        return await self._build_preview(entry, position_override=position_override)

    # ------------------------------------------------------------------
    # Retroactive debrief (unregistered play session)
    # ------------------------------------------------------------------

    async def submit_retroactive_debrief(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        debrief_text: str,
    ) -> dict[str, object]:
        """Record a debrief for a play session that wasn't tracked.

        Creates a pre-ended mission with ``mission_type="retroactive"``,
        runs LLM extraction synchronously (the result is needed for the
        updated briefing), and returns a fresh briefing preview.

        Raises:
            HTTPException: If the library entry is not found.
        """
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library entry not found",
            )

        # Extract state synchronously — we need it for the new briefing.
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

        # Return a fresh preview that includes the new retroactive data.
        return await self._build_preview(entry)

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

        Saves the debrief text, ends the mission immediately, and dispatches
        the LLM extraction to a background Taskiq worker. If the worker is
        unavailable, the sync fallback in ``_ensure_extractions_complete``
        handles it when the next mission starts.

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

        # Save debrief text and end the mission immediately.
        await self._mission_repo.set_debrief(mission.id, debrief_text)
        await self._mission_repo.end_mission(mission.id, ended_via="debrief_completed")

        # Dispatch async extraction (fire-and-forget with graceful degradation).
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

    async def _build_preview(
        self,
        entry: LibraryEntry,
        position_override: str | None = None,
    ) -> dict[str, object]:
        """Build a briefing preview dict for a library entry.

        Shared by ``preview_briefing`` and ``submit_retroactive_debrief``.
        Does NOT check for active missions.
        """
        await self._ensure_extractions_complete(entry.id)

        recent_missions = await self._mission_repo.get_recent_for_entry(entry.id, limit=1)
        last_context = None
        if recent_missions and recent_missions[0].extracted_state:
            last_context = recent_missions[0].extracted_state

        briefing_text = await self._generate_briefing(
            entry.id,
            entry.game.title,
            entry.mission_next_action,
            position_override=position_override,
        )

        return {
            "library_entry": entry,
            "briefing_text": briefing_text or None,
            "last_session_context": last_context,
        }

    async def _ensure_extractions_complete(self, library_entry_id: int) -> None:
        """Sync fallback: extract state for missions with debrief but no extraction.

        This handles the case where the Taskiq worker failed or hasn't processed
        the debrief yet. Called before briefing generation to ensure context is
        available.
        """
        pending = await self._mission_repo.get_pending_extractions(library_entry_id)
        for mission in pending:
            logger.info(
                "debrief_extraction_sync_fallback",
                mission_id=mission.id,
            )
            try:
                extracted = await self._llm_client.extract_debrief_state(
                    game_title=mission.library_entry.game.title,
                    debrief_text=mission.debrief_text,  # type: ignore[arg-type]
                )
                state_dict = {
                    "location": extracted.location,
                    "next_action": extracted.next_action,
                    "level": extracted.level,
                    "current_quest": extracted.current_quest,
                }
                await self._mission_repo.set_extracted_state(mission.id, state_dict)
                if extracted.next_action:
                    await self._library_repo.update(
                        mission.library_entry, mission_next_action=extracted.next_action
                    )
            except Exception:
                logger.warning(
                    "debrief_extraction_sync_fallback_failed",
                    mission_id=mission.id,
                    exc_info=True,
                )

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
        await self._ensure_extractions_complete(library_entry_id)
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
