"""add app_config dynamic-override table

Backoffice (Epic 21) Phase 3: a Postgres-backed source of truth for runtime
overrides of a curated set of operational knobs (kill-switches, abuse caps,
feature flags). One row per overridden key; no row = use the env/code baseline.
Precedence at read time: override (this table) > env var > code default.

Revision ID: c1d9e6f3a274
Revises: b7c2f4a18d55
Create Date: 2026-06-27 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d9e6f3a274"
down_revision: str | Sequence[str] | None = "b7c2f4a18d55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ``app_config`` override table."""
    op.create_table(
        "app_config",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    """Drop the ``app_config`` table."""
    op.drop_table("app_config")
