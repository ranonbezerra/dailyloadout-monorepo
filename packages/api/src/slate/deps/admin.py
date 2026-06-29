"""Backoffice service dependency providers.

The home for admin *service* DI. The admin auth gate (``AdminUserDep``) and the
older service providers still live in ``deps/auth.py``; new backoffice domains
wire their services here to keep ``auth.py`` within the file-size budget.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from slate.core.admin.picks_service import AdminPickService
from slate.core.admin.play_sessions_service import AdminPlaySessionService
from slate.infrastructure.db.repositories.admin import AdminAuditRepository
from slate.infrastructure.db.repositories.pick import PickRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.db.repositories.user import UserRepository

from .db import DbSession


def get_admin_pick_service(db: DbSession) -> AdminPickService:
    """Provide an ``AdminPickService`` wired to the pick + user repos."""
    return AdminPickService(PickRepository(db), UserRepository(db))


AdminPickServiceDep = Annotated[AdminPickService, Depends(get_admin_pick_service)]


def get_admin_play_session_service(db: DbSession) -> AdminPlaySessionService:
    """Provide an ``AdminPlaySessionService`` wired to the play-session + user repos."""
    return AdminPlaySessionService(
        PlaySessionRepository(db), UserRepository(db), AdminAuditRepository(db)
    )


AdminPlaySessionServiceDep = Annotated[
    AdminPlaySessionService, Depends(get_admin_play_session_service)
]
