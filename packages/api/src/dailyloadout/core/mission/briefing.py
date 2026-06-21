"""Briefing helpers: preview, extraction fallback, and generation."""

from __future__ import annotations

import structlog

from dailyloadout.core.mission.anti_hallucination import validate_briefing
from dailyloadout.infrastructure.db.models import LibraryEntry
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()


async def build_preview(
    mission_repo: MissionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    entry: LibraryEntry,
    position_override: str | None = None,
) -> dict[str, object]:
    """Build a briefing preview dict for a library entry.

    Shared by ``preview_briefing`` and ``submit_retroactive_debrief``.
    Does NOT check for active missions.
    """
    await ensure_extractions_complete(mission_repo, library_repo, llm_client, entry.id)

    recent_missions = await mission_repo.get_recent_for_entry(entry.id, limit=1)
    last_context = None
    if recent_missions and recent_missions[0].extracted_state:
        last_context = recent_missions[0].extracted_state

    briefing_text = await generate_briefing(
        mission_repo,
        library_repo,
        llm_client,
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


async def ensure_extractions_complete(
    mission_repo: MissionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    library_entry_id: int,
) -> None:
    """Sync fallback: extract state for missions with debrief but no extraction.

    This handles the case where the Taskiq worker failed or hasn't processed
    the debrief yet. Called before briefing generation to ensure context is
    available.
    """
    pending = await mission_repo.get_pending_extractions(library_entry_id)
    for mission in pending:
        logger.info(
            "debrief_extraction_sync_fallback",
            mission_id=mission.id,
        )
        try:
            extracted = await llm_client.extract_debrief_state(
                game_title=mission.library_entry.game.title,
                debrief_text=mission.debrief_text,  # type: ignore[arg-type]
            )
            state_dict = {
                "location": extracted.location,
                "next_action": extracted.next_action,
                "level": extracted.level,
                "current_quest": extracted.current_quest,
            }
            await mission_repo.set_extracted_state(mission.id, state_dict)
            if extracted.next_action:
                await library_repo.update(
                    mission.library_entry, mission_next_action=extracted.next_action
                )
        except Exception:
            logger.warning(
                "debrief_extraction_sync_fallback_failed",
                mission_id=mission.id,
                exc_info=True,
            )


async def generate_briefing(
    mission_repo: MissionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
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
    await ensure_extractions_complete(mission_repo, library_repo, llm_client, library_entry_id)
    recent_missions = await mission_repo.get_recent_for_entry(library_entry_id, limit=3)

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
        briefing = await llm_client.generate_briefing(
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
                "\n\n\u26a0\ufe0f Note: This briefing may contain inaccuracies. "
                "Some details could not be verified against your session notes."
            )

    return briefing
