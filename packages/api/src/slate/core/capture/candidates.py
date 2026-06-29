"""Candidate review/commit logic for the capture service.

Standalone functions (operating on the repositories) so ``service.py`` stays
focused on submission/ingestion orchestration and under the 300-line cap. The
service delegates confirm/reject/bulk-confirm here.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from slate.core.cache.invalidation import invalidate_user_stats
from slate.core.capture.games import get_or_create_game
from slate.infrastructure.db.models import Capture, LibraryEntry
from slate.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.platform import PlatformRepository


async def confirm_candidate(
    *,
    user_id: int,
    capture: Capture,
    candidate_public_id: UUID,
    platform_id: int,
    library_status: str,
    candidate_repo: CaptureCandidateRepository,
    capture_repo: CaptureRepository,
    game_repo: GameRepository,
    library_repo: LibraryRepository,
    platform_repo: PlatformRepository,
) -> LibraryEntry:
    """Confirm a candidate: create a library entry and mark it confirmed."""
    candidate = await candidate_repo.get_by_public_id(candidate_public_id)
    if candidate is None or candidate.capture_id != capture.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if candidate.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Candidate already {candidate.status}",
        )

    platform = await platform_repo.get_by_id(platform_id)
    if platform is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")

    game = await get_or_create_game(game_repo, candidate, created_by_user_id=user_id)
    if await library_repo.exists(user_id, game.id, platform_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Library entry already exists for this game and platform",
        )

    entry = await library_repo.create(
        user_id=user_id,
        game_id=game.id,
        platform_id=platform_id,
        status=library_status,
    )
    entry.game = game
    entry.platform = platform

    await candidate_repo.update_status(candidate.id, "confirmed", matched_game_id=game.id)
    await resolve_capture_status(capture.id, candidate_repo, capture_repo)
    await invalidate_user_stats(user_id)
    return entry


async def bulk_confirm_candidates(
    *,
    user_id: int,
    capture: Capture,
    confirm_public_ids: list[UUID],
    platform_id: int,
    library_status: str,
    title_overrides: dict[UUID, str] | None,
    candidate_repo: CaptureCandidateRepository,
    capture_repo: CaptureRepository,
    game_repo: GameRepository,
    library_repo: LibraryRepository,
    platform_repo: PlatformRepository,
) -> tuple[int, int]:
    """Confirm the listed candidates and reject the rest, in one call.

    Returns ``(confirmed, rejected)`` counts. Duplicate library entries are
    treated as already-imported (counted as confirmed), not an error, so a bulk
    import of 50-100 titles never aborts midway.
    """
    platform = await platform_repo.get_by_id(platform_id)
    if platform is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")

    confirm_set = set(confirm_public_ids)
    overrides = title_overrides or {}
    candidates = await candidate_repo.get_all_for_capture(capture.id)
    confirmed = 0
    rejected = 0

    for candidate in candidates:
        if candidate.status != "pending":
            continue
        if candidate.public_id not in confirm_set:
            await candidate_repo.update_status(candidate.id, "rejected")
            rejected += 1
            continue

        # Apply a user-corrected title (drops the stale catalog match).
        new_title = (overrides.get(candidate.public_id) or "").strip()
        if new_title and new_title != candidate.title:
            await candidate_repo.set_title(candidate.id, new_title)

        game = await get_or_create_game(game_repo, candidate, created_by_user_id=user_id)
        if not await library_repo.exists(user_id, game.id, platform_id):
            await library_repo.create(
                user_id=user_id,
                game_id=game.id,
                platform_id=platform_id,
                status=library_status,
            )
        await candidate_repo.update_status(candidate.id, "confirmed", matched_game_id=game.id)
        confirmed += 1

    await resolve_capture_status(capture.id, candidate_repo, capture_repo)
    if confirmed:
        await invalidate_user_stats(user_id)
    return confirmed, rejected


async def reject_candidate(
    *,
    capture: Capture,
    candidate_public_id: UUID,
    candidate_repo: CaptureCandidateRepository,
    capture_repo: CaptureRepository,
) -> None:
    """Reject a candidate."""
    candidate = await candidate_repo.get_by_public_id(candidate_public_id)
    if candidate is None or candidate.capture_id != capture.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if candidate.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Candidate already {candidate.status}",
        )

    await candidate_repo.update_status(candidate.id, "rejected")
    await resolve_capture_status(capture.id, candidate_repo, capture_repo)


async def resolve_capture_status(
    capture_id: int,
    candidate_repo: CaptureCandidateRepository,
    capture_repo: CaptureRepository,
) -> None:
    """Resolve the capture status from its candidates' statuses.

    - All confirmed -> ``committed``
    - All rejected  -> ``cancelled``
    - Mix           -> ``partially_committed``
    - Any pending   -> no change
    """
    candidates = await candidate_repo.get_all_for_capture(capture_id)
    if not candidates:
        return

    statuses = {c.status for c in candidates}
    if "pending" in statuses:
        return

    if statuses == {"confirmed"}:
        new_status = "committed"
    elif statuses == {"rejected"}:
        new_status = "cancelled"
    else:
        new_status = "partially_committed"

    await capture_repo.update_status(capture_id, new_status)
