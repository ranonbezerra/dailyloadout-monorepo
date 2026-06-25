"""Backlog Concierge service: runs the agent, then enforces the UUID guard.

Two paths share the same guard. ``reply`` is the buffered path — run to
completion, validate the pick (reroll once, else degrade). ``reply_stream``
(ROADMAP Epic 16) is the live path — prose tokens stream as they arrive while
the trailing ``RECOMMEND`` marker is withheld and validated before it surfaces,
so an invalid pick is never shown as a real recommendation mid-stream.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from dailyloadout.config import Settings
from dailyloadout.config import settings as default_settings
from dailyloadout.core.stats.service import StatsService
from dailyloadout.infrastructure.agent.base import AbstractBriefingAgent
from dailyloadout.infrastructure.agent.concierge.base import (
    AbstractConciergeAgent,
    ConciergeRequest,
    ConciergeTool,
)
from dailyloadout.infrastructure.agent.concierge.streaming import (
    RecommendationGate,
    TokenEvent,
    ToolEvent,
    split_recommendation,
)
from dailyloadout.infrastructure.agent.concierge.tools import (
    _resolve_entry,
    build_concierge_tools,
    validate_recommendation,
)
from dailyloadout.infrastructure.agent.concierge.tools_write import build_concierge_write_tools
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

SYSTEM_PROMPT = (
    "You are the Backlog Concierge for DailyLoadout — a friendly, concise gaming "
    "companion that helps the player decide what to play from THEIR OWN library.\n"
    "\n"
    "Rules:\n"
    "- Always ground answers in the user's real data. Use the tools — never invent "
    "games, stats, or progress.\n"
    "- Use your tools immediately and SILENTLY. NEVER ask the user for permission to "
    "look something up, and never say things like 'Can I check your library?' or "
    "'Let me check' — just call the tool and answer with what you find.\n"
    "- ALWAYS start by calling search_library with NO filters to see their whole "
    "library. Only pass a status/platform/genre filter when the user explicitly names "
    "one. Never tell the user they have nothing to play unless an unfiltered "
    "search_library truly returned no games.\n"
    "- Be ECONOMICAL with tools — call the fewest needed, since each call is slow. For "
    "a 'what should I play' question, search_library is usually enough; add "
    "estimate_session_fit only when they mention how much time they have, and "
    "get_mission_history only to recall where they left off in a specific game. Call "
    "get_play_stats ONLY when the user explicitly asks about their stats, habits, or "
    "history — never just to pick a game.\n"
    "- Keep replies short and conversational — a sentence or two, not an essay.\n"
    "- When you recommend ONE specific game, end your reply with a line in exactly this "
    "form, using the id from search_library:\n"
    "  RECOMMEND: <library_entry id>\n"
    "  Only emit that line for a game that appeared in search_library results.\n"
    "- If nothing fits, say so plainly and ask a clarifying question instead of guessing.\n"
    "\n"
    "You can also ACT on the player's library, but only when they clearly ask you to — never "
    "start, brief, or change anything just because you recommended it:\n"
    "- start_mission: begin a play session for a game (optionally briefing='quick'). Only one "
    "mission can be active at a time.\n"
    "- generate_briefing: write a catch-up briefing for the active mission.\n"
    "- submit_retroactive_debrief: log a past session the player didn't track live.\n"
    "- set_status: move a game between backlog/playing/paused/completed/dropped.\n"
    "After acting, confirm what you did in one short sentence."
)

# Sent on a reroll when the agent recommended a game that isn't in the library.
_CORRECTION_MESSAGE = (
    "That recommendation wasn't a game in my library. Call search_library again and "
    "only recommend a game that actually appears in the results."
)

_DEGRADE_NOTE = (
    "I'm not certain that one's in your library — want me to take another look "
    "or narrow it down by platform or mood?"
)


class ConciergeService:
    def __init__(
        self,
        *,
        library_repo: LibraryRepository,
        mission_repo: MissionRepository,
        stats_service: StatsService,
        agent: AbstractConciergeAgent,
        llm_client: AbstractLLMClient,
        briefing_agent: AbstractBriefingAgent | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._library_repo = library_repo
        self._mission_repo = mission_repo
        self._stats_service = stats_service
        self._agent = agent
        self._llm_client = llm_client
        self._briefing_agent = briefing_agent
        self._settings = settings or default_settings

    def _build_tools(self, user_id: int, user_created_at: datetime) -> list[ConciergeTool]:
        tools = build_concierge_tools(
            user_id=user_id,
            user_created_at=user_created_at,
            library_repo=self._library_repo,
            mission_repo=self._mission_repo,
            stats_service=self._stats_service,
        )
        if self._settings.concierge_write_tools_enabled:
            tools += build_concierge_write_tools(
                user_id=user_id,
                library_repo=self._library_repo,
                mission_repo=self._mission_repo,
                llm_client=self._llm_client,
                agent=self._briefing_agent,
                settings=self._settings,
            )
        return tools

    async def reply(
        self,
        *,
        user_id: int,
        user_created_at: datetime,
        thread_id: str,
        message: str,
    ) -> str:
        """Run one guarded chat turn and return the user-facing answer text.

        Buffered path (non-streaming): runs to completion, validates the pick
        with a single reroll, else degrades. ``reply_stream`` is the live path.
        """
        tools = self._build_tools(user_id, user_created_at)

        reply = await self._agent.respond(
            ConciergeRequest(
                thread_id=thread_id, message=message, system=SYSTEM_PROMPT, tools=tools
            )
        )
        prose, rec_id = split_recommendation(reply.text)

        if rec_id is not None and not await self._is_valid(user_id, rec_id):
            # Reroll once with a correction (Epic 7 guard pattern, MAX_REROLLS=1).
            reply = await self._agent.respond(
                ConciergeRequest(
                    thread_id=thread_id,
                    message=_CORRECTION_MESSAGE,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                )
            )
            prose, rec_id = split_recommendation(reply.text)
            if rec_id is not None and not await self._is_valid(user_id, rec_id):
                # Degrade rather than surface a game that isn't in the library.
                return f"{prose}\n\n{_DEGRADE_NOTE}".strip() if prose else _DEGRADE_NOTE

        return prose

    async def reply_stream(
        self,
        *,
        user_id: int,
        user_created_at: datetime,
        thread_id: str,
        message: str,
    ) -> AsyncIterator[dict[str, object]]:
        """Stream one guarded turn as typed event payloads (ROADMAP Epic 16).

        Prose tokens stream live; the trailing ``RECOMMEND`` marker is withheld
        by the gate and only surfaced — as a validated ``recommendation`` event
        or a ``degrade`` event — once the pick is checked against the library.
        Streaming can't un-send prose, so the buffered path's reroll becomes a
        degrade-in-stream; the guard guarantee (no invalid pick shown as valid)
        is preserved.
        """
        tools = self._build_tools(user_id, user_created_at)
        gate = RecommendationGate()

        async for event in self._agent.astream(
            ConciergeRequest(
                thread_id=thread_id, message=message, system=SYSTEM_PROMPT, tools=tools
            )
        ):
            if isinstance(event, ToolEvent):
                yield {"tool": event.name, "phase": event.phase}
            elif isinstance(event, TokenEvent):
                safe = gate.feed(event.text)
                if safe:
                    yield {"token": safe}

        tail, rec_id = gate.finish()
        if tail:
            yield {"token": tail}

        if rec_id is not None:
            entry = await _resolve_entry(self._library_repo, user_id, rec_id)
            if entry is not None:
                yield {"recommendation": {"id": rec_id, "title": entry.game.title}}
            else:
                yield {"degrade": _DEGRADE_NOTE}

    async def _is_valid(self, user_id: int, public_id: str) -> bool:
        return await validate_recommendation(self._library_repo, user_id, public_id)
