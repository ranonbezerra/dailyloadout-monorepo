"""Read-only tool functions for the Backlog Concierge.

Thin wrappers over existing repositories/services, returning LLM-friendly text.
Deliberately framework-free (no LangChain import) so the dummy provider and the
unit tests stay model-free; the LangGraph provider wraps these as tool objects.

Every function is scoped to a ``user_id`` — the Concierge can only read the
caller's own data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from dailyloadout.core.sanitization import wrap_user_data
from dailyloadout.core.stats.service import StatsService
from dailyloadout.infrastructure.agent.concierge.base import ConciergeTool
from dailyloadout.infrastructure.db.models import LibraryEntry
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

# Status weights for the session-fit heuristic (higher = readier to resume).
_STATUS_FIT = {"playing": 40, "paused": 30, "backlog": 15, "completed": 0, "dropped": 0}


def _entry_line(entry: LibraryEntry) -> str:
    """One-line summary of a library entry, including its id for recommendations.

    Game titles and saved next-actions are user/shared content, so they are
    fenced in a <user_data> block (the concierge SYSTEM prompt tells the model to
    treat that as DATA, never instructions). Platform, status, and id are trusted
    system values left unwrapped so the model can still use them for filtering
    and recommendations.
    """
    title = wrap_user_data(entry.game.title)
    parts = [f"{title} — {entry.platform.label} [{entry.status}]"]
    if entry.mission_next_action:
        parts.append(f"next: {wrap_user_data(entry.mission_next_action)}")
    parts.append(f"(id: {entry.public_id})")
    return "- " + " | ".join(parts)


async def search_library(
    library_repo: LibraryRepository,
    user_id: int,
    *,
    status: str | None = None,
    platform: str | None = None,
    genre: str | None = None,
    limit: int = 20,
) -> str:
    """List the user's games, optionally filtered by status, platform, or genre."""
    capped = max(1, min(limit, 50))
    entries = await library_repo.list_for_user(user_id, status=status, limit=capped)
    if platform:
        needle = platform.lower()
        entries = [
            e
            for e in entries
            if needle in e.platform.label.lower() or needle in e.platform.slug.lower()
        ]
    if genre:
        needle = genre.lower()
        entries = [e for e in entries if any(needle in g.lower() for g in (e.game.genres or []))]

    if not entries:
        return "No games match those filters in the library."
    return "\n".join(_entry_line(e) for e in entries)


async def get_mission_history(
    library_repo: LibraryRepository,
    mission_repo: MissionRepository,
    user_id: int,
    *,
    library_entry_public_id: str,
    limit: int = 3,
) -> str:
    """Recent session notes for one game: last debriefs and where the player left off."""
    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library."

    missions = await mission_repo.get_recent_for_entry(entry.id, limit=max(1, min(limit, 5)))
    lines = [f"Game: {wrap_user_data(entry.game.title)}"]
    if entry.mission_next_action:
        lines.append(f"Saved next action: {wrap_user_data(entry.mission_next_action)}")
    if not missions:
        lines.append("No recorded sessions yet.")
        return "\n".join(lines)

    for m in missions:
        state = m.extracted_state or {}
        bits = [str(v) for v in (state.get("location"), state.get("current_quest")) if v]
        summary = "; ".join(bits) if bits else (m.debrief_text or "").strip()[:160]
        # Mission state and debrief text are the player's own words — fence them.
        lines.append(f"- {wrap_user_data(summary or 'session recorded')}")
    return "\n".join(lines)


async def get_play_stats(
    stats_service: StatsService,
    user_id: int,
    user_created_at: datetime,
) -> str:
    """High-level play stats: totals, recent activity, and top genres/platforms."""
    overview = await stats_service.get_overview(user_id, user_created_at)
    genres = await stats_service.get_genre_stats(user_id)
    platforms = await stats_service.get_platform_stats(user_id)

    lines = [
        f"Total games: {overview.total_games}",
        f"Missions in the last 30 days: {overview.missions_last_30d}",
    ]
    if overview.avg_mission_duration_minutes is not None:
        lines.append(f"Average session: {round(overview.avg_mission_duration_minutes)} min")
    top_genres = sorted(genres.genres, key=lambda g: g.total_minutes, reverse=True)[:3]
    if top_genres:
        lines.append("Most-played genres: " + ", ".join(g.genre for g in top_genres))
    top_platforms = sorted(platforms.platforms, key=lambda p: p.total_minutes, reverse=True)[:3]
    if top_platforms:
        labels = ", ".join(p.platform_label for p in top_platforms)
        lines.append(f"Most-played platforms: {labels}")
    return "\n".join(lines)


async def estimate_session_fit(
    library_repo: LibraryRepository,
    user_id: int,
    *,
    library_entry_public_id: str,
    minutes: int,
) -> str:
    """Deterministic 0-100 fit score for playing one game in *minutes* right now."""
    entry = await _resolve_entry(library_repo, user_id, library_entry_public_id)
    if entry is None:
        return "That game is not in the library."

    score = _STATUS_FIT.get(entry.status, 10)
    reasons: list[str] = [f"status is '{entry.status}'"]

    if entry.mission_next_action:
        score += 20
        reasons.append("has a saved next step (quick to resume)")

    if entry.last_played_at is not None:
        days = (datetime.now(UTC) - entry.last_played_at).days
        if days <= 7:
            score += 15
            reasons.append("played within the last week")
        elif days >= 60:
            score -= 10
            reasons.append("not touched in a while (more re-orientation needed)")

    # Short sessions favour games you can drop into; long sessions suit anything.
    if minutes < 20 and not entry.mission_next_action:
        score -= 15
        reasons.append("short session with no clear resume point")
    elif minutes >= 60:
        score += 5
        reasons.append("plenty of time this session")

    score = max(0, min(100, score))
    title = wrap_user_data(entry.game.title)
    return f"Fit score for {title} in {minutes} min: {score}/100 ({'; '.join(reasons)})."


async def validate_recommendation(
    library_repo: LibraryRepository,
    user_id: int,
    public_id: str,
) -> bool:
    """True if *public_id* is a real library entry owned by *user_id* (Epic 7 guard)."""
    try:
        parsed = UUID(public_id)
    except (ValueError, TypeError):
        return False
    return await library_repo.get_by_public_id(parsed, user_id) is not None


async def _resolve_entry(
    library_repo: LibraryRepository,
    user_id: int,
    public_id: str,
) -> LibraryEntry | None:
    try:
        parsed = UUID(public_id)
    except (ValueError, TypeError):
        return None
    return await library_repo.get_by_public_id(parsed, user_id)


# -- LLM-facing argument schemas ------------------------------------------------


class SearchLibraryArgs(BaseModel):
    status: str | None = Field(
        None, description="Filter by status: backlog, playing, paused, completed, dropped."
    )
    platform: str | None = Field(None, description="Filter by platform name, e.g. 'Switch'.")
    genre: str | None = Field(None, description="Filter by genre, e.g. 'Metroidvania'.")
    limit: int = Field(20, description="Max games to return (1-50).")


class MissionHistoryArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    limit: int = Field(3, description="How many recent sessions to summarise (1-5).")


class PlayStatsArgs(BaseModel):
    """No arguments — returns the user's overall play stats."""


class SessionFitArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    minutes: int = Field(..., description="Minutes available to play right now.")


def build_concierge_tools(
    *,
    user_id: int,
    user_created_at: datetime,
    library_repo: LibraryRepository,
    mission_repo: MissionRepository,
    stats_service: StatsService,
) -> list[ConciergeTool]:
    """Build the per-request tool set, each bound to *user_id* and the repos."""

    async def _search(
        status: str | None = None,
        platform: str | None = None,
        genre: str | None = None,
        limit: int = 20,
    ) -> str:
        return await search_library(
            library_repo, user_id, status=status, platform=platform, genre=genre, limit=limit
        )

    async def _history(library_entry_public_id: str, limit: int = 3) -> str:
        return await get_mission_history(
            library_repo,
            mission_repo,
            user_id,
            library_entry_public_id=library_entry_public_id,
            limit=limit,
        )

    async def _stats() -> str:
        return await get_play_stats(stats_service, user_id, user_created_at)

    async def _fit(library_entry_public_id: str, minutes: int) -> str:
        return await estimate_session_fit(
            library_repo, user_id, library_entry_public_id=library_entry_public_id, minutes=minutes
        )

    return [
        ConciergeTool(
            name="search_library",
            description="List the user's games, optionally filtered by status, platform, or "
            "genre. Returns each game with its id — use that id with the other tools and "
            "when recommending a game.",
            args_schema=SearchLibraryArgs,
            coroutine=_search,
        ),
        ConciergeTool(
            name="get_mission_history",
            description="Recent session notes for one game: where the player left off and their "
            "saved next action.",
            args_schema=MissionHistoryArgs,
            coroutine=_history,
        ),
        ConciergeTool(
            name="get_play_stats",
            description="The user's overall play stats: totals, recent activity, top genres and "
            "platforms.",
            args_schema=PlayStatsArgs,
            coroutine=_stats,
        ),
        ConciergeTool(
            name="estimate_session_fit",
            description="A 0-100 score for how well one game fits the minutes the player has now.",
            args_schema=SessionFitArgs,
            coroutine=_fit,
        ),
    ]
