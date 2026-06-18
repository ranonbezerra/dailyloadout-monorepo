"""add audio_path to captures

Revision ID: e26e20621efc
Revises: dcab916f9edd
Create Date: 2026-06-17 22:34:10.954225

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e26e20621efc"
down_revision: str | Sequence[str] | None = "dcab916f9edd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("captures", sa.Column("audio_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("captures", "audio_path")
