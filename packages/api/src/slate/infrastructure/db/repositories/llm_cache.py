"""Repository for the semantic LLM completion cache (Epic 27).

``find_nearest`` is dual-path: on Postgres it uses pgvector's ``<=>`` cosine-distance
operator (the real ANN-capable path that scales); under SQLite tests it fetches the
scoped candidates and ranks in Python. Both honour the same scope (namespace + params)
and TTL, so the cache *logic* is fully covered by the SQLite suite.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from slate.infrastructure.db.models import LlmSemanticCacheEntry
from slate.infrastructure.embedding import cosine_similarity


class LlmSemanticCacheRepository:
    """Insert + nearest-neighbour lookup over cached completions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _is_postgres(self) -> bool:
        bind = self._session.bind
        return bind is not None and bind.dialect.name == "postgresql"

    def _scope(
        self, namespace: str, model: str, role: str, json_mode: bool
    ) -> list[ColumnElement[bool]]:
        now = datetime.now(UTC)
        return [
            LlmSemanticCacheEntry.namespace == namespace,
            LlmSemanticCacheEntry.model == model,
            LlmSemanticCacheEntry.role == role,
            LlmSemanticCacheEntry.json_mode == json_mode,
            LlmSemanticCacheEntry.expires_at > now,
        ]

    async def insert(
        self,
        *,
        namespace: str,
        model: str,
        role: str,
        json_mode: bool,
        embedding: list[float],
        completion: str,
        expires_at: datetime,
    ) -> None:
        """Store a completion + its prompt embedding."""
        self._session.add(
            LlmSemanticCacheEntry(
                namespace=namespace,
                model=model,
                role=role,
                json_mode=json_mode,
                prompt_embedding=embedding,
                completion=completion,
                expires_at=expires_at,
            )
        )
        await self._session.flush()

    async def find_nearest(
        self,
        *,
        namespace: str,
        model: str,
        role: str,
        json_mode: bool,
        embedding: list[float],
        min_similarity: float,
    ) -> tuple[str, float] | None:
        """Return ``(completion, cosine_similarity)`` of the nearest non-expired entry
        in the scope whose similarity clears *min_similarity*, else ``None``."""
        scope = self._scope(namespace, model, role, json_mode)
        if self._is_postgres():
            distance = LlmSemanticCacheEntry.prompt_embedding.cosine_distance(embedding)
            stmt = (
                select(LlmSemanticCacheEntry.completion, distance.label("distance"))
                .where(*scope)
                .order_by(distance)
                .limit(1)
            )
            row = (await self._session.execute(stmt)).first()
            if row is None:
                return None
            completion, dist = row
            similarity = 1.0 - float(dist)
            return (completion, similarity) if similarity >= min_similarity else None

        # SQLite (tests): fetch the scoped candidates and rank in Python.
        stmt = select(
            LlmSemanticCacheEntry.completion, LlmSemanticCacheEntry.prompt_embedding
        ).where(*scope)
        best: tuple[str, float] | None = None
        for completion, stored in (await self._session.execute(stmt)).all():
            similarity = cosine_similarity(embedding, [float(x) for x in stored])
            if similarity >= min_similarity and (best is None or similarity > best[1]):
                best = (completion, similarity)
        return best
