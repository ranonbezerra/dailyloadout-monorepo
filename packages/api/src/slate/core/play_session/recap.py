"""Recap helpers: preview, extraction fallback, and generation."""

from __future__ import annotations

import asyncio
from typing import Literal
from uuid import uuid4

import structlog

from slate.config import Settings
from slate.config import settings as _settings
from slate.core.play_session.anti_hallucination import validate_recap
from slate.core.play_session.retrieval import get_grounding_sessions
from slate.core.play_session.routing import resolve_auto_mode
from slate.infrastructure.agent.base import AbstractRecapAgent, DeepRecapRequest
from slate.infrastructure.agent.graph.state import PlaySessionContext
from slate.infrastructure.db.models import LibraryEntry, PlaySession
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.llm.base import AbstractLLMClient
from slate.infrastructure.research.base import ResearchUnavailableError

logger = structlog.get_logger()

RecapMode = Literal["quick", "deep", "auto"]


def _collect_previous_wrap_ups(recent_play_sessions: list[PlaySession]) -> list[dict[str, object]]:
    """Flatten recent ended play_sessions into the wrap_up context the LLM expects."""
    previous_wrap_ups: list[dict[str, object]] = []
    for m in recent_play_sessions:
        wrap_up_data: dict[str, object] = {}
        if m.extracted_state:
            wrap_up_data.update(m.extracted_state)
        if m.wrap_up_text:
            wrap_up_data["raw_text"] = m.wrap_up_text
        if wrap_up_data:
            previous_wrap_ups.append(wrap_up_data)
    return previous_wrap_ups


async def build_play_session_context(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    entry: LibraryEntry,
) -> PlaySessionContext:
    """Assemble the grounding context for a deep recap run.

    Mirrors the context ``generate_recap`` uses: the last 3 wrap_ups plus the most
    recent extracted location/quest/level and the entry's next action.
    """
    await ensure_extractions_complete(play_session_repo, library_repo, llm_client, entry.id)
    recent_play_sessions = await get_grounding_sessions(play_session_repo, entry.id, limit=3)
    previous_wrap_ups = _collect_previous_wrap_ups(recent_play_sessions)

    latest_state: dict[str, object] = {}
    if recent_play_sessions and recent_play_sessions[0].extracted_state:
        latest_state = recent_play_sessions[0].extracted_state

    return PlaySessionContext(
        game_title=entry.game.title,
        location=latest_state.get("location"),  # type: ignore[typeddict-item]
        current_quest=latest_state.get("current_quest"),  # type: ignore[typeddict-item]
        next_action=entry.play_session_next_action,
        level=latest_state.get("level"),  # type: ignore[typeddict-item]
        previous_wrap_ups=previous_wrap_ups,
    )


async def build_preview(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    entry: LibraryEntry,
    position_override: str | None = None,
    *,
    agent: AbstractRecapAgent | None = None,
    settings: Settings | None = None,
    mode: RecapMode = "quick",
    entitled_to_deep: bool = True,
) -> dict[str, object]:
    """Build a recap preview dict for a library entry.

    Shared by ``preview_recap`` and ``submit_retroactive_wrap_up`` (no active-session
    check). ``deep`` (or ``auto`` when the router escalates) with an *agent* runs the
    web-researched path (falling back to quick); otherwise the quick single-shot recap.
    """
    await ensure_extractions_complete(play_session_repo, library_repo, llm_client, entry.id)

    recent_play_sessions = await play_session_repo.get_recent_for_entry(entry.id, limit=1)
    last_context = None
    if recent_play_sessions and recent_play_sessions[0].extracted_state:
        last_context = recent_play_sessions[0].extracted_state

    if mode in ("deep", "auto") and agent is not None:
        recap_text, suspicious = await generate_recap_for_mode(
            play_session_repo,
            library_repo,
            llm_client,
            agent,
            settings or _settings,
            entry,
            mode,
            entitled_to_deep=entitled_to_deep,
        )
    else:
        recap_text, suspicious = await generate_recap(
            play_session_repo,
            library_repo,
            llm_client,
            entry.id,
            entry.game.title,
            entry.play_session_next_action,
            position_override=position_override,
        )

    return {
        "library_entry": entry,
        "recap_text": recap_text or None,
        "last_session_context": last_context,
        "suspicious": suspicious if recap_text else False,
    }


async def ensure_extractions_complete(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    library_entry_id: int,
) -> None:
    """Sync fallback: extract state for play_sessions with wrap_up but no extraction.

    Handles the case where the Taskiq worker failed or hasn't run yet; called before
    recap generation to ensure context is available.
    """
    pending = await play_session_repo.get_pending_extractions(library_entry_id)
    for play_session in pending:
        logger.info(
            "wrap_up_extraction_sync_fallback",
            play_session_id=play_session.id,
        )
        try:
            extracted = await llm_client.extract_wrap_up_state(
                game_title=play_session.library_entry.game.title,
                wrap_up_text=play_session.wrap_up_text,  # type: ignore[arg-type]
            )
            state_dict = {
                "location": extracted.location,
                "next_action": extracted.next_action,
                "level": extracted.level,
                "current_quest": extracted.current_quest,
            }
            await play_session_repo.set_extracted_state(play_session.id, state_dict)
            # NB: embedding happens on the async extraction task (the primary path);
            # this degraded fallback only restores extracted_state. Epic 28 backfills
            # any sessions left unembedded.
            if extracted.next_action:
                await library_repo.update(
                    play_session.library_entry, play_session_next_action=extracted.next_action
                )
        except Exception:
            logger.warning(
                "wrap_up_extraction_sync_fallback_failed",
                play_session_id=play_session.id,
                exc_info=True,
            )


async def generate_recap_for_mode(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractRecapAgent | None,
    settings: Settings,
    entry: LibraryEntry,
    mode: RecapMode,
    *,
    entitled_to_deep: bool = True,
) -> tuple[str, bool]:
    """Produce ``(recap_text, suspicious)`` for *mode*, degrading deep -> quick.

    ``mode="auto"`` runs the adaptive router (Epic 29). The deep path runs under a hard
    deadline; any timeout, outage, error, or empty result falls back to the quick recap.
    """

    async def _quick() -> tuple[str, bool]:
        return await generate_recap(
            play_session_repo,
            library_repo,
            llm_client,
            entry.id,
            entry.game.title,
            entry.play_session_next_action,
        )

    if mode == "auto":
        mode = await resolve_auto_mode(
            play_session_repo,
            library_repo,
            llm_client,
            settings,
            entry,
            agent=agent,
            entitled_to_deep=entitled_to_deep,
        )

    if mode != "deep" or agent is None:
        return await _quick()

    context = await build_play_session_context(play_session_repo, library_repo, llm_client, entry)
    try:
        # A unique thread_id per run (the recap graph is one-shot, not resumable —
        # a stable id would resume/accumulate prior state) + force_refresh so an
        # on-demand deep recap is always freshly researched, never a stale cache hit.
        result = await asyncio.wait_for(
            agent.deep_recap(
                DeepRecapRequest(context=context, thread_id=uuid4().hex, force_refresh=True)
            ),
            timeout=settings.deep_recap_deadline_seconds + 5,
        )
    except (TimeoutError, ResearchUnavailableError):
        logger.warning("deep_recap_fell_back_to_quick", library_entry_id=entry.id)
        return await _quick()
    except Exception:
        logger.warning("deep_recap_failed", library_entry_id=entry.id, exc_info=True)
        return await _quick()

    if result.text:
        logger.info(
            "recap_generated",
            library_entry_id=entry.id,
            mode="deep",
            suspicious=result.suspicious,
            output_chars=len(result.text),
        )
    return (result.text, result.suspicious) if result.text else await _quick()


async def generate_recap(
    play_session_repo: PlaySessionRepository,
    library_repo: LibraryRepository,
    llm_client: AbstractLLMClient,
    library_entry_id: int,
    game_title: str,
    current_next_action: str | None,
    position_override: str | None = None,
) -> tuple[str, bool]:
    """Generate a recap from the last 3 wrap_ups.

    *position_override*, if given, is passed to the LLM as the player's corrected
    position. Returns ``(recap_text, suspicious)`` — *suspicious* is the anti-hallucination
    verdict (low token overlap with the notes), surfaced by the caller as a discreet note.
    """
    await ensure_extractions_complete(
        play_session_repo, library_repo, llm_client, library_entry_id
    )
    recent_play_sessions = await get_grounding_sessions(
        play_session_repo, library_entry_id, limit=3
    )

    previous_wrap_ups = _collect_previous_wrap_ups(recent_play_sessions)

    try:
        recap = await llm_client.generate_recap(
            game_title=game_title,
            previous_wrap_ups=previous_wrap_ups,
            current_next_action=current_next_action,
            position_override=position_override,
        )
    except Exception:
        logger.warning("recap_generation_failed", exc_info=True)
        return "", False

    if not recap:
        return "", False

    # Anti-hallucination check (only meaningful when there are notes to verify against).
    suspicious = False
    if previous_wrap_ups:
        context_parts = [game_title]
        for d in previous_wrap_ups:
            context_parts.extend(str(v) for v in d.values() if v is not None)
        if current_next_action:
            context_parts.append(current_next_action)
        if position_override:
            context_parts.append(position_override)
        context_text = " ".join(context_parts)
        suspicious = validate_recap(recap, context_text).is_suspicious

    logger.info(
        "recap_generated",
        library_entry_id=library_entry_id,
        mode="quick",
        context_count=len(previous_wrap_ups),
        suspicious=suspicious,
        output_chars=len(recap),
    )
    return recap, suspicious
