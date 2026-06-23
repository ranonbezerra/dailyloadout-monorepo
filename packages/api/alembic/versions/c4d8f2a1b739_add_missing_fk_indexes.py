"""add_missing_fk_indexes

Revision ID: c4d8f2a1b739
Revises: 995377a9f175
Create Date: 2026-06-22 10:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8f2a1b739"
down_revision: str | Sequence[str] | None = "995377a9f175"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add indexes on frequently queried foreign key columns."""
    op.create_index("idx_library_entries_game_id", "library_entries", ["game_id"])
    op.create_index("idx_library_entries_platform_id", "library_entries", ["platform_id"])
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade() -> None:
    """Remove FK indexes."""
    op.drop_index("idx_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("idx_library_entries_platform_id", table_name="library_entries")
    op.drop_index("idx_library_entries_game_id", table_name="library_entries")
