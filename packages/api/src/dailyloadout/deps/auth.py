"""Authentication dependencies: service, token extraction, current user."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from dailyloadout.config import settings
from dailyloadout.core.auth.security import decode_access_token
from dailyloadout.core.auth.service import AuthService
from dailyloadout.infrastructure.db.models import User
from dailyloadout.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
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


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
RefreshTokenRepoDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repo)]


# ── Service ────────────────────────────────────────────────────────────


def get_auth_service(
    user_repo: UserRepoDep,
    rt_repo: RefreshTokenRepoDep,
) -> AuthService:
    """Provide an ``AuthService`` wired to the current repositories."""
    return AuthService(user_repo, rt_repo)


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
    except (JWTError, ValueError) as exc:
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
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
