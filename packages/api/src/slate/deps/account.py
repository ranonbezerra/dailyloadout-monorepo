"""DI for the account-lifecycle service (export + erasure).

Its own module because ``deps/auth.py`` is at the file-size budget and the export
side needs the cross-domain read repos (library/sessions/captures/picks).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from slate.core.auth.account import AccountService
from slate.core.auth.email_change import EmailChangeService
from slate.core.auth.sessions import SessionService
from slate.infrastructure.db.repositories.capture import CaptureRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.pick import PickRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from slate.infrastructure.db.repositories.user import UserRepository

from .db import DbSession


def get_account_service(db: DbSession) -> AccountService:
    """Provide an ``AccountService`` wired to the user + cross-domain read repos."""
    return AccountService(
        UserRepository(db),
        LibraryRepository(db),
        PlaySessionRepository(db),
        CaptureRepository(db),
        PickRepository(db),
    )


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


def get_email_change_service(db: DbSession) -> EmailChangeService:
    """Provide an ``EmailChangeService`` wired to the user repo (mailer internal)."""
    return EmailChangeService(UserRepository(db))


EmailChangeServiceDep = Annotated[EmailChangeService, Depends(get_email_change_service)]


def get_session_service(db: DbSession) -> SessionService:
    """Provide a ``SessionService`` wired to the refresh-token repo."""
    return SessionService(RefreshTokenRepository(db))


SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
