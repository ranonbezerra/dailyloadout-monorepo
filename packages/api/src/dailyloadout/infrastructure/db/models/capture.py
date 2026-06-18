"""Capture domain models: Capture, CaptureCandidate."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dailyloadout.infrastructure.db.models.auth import User  # noqa: F401
    from dailyloadout.infrastructure.db.models.library import Game  # noqa: F401

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dailyloadout.infrastructure.db.base import Base


class Capture(Base):
    __tablename__ = "captures"

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
    input_type: Mapped[str] = mapped_column(String, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    user: Mapped["User"] = relationship(back_populates="captures")
    candidates: Mapped[list["CaptureCandidate"]] = relationship(
        back_populates="capture", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_captures_user_status", "user_id", "status"),
        Index("idx_captures_created", text("created_at DESC")),
    )


class CaptureCandidate(Base):
    __tablename__ = "capture_candidates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
    )
    capture_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("captures.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    platform_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    igdb_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    igdb_title: Mapped[str | None] = mapped_column(String, nullable=True)
    igdb_cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    igdb_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    igdb_genres: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    igdb_first_release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    matched_game_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("games.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    capture: Mapped["Capture"] = relationship(back_populates="candidates")
    matched_game: Mapped["Game | None"] = relationship()
