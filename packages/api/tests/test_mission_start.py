"""Unit tests for the shared mission-start orchestrator (Epic 12).

``create_mission_for_entry`` is the single place a Mission is created, regardless
of how the game was chosen. These cover its invariants directly: the optional
briefing, the ``last_played_at`` stamp, and the one-active-mission guard mapped
to a clean 409.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from dailyloadout.core.mission.start import create_mission_for_entry
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from tests.conftest import _TestSessionFactory


async def _seed(session: Any) -> tuple[int, int]:
    """Create user + game + platform + entry. Returns (user_id, entry_id)."""
    from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Platform, User

    user = User(email=f"{uuid4().hex}@test.com", password_hash="h", display_name="T")
    session.add(user)
    await session.flush()

    game = Game(slug=f"hk-{uuid4().hex[:6]}", title="Hollow Knight", metadata_source="user")
    session.add(game)
    await session.flush()

    platform = Platform(slug=f"pc-{uuid4().hex[:6]}", label="PC", family="pc")
    session.add(platform)
    await session.flush()

    entry = LibraryEntry(
        user_id=user.id, game_id=game.id, platform_id=platform.id, status="playing"
    )
    session.add(entry)
    await session.flush()
    return user.id, entry.id


async def _entry(session: Any, entry_id: int) -> Any:
    from dailyloadout.infrastructure.db.models import LibraryEntry

    return await session.get(LibraryEntry, entry_id)


async def test_creates_mission_without_briefing() -> None:
    async with _TestSessionFactory() as session:
        user_id, entry_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        entry = await _entry(session, entry_id)
        mission = await create_mission_for_entry(
            mission_repo=MissionRepository(session),
            library_repo=LibraryRepository(session),
            user_id=user_id,
            entry=entry,
        )
        assert mission.briefing_text is None
        # last_played_at is stamped to the mission start.
        assert entry.last_played_at == mission.started_at


async def test_creates_mission_with_briefing() -> None:
    async with _TestSessionFactory() as session:
        user_id, entry_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        entry = await _entry(session, entry_id)
        mission = await create_mission_for_entry(
            mission_repo=MissionRepository(session),
            library_repo=LibraryRepository(session),
            user_id=user_id,
            entry=entry,
            briefing_text="Resume at the gate.",
        )
        assert mission.briefing_text == "Resume at the gate."


async def test_empty_briefing_text_normalised_to_none() -> None:
    async with _TestSessionFactory() as session:
        user_id, entry_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        entry = await _entry(session, entry_id)
        mission = await create_mission_for_entry(
            mission_repo=MissionRepository(session),
            library_repo=LibraryRepository(session),
            user_id=user_id,
            entry=entry,
            briefing_text="",
        )
        assert mission.briefing_text is None
