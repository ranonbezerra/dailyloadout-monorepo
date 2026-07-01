"""add last_totp_step to user_mfa (TOTP replay protection)

Track the highest consumed TOTP time-step per credential so an observed 6-digit
code cannot be replayed within its ~90s validity window (recovery codes were already
single-use; this closes the same gap for TOTP).

Revision ID: f1a4c7e9d2b6
Revises: e8b3d6c2a4f7
Create Date: 2026-06-30 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a4c7e9d2b6"
down_revision: str | Sequence[str] | None = "e8b3d6c2a4f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_mfa", sa.Column("last_totp_step", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_mfa", "last_totp_step")
