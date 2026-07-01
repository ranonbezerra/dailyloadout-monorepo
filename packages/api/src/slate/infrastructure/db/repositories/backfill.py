"""Repository for the batch re-inference / backfill job (Epic 28).

Finds rows whose AI-produced assets are stale relative to the *current* version —
embeddings (by ``embedding_model``) or extracted state (by ``extraction_version``) —
and pages them for reprocessing. A row is stale when its version marker is NULL
(never processed, or processed by an older build) or differs from the current one.

Paging is keyed by ``id > after_id`` so a run advances past rows regardless of
success: a failed item stays stale and is retried on the *next* run, never looping
the current one. Because each processed row's version flips to current, a re-run
naturally skips finished work — the job is idempotent and resumable.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from slate.infrastructure.db.models import Game, LibraryEntry, PlaySession


@dataclass(frozen=True)
class EmbeddingRow:
    """A session whose wrap-up embedding is stale."""

    id: int
    wrap_up_text: str | None
    extracted_state: dict[str, object] | None


@dataclass(frozen=True)
class ExtractionRow:
    """A session whose extracted state is stale (carries the game title to re-extract)."""

    id: int
    game_title: str
    wrap_up_text: str


class BackfillRepository:
    """Count and page stale rows, and stamp re-extracted state. Shares the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- embeddings ------------------------------------------------------

    async def count_stale_embeddings(self, current_model: str) -> int:
        """Sessions with a wrap-up whose embedding was not produced by *current_model*."""
        stmt = (
            select(func.count())
            .select_from(PlaySession)
            .where(
                PlaySession.wrap_up_text.is_not(None),
                or_(
                    PlaySession.embedding_model.is_(None),
                    PlaySession.embedding_model != current_model,
                ),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_embeddable(self) -> int:
        """Total sessions with a wrap-up (the denominator for the embedding backfill)."""
        stmt = (
            select(func.count())
            .select_from(PlaySession)
            .where(PlaySession.wrap_up_text.is_not(None))
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def page_stale_embeddings(
        self, current_model: str, after_id: int, limit: int
    ) -> list[EmbeddingRow]:
        """Next page of stale-embedding sessions with ``id > after_id``, id-ascending."""
        stmt = (
            select(PlaySession.id, PlaySession.wrap_up_text, PlaySession.extracted_state)
            .where(
                PlaySession.wrap_up_text.is_not(None),
                PlaySession.id > after_id,
                or_(
                    PlaySession.embedding_model.is_(None),
                    PlaySession.embedding_model != current_model,
                ),
            )
            .order_by(PlaySession.id)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [EmbeddingRow(id=r[0], wrap_up_text=r[1], extracted_state=r[2]) for r in rows]

    # --- extraction ------------------------------------------------------

    async def count_stale_extractions(self, current_version: str) -> int:
        """Sessions with a wrap-up whose extracted state is not at *current_version*."""
        stmt = (
            select(func.count())
            .select_from(PlaySession)
            .where(
                PlaySession.wrap_up_text.is_not(None),
                or_(
                    PlaySession.extraction_version.is_(None),
                    PlaySession.extraction_version != current_version,
                ),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def page_stale_extractions(
        self, current_version: str, after_id: int, limit: int
    ) -> list[ExtractionRow]:
        """Next page of stale-extraction sessions (joined to the game title), id-ascending."""
        stmt = (
            select(PlaySession.id, Game.title, PlaySession.wrap_up_text)
            .join(LibraryEntry, LibraryEntry.id == PlaySession.library_entry_id)
            .join(Game, Game.id == LibraryEntry.game_id)
            .where(
                PlaySession.wrap_up_text.is_not(None),
                PlaySession.id > after_id,
                or_(
                    PlaySession.extraction_version.is_(None),
                    PlaySession.extraction_version != current_version,
                ),
            )
            .order_by(PlaySession.id)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [ExtractionRow(id=r[0], game_title=r[1], wrap_up_text=r[2]) for r in rows]

    async def stamp_extraction(
        self, play_session_id: int, state: dict[str, object], version: str
    ) -> None:
        """Persist re-extracted state and mark it at *version*."""
        play_session = await self._session.get(PlaySession, play_session_id)
        if play_session is not None:
            play_session.extracted_state = state
            play_session.extraction_version = version
            await self._session.flush()
