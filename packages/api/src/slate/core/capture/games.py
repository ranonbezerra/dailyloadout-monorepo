"""Game resolution for capture commits.

Turns an extracted capture candidate into a canonical ``Game`` row — matching an
existing record by IGDB id or slug, or creating one. Split out of the capture
service so that orchestration (review → library commit) stays separate from the
catalog-matching detail.
"""

from __future__ import annotations

import re

from slate.infrastructure.db.models import CaptureCandidate, Game
from slate.infrastructure.db.repositories.game import GameRepository


def slugify(title: str) -> str:
    """Convert a game title into a URL-friendly slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")


async def get_or_create_game(
    game_repo: GameRepository,
    candidate: CaptureCandidate,
    *,
    created_by_user_id: int | None = None,
) -> Game:
    """Resolve a candidate to a ``Game`` row, creating it if needed.

    A newly-created row WITHOUT an IGDB match is a private manual row attributed
    to ``created_by_user_id`` (anti-abuse Block C): the capturing user sees their
    own game, but it stays out of everyone else's catalogue until validated. An
    IGDB-matched row is canonical/global (``is_shared`` follows the IGDB id).
    """
    if candidate.igdb_id is not None:
        game = await game_repo.get_by_igdb_id(candidate.igdb_id)
        if game is not None:
            return game

    title = candidate.igdb_title or candidate.title
    slug = slugify(title)
    existing = await game_repo.get_by_slug(slug)
    if existing is not None:
        return existing

    is_igdb = candidate.igdb_id is not None
    return await game_repo.create(
        slug=slug,
        title=title,
        metadata_source="igdb" if is_igdb else "capture",
        igdb_id=candidate.igdb_id,
        summary=candidate.igdb_summary,
        cover_url=candidate.igdb_cover_url,
        first_release_date=candidate.igdb_first_release_date,
        genres=candidate.igdb_genres,
        # Manual capture row → private + attributed; IGDB row → globally shared.
        created_by_user_id=None if is_igdb else created_by_user_id,
        is_shared=is_igdb,
    )
