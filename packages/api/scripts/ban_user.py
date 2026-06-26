"""Ban / unban a user by email (anti-abuse incident response, Phase 2).

Banning fully cuts an account off: ``is_banned`` is set (so the API 403s every
request), ``token_version`` is bumped (instantly killing all outstanding access
tokens), and every refresh token is revoked. Unbanning only clears the flag —
it does NOT re-mint sessions; the user simply logs in again.

Usage:
    poetry run python scripts/ban_user.py ban   abuser@example.com
    poetry run python scripts/ban_user.py unban abuser@example.com
"""

from __future__ import annotations

import asyncio
import sys

from dailyloadout.core.auth.service import AuthService
from dailyloadout.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository
from dailyloadout.infrastructure.db.session import async_session_factory


async def _run(action: str, email: str) -> int:
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_email(email)
        if user is None:
            print(f"✗ No active user with email {email!r}.")
            return 1

        service = AuthService(user_repo, RefreshTokenRepository(session))
        if action == "ban":
            await service.ban_user(user.id)
            await session.commit()
            print(f"✓ Banned {email} — all sessions killed.")
        else:
            await user_repo.set_banned(user.id, False)
            await session.commit()
            print(f"✓ Unbanned {email} — they may log in again.")
    return 0


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"ban", "unban"}:
        print("Usage: python scripts/ban_user.py {ban|unban} <email>")
        return 2
    return asyncio.run(_run(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    raise SystemExit(main())
