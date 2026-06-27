"""Auth domain models: User, OAuthIdentity, RefreshToken."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dailyloadout.infrastructure.db.models.capture import Capture
    from dailyloadout.infrastructure.db.models.library import LibraryEntry
    from dailyloadout.infrastructure.db.models.loadout import Loadout
    from dailyloadout.infrastructure.db.models.mission import Mission

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dailyloadout.infrastructure.db.base import Base, SoftDeleteMixin, TimestampMixin


class User(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locale: Mapped[str] = mapped_column(String, nullable=False, default="pt-BR")
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="America/Recife")
    # Anti-abuse: bumping this instantly invalidates every outstanding access
    # token (the ``tv`` JWT claim must match this value in get_current_user).
    token_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    # Anti-abuse: a banned account is rejected at the auth boundary (403).
    is_banned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    # Relationships
    oauth_identities: Mapped[list["OAuthIdentity"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    library_entries: Mapped[list["LibraryEntry"]] = relationship(back_populates="user")
    captures: Mapped[list["Capture"]] = relationship(back_populates="user")
    missions: Mapped[list["Mission"]] = relationship(back_populates="user")
    loadouts: Mapped[list["Loadout"]] = relationship(back_populates="user")

    __table_args__ = (
        Index(
            "idx_users_email_active",
            "email",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class AdminUser(Base):
    """Admin grant: a row here means the referenced user is a backoffice admin.

    Privilege is kept OFF the ``users`` table on purpose — a public user
    serializer physically cannot leak an admin flag that does not exist on the
    user row, and admin-ness is never carried in the JWT (it is checked
    per-request against this table, so revoking a grant is instant). Presence of
    a row = admin; there is no self-service path to create one (see
    ``scripts/grant_admin.py``). A future ``scopes`` column could add tiers
    without touching the user model.
    """

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Who granted this (audit trail); NULL for a CLI/bootstrap grant.
    granted_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", name="uq_admin_users_user_id"),)


class OAuthIdentity(Base):
    __tablename__ = "oauth_identities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    provider_uid: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="oauth_identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_uid", name="uq_oauth_provider_uid"),
        Index("idx_oauth_user", "user_id"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    device_label: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        Index(
            "idx_refresh_user_active",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("idx_refresh_tokens_user_id", "user_id"),
    )
