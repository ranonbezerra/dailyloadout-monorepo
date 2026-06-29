"""Reset a user's password by email (admin / dev recovery).

Sets a new bcrypt password hash, bumps ``token_version`` (kills outstanding
access tokens), and revokes every refresh token — so the only way back in is a
fresh login with the new password.

Usage:
    poetry run python scripts/reset_password.py user@example.com 'NewPassw0rd!'
"""

from __future__ import annotations

import asyncio
import sys

from slate.core.auth.security import hash_password
from slate.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from slate.infrastructure.db.repositories.user import UserRepository
from slate.infrastructure.db.session import async_session_factory


async def _run(email: str, new_password: str) -> int:
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_email(email)
        if user is None:
            print(f"✗ No active user with email {email!r}.")
            return 1

        user.password_hash = hash_password(new_password)
        await session.flush()
        await user_repo.bump_token_version(user.id)
        await RefreshTokenRepository(session).revoke_all_for_user(user.id)
        await session.commit()
        print(f"✓ Password reset for {email} — all existing sessions killed. Log in fresh.")
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/reset_password.py <email> <new_password>")
        return 2
    return asyncio.run(_run(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    raise SystemExit(main())
