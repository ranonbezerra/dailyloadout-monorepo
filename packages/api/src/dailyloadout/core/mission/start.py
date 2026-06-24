"""Shared mission-start orchestration (ROADMAP Epic 12 — Unified Mission Pipeline).

The single place a Mission is created, regardless of how the game was chosen —
a direct start, an accepted Loadout, or (later) the Concierge. Centralising it
keeps the "one active mission per user" constraint mapping and the
``last_played_at`` stamp consistent across every entrance to the play loop.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from dailyloadout.infrastructure.db.models import LibraryEntry, Mission
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

_ACTIVE_MISSION_DETAIL = "You already have an active mission. End it first."


async def create_mission_for_entry(
    *,
    mission_repo: MissionRepository,
    library_repo: LibraryRepository,
    user_id: int,
    entry: LibraryEntry,
    briefing_text: str | None = None,
) -> Mission:
    """Create an active mission for *entry*, with an optional briefing.

    Maps the one-active-mission DB constraint to a clean 409 and stamps the
    entry's ``last_played_at``. Callers load the entry and run any pre-checks
    (e.g. an early active-mission check to avoid wasting an LLM briefing call).
    """
    try:
        mission = await mission_repo.create(
            user_id=user_id,
            library_entry_id=entry.id,
            briefing_text=briefing_text or None,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_ACTIVE_MISSION_DETAIL,
        ) from None

    mission.library_entry = entry
    await library_repo.update(entry, last_played_at=mission.started_at)
    return mission
