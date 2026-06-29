"""Unit tests for PickService edge cases with mocked LLM."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from slate.core.pick.service import PickService
from slate.infrastructure.llm.base import PickSelection
from tests.conftest import _TestSessionFactory


async def _setup_user_and_entry(session: Any) -> tuple[int, int]:
    """Create a user, game, platform, and library entry. Return (user_id, entry_id)."""
    from slate.infrastructure.db.models import Game, LibraryEntry, Platform, User

    user = User(email="u@test.com", password_hash="h", display_name="T")
    session.add(user)
    await session.flush()

    game = Game(slug="hk", title="Hollow Knight", metadata_source="user")
    session.add(game)
    await session.flush()

    platform = Platform(slug="pc", label="PC", family="pc")
    session.add(platform)
    await session.flush()

    entry = LibraryEntry(
        user_id=user.id,
        game_id=game.id,
        platform_id=platform.id,
        status="playing",
    )
    session.add(entry)
    await session.flush()

    return user.id, entry.id


class TestSelectOneFailurePaths:
    async def test_llm_always_raises_returns_422(self) -> None:
        """When the LLM always raises, create_picks should raise 422."""
        async with _TestSessionFactory() as session:
            user_id, _ = await _setup_user_and_entry(session)
            await session.commit()

        async with _TestSessionFactory() as session:
            from slate.infrastructure.db.repositories.library import LibraryRepository
            from slate.infrastructure.db.repositories.pick import PickRepository
            from slate.infrastructure.db.repositories.play_session import (
                PlaySessionRepository,
            )

            llm = AsyncMock()
            llm.select_game = AsyncMock(side_effect=RuntimeError("LLM down"))

            service = PickService(
                pick_repo=PickRepository(session),
                library_repo=LibraryRepository(session),
                play_session_repo=PlaySessionRepository(session),
                llm_client=llm,
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.create_picks(
                    user_id=user_id,
                    mood="chill",
                    available_minutes=60,
                    mental_energy="medium",
                )
            assert exc_info.value.status_code == 422

    async def test_llm_returns_invalid_uuid_returns_422(self) -> None:
        """When the LLM returns UUIDs not in the candidate list, returns 422."""
        async with _TestSessionFactory() as session:
            user_id, _ = await _setup_user_and_entry(session)
            await session.commit()

        async with _TestSessionFactory() as session:
            from slate.infrastructure.db.repositories.library import LibraryRepository
            from slate.infrastructure.db.repositories.pick import PickRepository
            from slate.infrastructure.db.repositories.play_session import (
                PlaySessionRepository,
            )

            llm = AsyncMock()
            llm.select_game = AsyncMock(
                return_value=PickSelection(
                    library_entry_public_id="not-a-valid-id",
                    reasoning="test",
                )
            )

            service = PickService(
                pick_repo=PickRepository(session),
                library_repo=LibraryRepository(session),
                play_session_repo=PlaySessionRepository(session),
                llm_client=llm,
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.create_picks(
                    user_id=user_id,
                    mood="chill",
                    available_minutes=60,
                    mental_energy="medium",
                )
            assert exc_info.value.status_code == 422

    async def test_accept_with_active_play_session_returns_409(self) -> None:
        """Accepting a pick when a play_session is already active returns 409."""

        async with _TestSessionFactory() as session:
            user_id, entry_id = await _setup_user_and_entry(session)

            from slate.infrastructure.db.models import Pick, PlaySession

            play_session = PlaySession(user_id=user_id, library_entry_id=entry_id)
            session.add(play_session)
            await session.flush()

            pick = Pick(
                user_id=user_id,
                library_entry_id=entry_id,
                mood="chill",
                available_minutes=60,
                mental_energy="medium",
                reasoning="test",
            )
            session.add(pick)
            await session.flush()
            pick_pid = pick.public_id
            await session.commit()

        async with _TestSessionFactory() as session:
            from slate.infrastructure.db.repositories.library import LibraryRepository
            from slate.infrastructure.db.repositories.pick import PickRepository
            from slate.infrastructure.db.repositories.play_session import (
                PlaySessionRepository,
            )

            llm = AsyncMock()
            service = PickService(
                pick_repo=PickRepository(session),
                library_repo=LibraryRepository(session),
                play_session_repo=PlaySessionRepository(session),
                llm_client=llm,
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.accept_pick(user_id, pick_pid)
            assert exc_info.value.status_code == 409
