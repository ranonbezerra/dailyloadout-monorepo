"""unique index on lower(email) for active users

Account-integrity hardening (anti-abuse Block A): emails are normalized to
lowercase at the application layer, and this functional unique index enforces
case-insensitive uniqueness at the database layer for non-deleted users.
Assumes existing data is already clean (no case-folding collisions).

Revision ID: f7a2c4e91b08
Revises: b82c2e98f4b0
Create Date: 2026-06-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a2c4e91b08"
down_revision: str | Sequence[str] | None = "b82c2e98f4b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add a case-insensitive unique index on email for active users."""
    op.create_index(
        "uq_users_lower_email_active",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Drop the case-insensitive unique email index."""
    op.drop_index(
        "uq_users_lower_email_active",
        table_name="users",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
