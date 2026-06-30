"""Compose and persist the semantic embedding of a play_session wrap-up (Epic 24).

Shared by the async extraction task and its sync fallback, so an embedding is
produced wherever a wrap-up is extracted. Best-effort by design: the embedding
enriches retrieval but must never break the primary extraction — a backend failure
is logged and swallowed, and the session is simply left semantically unindexed (the
recap falls back to recent, and Epic 28's backfill can fill it in later).
"""

from __future__ import annotations

from collections.abc import Mapping

import structlog

from slate.infrastructure.db.repositories.play_session_embedding import (
    PlaySessionEmbeddingRepository,
)
from slate.infrastructure.embedding.base import AbstractEmbeddingClient

logger = structlog.get_logger()

# The structured fields folded into the embedding text, alongside the raw note.
_STATE_FIELDS = ("location", "current_quest", "next_action", "level")


def build_embedding_text(
    wrap_up_text: str | None,
    extracted_state: Mapping[str, object] | None,
) -> str:
    """Compose what to embed for a session: the raw note plus its structured state.

    Embedding both means a query matches whether it echoes the player's own wording
    or the normalised location/quest/level the LLM pulled out of it.
    """
    parts: list[str] = []
    if wrap_up_text:
        parts.append(wrap_up_text)
    if extracted_state:
        for field in _STATE_FIELDS:
            value = extracted_state.get(field)
            if value:
                parts.append(f"{field}: {value}")
    return "\n".join(parts)


async def embed_session(
    embedding_client: AbstractEmbeddingClient,
    embedding_repo: PlaySessionEmbeddingRepository,
    play_session_id: int,
    wrap_up_text: str | None,
    extracted_state: Mapping[str, object] | None,
) -> bool:
    """Embed a session's wrap-up and persist the vector. Returns whether one was stored."""
    text = build_embedding_text(wrap_up_text, extracted_state)
    if not text.strip():
        return False
    try:
        vector = await embedding_client.embed_one(text)
    except Exception:
        logger.warning("session_embedding_failed", play_session_id=play_session_id, exc_info=True)
        return False
    await embedding_repo.set_embedding(play_session_id, vector, embedding_client.model)
    return True
