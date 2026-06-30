"""Semantic LLM completion cache (Epic 27).

One row per cached completion: the prompt's embedding + the completion it produced,
scoped by ``(namespace, model, role, json_mode)`` so a lookup only ever considers
entries that are param-compatible and namespace-isolated. The vector is a pgvector
column on Postgres; a JSON list under SQLite tests (the repo ranks in Python there).
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from slate.infrastructure.db.base import Base, TimestampMixin

# Must match settings.embedding_dimensions and the embedding model (nomic-embed-text).
_EMBEDDING_DIM = 768


class LlmSemanticCacheEntry(TimestampMixin, Base):
    __tablename__ = "llm_semantic_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Isolation key: a lookup is scoped to one namespace so a completion that
    # embedded user data is never served to another user (see SemanticLLMCache).
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    json_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prompt_embedding: Mapped[list[float]] = mapped_column(
        Vector(_EMBEDDING_DIM).with_variant(JSON(), "sqlite"), nullable=False
    )
    completion: Mapped[str] = mapped_column(Text, nullable=False)
    # TTL: a lookup ignores expired rows (staleness guard) without needing a sweeper.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("idx_llm_cache_scope", "namespace", "model", "role", "json_mode"),)
