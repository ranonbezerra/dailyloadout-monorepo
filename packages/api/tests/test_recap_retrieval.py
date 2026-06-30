"""Semantic recap retrieval: ranking, per-user isolation, and recent fallback (Epic 24)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from slate.config import settings
from slate.core.play_session.retrieval import get_grounding_sessions
from slate.infrastructure.db.models import Game, LibraryEntry, Platform, PlaySession, User
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.embedding import DummyEmbeddingClient
from tests.conftest import _TestSessionFactory

_NOW = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
_CLIENT = DummyEmbeddingClient(dimensions=settings.embedding_dimensions)


async def _user(session: AsyncSession, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0])
    session.add(user)
    await session.flush()
    return user


async def _entry(
    session: AsyncSession, user_id: int, game_id: int, platform_id: int
) -> LibraryEntry:
    entry = LibraryEntry(
        user_id=user_id, game_id=game_id, platform_id=platform_id, status="playing"
    )
    session.add(entry)
    await session.flush()
    return entry


async def _session_row(
    session: AsyncSession,
    user_id: int,
    entry_id: int,
    text: str,
    *,
    days_ago: int,
    embed: bool = True,
) -> PlaySession:
    ps = PlaySession(
        user_id=user_id,
        library_entry_id=entry_id,
        play_session_type="regular",
        started_at=_NOW - timedelta(days=days_ago, hours=2),
        ended_at=_NOW - timedelta(days=days_ago),
        ended_via="wrap_up_completed",
        wrap_up_text=text,
        extracted_state={"location": text},
    )
    session.add(ps)
    await session.flush()
    if embed:
        ps.embedding = await _CLIENT.embed_one(text)
        ps.embedding_model = _CLIENT.model
        await session.flush()
    return ps


@pytest.fixture
def semantic_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "recap_retrieval", "semantic")


class TestSemanticRetrieval:
    async def test_ranks_relevant_older_session_over_recent_irrelevant(
        self, semantic_mode: None
    ) -> None:
        async with _TestSessionFactory() as s:
            user = await _user(s, "ranker@x.com")
            game = Game(slug="elden-ring", title="Elden Ring", metadata_source="user")
            platform = Platform(slug="pc", label="PC", family="pc")
            s.add_all([game, platform])
            await s.flush()
            entry = await _entry(s, user.id, game.id, platform.id)

            # Newest is the query; the irrelevant note is more recent than the
            # relevant one, so 'recent' and 'semantic' must disagree.
            latest = await _session_row(
                s, user.id, entry.id, "Stormveil Castle Margit boss", days_ago=1
            )
            irrelevant = await _session_row(
                s, user.id, entry.id, "Limgrave Tree Sentinel grace", days_ago=2
            )
            relevant = await _session_row(
                s, user.id, entry.id, "back at Stormveil Castle fighting Margit", days_ago=5
            )
            await s.commit()
            latest_id, relevant_id, irrelevant_id = latest.id, relevant.id, irrelevant.id

        async with _TestSessionFactory() as s:
            chosen = await get_grounding_sessions(PlaySessionRepository(s), entry.id, limit=2)
            ids = [ps.id for ps in chosen]

        assert ids[0] == latest_id  # the latest is always the immediate context
        assert relevant_id in ids  # the semantically similar older session is surfaced
        assert irrelevant_id not in ids  # the chronologically-closer irrelevant one is not

    async def test_never_returns_another_users_sessions(self, semantic_mode: None) -> None:
        async with _TestSessionFactory() as s:
            user_a = await _user(s, "a@x.com")
            user_b = await _user(s, "b@x.com")
            game = Game(slug="elden-ring", title="Elden Ring", metadata_source="user")
            platform = Platform(slug="pc", label="PC", family="pc")
            s.add_all([game, platform])
            await s.flush()
            entry_a = await _entry(s, user_a.id, game.id, platform.id)
            entry_b = await _entry(s, user_b.id, game.id, platform.id)

            # Identical text for both users → identical vectors. Isolation must come
            # from the (entry) scope, never from the vectors being different.
            await _session_row(s, user_a.id, entry_a.id, "Stormveil Castle Margit", days_ago=1)
            await _session_row(
                s, user_a.id, entry_a.id, "Stormveil Castle Margit again", days_ago=3
            )
            b_session = await _session_row(
                s, user_b.id, entry_b.id, "Stormveil Castle Margit", days_ago=1
            )
            await s.commit()
            entry_a_id, b_session_id = entry_a.id, b_session.id

        async with _TestSessionFactory() as s:
            chosen = await get_grounding_sessions(PlaySessionRepository(s), entry_a_id, limit=5)

        assert all(ps.library_entry_id == entry_a_id for ps in chosen)
        assert b_session_id not in [ps.id for ps in chosen]

    async def test_falls_back_to_recent_when_nothing_embedded(self, semantic_mode: None) -> None:
        async with _TestSessionFactory() as s:
            user = await _user(s, "fallback@x.com")
            game = Game(slug="elden-ring", title="Elden Ring", metadata_source="user")
            platform = Platform(slug="pc", label="PC", family="pc")
            s.add_all([game, platform])
            await s.flush()
            entry = await _entry(s, user.id, game.id, platform.id)
            # Extracted but NOT embedded → semantic finds nothing, must fall back.
            await _session_row(s, user.id, entry.id, "Stormveil", days_ago=1, embed=False)
            await s.commit()
            entry_id = entry.id

        async with _TestSessionFactory() as s:
            chosen = await get_grounding_sessions(PlaySessionRepository(s), entry_id, limit=3)

        assert len(chosen) == 1  # recovered via the recent (chronological) path
