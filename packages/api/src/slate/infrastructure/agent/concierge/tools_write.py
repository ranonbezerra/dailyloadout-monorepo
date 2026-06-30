"""Write tool functions for the Backlog Concierge (ROADMAP Epic 12).

These turn the Concierge from a recommender into the *conversational operator*
of the play_session pipeline: it can start a play_session, recap it, log an offline
session, and update a game's status — all funnelling through the same shared
orchestrator and guard rails the REST endpoints use.

Like the read tools (``tools.py``) these are framework-free and return
LLM-friendly text, never raising — service-layer ``HTTPException``s are caught
and rendered as a sentence the model can relay. Every function is scoped to a
``user_id`` so the Concierge can only mutate the caller's own data, and the
invariants (one active play_session per user; UUID-existence on every pick) hold here
exactly as they do on the REST surface.
"""

from __future__ import annotations

import structlog
from fastapi import HTTPException

from slate.config import Settings
from slate.core.cache.invalidation import invalidate_user_stats
from slate.core.play_session.recap import RecapMode, generate_recap_for_mode
from slate.core.play_session.start import create_play_session_for_entry
from slate.core.safety.guard import sanitize_and_audit
from slate.infrastructure.agent.base import AbstractRecapAgent
from slate.infrastructure.agent.concierge.base import ConciergeTool
from slate.infrastructure.agent.concierge.tools import _resolve_entry
from slate.infrastructure.agent.concierge.write_schemas import (
    GenerateRecapArgs,
    RetroactiveWrapUpArgs,
    SetStatusArgs,
    StartPlaySessionArgs,
)
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()

# The statuses a player can move a game between (mirrors the library schema).
_VALID_STATUSES = {"backlog", "playing", "paused", "completed", "dropped"}
# Conversational recap tops out at quick — deep research is slow and belongs
# to the deliberate recap flow, not a one-tap chat turn.
_RECAP_CHOICES = {"none", "quick"}


async def start_play_session(
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractRecapAgent | None,
    settings: Settings,
    user_id: int,
    *,
    library_entry_public_id: str,
    recap: str = "none",
) -> str:
    """Start a play_session for one game, optionally with a quick recap."""
    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library, so I can't start it."

    if await play_session_repo.get_active_for_user(user_id) is not None:
        return "There's already an active play_session. Finish or end it before starting another."

    choice = recap.strip().lower() if recap else "none"
    if choice not in _RECAP_CHOICES:
        choice = "none"

    recap_text: str | None = None
    if choice != "none":
        text, _ = await generate_recap_for_mode(
            play_session_repo,
            library_repo,
            llm_client,
            agent,
            settings,
            entry,
            "quick",
        )
        recap_text = text or None

    try:
        await create_play_session_for_entry(
            play_session_repo=play_session_repo,
            library_repo=library_repo,
            user_id=user_id,
            entry=entry,
            recap_text=recap_text,
        )
    except HTTPException:
        return "There's already an active play_session. Finish or end it before starting another."

    started = f"Started a play_session for {entry.game.title}."
    if recap_text:
        return f"{started}\n\nRecap:\n{recap_text}"
    return started


async def generate_recap(
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractRecapAgent | None,
    settings: Settings,
    user_id: int,
    *,
    mode: str = "quick",
) -> str:
    """Generate a recap for the user's active play_session and persist it.

    ``mode`` is accepted for tool-schema compatibility but always clamped to
    ``quick``: the deep-research graph is too expensive to trigger from a single
    chat turn (it would bypass the recap limiter + cost guard).
    """
    _ = mode  # accepted but intentionally ignored — always clamped to quick.
    play_session = await play_session_repo.get_active_for_user(user_id)
    if play_session is None:
        return "There's no active play_session to recap. Start one first."

    # Clamp to 'quick' (mirror start_play_session's _RECAP_CHOICES): one 6/min chat
    # turn must not be able to trigger the full deep-research graph and bypass the
    # recap limiter + cost guard.
    selected: RecapMode = "quick"
    recap_text, _ = await generate_recap_for_mode(
        play_session_repo,
        library_repo,
        llm_client,
        agent,
        settings,
        play_session.library_entry,
        selected,
    )
    if not recap_text:
        return "I couldn't put together a recap right now. Try again in a moment."

    await play_session_repo.set_recap(play_session.id, recap_text)
    return f"Recap for {play_session.library_entry.game.title}:\n{recap_text}"


async def submit_retroactive_wrap_up(
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    user_id: int,
    *,
    library_entry_public_id: str,
    wrap_up_text: str,
) -> str:
    """Log a past, untracked play session as a pre-ended retroactive play_session."""
    wrap_up_text = sanitize_and_audit(wrap_up_text, surface="wrap_up", user_id=user_id)
    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library, so I can't log a session for it."

    extracted_state = None
    try:
        extracted = await llm_client.extract_wrap_up_state(
            game_title=entry.game.title,
            wrap_up_text=wrap_up_text,
        )
        extracted_state = {
            "location": extracted.location,
            "next_action": extracted.next_action,
            "level": extracted.level,
            "current_quest": extracted.current_quest,
        }
        if extracted.next_action:
            await library_repo.update(entry, play_session_next_action=extracted.next_action)
    except Exception:
        logger.warning("concierge_retroactive_extraction_failed", exc_info=True)

    await play_session_repo.create_retroactive(
        user_id=user_id,
        library_entry_id=entry.id,
        wrap_up_text=wrap_up_text,
        extracted_state=extracted_state,
    )
    await invalidate_user_stats(user_id)
    next_action = (extracted_state or {}).get("next_action")
    logged = f"Logged your past session for {entry.game.title}."
    if next_action:
        return f"{logged} Saved next step: {next_action}"
    return logged


async def set_status(
    library_repo: LibraryRepository,
    user_id: int,
    *,
    library_entry_public_id: str,
    status: str,
) -> str:
    """Change a library entry's status (backlog/playing/paused/completed/dropped)."""
    normalised = status.strip().lower()
    if normalised not in _VALID_STATUSES:
        options = ", ".join(sorted(_VALID_STATUSES))
        return f"'{status}' isn't a valid status. Use one of: {options}."

    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library."

    await library_repo.update(entry, status=normalised)
    await invalidate_user_stats(user_id)
    return f"Marked {entry.game.title} as {normalised}."


def build_concierge_write_tools(
    *,
    user_id: int,
    library_repo: LibraryRepository,
    play_session_repo: PlaySessionRepository,
    llm_client: AbstractLLMClient,
    agent: AbstractRecapAgent | None,
    settings: Settings,
) -> list[ConciergeTool]:
    """Build the per-request write tool set, each bound to *user_id* and the repos."""

    async def _start(library_entry_public_id: str, recap: str = "none") -> str:
        return await start_play_session(
            library_repo,
            play_session_repo,
            llm_client,
            agent,
            settings,
            user_id,
            library_entry_public_id=library_entry_public_id,
            recap=recap,
        )

    async def _recap(mode: str = "quick") -> str:
        return await generate_recap(
            library_repo, play_session_repo, llm_client, agent, settings, user_id, mode=mode
        )

    async def _retro(library_entry_public_id: str, wrap_up_text: str) -> str:
        return await submit_retroactive_wrap_up(
            library_repo,
            play_session_repo,
            llm_client,
            user_id,
            library_entry_public_id=library_entry_public_id,
            wrap_up_text=wrap_up_text,
        )

    async def _status(library_entry_public_id: str, status: str) -> str:
        return await set_status(
            library_repo, user_id, library_entry_public_id=library_entry_public_id, status=status
        )

    return [
        ConciergeTool(
            name="start_play_session",
            description="Start a play session (play_session) for one game from the library. Pass "
            "recap='quick' to include a short catch-up recap. Only one play_session can be "
            "active at a time.",
            args_schema=StartPlaySessionArgs,
            coroutine=_start,
        ),
        ConciergeTool(
            name="generate_recap",
            description="Write a catch-up recap for the currently active play_session "
            "and save it. Use after start_play_session, or when the player asks for a "
            "refresher on where they left off.",
            args_schema=GenerateRecapArgs,
            coroutine=_recap,
        ),
        ConciergeTool(
            name="submit_retroactive_wrap_up",
            description="Log a past play session the player did NOT track live (e.g. 'I played "
            "two hours offline'). Records what happened and saves their next step.",
            args_schema=RetroactiveWrapUpArgs,
            coroutine=_retro,
        ),
        ConciergeTool(
            name="set_status",
            description="Change a game's status in the library: backlog, playing, paused, "
            "completed, or dropped.",
            args_schema=SetStatusArgs,
            coroutine=_status,
        ),
    ]
