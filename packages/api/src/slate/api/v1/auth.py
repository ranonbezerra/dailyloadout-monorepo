"""Auth API endpoints: register, login, refresh, logout, me."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from slate.api.v1._rate_limit import account_email_identity, account_rate_limit, rate_limit
from slate.api.v1.auth_cookies import (
    clear_refresh_cookie,
    is_cookie_mode,
    read_refresh_cookie,
    set_refresh_cookie,
)
from slate.config import settings
from slate.core.auth import login_stepup
from slate.core.auth.breach import BreachedPasswordError
from slate.core.auth.schemas import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from slate.core.auth.security import create_mfa_challenge_token
from slate.core.auth.service import EmailRejectedError
from slate.deps import AuthServiceDep, CurrentUserDep, MfaServiceDep
from slate.deps.captcha import verify_turnstile

# Per-IP limiters (Redis-backed, fail-open); no-op'd in tests via conftest.
_check_login_rate = rate_limit(
    "auth_login", settings.rate_limit_login_per_minute, 60, by="ip", fail_closed=True
)
# Per-account backstop: caps attempts against a single email regardless of how
# many source IPs an attacker rotates through (credential stuffing).
_check_login_account_rate = account_rate_limit(
    "auth_login_acct", settings.rate_limit_login_per_minute, 60, account_email_identity
)
_check_register_rate = rate_limit(
    "auth_register",
    settings.rate_limit_register_per_minute,
    60,
    by="ip",
    fail_closed=True,
    times_key="rate_limit_register_per_minute",
)
# Resend-verification: per-IP cap (email-bombing), fail-open (no account mint).
_check_resend_rate = rate_limit(
    "auth_resend_verification",
    settings.rate_limit_register_per_minute,
    60,
    by="ip",
    times_key="rate_limit_register_per_minute",
)
# Per-account backstop on register (fail-closed): the per-target axis login has.
_check_register_account_rate = account_rate_limit(
    "auth_register_acct",
    settings.rate_limit_register_per_minute,
    60,
    account_email_identity,
    times_key="rate_limit_register_per_minute",
)
# Email-verify: anonymous DB read/write, cap per-IP (fail-open — token is signed).
_check_verify_rate = rate_limit(
    "auth_verify_email",
    settings.rate_limit_register_per_minute,
    60,
    by="ip",
    times_key="rate_limit_register_per_minute",
)


router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(_check_register_rate),
        Depends(_check_register_account_rate),
        Depends(verify_turnstile),
    ],
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
    except (EmailRejectedError, BreachedPasswordError) as exc:
        # Bad email or breached password → 422 (invalid input), never a 409 oracle.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
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
    response_model=LoginResponse,
    dependencies=[Depends(_check_login_rate), Depends(_check_login_account_rate)],
)
async def login(
    body: LoginRequest,
    auth_service: AuthServiceDep,
    mfa_service: MfaServiceDep,
    request: Request,
    response: Response,
) -> LoginResponse:
    """Authenticate with email/password.

    MFA-enabled accounts get ``mfa_required`` + a short-lived ``mfa_token`` (no
    session) to exchange at ``/mfa/login``. After repeated failures on the account,
    a Turnstile step-up is required. Cookie mode sets the httpOnly refresh cookie;
    body mode returns both tokens.
    """
    # Step-up: once an account has too many recent failures, gate login on a CAPTCHA
    # (verify_turnstile is a no-op when Turnstile isn't configured — dev/tests).
    if await login_stepup.login_stepup_required(body.email):
        await verify_turnstile(request)
    try:
        user = await auth_service.verify_credentials(body.email, body.password)
    except ValueError as exc:
        await login_stepup.record_login_failure(body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    await login_stepup.reset_login_failures(body.email)

    if await mfa_service.is_enabled(user.id):
        challenge = create_mfa_challenge_token(str(user.public_id), user.token_version)
        return LoginResponse(mfa_required=True, mfa_token=challenge)

    access_token, refresh_token = await auth_service.issue_tokens(user)
    if is_cookie_mode(request):
        set_refresh_cookie(response, refresh_token)
        return LoginResponse(access_token=access_token)

    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/verify",
    response_model=MessageResponse,
    dependencies=[Depends(_check_verify_rate)],
)
async def verify_email(
    auth_service: AuthServiceDep,
    body: VerifyEmailRequest | None = None,
    token: str = Query(default=""),
) -> MessageResponse:
    """Verify an email address from a signed token (body or query).

    Idempotent: an already-verified account still returns 200. An
    expired/invalid/missing token returns 400.
    """
    raw_token = (body.token if body else "") or token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token is required",
        )
    try:
        await auth_service.verify_email(raw_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MessageResponse(message="Email verified")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    dependencies=[Depends(_check_resend_rate)],
)
async def resend_verification(
    body: ResendVerificationRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """Re-send a verification email. Response is neutral (no account oracle)."""
    await auth_service.resend_verification(body.email)
    return MessageResponse(message="If the account exists, a verification email was sent.")


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


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    auth_service: AuthServiceDep,
    current_user: CurrentUserDep,
    response: Response,
    request: Request,
) -> MessageResponse:
    """Log out everywhere: revoke all refresh tokens and kill all access tokens.

    Bumps the user's ``token_version`` (instantly invalidating every outstanding
    access token, including the one used for this request) and revokes every
    refresh token. In cookie mode the local refresh cookie is also cleared.
    """
    await auth_service.revoke_all_sessions(current_user.id)
    if is_cookie_mode(request):
        clear_refresh_cookie(response)
    return MessageResponse(message="Logged out everywhere")


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
