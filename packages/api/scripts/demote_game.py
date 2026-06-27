"""Demote a shared manual game back to private (catalogue abuse response).

A manual game auto-promotes to the shared catalogue once it has enough distinct
owners (anti-abuse Block C). The residual Sybil vector is a few colluding
verified accounts pushing a poisoned manual row over that threshold. This CLI is
the admin demote path: it flips ``is_shared`` back to False so the row is once
again visible only to its creator, removing it from everyone else's catalogue.

Promotions are logged (``catalog_game_promoted`` with ``igdb_corroborated``), so
an uncorroborated promotion is the signal to review/demote here.

Usage:
    poetry run python scripts/demote_game.py <slug>
"""

from __future__ import annotations

import asyncio
import sys

from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.session import async_session_factory


async def _run(slug: str) -> int:
    async with async_session_factory() as session:
        game_repo = GameRepository(session)
        game = await game_repo.get_by_slug(slug)
        if game is None:
            print(f"✗ No game with slug {slug!r}.")
            return 1
        if not game.is_shared:
            print(f"• Game {slug!r} is already private — nothing to do.")
            return 0

        await game_repo.update(game, is_shared=False)
        await session.commit()
        print(
            f"✓ Demoted {slug!r} to private "
            f"(was created_by_user_id={game.created_by_user_id}, igdb_id={game.igdb_id})."
        )
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/demote_game.py <slug>")
        return 2
    return asyncio.run(_run(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
