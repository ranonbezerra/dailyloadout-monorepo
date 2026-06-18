"""add_nintendo_switch_2_platform

Revision ID: 95879cf6d61f
Revises: f3a1b8c92d47
Create Date: 2026-06-18 14:20:20.702778

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95879cf6d61f"
down_revision: str | Sequence[str] | None = "f3a1b8c92d47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Nintendo Switch 2 platform."""
    platforms_table = sa.table(
        "platforms",
        sa.column("slug", sa.String),
        sa.column("label", sa.String),
        sa.column("family", sa.String),
    )
    op.bulk_insert(
        platforms_table,
        [{"slug": "switch-2", "label": "Nintendo Switch 2", "family": "nintendo"}],
    )


def downgrade() -> None:
    """Remove Nintendo Switch 2 platform."""
    op.execute("DELETE FROM platforms WHERE slug = 'switch-2'")
