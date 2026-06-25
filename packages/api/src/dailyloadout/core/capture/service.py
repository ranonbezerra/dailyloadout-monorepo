"""Capture service: submission, candidate management, and library integration."""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException, status

from dailyloadout.infrastructure.db.models import Capture, CaptureCandidate, Game, LibraryEntry
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.platform import PlatformRepository


def _slugify(title: str) -> str:
    """Convert a game title into a URL-friendly slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")


class CaptureService:
    """Orchestrates capture submission, candidate review, and library commits."""

    def __init__(
        self,
        capture_repo: CaptureRepository,
        candidate_repo: CaptureCandidateRepository,
        game_repo: GameRepository,
        library_repo: LibraryRepository,
        platform_repo: PlatformRepository,
    ) -> None:
        self._capture_repo = capture_repo
        self._candidate_repo = candidate_repo
        self._game_repo = game_repo
        self._library_repo = library_repo
        self._platform_repo = platform_repo

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    async def submit_text(self, user_id: int, raw_text: str, input_type: str = "text") -> Capture:
        """Create a new capture with status ``queued``."""
        return await self._capture_repo.create(
            user_id=user_id,
            input_type=input_type,
            raw_text=raw_text,
        )

    async def submit_photo(self, user_id: int, image_path: str) -> Capture:
        """Create a capture from a photo."""
        return await self._capture_repo.create(
            user_id=user_id,
            input_type="photo",
            image_path=image_path,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_capture(self, user_id: int, capture_public_id: UUID) -> Capture:
        """Return a capture scoped to *user_id*, or raise 404."""
        capture = await self._capture_repo.get_by_public_id(capture_public_id, user_id=user_id)
        if capture is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capture not found",
            )
        return capture

    async def list_captures(
        self,
        user_id: int,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Capture], int]:
        """Return the user's captures along with the total count."""
        captures = await self._capture_repo.list_for_user(
            user_id, status=status_filter, limit=limit, offset=offset
        )
        total = await self._capture_repo.count_for_user(user_id, status=status_filter)
        return captures, total

    # ------------------------------------------------------------------
    # Candidate actions
    # ------------------------------------------------------------------

    async def confirm_candidate(
        self,
        user_id: int,
        capture_public_id: UUID,
        candidate_public_id: UUID,
        platform_id: int,
        library_status: str = "backlog",
    ) -> LibraryEntry:
        """Confirm a candidate: create a library entry and mark it confirmed.

        Raises:
            HTTPException: If the capture, candidate, or platform is not found,
                or the candidate is not in ``pending`` status.
        """
        capture = await self.get_capture(user_id, capture_public_id)

        candidate = await self._candidate_repo.get_by_public_id(candidate_public_id)
        if candidate is None or candidate.capture_id != capture.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found",
            )
        if candidate.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate already {candidate.status}",
            )

        platform = await self._platform_repo.get_by_id(platform_id)
        if platform is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform not found",
            )

        game = await self._get_or_create_game(candidate)

        # Check for duplicate library entry.
        if await self._library_repo.exists(user_id, game.id, platform_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Library entry already exists for this game and platform",
            )

        entry = await self._library_repo.create(
            user_id=user_id,
            game_id=game.id,
            platform_id=platform_id,
            status=library_status,
        )
        entry.game = game
        entry.platform = platform

        # Mark candidate as confirmed.
        await self._candidate_repo.update_status(
            candidate.id, "confirmed", matched_game_id=game.id
        )
        await self._resolve_capture_status(capture.id)

        return entry

    async def _get_or_create_game(self, candidate: CaptureCandidate) -> Game:
        """Resolve a candidate to a ``Game`` row, creating it if needed."""
        if candidate.igdb_id is not None:
            game = await self._game_repo.get_by_igdb_id(candidate.igdb_id)
            if game is not None:
                return game

        title = candidate.igdb_title or candidate.title
        slug = _slugify(title)
        existing = await self._game_repo.get_by_slug(slug)
        if existing is not None:
            return existing

        return await self._game_repo.create(
            slug=slug,
            title=title,
            metadata_source="igdb" if candidate.igdb_id else "capture",
            igdb_id=candidate.igdb_id,
            summary=candidate.igdb_summary,
            cover_url=candidate.igdb_cover_url,
            first_release_date=candidate.igdb_first_release_date,
            genres=candidate.igdb_genres,
        )

    async def bulk_confirm_candidates(
        self,
        user_id: int,
        capture_public_id: UUID,
        confirm_public_ids: list[UUID],
        platform_id: int,
        library_status: str = "backlog",
        title_overrides: dict[UUID, str] | None = None,
    ) -> tuple[int, int]:
        """Confirm the listed candidates and reject the rest, in one call.

        Returns ``(confirmed, rejected)`` counts. Duplicate library entries are
        treated as already-imported (counted as confirmed), not an error, so a
        bulk import of 50-100 titles never aborts midway.
        """
        capture = await self.get_capture(user_id, capture_public_id)
        platform = await self._platform_repo.get_by_id(platform_id)
        if platform is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform not found",
            )

        confirm_set = set(confirm_public_ids)
        overrides = title_overrides or {}
        candidates = await self._candidate_repo.get_all_for_capture(capture.id)
        confirmed = 0
        rejected = 0

        for candidate in candidates:
            if candidate.status != "pending":
                continue
            if candidate.public_id not in confirm_set:
                await self._candidate_repo.update_status(candidate.id, "rejected")
                rejected += 1
                continue

            # Apply a user-corrected title (drops the stale catalog match).
            new_title = (overrides.get(candidate.public_id) or "").strip()
            if new_title and new_title != candidate.title:
                await self._candidate_repo.set_title(candidate.id, new_title)

            game = await self._get_or_create_game(candidate)
            if not await self._library_repo.exists(user_id, game.id, platform_id):
                await self._library_repo.create(
                    user_id=user_id,
                    game_id=game.id,
                    platform_id=platform_id,
                    status=library_status,
                )
            await self._candidate_repo.update_status(
                candidate.id, "confirmed", matched_game_id=game.id
            )
            confirmed += 1

        await self._resolve_capture_status(capture.id)
        return confirmed, rejected

    async def reject_candidate(
        self,
        user_id: int,
        capture_public_id: UUID,
        candidate_public_id: UUID,
    ) -> None:
        """Reject a candidate.

        Raises:
            HTTPException: If the capture or candidate is not found, or the
                candidate is not in ``pending`` status.
        """
        capture = await self.get_capture(user_id, capture_public_id)

        candidate = await self._candidate_repo.get_by_public_id(candidate_public_id)
        if candidate is None or candidate.capture_id != capture.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found",
            )
        if candidate.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate already {candidate.status}",
            )

        await self._candidate_repo.update_status(candidate.id, "rejected")
        await self._resolve_capture_status(capture.id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _resolve_capture_status(self, capture_id: int) -> None:
        """Check whether all candidates are resolved and update the capture status.

        - All confirmed -> ``committed``
        - All rejected  -> ``cancelled``
        - Mix           -> ``partially_committed``
        - Any pending   -> no change
        """
        candidates = await self._candidate_repo.get_all_for_capture(capture_id)
        if not candidates:
            return

        statuses = {c.status for c in candidates}
        if "pending" in statuses:
            return  # Still has unresolved candidates.

        if statuses == {"confirmed"}:
            new_status = "committed"
        elif statuses == {"rejected"}:
            new_status = "cancelled"
        else:
            new_status = "partially_committed"

        await self._capture_repo.update_status(capture_id, new_status)
