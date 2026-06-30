"""add llm_semantic_cache table (Epic 27)

Semantic LLM completion cache: one row per cached completion, keyed for lookup by
``(namespace, model, role, json_mode)`` with a pgvector embedding of the prompt. A
near-duplicate prompt (cosine over a threshold) reuses the completion. No ANN index
yet — the scoped + TTL'd candidate set is small for the safe targets this starts on;
an hnsw index is a scale follow-up.

Revision ID: e8b3d6c2a4f7
Revises: d5e2c7a9f1b4
Create Date: 2026-06-30 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8b3d6c2a4f7"
down_revision: str | Sequence[str] | None = "d5e2c7a9f1b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMBEDDING_DIM = 768


def upgrade() -> None:
    """Create the ``llm_semantic_cache`` table (pgvector already enabled in Epic 24)."""
    op.create_table(
        "llm_semantic_cache",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("json_mode", sa.Boolean(), nullable=False),
        sa.Column("prompt_embedding", Vector(_EMBEDDING_DIM), nullable=False),
        sa.Column("completion", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_llm_cache_scope",
        "llm_semantic_cache",
        ["namespace", "model", "role", "json_mode"],
    )


def downgrade() -> None:
    op.drop_index("idx_llm_cache_scope", table_name="llm_semantic_cache")
    op.drop_table("llm_semantic_cache")
