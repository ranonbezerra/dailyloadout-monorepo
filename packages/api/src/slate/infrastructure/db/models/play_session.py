"""PlaySession domain model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slate.infrastructure.db.models.auth import User
    from slate.infrastructure.db.models.library import LibraryEntry

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slate.infrastructure.db.base import Base, TimestampMixin

# Width of the wrap-up embedding. Must match settings.embedding_dimensions and the
# embedding model (nomic-embed-text = 768); a change means a migration + re-embed.
_EMBEDDING_DIM = 768


class PlaySession(TimestampMixin, Base):
    __tablename__ = "play_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    library_entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("library_entries.id", ondelete="CASCADE"), nullable=False
    )
    recap_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    wrap_up_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_state: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    # Semantic embedding of the wrap-up (Epic 24). pgvector on Postgres; a JSON list
    # under SQLite tests (retrieval ranks in Python, so no pgvector operator is used).
    # Deferred: 768 floats must never be dragged into ordinary session/stats queries.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(_EMBEDDING_DIM).with_variant(JSON(), "sqlite"),
        nullable=True,
        deferred=True,
    )
    # The model that produced `embedding`, so a model swap can be detected and the
    # corpus re-embedded (never silently mixing vector spaces during retrieval).
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    play_session_type: Mapped[str] = mapped_column(
        String, nullable=False, default="regular", server_default="regular"
    )
    ended_via: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="play_sessions")
    library_entry: Mapped["LibraryEntry"] = relationship(back_populates="play_sessions")

    __table_args__ = (
        # One active play_session per user, enforced at DB level.
        Index(
            "idx_play_sessions_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("idx_play_sessions_entry_ended", "library_entry_id", text("ended_at DESC")),
        # Stats/history queries filter by user and ended play_sessions — the inverse
        # of the partial active index above. These composite indexes back the
        # "ended play_sessions for a user, newest first" and timeline scans.
        Index("idx_play_sessions_user_ended_at", "user_id", text("ended_at DESC")),
        Index("idx_play_sessions_user_started_at", "user_id", text("started_at DESC")),
    )
