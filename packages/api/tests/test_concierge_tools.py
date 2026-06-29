"""Unit tests for the Backlog Concierge read-only tool functions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from slate.core.stats.service import StatsService
from slate.infrastructure.agent.concierge.tools import (
    build_concierge_tools,
    estimate_session_fit,
    get_play_session_history,
    get_play_stats,
    search_library,
    validate_recommendation,
)
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.db.repositories.stats import StatsRepository
from tests.conftest import _TestSessionFactory


async def _seed(
    session: Any, *, status: str = "playing", next_action: str | None = None
) -> tuple[int, str, int]:
    """Create user + game + platform + entry. Returns (user_id, entry_public_id, entry_id)."""
    from slate.infrastructure.db.models import Game, LibraryEntry, Platform, User

    user = User(email=f"{uuid4().hex}@test.com", password_hash="h", display_name="T")
    session.add(user)
    await session.flush()

    game = Game(
        slug=f"hk-{uuid4().hex[:6]}",
        title="Hollow Knight",
        metadata_source="user",
        genres=["Metroidvania"],
    )
    session.add(game)
    await session.flush()

    platform = Platform(slug=f"pc-{uuid4().hex[:6]}", label="PC", family="pc")
    session.add(platform)
    await session.flush()

    entry = LibraryEntry(
        user_id=user.id,
        game_id=game.id,
        platform_id=platform.id,
        status=status,
        play_session_next_action=next_action,
    )
    session.add(entry)
    await session.flush()
    return user.id, str(entry.public_id), entry.id


async def test_search_library_lists_entry_with_id() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await search_library(LibraryRepository(session), user_id)
        assert "Hollow Knight" in out
        assert public_id in out


async def test_search_library_filters() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        repo = LibraryRepository(session)
        assert "Hollow Knight" in await search_library(repo, user_id, genre="metroid")
        assert "No games match" in await search_library(repo, user_id, genre="racing")
        assert "Hollow Knight" in await search_library(repo, user_id, platform="pc")
        assert "No games match" in await search_library(repo, user_id, platform="switch")


async def test_get_play_session_history_no_sessions() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session, next_action="Beat the boss")
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await get_play_session_history(
            LibraryRepository(session),
            PlaySessionRepository(session),
            user_id,
            library_entry_public_id=public_id,
        )
        assert "Beat the boss" in out
        assert "No recorded sessions yet" in out


async def test_get_play_session_history_with_session() -> None:
    from slate.infrastructure.db.models import PlaySession

    async with _TestSessionFactory() as session:
        user_id, public_id, entry_id = await _seed(session)
        now = datetime.now(UTC)
        session.add(
            PlaySession(
                user_id=user_id,
                library_entry_id=entry_id,
                play_session_type="quick",
                started_at=now - timedelta(hours=2),
                ended_at=now - timedelta(hours=1),
                extracted_state={
                    "location": "City of Tears",
                    "current_quest": "Find the elevator",
                },
            )
        )
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await get_play_session_history(
            LibraryRepository(session),
            PlaySessionRepository(session),
            user_id,
            library_entry_public_id=public_id,
        )
        assert "City of Tears" in out


async def test_get_play_session_history_unknown_game() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await get_play_session_history(
            LibraryRepository(session),
            PlaySessionRepository(session),
            user_id,
            library_entry_public_id=str(uuid4()),
        )
        assert "not in the library" in out


async def test_get_play_stats() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        stats = StatsService(StatsRepository(session))
        out = await get_play_stats(stats, user_id, datetime.now(UTC) - timedelta(days=10))
        assert "Total games: 1" in out


async def test_estimate_session_fit_scores() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session, status="playing", next_action="Resume run")
        await session.commit()

    async with _TestSessionFactory() as session:
        repo = LibraryRepository(session)
        out = await estimate_session_fit(
            repo, user_id, library_entry_public_id=public_id, minutes=90
        )
        assert "/100" in out
        assert "Hollow Knight" in out

        missing = await estimate_session_fit(
            repo, user_id, library_entry_public_id=str(uuid4()), minutes=30
        )
        assert "not in the library" in missing


async def test_estimate_session_fit_short_session_penalty() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session, status="backlog")
        await session.commit()

    async with _TestSessionFactory() as session:
        out = await estimate_session_fit(
            LibraryRepository(session), user_id, library_entry_public_id=public_id, minutes=10
        )
        assert "short session" in out


async def test_validate_recommendation() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        repo = LibraryRepository(session)
        assert await validate_recommendation(repo, user_id, public_id) is True
        assert await validate_recommendation(repo, user_id, str(uuid4())) is False
        assert await validate_recommendation(repo, user_id, "not-a-uuid") is False


async def test_build_concierge_tools_shapes() -> None:
    async with _TestSessionFactory() as session:
        user_id, _, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        tools = build_concierge_tools(
            user_id=user_id,
            user_created_at=datetime.now(UTC),
            library_repo=LibraryRepository(session),
            play_session_repo=PlaySessionRepository(session),
            stats_service=StatsService(StatsRepository(session)),
        )
        names = {t.name for t in tools}
        assert names == {
            "search_library",
            "get_play_session_history",
            "get_play_stats",
            "estimate_session_fit",
        }
        # The bound search tool should return the seeded game.
        search = next(t for t in tools if t.name == "search_library")
        assert "Hollow Knight" in await search.coroutine()
        stats = next(t for t in tools if t.name == "get_play_stats")
        assert "Total games: 1" in await stats.coroutine()
