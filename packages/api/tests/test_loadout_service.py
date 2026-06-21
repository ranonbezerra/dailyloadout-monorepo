"""Unit tests for LoadoutService edge cases with mocked LLM."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from dailyloadout.core.loadout.service import LoadoutService
from dailyloadout.infrastructure.llm.base import LoadoutPick
from tests.conftest import _TestSessionFactory


async def _setup_user_and_entry(session: Any) -> tuple[int, int]:
    """Create a user, game, platform, and library entry. Return (user_id, entry_id)."""
    from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Platform, User

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


class TestPickOneFailurePaths:
    async def test_llm_always_raises_returns_422(self) -> None:
        """When the LLM always raises, create_loadouts should raise 422."""
        async with _TestSessionFactory() as session:
            user_id, _ = await _setup_user_and_entry(session)
            await session.commit()

        async with _TestSessionFactory() as session:
            from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
            from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository
            from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

            llm = AsyncMock()
            llm.pick_loadout_game = AsyncMock(side_effect=RuntimeError("LLM down"))

            service = LoadoutService(
                loadout_repo=LoadoutRepository(session),
                library_repo=LibraryRepository(session),
                mission_repo=MissionRepository(session),
                llm_client=llm,
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.create_loadouts(
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
            from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
            from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository
            from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

            llm = AsyncMock()
            llm.pick_loadout_game = AsyncMock(
                return_value=LoadoutPick(
                    library_entry_public_id="not-a-valid-id",
                    reasoning="test",
                )
            )

            service = LoadoutService(
                loadout_repo=LoadoutRepository(session),
                library_repo=LibraryRepository(session),
                mission_repo=MissionRepository(session),
                llm_client=llm,
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.create_loadouts(
                    user_id=user_id,
                    mood="chill",
                    available_minutes=60,
                    mental_energy="medium",
                )
            assert exc_info.value.status_code == 422

    async def test_accept_with_active_mission_returns_409(self) -> None:
        """Accepting a loadout when a mission is already active returns 409."""

        async with _TestSessionFactory() as session:
            user_id, entry_id = await _setup_user_and_entry(session)

            from dailyloadout.infrastructure.db.models import Loadout, Mission

            mission = Mission(user_id=user_id, library_entry_id=entry_id)
            session.add(mission)
            await session.flush()

            loadout = Loadout(
                user_id=user_id,
                library_entry_id=entry_id,
                mood="chill",
                available_minutes=60,
                mental_energy="medium",
                reasoning="test",
            )
            session.add(loadout)
            await session.flush()
            loadout_pid = loadout.public_id
            await session.commit()

        async with _TestSessionFactory() as session:
            from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
            from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository
            from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

            llm = AsyncMock()
            service = LoadoutService(
                loadout_repo=LoadoutRepository(session),
                library_repo=LibraryRepository(session),
                mission_repo=MissionRepository(session),
                llm_client=llm,
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.accept_loadout(user_id, loadout_pid)
            assert exc_info.value.status_code == 409
