"""Auth API endpoints: register, login, refresh, logout, me."""

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from dailyloadout.config import settings
from dailyloadout.core.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from dailyloadout.deps import AuthServiceDep, CurrentUserDep

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Register a new user and return access + refresh tokens."""
    if settings.single_user_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration disabled in single-user mode",
        )

    try:
        _user, access_token, refresh_token = await auth_service.register(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Authenticate with email/password and receive tokens."""
    try:
        _user, access_token, refresh_token = await auth_service.login(
            email=body.email,
            password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Rotate the refresh token and issue a new access token."""
    try:
        access_token, refresh_token = await auth_service.refresh(body.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """Revoke the given refresh token."""
    await auth_service.logout(body.refresh_token)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
