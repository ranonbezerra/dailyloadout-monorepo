"""Smoke-test the live IGDB client (ROADMAP Epic 14 / Epic 3 enrichment).

Hits the real IGDB API with the credentials in your environment and prints what
comes back, so you can confirm IGDB_CLIENT_ID / IGDB_CLIENT_SECRET work end to
end without booting the whole app.

Usage:
    poetry run python scripts/check_igdb.py "Hollow Knight"
    make igdb-check q="Hollow Knight"
"""

from __future__ import annotations

import asyncio
import sys

from dailyloadout.config import settings
from dailyloadout.infrastructure.igdb.client import IGDBClient
from dailyloadout.infrastructure.igdb.exceptions import IGDBNotConfiguredError


async def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "Hollow Knight"

    try:
        client = IGDBClient(settings)
    except IGDBNotConfiguredError:
        print("✗ IGDB is not configured. Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET in your .env.")
        return 1

    print(f'Searching IGDB for "{query}"…\n')
    try:
        results = await client.search_games(query, limit=5)
    except Exception as exc:
        print(f"✗ Request failed: {type(exc).__name__}: {exc}")
        return 1

    if not results:
        print("No results (the request succeeded but matched nothing).")
        return 0

    for game in results:
        print(f"• {game.title}  (igdb_id={game.igdb_id})")
        print(f"    release : {game.first_release_date}")
        print(f"    genres  : {', '.join(game.genres) if game.genres else '—'}")
        print(f"    cover   : {game.cover_url or '—'}")
        summary = (game.summary or "").strip().replace("\n", " ")
        print(f"    summary : {summary[:140] + '…' if len(summary) > 140 else summary or '—'}")
        print()

    print(f"✓ IGDB is working — {len(results)} result(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
