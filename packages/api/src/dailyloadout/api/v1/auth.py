"""Auth API endpoints: register, login, refresh, logout, me."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pyrate_limiter import Duration, Limiter, Rate

from dailyloadout.api.v1.auth_cookies import (
    clear_refresh_cookie,
    is_cookie_mode,
    read_refresh_cookie,
    set_refresh_cookie,
)
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

_login_limiter = Limiter(Rate(10, Duration.MINUTE))
_register_limiter = Limiter(Rate(5, Duration.MINUTE))


async def _check_login_rate(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    allowed = _login_limiter.try_acquire(client_ip, blocking=False)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )


async def _check_register_rate(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    allowed = _register_limiter.try_acquire(client_ip, blocking=False)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later.",
        )


router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_check_register_rate)],
)
async def register(
    body: RegisterRequest,
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Register a new user and return access + refresh tokens.

    Cookie mode (``X-Auth-Mode: cookie``): the refresh token is set as an
    httpOnly cookie and the JSON body's ``refresh_token`` is empty. Body mode
    (default, used by the app): unchanged — both tokens in the body.
    """
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

    if is_cookie_mode(request):
        set_refresh_cookie(response, refresh_token)
        return TokenResponse(access_token=access_token, refresh_token="")

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(_check_login_rate)],
)
async def login(
    body: LoginRequest,
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Authenticate with email/password and receive tokens.

    Cookie mode sets the refresh token as an httpOnly cookie (empty in body);
    body mode (the default, used by the app) returns both tokens in the body.
    """
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

    if is_cookie_mode(request):
        set_refresh_cookie(response, refresh_token)
        return TokenResponse(access_token=access_token, refresh_token="")

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
) -> TokenResponse:
    """Rotate the refresh token and issue a new access token.

    Cookie mode reads the refresh token from the httpOnly cookie (the body is
    ignored / may be absent), rotates it, and sets the new cookie. Body mode
    reads ``body.refresh_token`` and returns both tokens — unchanged for the app.
    """
    cookie_mode = is_cookie_mode(request)
    if cookie_mode:
        raw_refresh = read_refresh_cookie(request) or ""
    else:
        raw_refresh = body.refresh_token if body else ""

    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        access_token, refresh_token = await auth_service.refresh(raw_refresh)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if cookie_mode:
        set_refresh_cookie(response, refresh_token)
        return TokenResponse(access_token=access_token, refresh_token="")

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
) -> MessageResponse:
    """Revoke the refresh token and, in cookie mode, clear the cookie."""
    if is_cookie_mode(request):
        raw_refresh = read_refresh_cookie(request) or ""
        if raw_refresh:
            await auth_service.logout(raw_refresh)
        clear_refresh_cookie(response)
        return MessageResponse(message="Logged out")

    await auth_service.logout(body.refresh_token if body else "")
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
