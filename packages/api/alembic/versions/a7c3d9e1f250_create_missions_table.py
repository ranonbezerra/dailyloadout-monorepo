"""create missions table

Revision ID: a7c3d9e1f250
Revises: 95879cf6d61f
Create Date: 2026-06-18 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3d9e1f250"
down_revision: str | Sequence[str] | None = "95879cf6d61f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "missions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("library_entry_id", sa.BigInteger(), nullable=False),
        sa.Column("briefing_text", sa.Text(), nullable=True),
        sa.Column("debrief_text", sa.Text(), nullable=True),
        sa.Column("extracted_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ended_via", sa.String(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["library_entry_id"],
            ["library_entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )

    # Partial unique index: one active mission per user.
    op.create_index(
        "idx_missions_user_active",
        "missions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )

    # Index for querying ended missions by library entry.
    op.create_index(
        "idx_missions_entry_ended",
        "missions",
        ["library_entry_id", sa.literal_column("ended_at DESC")],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_missions_entry_ended", table_name="missions")
    op.drop_index("idx_missions_user_active", table_name="missions")
    op.drop_table("missions")
