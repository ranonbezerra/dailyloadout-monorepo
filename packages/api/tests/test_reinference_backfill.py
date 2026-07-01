"""Batch re-inference / backfill: idempotency, resume, limit, budget, both kinds (Epic 28)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slate.config import settings
from slate.core.backfill.service import BackfillService
from slate.infrastructure.db.models import Game, LibraryEntry, Platform, PlaySession, User
from slate.infrastructure.embedding import DummyEmbeddingClient
from slate.infrastructure.llm.dummy import DummyLLMClient
from tests.conftest import _TestSessionFactory

_NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
_EMAIL = iter(f"bf{i}@x.com" for i in range(1000))


class FailingEmbeddingClient(DummyEmbeddingClient):
    """Embeds nothing — every call raises, so embed_session returns False."""

    async def embed(self, texts: list[str]) -> list[list[float]]:  # type: ignore[override]
        raise RuntimeError("embedding backend down")


class FailingLLMClient(DummyLLMClient):
    """Extraction raises — the item is caught, counted failed, and left stale."""

    async def extract_wrap_up_state(self, game_title: str, wrap_up_text: str):  # type: ignore[override]
        raise RuntimeError("llm backend down")


async def _fixtures(session: AsyncSession) -> tuple[User, LibraryEntry]:
    user = User(email=next(_EMAIL), display_name="bf")
    game = Game(slug="elden-ring", title="Elden Ring", metadata_source="user")
    platform = Platform(slug="pc", label="PC", family="pc")
    session.add_all([user, game, platform])
    await session.flush()
    entry = LibraryEntry(
        user_id=user.id, game_id=game.id, platform_id=platform.id, status="playing"
    )
    session.add(entry)
    await session.flush()
    return user, entry


async def _seed(
    session: AsyncSession,
    user: User,
    entry: LibraryEntry,
    text: str,
    *,
    embedding_model: str | None = None,
    extraction_version: str | None = None,
    extracted_state: dict[str, object] | None = None,
) -> PlaySession:
    ps = PlaySession(
        user_id=user.id,
        library_entry_id=entry.id,
        play_session_type="regular",
        started_at=_NOW - timedelta(hours=2),
        ended_at=_NOW,
        ended_via="wrap_up_completed",
        wrap_up_text=text,
        extracted_state=extracted_state,
        embedding_model=embedding_model,
        extraction_version=extraction_version,
    )
    session.add(ps)
    await session.flush()
    return ps


def _service(*, embed_model: str = "new-embed", failing: bool = False) -> BackfillService:
    cls = FailingEmbeddingClient if failing else DummyEmbeddingClient
    return BackfillService(
        _TestSessionFactory,
        DummyLLMClient(),
        cls(dimensions=settings.embedding_dimensions, model=embed_model),
        settings,
    )


async def _get(play_session_id: int) -> PlaySession:
    async with _TestSessionFactory() as s:
        row = await s.get(PlaySession, play_session_id)
        assert row is not None
        return row


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


class TestEmbeddingsBackfill:
    async def test_plan_counts_only_stale(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            await _seed(s, user, entry, "current", embedding_model="new-embed")
            await _seed(s, user, entry, "old", embedding_model="old-embed")
            await _seed(s, user, entry, "never")  # embedding_model NULL
            await s.commit()

        plan = await _service(embed_model="new-embed").plan("embeddings")
        assert plan.total == 3
        assert plan.stale == 2  # old + null; the current one is skipped
        assert plan.current_version == "new-embed"

    async def test_run_is_idempotent(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            stale = await _seed(s, user, entry, "note one", embedding_model="old-embed")
            await _seed(s, user, entry, "note two")  # null
            await s.commit()
        svc = _service(embed_model="new-embed")

        first = await svc.run("embeddings")
        assert first.processed == 2 and first.failed == 0 and first.stopped is None

        row = await _get(stale.id)
        assert row.embedding_model == "new-embed"  # stamped to current

        # Re-run: everything is current now, so nothing is reprocessed.
        assert (await svc.plan("embeddings")).stale == 0
        second = await svc.run("embeddings")
        assert second.processed == 0

    async def test_limit_caps_rows_attempted(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            for i in range(3):
                await _seed(s, user, entry, f"note {i}")  # all null → stale
            await s.commit()
        svc = _service(embed_model="new-embed")

        report = await svc.run("embeddings", limit=1)
        assert report.processed == 1 and report.stopped == "limit"
        assert (await svc.plan("embeddings")).stale == 2  # the other two remain

    async def test_failure_leaves_row_stale_for_retry(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            ps = await _seed(s, user, entry, "note", embedding_model="old-embed")
            await s.commit()
        svc = _service(embed_model="new-embed", failing=True)

        report = await svc.run("embeddings")
        assert report.processed == 0 and report.failed == 1

        row = await _get(ps.id)
        assert row.embedding_model == "old-embed"  # unchanged → still stale, retried next run

    async def test_budget_hook_stops_before_processing(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            await _seed(s, user, entry, "note")  # stale
            await s.commit()

        async def _no_budget() -> bool:
            return False

        report = await _service().run("embeddings", budget_ok=_no_budget)
        assert report.processed == 0 and report.stopped == "budget"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


class TestExtractionBackfill:
    async def test_run_reextracts_and_is_idempotent(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            ps = await _seed(s, user, entry, "got the sword in the crypt")  # version NULL
            await s.commit()
        svc = _service()

        report = await svc.run("extraction")
        assert report.processed == 1 and report.failed == 0

        row = await _get(ps.id)
        assert row.extraction_version == settings.extraction_version  # stamped
        assert row.extracted_state is not None  # re-extracted
        assert row.embedding_model is not None  # re-embedded with the new state

        assert (await svc.plan("extraction")).stale == 0
        assert (await svc.run("extraction")).processed == 0

    async def test_plan_ignores_sessions_without_wrap_up(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            await _seed(s, user, entry, "has a note")  # counts
            # A session with no wrap-up yet is not backfillable.
            s.add(
                PlaySession(
                    user_id=user.id,
                    library_entry_id=entry.id,
                    play_session_type="regular",
                    started_at=_NOW,
                )
            )
            await s.commit()

        plan = await _service().plan("extraction")
        assert plan.total == 1 and plan.stale == 1

    async def test_extraction_failure_leaves_row_stale(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            ps = await _seed(s, user, entry, "note")  # extraction_version NULL
            await s.commit()
        svc = BackfillService(
            _TestSessionFactory,
            FailingLLMClient(),
            DummyEmbeddingClient(dimensions=settings.embedding_dimensions),
            settings,
        )

        report = await svc.run("extraction")
        assert report.processed == 0 and report.failed == 1

        assert (await _get(ps.id)).extraction_version is None  # unchanged → retried next run

    async def test_no_stale_rows_remain_after_run(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            for i in range(3):
                await _seed(s, user, entry, f"note {i}")
            await s.commit()
        await _service().run("extraction")

        async with _TestSessionFactory() as s:
            stmt = select(PlaySession).where(
                PlaySession.wrap_up_text.is_not(None),
                PlaySession.extraction_version.is_(None),
            )
            assert (await s.execute(stmt)).scalars().first() is None


class TestTaskiqWrapper:
    async def test_task_runs_the_service_on_the_worker(self) -> None:
        """The Taskiq wrapper builds the service (dummy providers in tests) and runs it."""
        from unittest.mock import patch

        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            ps = await _seed(s, user, entry, "task note")  # embedding_model NULL → stale
            await s.commit()

        with patch("slate.infrastructure.db.session.async_session_factory", _TestSessionFactory):
            from slate.infrastructure.tasks.backfill import backfill_task

            await backfill_task.original_func("embeddings")

        assert (await _get(ps.id)).embedding_model is not None  # the task re-embedded it
