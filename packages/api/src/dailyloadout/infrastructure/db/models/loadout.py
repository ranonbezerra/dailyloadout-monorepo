"""Loadout domain model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dailyloadout.infrastructure.db.models.auth import User  # noqa: F401
    from dailyloadout.infrastructure.db.models.library import LibraryEntry  # noqa: F401
    from dailyloadout.infrastructure.db.models.mission import Mission  # noqa: F401

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dailyloadout.infrastructure.db.base import Base


class Loadout(Base):
    __tablename__ = "loadouts"

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
    mission_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("missions.id", ondelete="SET NULL"), nullable=True
    )
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
    user: Mapped["User"] = relationship(back_populates="loadouts")
    library_entry: Mapped["LibraryEntry | None"] = relationship(back_populates="loadouts")
    mission: Mapped["Mission | None"] = relationship()

    __table_args__ = (
        Index("idx_loadouts_user_action", "user_id", "action"),
        Index("idx_loadouts_user_created", "user_id", text("created_at DESC")),
    )
