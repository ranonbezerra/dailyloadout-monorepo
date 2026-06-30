"""MFA (TOTP) endpoints: enroll, confirm, recovery codes, disable, status, login.

Enrollment/management endpoints are authenticated. ``/mfa/login`` is the public
second step of a two-factor sign-in: it exchanges a short-lived challenge token
(from ``/v1/auth/login``) plus a code for real session tokens. Endpoints that
verify a secret (code) are rate-limited fail-closed.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from slate.api.v1._rate_limit import rate_limit
from slate.api.v1.auth_cookies import is_cookie_mode, set_refresh_cookie
from slate.config import settings
from slate.core.auth.schemas import (
    LoginResponse,
    MessageResponse,
    MfaCodeRequest,
    MfaEnrollResponse,
    MfaLoginRequest,
    MfaRecoveryCodesResponse,
    MfaStatusResponse,
)
from slate.core.auth.security import decode_mfa_challenge_token
from slate.deps import AuthServiceDep, CurrentUserDep, MfaServiceDep

# Code-verifying endpoints are brute-forceable → reuse the login cap, fail-closed.
_check_mfa_login_rate = rate_limit(
    "auth_mfa_login", settings.rate_limit_login_per_minute, 60, by="ip", fail_closed=True
)
_check_mfa_verify_rate = rate_limit(
    "auth_mfa_verify", settings.rate_limit_login_per_minute, 60, by="ip", fail_closed=True
)

router = APIRouter(prefix="/v1/auth/mfa", tags=["auth"])


@router.get("/status", response_model=MfaStatusResponse)
async def mfa_status(
    current_user: CurrentUserDep,
    mfa_service: MfaServiceDep,
) -> MfaStatusResponse:
    """Report whether MFA is enabled and how many recovery codes remain."""
    enabled, remaining = await mfa_service.status(current_user.id)
    return MfaStatusResponse(enabled=enabled, recovery_codes_remaining=remaining)


@router.post("/enroll", response_model=MfaEnrollResponse)
async def mfa_enroll(
    current_user: CurrentUserDep,
    mfa_service: MfaServiceDep,
) -> MfaEnrollResponse:
    """Begin enrollment: return a fresh secret + otpauth URI (QR) to scan.

    Not yet active — the user must confirm with a code via ``/mfa/confirm``.
    """
    try:
        secret, uri = await mfa_service.start_enrollment(current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return MfaEnrollResponse(secret=secret, otpauth_uri=uri)


@router.post(
    "/confirm",
    response_model=MfaRecoveryCodesResponse,
    dependencies=[Depends(_check_mfa_verify_rate)],
)
async def mfa_confirm(
    body: MfaCodeRequest,
    current_user: CurrentUserDep,
    mfa_service: MfaServiceDep,
) -> MfaRecoveryCodesResponse:
    """Confirm enrollment with a code; activate MFA and return recovery codes.

    The recovery codes are shown exactly once — only their hashes are stored.
    """
    try:
        codes = await mfa_service.confirm_enrollment(current_user, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MfaRecoveryCodesResponse(recovery_codes=codes)


@router.post(
    "/recovery-codes",
    response_model=MfaRecoveryCodesResponse,
    dependencies=[Depends(_check_mfa_verify_rate)],
)
async def mfa_regenerate_recovery_codes(
    body: MfaCodeRequest,
    current_user: CurrentUserDep,
    mfa_service: MfaServiceDep,
) -> MfaRecoveryCodesResponse:
    """Replace the recovery-code set after verifying a current factor."""
    try:
        codes = await mfa_service.regenerate_recovery_codes(current_user, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MfaRecoveryCodesResponse(recovery_codes=codes)


@router.post(
    "/disable",
    response_model=MessageResponse,
    dependencies=[Depends(_check_mfa_verify_rate)],
)
async def mfa_disable(
    body: MfaCodeRequest,
    current_user: CurrentUserDep,
    mfa_service: MfaServiceDep,
) -> MessageResponse:
    """Disable MFA after verifying a current TOTP or recovery code."""
    try:
        await mfa_service.disable(current_user, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageResponse(message="MFA disabled")


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(_check_mfa_login_rate)],
)
async def mfa_login(
    body: MfaLoginRequest,
    auth_service: AuthServiceDep,
    mfa_service: MfaServiceDep,
    request: Request,
    response: Response,
) -> LoginResponse:
    """Complete a two-factor sign-in: challenge token + code → session tokens."""
    try:
        public_id_str, token_version = decode_mfa_challenge_token(body.mfa_token)
        user = await auth_service.get_current_user(UUID(public_id_str))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    # A password change / logout-everywhere since the challenge was issued bumps
    # token_version → the pending challenge is stale and must be rejected.
    if user.token_version != token_version or not await mfa_service.verify_challenge(
        user.id, body.code
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA challenge",
        )

    access_token, refresh_token = await auth_service.issue_tokens(user)
    if is_cookie_mode(request):
        set_refresh_cookie(response, refresh_token)
        return LoginResponse(access_token=access_token)
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)
