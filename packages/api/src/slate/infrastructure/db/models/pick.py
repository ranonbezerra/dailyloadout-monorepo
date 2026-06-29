"""Pick domain model."""

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slate.infrastructure.db.models.auth import User
    from slate.infrastructure.db.models.library import LibraryEntry
    from slate.infrastructure.db.models.play_session import PlaySession

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slate.infrastructure.db.base import Base, TimestampMixin


class Pick(TimestampMixin, Base):
    __tablename__ = "picks"

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
    library_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("library_entries.id", ondelete="SET NULL"), nullable=True
    )
    # User inputs
    mood: Mapped[str] = mapped_column(String, nullable=False)
    available_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mental_energy: Mapped[str] = mapped_column(String, nullable=False)
    context: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # LLM output
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Action tracking: null=pending, "accepted", "rejected", "ignored"
    action: Mapped[str | None] = mapped_column(String, nullable=True)
    play_session_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("play_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="picks")
    library_entry: Mapped["LibraryEntry | None"] = relationship(back_populates="picks")
    play_session: Mapped["PlaySession | None"] = relationship()

    __table_args__ = (
        Index("idx_picks_user_action", "user_id", "action"),
        Index("idx_picks_user_created", "user_id", text("created_at DESC")),
    )
