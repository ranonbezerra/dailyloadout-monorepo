"""Tests for ConciergeService: the UUID guard, reroll, and degrade paths."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from dailyloadout.core.concierge.service import ConciergeService, _split_recommendation
from dailyloadout.core.stats.service import StatsService
from dailyloadout.infrastructure.agent.concierge.base import (
    AbstractConciergeAgent,
    ConciergeReply,
    ConciergeRequest,
)
from dailyloadout.infrastructure.agent.concierge.dummy import DummyConciergeAgent
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.db.repositories.stats import StatsRepository
from dailyloadout.infrastructure.llm.dummy import DummyLLMClient
from tests.conftest import _TestSessionFactory

_FAKE_ID = "00000000-0000-0000-0000-000000000000"


async def _seed(session: Any, *, with_entry: bool = True) -> tuple[int, str | None]:
    from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Platform, User

    user = User(email=f"{uuid4().hex}@test.com", password_hash="h", display_name="T")
    session.add(user)
    await session.flush()
    if not with_entry:
        return user.id, None

    game = Game(slug=f"g-{uuid4().hex[:6]}", title="Hollow Knight", metadata_source="user")
    session.add(game)
    await session.flush()
    platform = Platform(slug=f"p-{uuid4().hex[:6]}", label="PC", family="pc")
    session.add(platform)
    await session.flush()
    entry = LibraryEntry(
        user_id=user.id, game_id=game.id, platform_id=platform.id, status="playing"
    )
    session.add(entry)
    await session.flush()
    return user.id, str(entry.public_id)


def _service(session: Any, agent: AbstractConciergeAgent) -> ConciergeService:
    return ConciergeService(
        library_repo=LibraryRepository(session),
        mission_repo=MissionRepository(session),
        stats_service=StatsService(StatsRepository(session)),
        agent=agent,
        llm_client=DummyLLMClient(),
    )


class _AlwaysInvalidAgent(AbstractConciergeAgent):
    """Recommends a non-existent game on every turn (forces degrade)."""

    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        return ConciergeReply(text=f"Try this one.\nRECOMMEND: {_FAKE_ID}")


class _NoPickAgent(AbstractConciergeAgent):
    """Chats without ever recommending a specific game."""

    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        return ConciergeReply(text="Tell me how much time you have and I'll suggest something.")


def test_split_recommendation() -> None:
    assert _split_recommendation("Play this.\nRECOMMEND: abc") == ("Play this.", "abc")
    assert _split_recommendation("Just chatting.") == ("Just chatting.", None)


async def test_valid_recommendation_passes_through() -> None:
    async with _TestSessionFactory() as session:
        user_id, public_id = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        service = _service(session, DummyConciergeAgent())
        text = await service.reply(
            user_id=user_id,
            user_created_at=datetime.now(UTC),
            thread_id="t1",
            message="What should I play tonight?",
        )
        # The validated pick's prose is returned, with the marker stripped.
        assert "give this a go" in text
        assert "RECOMMEND" not in text
        assert public_id not in text  # the id is a machine marker, not shown


async def test_invalid_recommendation_rerolls_to_valid() -> None:
    async with _TestSessionFactory() as session:
        user_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        service = _service(session, DummyConciergeAgent())
        # "[invalid]" makes the dummy recommend a fake id on the first turn;
        # the reroll (no marker) then recommends a real one.
        text = await service.reply(
            user_id=user_id,
            user_created_at=datetime.now(UTC),
            thread_id="t2",
            message="[invalid] what should I play?",
        )
        assert "give this a go" in text
        assert _FAKE_ID not in text
        assert "RECOMMEND" not in text


async def test_persistently_invalid_recommendation_degrades() -> None:
    async with _TestSessionFactory() as session:
        user_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        service = _service(session, _AlwaysInvalidAgent())
        text = await service.reply(
            user_id=user_id,
            user_created_at=datetime.now(UTC),
            thread_id="t3",
            message="What should I play?",
        )
        # Never surfaces the bogus id; degrades to a clarifying nudge instead.
        assert _FAKE_ID not in text
        assert "take another look" in text


async def test_no_recommendation_is_passed_through() -> None:
    async with _TestSessionFactory() as session:
        user_id, _ = await _seed(session)
        await session.commit()

    async with _TestSessionFactory() as session:
        service = _service(session, _NoPickAgent())
        text = await service.reply(
            user_id=user_id,
            user_created_at=datetime.now(UTC),
            thread_id="t4",
            message="Hey there",
        )
        assert text == "Tell me how much time you have and I'll suggest something."


async def test_empty_library_makes_no_pick() -> None:
    async with _TestSessionFactory() as session:
        user_id, _ = await _seed(session, with_entry=False)
        await session.commit()

    async with _TestSessionFactory() as session:
        service = _service(session, DummyConciergeAgent())
        text = await service.reply(
            user_id=user_id,
            user_created_at=datetime.now(UTC),
            thread_id="t5",
            message="What should I play?",
        )
        assert "couldn't find anything" in text
        assert "RECOMMEND" not in text


@pytest.mark.parametrize(
    ("provider", "app_env", "expected"),
    [
        ("dummy", "testing", "DummyConciergeAgent"),
        ("langgraph", "production", "LangGraphConciergeAgent"),
    ],
)
def test_factory_selects_provider(provider: str, app_env: str, expected: str) -> None:
    from dailyloadout.config import Settings
    from dailyloadout.infrastructure.agent.concierge.factory import get_concierge_agent

    agent = get_concierge_agent(Settings(concierge_provider=provider, app_env=app_env))
    assert type(agent).__name__ == expected


def test_factory_rejects_unknown_provider() -> None:
    from dailyloadout.config import Settings
    from dailyloadout.infrastructure.agent.concierge.factory import get_concierge_agent

    with pytest.raises(ValueError, match="Unknown concierge provider"):
        get_concierge_agent(Settings(concierge_provider="bogus", app_env="production"))
