"""Authentication dependencies: service, token extraction, current user."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError

from dailyloadout.config import settings
from dailyloadout.core.admin.config_service import AdminConfigService
from dailyloadout.core.admin.dashboard_service import AdminDashboardService
from dailyloadout.core.admin.service import AdminUserService
from dailyloadout.core.auth.security import decode_access_token
from dailyloadout.core.auth.service import AuthService
from dailyloadout.infrastructure.config.dynamic import dynamic_config
from dailyloadout.infrastructure.db.models import User
from dailyloadout.infrastructure.db.repositories.admin import (
    AdminAuditRepository,
    AdminRepository,
)
from dailyloadout.infrastructure.db.repositories.app_config import AppConfigRepository
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
from dailyloadout.infrastructure.db.repositories.oauth import OAuthIdentityRepository
from dailyloadout.infrastructure.db.repositories.refresh_token import (
    RefreshTokenRepository,
)
from dailyloadout.infrastructure.db.repositories.user import UserRepository

from .db import DbSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


# ── Repositories ───────────────────────────────────────────────────────


def get_user_repo(db: DbSession) -> UserRepository:
    """Provide a ``UserRepository`` bound to the current session."""
    return UserRepository(db)


def get_refresh_token_repo(db: DbSession) -> RefreshTokenRepository:
    """Provide a ``RefreshTokenRepository`` bound to the current session."""
    return RefreshTokenRepository(db)


def get_oauth_repo(db: DbSession) -> OAuthIdentityRepository:
    """Provide an ``OAuthIdentityRepository`` bound to the current session."""
    return OAuthIdentityRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
RefreshTokenRepoDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repo)]
OAuthRepoDep = Annotated[OAuthIdentityRepository, Depends(get_oauth_repo)]


# ── Service ────────────────────────────────────────────────────────────


def get_auth_service(
    user_repo: UserRepoDep,
    rt_repo: RefreshTokenRepoDep,
    oauth_repo: OAuthRepoDep,
) -> AuthService:
    """Provide an ``AuthService`` wired to the current repositories.

    The mailer is resolved internally (best-effort SMTP; no-op when unconfigured).
    """
    return AuthService(user_repo, rt_repo, oauth_repo=oauth_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TokenDep = Annotated[str | None, Depends(oauth2_scheme)]


# ── Current user ───────────────────────────────────────────────────────


async def get_current_user(
    token: TokenDep,
    db: DbSession,
) -> User:
    """Resolve the currently authenticated user from the JWT bearer token.

    In single-user mode, JWT validation is bypassed and the single user
    configured via ``settings.single_user_email`` is returned directly.
    """
    user_repo = UserRepository(db)

    # Single-user mode: bypass JWT and return the configured user.
    if settings.single_user_mode:
        user = await user_repo.get_by_email(settings.single_user_email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Single-user account not found",
            )
        return user

    # Normal mode: validate the Bearer token.
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        subject = str(payload.get("sub")) if payload.get("sub") is not None else None
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        public_id = UUID(subject)
        token_version = payload.get("tv")
    except (PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await user_repo.get_by_public_id(public_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Session kill-switch: a stale token_version means the session was revoked
    # (logout-everywhere, ban, or theft response) — reject every old token.
    if not isinstance(token_version, int) or token_version != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Incident response: a banned account is cut off at the auth boundary.
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended",
        )

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_verified_user(current_user: CurrentUserDep) -> User:
    """Require the authenticated user to have a verified email.

    Gate for cost-bearing routes (LLM / IGDB / research). Raises **403** when
    ``email_verified`` is False. In single-user mode the configured account is
    trusted, so this is effectively a pass-through.
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return current_user


RequireVerifiedUserDep = Annotated[User, Depends(get_verified_user)]


# ── Admin (backoffice) ─────────────────────────────────────────────────


async def get_admin_user(current_user: CurrentUserDep, db: DbSession) -> User:
    """Require the authenticated user to hold a backoffice admin grant.

    Admin rights live in the ``admin_users`` table (never on the user row and
    never in the JWT), so this is checked against the DB on every request — a
    revoked grant takes effect immediately. Raises **403** for non-admins.

    Single-user mode is rejected outright: the backoffice is a multi-user,
    audited surface and must not be reachable through the JWT-bypass account.
    """
    if settings.single_user_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access not available",
        )
    if not await AdminRepository(db).is_admin(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


AdminUserDep = Annotated[User, Depends(get_admin_user)]


def get_admin_user_service(
    user_repo: UserRepoDep,
    rt_repo: RefreshTokenRepoDep,
    auth_service: AuthServiceDep,
    db: DbSession,
) -> AdminUserService:
    """Provide an ``AdminUserService`` wired to the current repositories.

    Reuses the request's ``AuthService`` for the ban primitive (session
    kill-switch) so the backoffice never re-implements that incident logic.
    """
    return AdminUserService(
        user_repo,
        AdminRepository(db),
        AdminAuditRepository(db),
        rt_repo,
        auth_service,
    )


AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]


def get_admin_config_service(db: DbSession) -> AdminConfigService:
    """Provide an ``AdminConfigService`` over the process-wide config overlay."""
    return AdminConfigService(
        AppConfigRepository(db),
        AdminAuditRepository(db),
        dynamic_config,
    )


AdminConfigServiceDep = Annotated[AdminConfigService, Depends(get_admin_config_service)]


def get_admin_dashboard_service(db: DbSession) -> AdminDashboardService:
    """Provide an ``AdminDashboardService`` wired to the read-side repositories."""
    return AdminDashboardService(
        UserRepository(db),
        AdminRepository(db),
        AdminAuditRepository(db),
        AppConfigRepository(db),
        MissionRepository(db),
        GameRepository(db),
    )


AdminDashboardServiceDep = Annotated[
    AdminDashboardService, Depends(get_admin_dashboard_service)
]
