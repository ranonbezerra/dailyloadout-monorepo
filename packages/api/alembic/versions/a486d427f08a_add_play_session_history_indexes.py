"""add play_session history indexes

Revision ID: a486d427f08a
Revises: d5e9a1c7b240
Create Date: 2026-06-25 22:01:25.493153

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a486d427f08a"
down_revision: str | Sequence[str] | None = "d5e9a1c7b240"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite indexes backing per-user ended/history queries.

    Stats and play_session-history filter ``user_id AND ended_at IS NOT NULL`` and
    scan timelines newest-first — the inverse of the existing partial active
    index. The LangGraph checkpoint tables seen by autogenerate are runtime-
    managed (not in our models) and intentionally not touched here.
    """
    op.create_index(
        "idx_play_sessions_user_ended_at",
        "play_sessions",
        ["user_id", sa.literal_column("ended_at DESC")],
        unique=False,
    )
    op.create_index(
        "idx_play_sessions_user_started_at",
        "play_sessions",
        ["user_id", sa.literal_column("started_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Drop the play_session history indexes."""
    op.drop_index("idx_play_sessions_user_started_at", table_name="play_sessions")
    op.drop_index("idx_play_sessions_user_ended_at", table_name="play_sessions")
