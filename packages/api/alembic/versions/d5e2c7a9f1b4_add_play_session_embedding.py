"""add wrap-up embedding to play_sessions (Epic 24)

RAG over PlaySession history: store a pgvector embedding of each wrap-up so the
recap can ground on the *semantically* most relevant prior sessions, not just the
chronological last-N. Enables the `vector` extension and adds two nullable columns —
the embedding and the model that produced it (so a model swap is detected and the
corpus re-embedded, never silently mixing vector spaces).

Revision ID: d5e2c7a9f1b4
Revises: c4f1a9b2e7d3
Create Date: 2026-06-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e2c7a9f1b4"
down_revision: str | Sequence[str] | None = "c4f1a9b2e7d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match settings.embedding_dimensions and the embedding model (nomic-embed-text).
_EMBEDDING_DIM = 768


def upgrade() -> None:
    """Enable pgvector and add the embedding columns to ``play_sessions``."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "play_sessions",
        sa.Column("embedding", Vector(_EMBEDDING_DIM), nullable=True),
    )
    op.add_column(
        "play_sessions",
        sa.Column("embedding_model", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Drop the embedding columns. Leave the `vector` extension installed —
    dropping a shared extension on a single feature's downgrade is unsafe."""
    op.drop_column("play_sessions", "embedding_model")
    op.drop_column("play_sessions", "embedding")
