"""Duplicate detection for library-import candidates (ROADMAP Epic 14).

Flags candidates whose game is already in the user's library for a chosen
platform, so the import UI can warn before adding. Purely advisory — the
bulk-confirm path also skips true duplicates — and platform-scoped, since the
same game on a different platform is a legitimate separate entry.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from slate.core.capture.games import slugify
from slate.infrastructure.db.models import CaptureCandidate
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.library import LibraryRepository


async def find_duplicate_candidate_ids(
    *,
    candidates: Iterable[CaptureCandidate],
    game_repo: GameRepository,
    library_repo: LibraryRepository,
    user_id: int,
    platform_id: int,
) -> list[UUID]:
    """Return the public_ids of pending candidates already owned on *platform_id*.

    Resolves each candidate to an existing ``Game`` (by IGDB id, else by slug of
    the title) without creating anything, then checks the library for a matching
    entry on the platform.
    """
    duplicates: list[UUID] = []
    for candidate in candidates:
        if candidate.status != "pending":
            continue

        game = None
        if candidate.igdb_id is not None:
            game = await game_repo.get_by_igdb_id(candidate.igdb_id)
        if game is None:
            game = await game_repo.get_by_slug(slugify(candidate.igdb_title or candidate.title))

        if game is not None and await library_repo.exists(user_id, game.id, platform_id):
            duplicates.append(candidate.public_id)

    return duplicates
