"""game catalogue visibility (is_shared)

Anti-abuse Block C: manual ``games`` rows become PRIVATE to their creator until
validated, so one account can't spam offensive/junk titles into everyone's
catalogue. Adds ``is_shared`` (NOT NULL, default false). A game is browsable by
user U when ``igdb_id IS NOT NULL OR is_shared IS TRUE OR created_by_user_id = U``.

EXISTING rows are back-filled to ``is_shared = true`` so current global
visibility is preserved (nothing is retroactively hidden); only NEW manual rows
start private and earn sharing via IGDB enrichment or distinct-owner promotion.

The LangGraph checkpoint tables that autogenerate flags are runtime-managed (not
in our models) and intentionally left untouched.

Revision ID: c1f7a9d3e4b2
Revises: f7a2c4e91b08
Create Date: 2026-06-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1f7a9d3e4b2"
down_revision: str | Sequence[str] | None = "f7a2c4e91b08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``is_shared`` and preserve current global visibility for existing rows."""
    op.add_column(
        "games",
        sa.Column(
            "is_shared",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Preserve the pre-Block-C behaviour: every row that exists today was globally
    # visible, so mark it shared. New rows keep the server default (false).
    op.execute("UPDATE games SET is_shared = true")


def downgrade() -> None:
    """Drop the catalogue-visibility column."""
    op.drop_column("games", "is_shared")
