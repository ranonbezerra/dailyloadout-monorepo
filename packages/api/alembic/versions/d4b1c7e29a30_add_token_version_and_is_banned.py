"""add token_version and is_banned to users

Anti-abuse Phase 2 (session kill-switch & incident response): adds the
``token_version`` counter (bumped to invalidate all outstanding access tokens
via the ``tv`` JWT claim) and the ``is_banned`` flag (rejected at the auth
boundary) to the users table.

Revision ID: d4b1c7e29a30
Revises: c1f7a9d3e4b2
Create Date: 2026-06-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b1c7e29a30"
down_revision: str | Sequence[str] | None = "c1f7a9d3e4b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``token_version`` and ``is_banned`` columns to ``users``."""
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_banned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Drop the anti-abuse columns from ``users``."""
    op.drop_column("users", "is_banned")
    op.drop_column("users", "token_version")
