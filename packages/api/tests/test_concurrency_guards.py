"""Atomic state-transition guards (security hardening).

Each terminal-state write — accepting/rejecting a Pick, confirming/rejecting a
capture candidate, ending a play_session — is a conditional UPDATE guarded by
the current state, so two concurrent requests for the same resource can't both
win. These tests exercise the repository guards directly: the SECOND claim on an
already-transitioned row must return ``False`` (which the services map to a 409),
proving the check-then-write race is closed at the data layer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from slate.infrastructure.db.models import (
    Capture,
    CaptureCandidate,
    Game,
    LibraryEntry,
    MfaRecoveryCode,
    Pick,
    Platform,
    PlaySession,
    User,
    UserMfa,
)
from slate.infrastructure.db.repositories.capture import CaptureCandidateRepository
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.mfa import MfaRepository
from slate.infrastructure.db.repositories.pick import PickRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.db.repositories.refresh_token import RefreshTokenRepository

_ENGINE = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
_Session = async_sessionmaker(_ENGINE, expire_on_commit=False)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    from slate.infrastructure.db.base import Base

    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        yield s
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _seed_user_game_platform(session: AsyncSession) -> tuple[User, LibraryEntry]:
    user = User(email="racer@example.com", password_hash="x", display_name="Racer")
    game = Game(slug="hades", title="Hades", metadata_source="manual")
    platform = Platform(slug="pc", label="PC", family="pc")
    session.add_all([user, game, platform])
    await session.flush()
    entry = LibraryEntry(
        user_id=user.id, game_id=game.id, platform_id=platform.id, status="backlog"
    )
    session.add(entry)
    await session.flush()
    return user, entry


class TestPickActionGuard:
    async def test_second_set_action_loses(self, session: AsyncSession) -> None:
        user, entry = await _seed_user_game_platform(session)
        pick = Pick(
            user_id=user.id,
            library_entry_id=entry.id,
            mood="chill",
            available_minutes=60,
            mental_energy="medium",
        )
        session.add(pick)
        await session.flush()
        repo = PickRepository(session)

        # First claim wins; a concurrent accept/reject of the same pick loses.
        assert await repo.set_action(pick.id, "accepted") is True
        assert await repo.set_action(pick.id, "rejected") is False


class TestCandidateStatusGuard:
    async def test_second_claim_loses(self, session: AsyncSession) -> None:
        user, _ = await _seed_user_game_platform(session)
        capture = Capture(user_id=user.id, input_type="text", raw_text="hades")
        session.add(capture)
        await session.flush()
        candidate = CaptureCandidate(capture_id=capture.id, title="Hades", status="pending")
        session.add(candidate)
        await session.flush()
        repo = CaptureCandidateRepository(session)

        assert await repo.claim_status(candidate.id, "confirmed") is True
        # A concurrent confirm OR reject of the same candidate must lose.
        assert await repo.claim_status(candidate.id, "rejected") is False


class TestPlaySessionEndGuard:
    async def test_second_end_loses(self, session: AsyncSession) -> None:
        user, entry = await _seed_user_game_platform(session)
        play_session = PlaySession(user_id=user.id, library_entry_id=entry.id)
        session.add(play_session)
        await session.flush()
        repo = PlaySessionRepository(session)

        assert await repo.end_play_session(play_session.id, ended_via="wrap_up_completed") is True
        # A concurrent end / wrap-up must not double-end (would re-dispatch LLM work).
        assert await repo.end_play_session(play_session.id, ended_via="paused_app") is False


class TestRefreshRevokeGuard:
    async def test_second_revoke_loses(self, session: AsyncSession) -> None:
        user = User(email="r@example.com", password_hash="x", display_name="R")
        session.add(user)
        await session.flush()
        repo = RefreshTokenRepository(session)
        token = await repo.create(
            user_id=user.id, token_hash="h", expires_at=datetime.now(UTC) + timedelta(days=1)
        )
        # First rotation revokes; a concurrent rotation of the same token loses,
        # so it can't mint a second (undetected) token family.
        assert await repo.revoke(token.id) is True
        assert await repo.revoke(token.id) is False


class TestMfaConsumeGuards:
    async def test_recovery_code_consumed_once(self, session: AsyncSession) -> None:
        user = User(email="m@example.com", password_hash="x", display_name="M")
        session.add(user)
        await session.flush()
        session.add(MfaRecoveryCode(user_id=user.id, code_hash="abc"))
        await session.flush()
        repo = MfaRepository(session)

        assert await repo.consume_recovery_code(user.id, "abc") is True
        # A concurrent second submission of the same code must not double-spend.
        assert await repo.consume_recovery_code(user.id, "abc") is False

    async def test_totp_step_advances_only_forward(self, session: AsyncSession) -> None:
        user = User(email="t@example.com", password_hash="x", display_name="T")
        session.add(user)
        await session.flush()
        session.add(UserMfa(user_id=user.id, totp_secret="s"))
        await session.flush()
        repo = MfaRepository(session)

        assert await repo.try_advance_totp_step(user.id, 100) is True
        # Same step (replay) and an older step both lose; a newer step wins.
        assert await repo.try_advance_totp_step(user.id, 100) is False
        assert await repo.try_advance_totp_step(user.id, 99) is False
        assert await repo.try_advance_totp_step(user.id, 101) is True


class TestUpdateMassAssignmentGuard:
    async def test_library_update_rejects_ownership_field(self, session: AsyncSession) -> None:
        _user, entry = await _seed_user_game_platform(session)
        repo = LibraryRepository(session)
        await repo.update(entry, status="playing")  # allowed field is fine
        with pytest.raises(ValueError, match="cannot be updated"):
            await repo.update(entry, user_id=999)

    async def test_game_update_rejects_identity_field(self, session: AsyncSession) -> None:
        import uuid

        _user, entry = await _seed_user_game_platform(session)
        game = await session.get(Game, entry.game_id)
        assert game is not None
        repo = GameRepository(session)
        with pytest.raises(ValueError, match="cannot be updated"):
            await repo.update(game, public_id=uuid.uuid4())
