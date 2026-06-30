"""Choose which prior sessions ground the recap — recent vs semantic (Epic 24).

``recap_retrieval`` is the A/B switch:

- ``recent``   — the chronological last-N (Epic 6 behaviour). The default.
- ``semantic`` — the most *relevant* prior sessions by cosine similarity over their
  wrap-up embeddings, scoped to one ``(user, entry)``. The query is the latest
  session (always kept, as the immediate "where I left off"); the remaining slots go
  to the sessions most similar to it — surfacing the quest you're mid-way through
  even when it's older than the last 3.

Retrieval is per-game, so the candidate set is tiny: ranking in Python is correct
and cheap (no pgvector ANN needed). Falls back to ``recent`` whenever nothing is
embedded yet, so a fresh corpus or a failed-embedding path never breaks the recap.
"""

from __future__ import annotations

from slate.config import settings as _settings
from slate.infrastructure.db.models import PlaySession
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.embedding import rank_by_similarity
from slate.infrastructure.embedding.factory import get_embedding_client


async def get_grounding_sessions(
    play_session_repo: PlaySessionRepository,
    library_entry_id: int,
    *,
    limit: int = 3,
) -> list[PlaySession]:
    """Return up to *limit* prior sessions to ground the recap, per settings.recap_retrieval."""
    if _settings.recap_retrieval == "semantic":
        semantic = await _semantic(play_session_repo, library_entry_id, limit)
        if semantic:
            return semantic
        # Nothing embedded yet → fall through to the chronological path.
    return await play_session_repo.get_recent_for_entry(library_entry_id, limit=limit)


async def _semantic(
    play_session_repo: PlaySessionRepository,
    library_entry_id: int,
    limit: int,
) -> list[PlaySession]:
    """The latest session + the (limit-1) most similar older ones; [] if none embedded."""
    model = get_embedding_client(_settings).model
    candidates = await play_session_repo.get_embedded_for_entry(library_entry_id, model)
    if not candidates:
        return []

    # Newest first → the latest session is the query and is always included.
    query_session, query_vector = candidates[0]
    older = candidates[1:]
    if not older or limit <= 1:
        return [query_session]

    by_id = {session.id: session for session, _ in older}
    ranked = rank_by_similarity(
        query_vector,
        [(session.id, vector) for session, vector in older],
        top_k=limit - 1,
    )
    return [query_session] + [by_id[session_id] for session_id, _ in ranked]
