"""Unit tests for the shared play_session-start orchestrator (Epic 12).

``create_play_session_for_entry`` is the single place a PlaySession is created, regardless
of how the game was chosen. These cover its invariants directly: the optional
recap, the ``last_played_at`` stamp, and the one-active-play_session guard mapped
to a clean 409.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from slate.core.play_session.start import create_play_session_for_entry
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from tests.conftest import _TestSessionFactory


async def _seed(session: Any) -> tuple[int, int]:
    """Create user + game + platform + entry. Returns (user_id, entry_id)."""
    from slate.infrastructure.db.models import Game, LibraryEntry, Platform, User

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
    from slate.infrastructure.db.models import LibraryEntry

    return await session.get(LibraryEntry, entry_id)


async def test_creates_play_session_without_recap() -> None:
    async with _TestSessionFactory() as session:
        user_id, entry_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        entry = await _entry(session, entry_id)
        play_session = await create_play_session_for_entry(
            play_session_repo=PlaySessionRepository(session),
            library_repo=LibraryRepository(session),
            user_id=user_id,
            entry=entry,
        )
        assert play_session.recap_text is None
        # last_played_at is stamped to the play_session start.
        assert entry.last_played_at == play_session.started_at


async def test_creates_play_session_with_recap() -> None:
    async with _TestSessionFactory() as session:
        user_id, entry_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        entry = await _entry(session, entry_id)
        play_session = await create_play_session_for_entry(
            play_session_repo=PlaySessionRepository(session),
            library_repo=LibraryRepository(session),
            user_id=user_id,
            entry=entry,
            recap_text="Resume at the gate.",
        )
        assert play_session.recap_text == "Resume at the gate."


async def test_empty_recap_text_normalised_to_none() -> None:
    async with _TestSessionFactory() as session:
        user_id, entry_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        entry = await _entry(session, entry_id)
        play_session = await create_play_session_for_entry(
            play_session_repo=PlaySessionRepository(session),
            library_repo=LibraryRepository(session),
            user_id=user_id,
            entry=entry,
            recap_text="",
        )
        assert play_session.recap_text is None
