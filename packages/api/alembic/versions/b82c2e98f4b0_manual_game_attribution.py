"""manual game attribution

Revision ID: b82c2e98f4b0
Revises: a486d427f08a
Create Date: 2026-06-26 09:40:44.421572

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b82c2e98f4b0"
down_revision: str | Sequence[str] | None = "a486d427f08a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record who first added each manual ``games`` row (attribution only).

    ``Game`` rows stay global/shared and ``slug`` stays globally unique
    (``games_slug_key`` untouched). ``created_by_user_id`` is nullable — NULL for
    IGDB / legacy rows — and exists so a future admin trash-review can audit
    manual additions. Visibility is unaffected; editing is gated in the service.

    The LangGraph checkpoint tables that autogenerate flags are runtime-managed
    (not in our models) and intentionally left untouched.
    """
    op.add_column(
        "games",
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_games_created_by_user_id_users",
        "games",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_games_created_by_user_id"),
        "games",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the manual-game attribution column."""
    op.drop_index(op.f("ix_games_created_by_user_id"), table_name="games")
    op.drop_constraint("fk_games_created_by_user_id_users", "games", type_="foreignkey")
    op.drop_column("games", "created_by_user_id")
