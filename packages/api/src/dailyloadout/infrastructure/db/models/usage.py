"""Per-user, per-day usage counters (ROADMAP Epic 14).

A small, reusable primitive for free-tier abuse/cost guards — e.g. library
import images per day and vision-fallback calls per day. One row per
(user, key, day); the count is incremented as the quota is consumed.
"""

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from dailyloadout.infrastructure.db.base import Base, TimestampMixin


class UsageCounter(TimestampMixin, Base):
    __tablename__ = "usage_counters"

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
    # The quota key, e.g. "library_import_images" or "ocr_vision_fallback".
    key: Mapped[str] = mapped_column(String, nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "key", "day", name="uq_usage_counters_user_key_day"),
    )
