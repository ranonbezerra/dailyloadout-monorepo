"""Dynamic operational config model: the ``app_config`` override table.

Backoffice (Epic 21) Phase 3. The source of truth for *runtime overrides* of a
curated set of operational knobs (kill-switches, abuse caps, feature flags). One
row per overridden key; the absence of a row means "use the env/code baseline".
Postgres — not Redis — is the source of truth because it is durable (survives a
Redis flush/restart) and auditable; Redis is at most a short read-cache.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from slate.infrastructure.db.base import Base


class AppConfig(Base):
    """A runtime override for one curated operational key.

    ``value`` is JSON-typed so a key can hold a bool, int, or (later) a richer
    shape without a schema change. ``updated_by`` records which admin last wrote
    it (``SET NULL`` so the row survives a deleted account); the audit trail in
    ``admin_audit_log`` carries the full who/when/old→new history.
    """

    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[object] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
