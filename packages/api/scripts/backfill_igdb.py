"""Backfill IGDB metadata onto games created before IGDB was configured.

Finds every game with ``igdb_id IS NULL`` (typically capture/manual rows from
before you had IGDB credentials), re-matches it against the live IGDB catalogue,
and fills in genres / cover / summary / release date. This is what makes the
"Time by Genre" chart (and covers) populate for your older library.

Usage:
    poetry run python scripts/backfill_igdb.py --dry-run        # preview matches
    poetry run python scripts/backfill_igdb.py                  # apply
    poetry run python scripts/backfill_igdb.py --limit 50       # first 50 only
    make igdb-backfill                                          # dry-run preview
    make igdb-backfill args="--apply"                          # apply
"""

from __future__ import annotations

import argparse
import asyncio

from dailyloadout.config import settings
from dailyloadout.core.library.backfill import BackfillReport, backfill_games
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.session import async_session_factory
from dailyloadout.infrastructure.igdb.client import IGDBClient
from dailyloadout.infrastructure.igdb.exceptions import IGDBNotConfiguredError


def _print_report(report: BackfillReport, *, dry_run: bool) -> None:
    verb = "Would enrich" if dry_run else "Enriched"
    matched = report.matched_dry_run if dry_run else report.enriched

    print(f"\nScanned {report.scanned} unenriched game(s).\n")
    if matched:
        print(f"✓ {verb} {len(matched)}:")
        for item in matched:
            print(f"    {item.title!r} → {item.igdb_title!r}  (score {item.score:.2f})")
    if report.skipped_collision:
        print(f"\n⊘ Skipped {len(report.skipped_collision)} (IGDB match already in catalogue):")
        for item in report.skipped_collision:
            print(f"    {item.title!r} → {item.igdb_title!r}")
    if report.unmatched:
        print(f"\n? No confident match for {len(report.unmatched)}:")
        for title in report.unmatched:
            print(f"    {title!r}")
    print()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill IGDB metadata onto unenriched games.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag the script runs as a dry-run preview.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only (default behaviour; explicit flag for clarity).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N games.")
    args = parser.parse_args()

    dry_run = not args.apply

    try:
        igdb_client = IGDBClient(settings)
    except IGDBNotConfiguredError:
        print("✗ IGDB is not configured. Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET in your .env.")
        return 1

    if dry_run:
        print("Running in DRY-RUN mode (no changes written). Pass --apply to persist.")

    async with async_session_factory() as session:
        repo = GameRepository(session)
        report = await backfill_games(
            game_repo=repo,
            igdb_client=igdb_client,
            min_score=settings.catalog_match_min_score,
            dry_run=dry_run,
            limit=args.limit,
        )
        if not dry_run:
            await session.commit()

    _print_report(report, dry_run=dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
