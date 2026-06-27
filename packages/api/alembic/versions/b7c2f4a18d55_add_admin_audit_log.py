"""add admin_audit_log table

Backoffice (Epic 21) Phase 2: every mutating admin action (ban/unban/verify, and
future config edits) writes an append-only row here — who acted, what action, on
whom, and an optional free-text detail. Both user FKs are ``SET NULL`` on delete
so the trail survives even if a referenced account is hard-deleted.

Revision ID: b7c2f4a18d55
Revises: a3f5e1c8b920
Create Date: 2026-06-27 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c2f4a18d55"
down_revision: str | Sequence[str] | None = "a3f5e1c8b920"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ``admin_audit_log`` table."""
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_user_id", sa.BigInteger(), nullable=True),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_admin_audit_created", "admin_audit_log", ["created_at"])


def downgrade() -> None:
    """Drop the ``admin_audit_log`` table."""
    op.drop_index("idx_admin_audit_created", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
