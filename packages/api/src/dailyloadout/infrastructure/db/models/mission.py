"""Mission domain model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dailyloadout.infrastructure.db.models.auth import User  # noqa: F401
    from dailyloadout.infrastructure.db.models.library import LibraryEntry  # noqa: F401

from sqlalchemy import (
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

from dailyloadout.infrastructure.db.base import Base


class Mission(Base):
    __tablename__ = "missions"

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
    briefing_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    debrief_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_state: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    mission_type: Mapped[str] = mapped_column(
        String, nullable=False, default="regular", server_default="regular"
    )
    ended_via: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="missions")
    library_entry: Mapped["LibraryEntry"] = relationship(back_populates="missions")

    __table_args__ = (
        # One active mission per user, enforced at DB level.
        Index(
            "idx_missions_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("idx_missions_entry_ended", "library_entry_id", text("ended_at DESC")),
    )
