"""create picks table

Revision ID: b8d4e2f3a561
Revises: a7c3d9e1f250
Create Date: 2026-06-20 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d4e2f3a561"
down_revision: str | Sequence[str] | None = "a7c3d9e1f250"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "picks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("library_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("mood", sa.String(), nullable=False),
        sa.Column("available_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("mental_energy", sa.String(), nullable=False),
        sa.Column("context", sa.String(120), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("play_session_id", sa.BigInteger(), nullable=True),
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
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["library_entry_id"],
            ["library_entries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["play_session_id"],
            ["play_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )

    op.create_index(
        "idx_picks_user_action",
        "picks",
        ["user_id", "action"],
    )

    op.create_index(
        "idx_picks_user_created",
        "picks",
        ["user_id", sa.literal_column("created_at DESC")],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_picks_user_created", table_name="picks")
    op.drop_index("idx_picks_user_action", table_name="picks")
    op.drop_table("picks")
