"""add_play_session_type

Revision ID: 995377a9f175
Revises: b8d4e2f3a561
Create Date: 2026-06-20 18:56:02.503054

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "995377a9f175"
down_revision: str | Sequence[str] | None = "b8d4e2f3a561"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOTE: picks.context is created by b8d4e2f3a561 (create_picks_table).
    # It was previously also added here, which double-added it on a from-scratch
    # `upgrade head` (existing DBs were unaffected). Removed — the create_table is
    # the column's single owner.
    op.add_column(
        "play_sessions",
        sa.Column("play_session_type", sa.String(), server_default="regular", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("play_sessions", "play_session_type")
