"""add image_path to captures

Revision ID: f3a1b8c92d47
Revises: e26e20621efc
Create Date: 2026-06-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a1b8c92d47"
down_revision: str | Sequence[str] | None = "e26e20621efc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("captures", sa.Column("image_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("captures", "image_path")
