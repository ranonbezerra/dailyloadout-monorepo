"""Repository for play_session wrap-up embeddings (Epic 24).

Split from ``PlaySessionRepository`` so the vector concern stays cohesive (and the
core repo under the size budget). Shares the caller's session.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from slate.infrastructure.db.models import PlaySession


class PlaySessionEmbeddingRepository:
    """Store + fetch the wrap-up embedding vectors on ``play_sessions``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_embedding(
        self,
        play_session_id: int,
        embedding: list[float],
        model: str,
    ) -> None:
        """Store the wrap-up embedding and the model that produced it."""
        play_session = await self._session.get(PlaySession, play_session_id)
        if play_session is not None:
            play_session.embedding = embedding
            play_session.embedding_model = model
            await self._session.flush()

    async def get_embedded_for_entry(
        self,
        library_entry_id: int,
        model: str,
        limit: int = 200,
    ) -> list[tuple[PlaySession, list[float]]]:
        """Ended sessions for the entry embedded by *model*, newest first.

        Loads the (otherwise deferred) ``embedding`` column and returns each session
        with its vector as a plain ``list[float]`` (pgvector returns an array on
        Postgres; SQLite a list — both coerced). Scoped to one entry and one model,
        so retrieval never mixes vector spaces across a model swap.
        """
        stmt = (
            select(PlaySession)
            .options(undefer(PlaySession.embedding))
            .where(
                PlaySession.library_entry_id == library_entry_id,
                PlaySession.ended_at.is_not(None),
                PlaySession.extracted_state.is_not(None),
                PlaySession.embedding.is_not(None),
                PlaySession.embedding_model == model,
            )
            .order_by(PlaySession.ended_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        sessions = list(result.scalars().all())
        return [(s, [float(x) for x in s.embedding or []]) for s in sessions]
