"""Async task: extract structured state from a mission debrief via LLM."""

from __future__ import annotations

import structlog

from dailyloadout.infrastructure.tasks.broker import broker

logger = structlog.get_logger()


@broker.task(retry_on_error=True, max_retries=3)
async def extract_debrief_state_task(
    mission_id: int,
    game_title: str,
    debrief_text: str,
) -> None:
    """Extract structured state from a debrief and persist it.

    Runs as a background Taskiq task with up to 3 retries on failure.
    If all retries fail, the sync fallback in ``_ensure_extractions_complete``
    will handle it when the next mission starts.
    """
    from dailyloadout.config import settings as app_settings
    from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
    from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
    from dailyloadout.infrastructure.db.session import async_session_factory
    from dailyloadout.infrastructure.llm.factory import get_llm_client

    llm_client = get_llm_client(app_settings)

    async with async_session_factory() as session:
        mission_repo = MissionRepository(session)
        library_repo = LibraryRepository(session)

        extracted = await llm_client.extract_debrief_state(
            game_title=game_title,
            debrief_text=debrief_text,
        )

        state_dict = {
            "location": extracted.location,
            "next_action": extracted.next_action,
            "level": extracted.level,
            "current_quest": extracted.current_quest,
        }
        await mission_repo.set_extracted_state(mission_id, state_dict)

        # Update the denormalised next action on the library entry.
        if extracted.next_action:
            from dailyloadout.infrastructure.db.models import Mission

            mission = await session.get(Mission, mission_id)
            if mission and mission.library_entry_id:
                from dailyloadout.infrastructure.db.models import LibraryEntry

                entry = await session.get(LibraryEntry, mission.library_entry_id)
                if entry:
                    await library_repo.update(entry, mission_next_action=extracted.next_action)

        await session.commit()

    logger.info(
        "debrief_extraction_completed",
        mission_id=mission_id,
    )
