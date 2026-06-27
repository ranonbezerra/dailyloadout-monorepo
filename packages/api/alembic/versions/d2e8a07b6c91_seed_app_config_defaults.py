"""seed app_config with the standard operational values

Backoffice (Epic 21) Phase 3. Pre-populates the ``app_config`` override table
with the current standard value of every curated knob, so the backoffice shows
real, editable rows from day one and the managed baseline is captured in version
history (auditable, reviewable) rather than living only in code defaults.

Precedence note: once a key has a row here, the runtime overlay treats Postgres
as authoritative for it (override > env > default), so these values — not the
matching env vars — are what the app reads. Values are hard-coded (not imported
from app code) so this migration stays a faithful historical snapshot.

Revision ID: d2e8a07b6c91
Revises: c1d9e6f3a274
Create Date: 2026-06-27 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e8a07b6c91"
down_revision: str | Sequence[str] | None = "c1d9e6f3a274"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The standard values, snapshotted from config.py at this point in history.
# (key, JSON value)
_SEED: list[tuple[str, object]] = [
    # Kill-switches
    ("rate_limit_enabled", True),
    ("cost_guard_enabled", True),
    ("concierge_write_tools_enabled", True),
    # Incident-tunable caps
    ("cost_user_per_day", 200),
    ("cost_global_per_day", 5000),
    ("rate_limit_register_per_minute", 5),
    ("igdb_user_budget_per_day", 300),
    # Product rules
    ("catalog_share_threshold", 5),
    ("block_disposable_emails", True),
]


def _table() -> sa.Table:
    return sa.table(
        "app_config",
        sa.column("key", sa.String()),
        sa.column("value", postgresql.JSONB()),
        sa.column("updated_by", sa.BigInteger()),
    )


def upgrade() -> None:
    """Insert the standard value for every curated key (system seed)."""
    op.bulk_insert(
        _table(),
        [{"key": key, "value": value, "updated_by": None} for key, value in _SEED],
    )


def downgrade() -> None:
    """Remove the seeded rows."""
    keys = tuple(key for key, _ in _SEED)
    table = _table()
    op.execute(table.delete().where(table.c.key.in_(keys)))
