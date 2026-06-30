"""Pick service: daily game suggestion with UUID validation."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from slate.core.pick.logging import log_pick_actioned, log_pick_created, log_pick_requested
from slate.core.pick.selection import select_one
from slate.core.play_session.start import create_play_session_for_entry
from slate.infrastructure.db.models import Pick
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.pick import PickRepository
from slate.infrastructure.db.repositories.play_session import (
    PlaySessionRepository,
)
from slate.infrastructure.llm.base import AbstractLLMClient

_ACTIVE_PLAY_SESSION_DETAIL = "You already have an active play session. End it first."


class PickService:
    """Orchestrates daily Pick: question → LLM selection → accept/reject."""

    def __init__(
        self,
        pick_repo: PickRepository,
        library_repo: LibraryRepository,
        play_session_repo: PlaySessionRepository,
        llm_client: AbstractLLMClient,
    ) -> None:
        self._pick_repo = pick_repo
        self._library_repo = library_repo
        self._play_session_repo = play_session_repo
        self._llm_client = llm_client

    async def create_pick(
        self,
        user_id: int,
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
        cooldown_hours: int = 12,
    ) -> Pick:
        """Create a single Pick suggestion."""
        results = await self.create_picks(
            user_id=user_id,
            mood=mood,
            available_minutes=available_minutes,
            mental_energy=mental_energy,
            context=context,
            count=1,
            cooldown_hours=cooldown_hours,
        )
        return results[0]

    async def create_picks(
        self,
        user_id: int,
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
        count: int = 1,
        cooldown_hours: int = 12,
    ) -> list[Pick]:
        """Create up to *count* Pick suggestions with distinct games."""
        entries = await self._library_repo.list_eligible_for_pick(
            user_id, cooldown_hours=cooldown_hours
        )
        log_pick_requested(
            user_id=user_id,
            eligible_count=len(entries),
            requested_count=count,
            mood=mood,
            available_minutes=available_minutes,
            mental_energy=mental_energy,
            has_context=context is not None,
        )

        if not entries:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No eligible games in your library. "
                "Add games first or wait for the cooldown.",
            )

        # Build candidate list for the LLM.
        entry_by_pid: dict[str, object] = {}
        all_candidates: list[dict[str, object]] = []
        for entry in entries:
            pid = str(entry.public_id)
            entry_by_pid[pid] = entry
            all_candidates.append(
                {
                    "public_id": pid,
                    "game_title": entry.game.title,
                    "platform": entry.platform.label,
                    "status": entry.status,
                    "last_played_at": (
                        str(entry.last_played_at) if entry.last_played_at else None
                    ),
                    "play_session_next_action": entry.play_session_next_action,
                    "genres": entry.game.genres or [],
                    "summary": entry.game.summary,
                }
            )

        # Cap count to available candidates.
        count = min(count, len(all_candidates))

        results: list[Pick] = []
        picked_ids: set[str] = set()
        remaining = list(all_candidates)

        for _ in range(count):
            if not remaining:
                break

            valid_ids = {str(c["public_id"]) for c in remaining}
            selected = await select_one(
                self._llm_client,
                remaining,
                valid_ids,
                mood,
                available_minutes,
                mental_energy,
                context,
            )

            if selected is None:
                break

            picked_id, reasoning = selected
            picked_ids.add(picked_id)

            # Find the matching entry.
            from slate.infrastructure.db.models import LibraryEntry

            chosen_entry: LibraryEntry = entry_by_pid[picked_id]  # type: ignore[assignment]

            pick = await self._pick_repo.create(
                user_id=user_id,
                library_entry_id=chosen_entry.id,
                mood=mood,
                available_minutes=available_minutes,
                mental_energy=mental_energy,
                reasoning=reasoning,
                context=context,
            )
            pick.library_entry = chosen_entry
            results.append(pick)
            log_pick_created(user_id=user_id, pick=pick)

            # Remove picked entry from remaining candidates.
            remaining = [c for c in remaining if str(c["public_id"]) != picked_id]

        if not results:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Could not pick a valid game. Please try again.",
            )

        return results

    async def create_and_start(
        self,
        user_id: int,
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
        recap_text: str | None = None,
        cooldown_hours: int = 12,
    ) -> Pick:
        """AI-pick one game and start a play_session for it in a single step.

        The DECIDE=AI entrance to the unified pipeline (ROADMAP Epic 12):
        records the Pick decision, then accepts it through the shared
        orchestrator (optionally with a pre-generated *recap_text*).
        """
        # Fail fast before spending an LLM selection if a play_session is already active.
        if await self._play_session_repo.get_active_for_user(user_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_ACTIVE_PLAY_SESSION_DETAIL,
            )
        pick = await self.create_pick(
            user_id, mood, available_minutes, mental_energy, context, cooldown_hours
        )
        return await self.accept_pick(user_id, pick.public_id, recap_text=recap_text)

    async def accept_pick(
        self,
        user_id: int,
        pick_public_id: UUID,
        recap_text: str | None = None,
    ) -> Pick:
        """Accept a Pick and start a play_session via the shared orchestrator
        (ROADMAP Epic 12), optionally with a pre-generated *recap_text*."""
        pick = await self._pick_repo.get_by_public_id(pick_public_id, user_id=user_id)
        if pick is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pick not found",
            )

        if pick.action is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Pick already {pick.action}",
            )

        entry = pick.library_entry
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="The suggested game is no longer in your library.",
            )

        # Early active-play_session check for a clean 409 (orchestrator maps the DB
        # constraint as a backstop).
        if await self._play_session_repo.get_active_for_user(user_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_ACTIVE_PLAY_SESSION_DETAIL,
            )

        play_session = await create_play_session_for_entry(
            play_session_repo=self._play_session_repo,
            library_repo=self._library_repo,
            user_id=user_id,
            entry=entry,
            recap_text=recap_text,
        )

        await self._pick_repo.set_action(pick.id, "accepted")
        await self._pick_repo.set_play_session(pick.id, play_session.id)
        log_pick_actioned(user_id=user_id, pick=pick, action="accepted")

        return await self._get_pick(user_id, pick_public_id)

    async def reject_pick(
        self,
        user_id: int,
        pick_public_id: UUID,
    ) -> Pick:
        """Reject a Pick suggestion.

        Raises:
            HTTPException 404: Pick not found.
            HTTPException 409: Pick already actioned.
        """
        pick = await self._pick_repo.get_by_public_id(pick_public_id, user_id=user_id)
        if pick is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pick not found",
            )

        if pick.action is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Pick already {pick.action}",
            )

        await self._pick_repo.set_action(pick.id, "rejected")
        log_pick_actioned(user_id=user_id, pick=pick, action="rejected")

        # Re-fetch for response.
        return await self._get_pick(user_id, pick_public_id)

    async def get_latest_pending(self, user_id: int) -> Pick | None:
        """Return the latest pending Pick, or None."""
        return await self._pick_repo.get_pending_for_user(user_id)

    async def list_picks(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Pick], int]:
        """Return the user's picks along with the total count."""
        picks = await self._pick_repo.list_for_user(user_id, limit=limit, offset=offset)
        total = await self._pick_repo.count_for_user(user_id)
        return picks, total

    async def _get_pick(self, user_id: int, pick_public_id: UUID) -> Pick:
        """Fetch a pick or raise 404."""
        pick = await self._pick_repo.get_by_public_id(pick_public_id, user_id=user_id)
        if pick is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pick not found",
            )
        return pick
