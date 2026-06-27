"""add admin_users grant table

Backoffice (Epic 21) Phase 1: admin rights are modelled as a grant row, not a
flag on ``users``. A row here = the user is a backoffice admin. Keeping the
privilege off the user table means a public user serializer cannot leak it, and
admin-ness is checked per request (never carried in the JWT).

Revision ID: a3f5e1c8b920
Revises: d4b1c7e29a30
Create Date: 2026-06-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f5e1c8b920"
down_revision: str | Sequence[str] | None = "d4b1c7e29a30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ``admin_users`` grant table."""
    op.create_table(
        "admin_users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("granted_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_admin_users_user_id"),
    )


def downgrade() -> None:
    """Drop the ``admin_users`` table."""
    op.drop_table("admin_users")
