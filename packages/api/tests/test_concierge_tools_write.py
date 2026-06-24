"""Unit tests for the Backlog Concierge write tool functions (Epic 12).

These exercise the same guard rails the REST surface enforces — UUID-existence
on every pick and one active mission per user — driving the tools directly so no
model is required.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from dailyloadout.config import settings
from dailyloadout.infrastructure.agent.concierge.tools_write import (
    build_concierge_write_tools,
    generate_briefing,
    set_status,
    start_mission,
    submit_retroactive_debrief,
)
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.llm.dummy import DummyLLMClient
from tests.conftest import _TestSessionFactory


async def _seed(session: Any, *, status: str = "playing") -> tuple[int, str, int]:
    """Create user + game + platform + entry. Returns (user_id, entry_public_id, entry_id)."""
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

    entry = LibraryEntry(user_id=user.id, game_id=game.id, platform_id=platform.id, status=status)
    session.add(entry)
    await session.flush()
    return user.id, str(entry.public_id), entry.id


# -- start_mission --------------------------------------------------------------


async def test_start_mission_creates_active_mission() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await start_mission(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
            library_entry_public_id=public_id,
        )
        assert "Started a mission for Hollow Knight" in out
        await session.commit()

    async with _TestSessionFactory() as session:
        active = await MissionRepository(session).get_active_for_user(user_id)
        assert active is not None
        assert active.briefing_text is None


async def test_start_mission_with_quick_briefing() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await start_mission(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
            library_entry_public_id=public_id,
            briefing="quick",
        )
        assert "Briefing:" in out
        await session.commit()

    async with _TestSessionFactory() as session:
        active = await MissionRepository(session).get_active_for_user(user_id)
        assert active is not None
        assert active.briefing_text


async def test_start_mission_unknown_game() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await start_mission(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
            library_entry_public_id=str(uuid4()),
        )
        assert "not in the library" in out


async def test_start_mission_rejects_second_active() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        await start_mission(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
            library_entry_public_id=public_id,
        )
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await start_mission(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
            library_entry_public_id=public_id,
        )
        assert "already an active mission" in out


# -- generate_briefing ----------------------------------------------------------


async def test_generate_briefing_needs_active_mission() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await generate_briefing(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
        )
        assert "no active mission" in out.lower()


async def test_generate_briefing_persists_on_active_mission() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        await start_mission(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
            library_entry_public_id=public_id,
        )
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await generate_briefing(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            None,
            settings,
            user_id,
        )
        assert "Hollow Knight" in out
        await session.commit()

    async with _TestSessionFactory() as session:
        active = await MissionRepository(session).get_active_for_user(user_id)
        assert active is not None
        assert active.briefing_text


# -- submit_retroactive_debrief -------------------------------------------------


async def test_retroactive_debrief_logs_session() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, entry_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await submit_retroactive_debrief(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            user_id,
            library_entry_public_id=public_id,
            debrief_text="Cleared the second boss and unlocked the dash.",
        )
        assert "Logged your past session" in out
        await session.commit()

    async with _TestSessionFactory() as session:
        missions = await MissionRepository(session).get_recent_for_entry(entry_id, limit=5)
        assert len(missions) == 1
        assert missions[0].mission_type == "retroactive"


async def test_retroactive_debrief_unknown_game() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await submit_retroactive_debrief(
            LibraryRepository(session),
            MissionRepository(session),
            DummyLLMClient(),
            user_id,
            library_entry_public_id=str(uuid4()),
            debrief_text="played offline",
        )
        assert "not in the library" in out


# -- set_status -----------------------------------------------------------------


async def test_set_status_updates_entry() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session, status="backlog")
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await set_status(
            LibraryRepository(session),
            user_id,
            library_entry_public_id=public_id,
            status="completed",
        )
        assert "Marked Hollow Knight as completed" in out
        await session.commit()

    async with _TestSessionFactory() as session:
        from uuid import UUID

        entry = await LibraryRepository(session).get_by_public_id(UUID(public_id), user_id)
        assert entry is not None
        assert entry.status == "completed"


async def test_set_status_rejects_invalid_status() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await set_status(
            LibraryRepository(session),
            user_id,
            library_entry_public_id=public_id,
            status="finished",
        )
        assert "isn't a valid status" in out


async def test_set_status_unknown_game() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await set_status(
            LibraryRepository(session),
            user_id,
            library_entry_public_id=str(uuid4()),
            status="playing",
        )
        assert "not in the library" in out


# -- builder --------------------------------------------------------------------


async def test_build_concierge_write_tools_shapes() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        tools = build_concierge_write_tools(
            user_id=user_id,
            library_repo=LibraryRepository(session),
            mission_repo=MissionRepository(session),
            llm_client=DummyLLMClient(),
            agent=None,
            settings=settings,
        )
        names = {t.name for t in tools}
        assert names == {
            "start_mission",
            "generate_briefing",
            "submit_retroactive_debrief",
            "set_status",
        }
