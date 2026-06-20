"""Library domain models: Platform, Game, LibraryEntry."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dailyloadout.infrastructure.db.models.auth import User  # noqa: F401
    from dailyloadout.infrastructure.db.models.loadout import Loadout  # noqa: F401
    from dailyloadout.infrastructure.db.models.mission import Mission  # noqa: F401

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dailyloadout.infrastructure.db.base import Base


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    family: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    library_entries: Mapped[list["LibraryEntry"]] = relationship(back_populates="platform")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
    )
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    igdb_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    first_release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    genres: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    metadata_source: Mapped[str] = mapped_column(String, nullable=False)
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
    library_entries: Mapped[list["LibraryEntry"]] = relationship(back_populates="game")

    __table_args__ = (
        Index(
            "idx_games_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )


class LibraryEntry(Base):
    __tablename__ = "library_entries"

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
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("games.id"), nullable=False)
    platform_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("platforms.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="backlog")
    acquired_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mission_next_action: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    user: Mapped["User"] = relationship(back_populates="library_entries")
    game: Mapped["Game"] = relationship(back_populates="library_entries")
    platform: Mapped["Platform"] = relationship(back_populates="library_entries")
    missions: Mapped[list["Mission"]] = relationship(back_populates="library_entry")
    loadouts: Mapped[list["Loadout"]] = relationship(back_populates="library_entry")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "game_id", "platform_id", name="uq_library_user_game_platform"
        ),
        Index("idx_library_user_status", "user_id", "status"),
        Index(
            "idx_library_user_last_played",
            "user_id",
            text("last_played_at DESC NULLS LAST"),
        ),
    )
