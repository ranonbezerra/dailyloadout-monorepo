"""Direct repository tests for uncovered branches."""

from __future__ import annotations

from slate.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from slate.infrastructure.db.repositories.game import GameRepository
from tests.conftest import _TestSessionFactory


class TestGameRepository:
    async def test_get_by_id_returns_none(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            result = await repo.get_by_id(9999)
            assert result is None

    async def test_get_by_id_returns_game(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            game = await repo.create(
                slug="hollow-knight",
                title="Hollow Knight",
                metadata_source="user",
            )
            found = await repo.get_by_id(game.id)
            assert found is not None
            assert found.title == "Hollow Knight"

    async def test_get_by_igdb_id_returns_none(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            result = await repo.get_by_igdb_id(12345)
            assert result is None

    async def test_get_by_igdb_id_returns_game(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            await repo.create(
                slug="elden-ring",
                title="Elden Ring",
                metadata_source="igdb",
                igdb_id=42,
            )
            found = await repo.get_by_igdb_id(42)
            assert found is not None
            assert found.title == "Elden Ring"

    async def test_get_by_slug_returns_none(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            result = await repo.get_by_slug("nonexistent")
            assert result is None

    async def test_get_by_slug_returns_game(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            await repo.create(
                slug="celeste",
                title="Celeste",
                metadata_source="user",
            )
            found = await repo.get_by_slug("celeste")
            assert found is not None
            assert found.title == "Celeste"


class TestCaptureRepository:
    async def test_get_queued_returns_none_when_empty(self) -> None:
        async with _TestSessionFactory() as session:
            repo = CaptureRepository(session)
            result = await repo.get_queued()
            assert result is None


class TestCaptureCandidateRepository:
    async def test_create_bulk(self) -> None:
        from slate.infrastructure.db.models import Capture, User

        async with _TestSessionFactory() as session:
            user = User(email="test@x.com", password_hash="h", display_name="T")
            session.add(user)
            await session.flush()

            capture = Capture(
                user_id=user.id,
                input_type="text",
                raw_text="test",
                status="processing",
            )
            session.add(capture)
            await session.flush()

            repo = CaptureCandidateRepository(session)
            candidates = await repo.create_bulk(
                capture.id,
                [
                    {"title": "Hades", "confidence": 0.9},
                    {"title": "Celeste", "confidence": 0.8},
                ],
            )
            assert len(candidates) == 2
            assert candidates[0].title == "Hades"
            assert candidates[1].title == "Celeste"
