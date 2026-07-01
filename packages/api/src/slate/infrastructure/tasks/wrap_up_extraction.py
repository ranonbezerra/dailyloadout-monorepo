"""Async task: extract structured state from a play_session wrap_up via LLM."""

from __future__ import annotations

import structlog

from slate.infrastructure.observability import job_context
from slate.infrastructure.tasks.broker import broker

logger = structlog.get_logger()

# Defensive cap on the LLM input inside the worker. The normal submit path already
# caps the wrap-up at 2000 chars (sanitize_untrusted_text); this bounds a forged /
# misrouted broker message that skipped that path, so it can't drive unbounded LLM
# work. Set above the submit cap so legitimate input is never truncated.
_MAX_WRAP_UP_CHARS = 4000


@broker.task(retry_on_error=True, max_retries=3)
async def extract_wrap_up_state_task(
    play_session_id: int,
    game_title: str,
    wrap_up_text: str,
    user_id: int,
) -> None:
    """Extract structured state from a wrap_up and persist it.

    Runs as a background Taskiq task with up to 3 retries on failure.
    If all retries fail, the sync fallback in ``_ensure_extractions_complete``
    will handle it when the next play_session starts.

    *user_id* is the enqueuer's authenticated id; the task refuses to write unless
    the target play_session belongs to it, so a forged broker message can't
    cross-write another user's state.
    """
    from slate.config import settings as app_settings
    from slate.core.play_session.embedding import embed_session
    from slate.infrastructure.db.models import LibraryEntry, PlaySession
    from slate.infrastructure.db.repositories.library import LibraryRepository
    from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
    from slate.infrastructure.db.repositories.play_session_embedding import (
        PlaySessionEmbeddingRepository,
    )
    from slate.infrastructure.db.session import async_session_factory
    from slate.infrastructure.embedding.factory import get_embedding_client
    from slate.infrastructure.llm.factory import get_llm_client

    wrap_up_text = wrap_up_text[:_MAX_WRAP_UP_CHARS]

    with job_context("wrap_up_extraction", play_session_id=play_session_id):
        llm_client = get_llm_client(app_settings)
        logger.info("wrap_up_extraction_started")

        async with async_session_factory() as session:
            play_session = await session.get(PlaySession, play_session_id)
            if play_session is None or play_session.user_id != user_id:
                logger.warning("wrap_up_extraction_owner_mismatch")
                return

            play_session_repo = PlaySessionRepository(session)
            library_repo = LibraryRepository(session)

            extracted = await llm_client.extract_wrap_up_state(
                game_title=game_title,
                wrap_up_text=wrap_up_text,
            )

            state_dict = {
                "location": extracted.location,
                "next_action": extracted.next_action,
                "level": extracted.level,
                "current_quest": extracted.current_quest,
            }
            await play_session_repo.set_extracted_state(play_session_id, state_dict)

            # Embed the wrap-up + extracted state for semantic recap retrieval
            # (Epic 24). Best-effort: a failure here never fails the extraction.
            await embed_session(
                get_embedding_client(app_settings),
                PlaySessionEmbeddingRepository(session),
                play_session_id,
                wrap_up_text,
                state_dict,
            )

            # Update the denormalised next action on the library entry.
            if extracted.next_action and play_session.library_entry_id:
                entry = await session.get(LibraryEntry, play_session.library_entry_id)
                if entry:
                    await library_repo.update(
                        entry, play_session_next_action=extracted.next_action
                    )

            await session.commit()

        logger.info(
            "wrap_up_extraction_completed",
            has_next_action=bool(extracted.next_action),
        )
