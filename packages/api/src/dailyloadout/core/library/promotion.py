"""Catalogue promotion: expose a genuinely-adopted manual game globally.

Extracted from ``LibraryService`` to keep that file focused. A private manual
row joins the shared catalogue once enough INDEPENDENT users own it (Block C).
"""

from __future__ import annotations

import structlog

from dailyloadout.core.library.backfill import enrich_in_place
from dailyloadout.core.library.igdb_budget import igdb_budget_allows
from dailyloadout.infrastructure.db.models import Game
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient

logger = structlog.get_logger()


async def maybe_promote_to_shared(
    game: Game,
    user_id: int,
    *,
    game_repo: GameRepository,
    library_repo: LibraryRepository,
    igdb_client: IGDBSearchClient | None,
    min_score: float,
    threshold: int,
) -> None:
    """Promote a private manual *game* to globally shared once enough own it.

    Anti-Sybil hardening: before exposing it globally we attempt an IGDB
    **corroboration** (best-effort, budget-gated → a real game gets an
    ``igdb_id``), then log the promotion with whether it was corroborated, so
    the residual vector (a few colluding verified accounts) is observable and
    demotable (``scripts/demote_game.py``). Globally-visible fields were
    sanitized at creation. Attribution preserved; canonical/IGDB rows are
    already shared.
    """
    if game.igdb_id is not None or game.is_shared or game.created_by_user_id is None:
        return
    owners = await library_repo.count_distinct_owners(game.id)
    if owners < threshold:
        return

    if igdb_client is not None and await igdb_budget_allows(user_id):
        await enrich_in_place(
            game, igdb_client=igdb_client, game_repo=game_repo, min_score=min_score
        )

    await game_repo.update(game, is_shared=True)
    logger.info(
        "catalog_game_promoted",
        game_id=game.id,
        owners=owners,
        igdb_corroborated=game.igdb_id is not None,
        created_by_user_id=game.created_by_user_id,
    )
