"""Grant / revoke / list backoffice admin rights by email (Epic 21, Phase 1).

Admin rights are a row in ``admin_users`` — never a flag on the user record and
never a JWT claim — so a grant takes effect (and a revoke is enforced) on the
next request. There is no self-service path to admin; bootstrapping the first
admin is this CLI's job.

Usage:
    poetry run python scripts/grant_admin.py grant  admin@example.com
    poetry run python scripts/grant_admin.py revoke admin@example.com
    poetry run python scripts/grant_admin.py list
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from dailyloadout.infrastructure.db.models import AdminUser, User
from dailyloadout.infrastructure.db.repositories.admin import AdminRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository
from dailyloadout.infrastructure.db.session import async_session_factory


async def _grant(email: str) -> int:
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_email(email)
        if user is None:
            print(f"✗ No active user with email {email!r}.")
            return 1
        await AdminRepository(session).grant(user.id)
        await session.commit()
        print(f"✓ Granted admin to {email}.")
    return 0


async def _revoke(email: str) -> int:
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_email(email)
        if user is None:
            print(f"✗ No active user with email {email!r}.")
            return 1
        removed = await AdminRepository(session).revoke(user.id)
        await session.commit()
        if removed:
            print(f"✓ Revoked admin from {email}.")
        else:
            print(f"• {email} was not an admin; nothing to do.")
    return 0


async def _list() -> int:
    async with async_session_factory() as session:
        stmt = (
            select(User.email).join(AdminUser, AdminUser.user_id == User.id).order_by(User.email)
        )
        emails = (await session.execute(stmt)).scalars().all()
        if not emails:
            print("• No admins.")
        else:
            print(f"Admins ({len(emails)}):")
            for email in emails:
                print(f"  - {email}")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "list" and len(args) == 1:
        return asyncio.run(_list())
    if len(args) == 2 and args[0] in {"grant", "revoke"}:
        runner = _grant if args[0] == "grant" else _revoke
        return asyncio.run(runner(args[1]))
    print("Usage: python scripts/grant_admin.py {grant|revoke <email> | list}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
