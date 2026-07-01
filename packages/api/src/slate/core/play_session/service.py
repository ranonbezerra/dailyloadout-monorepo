"""PlaySession service: lifecycle management, recap, and wrap_up orchestration."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status

from slate.config import Settings
from slate.config import settings as default_settings
from slate.core.cache.invalidation import invalidate_user_stats
from slate.core.play_session.recap import (
    RecapMode,
    build_preview,
    generate_recap,
    generate_recap_for_mode,
)
from slate.core.play_session.start import create_play_session_for_entry
from slate.core.safety.guard import sanitize_and_audit
from slate.infrastructure.agent.base import AbstractRecapAgent
from slate.infrastructure.db.models import LibraryEntry, PlaySession
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()


class PlaySessionService:
    """Orchestrates play_session lifecycle: start, recap, wrap_up, and end."""

    def __init__(
        self,
        play_session_repo: PlaySessionRepository,
        library_repo: LibraryRepository,
        llm_client: AbstractLLMClient,
        agent: AbstractRecapAgent | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._play_session_repo = play_session_repo
        self._library_repo = library_repo
        self._llm_client = llm_client
        self._agent = agent
        self._settings = settings or default_settings

    # -- Start play_session ---------------------------------------------------

    async def _load_startable_entry(
        self, user_id: int, library_entry_public_id: UUID
    ) -> LibraryEntry:
        """Load an entry for start/preview; raise 404 if missing, 409 if busy."""
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Library entry not found"
            )
        if await self._play_session_repo.get_active_for_user(user_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active play_session. End it first.",
            )
        return entry

    async def start_play_session(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        recap_text: str | None = None,
        mode: RecapMode = "quick",
        skip_recap: bool = False,
    ) -> PlaySession:
        """Start a new play_session for a library entry.

        If *recap_text* is provided, it's used as-is. If *skip_recap* is
        set, the play_session starts with no recap at all (the "just play" path).
        Otherwise a recap is generated in *mode* (quick or deep).
        """
        entry = await self._load_startable_entry(user_id, library_entry_public_id)

        if recap_text is None and not skip_recap:
            recap_text, _ = await generate_recap_for_mode(
                self._play_session_repo,
                self._library_repo,
                self._llm_client,
                self._agent,
                self._settings,
                entry,
                mode,
            )

        return await create_play_session_for_entry(
            play_session_repo=self._play_session_repo,
            library_repo=self._library_repo,
            user_id=user_id,
            entry=entry,
            recap_text=recap_text,
        )

    # -- Preview recap ------------------------------------------------

    async def preview_recap(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        position_override: str | None = None,
        mode: RecapMode = "quick",
    ) -> dict[str, object]:
        """Preview a recap (quick or deep) without creating a play_session."""
        entry = await self._load_startable_entry(user_id, library_entry_public_id)
        return await build_preview(
            self._play_session_repo,
            self._library_repo,
            self._llm_client,
            entry,
            position_override=position_override,
            agent=self._agent,
            settings=self._settings,
            mode=mode,
        )

    # -- Retroactive wrap_up ---------------------------------------------

    async def submit_retroactive_wrap_up(
        self,
        user_id: int,
        library_entry_public_id: UUID,
        wrap_up_text: str,
    ) -> dict[str, object]:
        """Record a wrap_up for a play session that wasn't tracked.

        Creates a pre-ended play_session with ``play_session_type="retroactive"``,
        runs LLM extraction synchronously, and returns a fresh recap
        preview.
        """
        wrap_up_text = sanitize_and_audit(wrap_up_text, surface="wrap_up", user_id=user_id)
        entry = await self._library_repo.get_by_public_id(library_entry_public_id, user_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Library entry not found"
            )

        extracted_state = None
        try:
            extracted = await self._llm_client.extract_wrap_up_state(
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
                await self._library_repo.update(
                    entry, play_session_next_action=extracted.next_action
                )
        except Exception:
            logger.warning("retroactive_extraction_failed", exc_info=True)

        await self._play_session_repo.create_retroactive(
            user_id=user_id,
            library_entry_id=entry.id,
            wrap_up_text=wrap_up_text,
            extracted_state=extracted_state,
        )
        await invalidate_user_stats(user_id)

        return await build_preview(
            self._play_session_repo,
            self._library_repo,
            self._llm_client,
            entry,
        )

    # -- Query -----------------------------------------------------------

    async def get_play_session(self, user_id: int, play_session_public_id: UUID) -> PlaySession:
        """Return a play_session scoped to *user_id*, or raise 404."""
        play_session = await self._play_session_repo.get_by_public_id(
            play_session_public_id, user_id=user_id
        )
        if play_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="PlaySession not found"
            )
        return play_session

    async def get_active_play_session(self, user_id: int) -> PlaySession | None:
        """Return the user's active play_session, or None."""
        return await self._play_session_repo.get_active_for_user(user_id)

    async def list_play_sessions(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PlaySession], int]:
        """Return the user's play_sessions along with the total count."""
        play_sessions = await self._play_session_repo.list_for_user(
            user_id, limit=limit, offset=offset
        )
        total = await self._play_session_repo.count_for_user(user_id)
        return play_sessions, total

    async def submit_wrap_up(
        self,
        user_id: int,
        play_session_public_id: UUID,
        wrap_up_text: str,
    ) -> PlaySession:
        """Submit a wrap_up for a play_session and end it.

        Saves the wrap_up text, ends the play_session immediately, and dispatches
        the LLM extraction to a background Taskiq worker.
        """
        wrap_up_text = sanitize_and_audit(wrap_up_text, surface="wrap_up", user_id=user_id)
        play_session = await self.get_play_session(user_id, play_session_public_id)

        # End first via the atomic claim; a concurrent end/wrap-up loses → 409.
        if not await self._play_session_repo.end_play_session(
            play_session.id, ended_via="wrap_up_completed"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="PlaySession is already ended"
            )
        await self._play_session_repo.set_wrap_up(play_session.id, wrap_up_text)
        await invalidate_user_stats(user_id)

        game_title = play_session.library_entry.game.title
        try:
            from slate.infrastructure.tasks.wrap_up_extraction import extract_wrap_up_state_task

            await extract_wrap_up_state_task.kiq(
                play_session.id, game_title, wrap_up_text, user_id
            )
            logger.info(
                "wrap_up_extraction_dispatched",
                user_id=user_id,
                play_session_id=play_session.id,
            )
        except Exception:
            logger.warning(
                "wrap_up_extraction_dispatch_failed",
                play_session_id=play_session.id,
                exc_info=True,
            )

        return await self.get_play_session(user_id, play_session_public_id)

    async def end_play_session(
        self,
        user_id: int,
        play_session_public_id: UUID,
        ended_via: str = "paused_app",
    ) -> PlaySession:
        """End a play_session without a wrap_up (atomic claim; already-ended → 409)."""
        play_session = await self.get_play_session(user_id, play_session_public_id)
        if not await self._play_session_repo.end_play_session(
            play_session.id, ended_via=ended_via
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="PlaySession is already ended"
            )
        await invalidate_user_stats(user_id)
        return await self.get_play_session(user_id, play_session_public_id)

    async def regenerate_recap(
        self,
        user_id: int,
        play_session_public_id: UUID,
        position_override: str | None = None,
    ) -> PlaySession:
        """Regenerate the recap for an active play_session.

        If *position_override* is provided, it replaces the stored session
        context for suggestion generation.
        """
        play_session = await self.get_play_session(user_id, play_session_public_id)
        if play_session.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot regenerate recap for an ended play_session",
            )

        entry = play_session.library_entry
        recap_text, _ = await generate_recap(
            self._play_session_repo,
            self._library_repo,
            self._llm_client,
            entry.id,
            entry.game.title,
            entry.play_session_next_action,
            position_override=position_override,
        )
        if recap_text:
            await self._play_session_repo.set_recap(play_session.id, recap_text)

        return await self.get_play_session(user_id, play_session_public_id)
