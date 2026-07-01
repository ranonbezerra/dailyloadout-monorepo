"""add refresh_tokens.public_id (session management)

Give each refresh token an opaque UUID handle so the API can list and revoke
individual sessions without exposing the sequential primary key. Existing rows
are backfilled by the ``gen_random_uuid()`` server default.

Revision ID: b2f8a1c3d4e5
Revises: a1e7c4b9d2f6
Create Date: 2026-07-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2f8a1c3d4e5"
down_revision: str | Sequence[str] | None = "a1e7c4b9d2f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the unique ``public_id`` handle to ``refresh_tokens``."""
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "public_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_unique_constraint("uq_refresh_tokens_public_id", "refresh_tokens", ["public_id"])


def downgrade() -> None:
    op.drop_constraint("uq_refresh_tokens_public_id", "refresh_tokens", type_="unique")
    op.drop_column("refresh_tokens", "public_id")
