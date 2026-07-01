"""Adaptive recap routing: pick quick vs deep from retrieval relevance (Epic 29).

The DB-touching half of the adaptive router. The pure decision logic (evaluator +
entitlement-gated action) lives in ``adaptive.py``; here we retrieve the player's own
history (Epic 24) and feed it to that logic. ``ensure_extractions_complete`` is imported
lazily to avoid a module-load cycle with ``recap.py`` (which calls this at generation time).
"""

from __future__ import annotations

from typing import Literal

import structlog

from slate.config import Settings
from slate.core.play_session.adaptive import evaluate_local_relevance, route_recap
from slate.core.play_session.retrieval import get_grounding_sessions
from slate.infrastructure.agent.base import AbstractRecapAgent
from slate.infrastructure.db.models import LibraryEntry
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()


async def resolve_auto_mode(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    settings: Settings,
    entry: LibraryEntry,
    *,
    agent: AbstractRecapAgent | None,
    entitled_to_deep: bool,
) -> Literal["quick", "deep"]:
    """Grade the retrieved local history and route to ``quick`` or ``deep``.

    Enough local grounding stays quick; thin/absent history escalates to deep — but only
    for an entitled user. Falls back to quick when the feature is off or no agent exists.
    The router only *chooses* the path; the downstream deadline + guards are untouched.
    """
    from slate.core.play_session.recap import ensure_extractions_complete

    if not settings.adaptive_recap_enabled or agent is None:
        return "quick"
    await ensure_extractions_complete(play_session_repo, library_repo, llm_client, entry.id)
    sessions = await get_grounding_sessions(play_session_repo, entry.id, limit=3)
    verdict = evaluate_local_relevance(sessions, settings)
    chosen = route_recap(verdict, entitled_to_deep=entitled_to_deep)
    logger.info(
        "adaptive_recap_routed",
        library_entry_id=entry.id,
        verdict=verdict,
        chosen=chosen,
        entitled_to_deep=entitled_to_deep,
        session_count=len(sessions),
    )
    return chosen
