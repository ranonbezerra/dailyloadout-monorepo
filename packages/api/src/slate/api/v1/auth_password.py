"""Password recovery endpoints: forgot, reset, and change password.

Split out of ``auth.py`` to keep each router file focused (and under the
300-line cap). All three flows fail safe: ``forgot`` is neutral (no account
oracle), and password changes cut off every existing session.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from slate.api.v1._rate_limit import rate_limit
from slate.api.v1.auth_cookies import is_cookie_mode, set_refresh_cookie
from slate.config import settings
from slate.core.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from slate.deps import CurrentUserDep, PasswordRecoveryServiceDep

# Forgot-password emails are abuse-prone (email bombing); reuse the register cap.
# Fail-open is fine — it mints no account and the response is neutral regardless.
_check_forgot_rate = rate_limit(
    "auth_forgot_password",
    settings.rate_limit_register_per_minute,
    60,
    by="ip",
    times_key="rate_limit_register_per_minute",
)
# Reset/change verify a secret (token or current password) → brute-forceable.
# Reuse the login cap; fail-closed so a downed limiter can't open the gate.
_check_reset_rate = rate_limit(
    "auth_reset_password", settings.rate_limit_login_per_minute, 60, by="ip", fail_closed=True
)
_check_change_rate = rate_limit(
    "auth_change_password", settings.rate_limit_login_per_minute, 60, by="ip", fail_closed=True
)


router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(_check_forgot_rate)],
)
async def forgot_password(
    body: ForgotPasswordRequest,
    recovery_service: PasswordRecoveryServiceDep,
) -> MessageResponse:
    """Request a password-reset link. Response is neutral (no account oracle)."""
    await recovery_service.forgot_password(body.email)
    return MessageResponse(message="If the account exists, a reset email was sent.")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(_check_reset_rate)],
)
async def reset_password(
    body: ResetPasswordRequest,
    recovery_service: PasswordRecoveryServiceDep,
) -> MessageResponse:
    """Set a new password from a reset token, killing all existing sessions.

    The user must sign in again with the new password (no tokens are issued
    here — a reset link should not auto-authenticate).
    """
    try:
        await recovery_service.reset_password(body.token, body.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MessageResponse(message="Password reset. Please sign in with your new password.")


@router.post(
    "/change-password",
    response_model=TokenResponse,
    dependencies=[Depends(_check_change_rate)],
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUserDep,
    recovery_service: PasswordRecoveryServiceDep,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Change the authenticated user's password and reissue tokens.

    Verifies the current password, sets the new one, revokes every *other*
    session, and returns a fresh token pair so this device stays signed in.
    """
    try:
        access_token, refresh_token = await recovery_service.change_password(
            current_user,
            body.current_password,
            body.new_password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if is_cookie_mode(request):
        set_refresh_cookie(response, refresh_token)
        return TokenResponse(access_token=access_token, refresh_token="")

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
