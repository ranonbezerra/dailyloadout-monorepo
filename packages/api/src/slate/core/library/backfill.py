"""Backfill IGDB metadata onto games that predate IGDB credentials.

Games created from captures/manual entry before ``IGDB_CLIENT_ID`` was set have
``igdb_id IS NULL`` and no genres/cover/summary — which is why, e.g., the
"Time by Genre" analytics chart renders empty. This module re-matches each such
game against the live IGDB catalogue (reusing the same fuzzy scorer the bulk
library-import uses) and fills in the canonical metadata.

It is deliberately conservative:

* The game's ``title``/``slug`` are left untouched (we only fill metadata), so
  no slug collisions and the user's known title is preserved.
* If the matched ``igdb_id`` already belongs to a *different* catalogue row, the
  unenriched row is a duplicate of an already-canonical game; we **skip** it and
  report it rather than risk a merge (repointing library entries is a separate,
  riskier operation).

The single-game core (``enrich_game``) is shared with ``LibraryService``: when a
manual create resolves to a game we already hold but lack IGDB info for, the same
in-place enrichment runs on the fly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from slate.core.capture.games import slugify
from slate.infrastructure.catalog.matcher import best_match
from slate.infrastructure.db.models import Game
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.igdb.base import IGDBSearchClient
from slate.infrastructure.igdb.schemas import IGDBGame

logger = structlog.get_logger()


@dataclass
class BackfillItem:
    """One game's outcome: the local title, the matched IGDB title, the score."""

    title: str
    igdb_title: str
    score: float


@dataclass
class BackfillReport:
    """Aggregate outcome of a backfill run."""

    enriched: list[BackfillItem] = field(default_factory=list)
    matched_dry_run: list[BackfillItem] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    skipped_collision: list[BackfillItem] = field(default_factory=list)

    @property
    def scanned(self) -> int:
        return (
            len(self.enriched)
            + len(self.matched_dry_run)
            + len(self.unmatched)
            + len(self.skipped_collision)
        )


async def _match_for_enrich(
    game: Game,
    *,
    igdb_client: IGDBSearchClient,
    game_repo: GameRepository,
    min_score: float,
    search_limit: int = 5,
) -> tuple[IGDBGame, float] | None:
    """Return a confident, non-colliding IGDB match for *game*, else ``None``.

    A match collides when its ``igdb_id`` already belongs to a *different*
    catalogue row — in that case we refuse to enrich (the row is a duplicate of
    an already-canonical game).
    """
    candidates = await igdb_client.search_games(game.title, limit=search_limit)
    result = best_match(game.title, candidates, min_score)
    if result is None:
        return None

    igdb_game, _score = result
    existing = await game_repo.get_by_igdb_id(igdb_game.igdb_id)
    if existing is not None and existing.id != game.id:
        return None  # collision — leave the row as-is

    return result


async def _write_enrichment(game: Game, igdb_game: IGDBGame, *, game_repo: GameRepository) -> None:
    """Fill IGDB metadata onto *game* in place (title/slug untouched)."""
    await game_repo.update(
        game,
        igdb_id=igdb_game.igdb_id,
        summary=igdb_game.summary,
        cover_url=igdb_game.cover_url,
        genres=igdb_game.genres,
        first_release_date=igdb_game.first_release_date,
        metadata_source="igdb",
    )


async def enrich_game(
    game: Game,
    *,
    igdb_client: IGDBSearchClient,
    game_repo: GameRepository,
    min_score: float,
    search_limit: int = 5,
) -> bool:
    """Enrich a single un-enriched *game* in place from IGDB.

    Returns ``True`` if the game was enriched, ``False`` otherwise (no confident
    match, or a collision with an already-canonical row). Preserves the
    collision-skip semantics shared with :func:`backfill_games`.
    """
    match = await _match_for_enrich(
        game,
        igdb_client=igdb_client,
        game_repo=game_repo,
        min_score=min_score,
        search_limit=search_limit,
    )
    if match is None:
        return False

    igdb_game, _score = match
    await _write_enrichment(game, igdb_game, game_repo=game_repo)
    return True


async def enrich_in_place(
    game: Game,
    *,
    igdb_client: IGDBSearchClient | None,
    game_repo: GameRepository,
    min_score: float,
) -> None:
    """Best-effort on-the-fly enrichment of an existing un-enriched global row.

    Swallows IGDB failures (logged) so a manual create never fails because the
    catalogue lookup did.
    """
    if igdb_client is None:
        return
    try:
        await enrich_game(game, igdb_client=igdb_client, game_repo=game_repo, min_score=min_score)
    except Exception:
        logger.warning("library_igdb_enrich_failed", exc_info=True)


async def reconcile_manual_title(
    title: str,
    *,
    igdb_client: IGDBSearchClient | None,
    game_repo: GameRepository,
    min_score: float,
) -> Game | None:
    """Resolve *title* to a canonical GLOBAL IGDB row, or ``None``.

    Mirrors ``get_or_create_game``'s dedup (by IGDB id, then global slug). Used
    when a manual create finds nothing in our DB and falls through to IGDB.
    Returns ``None`` when no client is configured or no confident match exists.
    """
    if igdb_client is None:
        return None
    try:
        candidates = await igdb_client.search_games(title, limit=5)
    except Exception:
        logger.warning("library_igdb_reconcile_failed", exc_info=True)
        return None

    result = best_match(title, candidates, min_score)
    if result is None:
        return None
    match, _score = result

    existing = await game_repo.get_by_igdb_id(match.igdb_id)
    if existing is not None:
        return existing

    existing = await game_repo.get_by_slug(slugify(match.title))
    if existing is not None:
        return existing

    return await game_repo.create(
        slug=slugify(match.title),
        title=match.title,
        metadata_source="igdb",
        igdb_id=match.igdb_id,
        summary=match.summary,
        cover_url=match.cover_url,
        first_release_date=match.first_release_date,
        genres=match.genres,
        created_by_user_id=None,
        # Canonical IGDB row: globally visible. ``igdb_id`` alone already satisfies
        # the visibility rule; set the flag too for clarity/consistency.
        is_shared=True,
    )


async def backfill_games(
    *,
    game_repo: GameRepository,
    igdb_client: IGDBSearchClient,
    min_score: float,
    dry_run: bool = False,
    limit: int | None = None,
    search_limit: int = 5,
) -> BackfillReport:
    """Enrich games with ``igdb_id IS NULL`` against IGDB.

    Returns a :class:`BackfillReport`. When ``dry_run`` is true, matches are
    reported under ``matched_dry_run`` and nothing is written.
    """
    games = await game_repo.list_unenriched(limit=limit)
    report = BackfillReport()

    for game in games:
        candidates = await igdb_client.search_games(game.title, limit=search_limit)
        result = best_match(game.title, candidates, min_score)
        if result is None:
            report.unmatched.append(game.title)
            continue

        igdb_game, score = result
        item = BackfillItem(title=game.title, igdb_title=igdb_game.title, score=score)

        existing = await game_repo.get_by_igdb_id(igdb_game.igdb_id)
        if existing is not None and existing.id != game.id:
            report.skipped_collision.append(item)
            continue

        if dry_run:
            report.matched_dry_run.append(item)
            continue

        await _write_enrichment(game, igdb_game, game_repo=game_repo)
        report.enriched.append(item)

    return report
