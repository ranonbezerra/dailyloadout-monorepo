"""add extraction_version to play_sessions (Epic 28)

Batch re-inference / backfill: mark which extraction prompt+model produced each
row's ``extracted_state`` so a prompt/model change is detectable and the corpus can
be re-extracted idempotently (mirrors ``embedding_model`` for the embedding side).

Revision ID: a1e7c4b9d2f6
Revises: f1a4c7e9d2b6
Create Date: 2026-07-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1e7c4b9d2f6"
down_revision: str | Sequence[str] | None = "f1a4c7e9d2b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable extraction-version marker to ``play_sessions``."""
    op.add_column(
        "play_sessions",
        sa.Column("extraction_version", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Drop the extraction-version marker."""
    op.drop_column("play_sessions", "extraction_version")
