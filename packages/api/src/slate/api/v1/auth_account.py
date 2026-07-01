"""Account-lifecycle endpoints: data export, erasure (GDPR/LGPD), and email change.

Served under ``/v1/auth`` (a separate module from ``auth.py`` to keep each router
within the file-size budget). Destructive/sensitive actions re-authenticate with
the account password and are rate-limited so a stolen access token can't
brute-force the password through them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.auth.account import ReauthError
from slate.core.auth.schemas import (
    ChangeEmailRequest,
    ConfirmEmailChangeRequest,
    DeleteAccountRequest,
    MessageResponse,
)
from slate.deps.account import AccountServiceDep, EmailChangeServiceDep
from slate.deps.auth import CurrentUserDep
from slate.infrastructure.email.validation import EmailRejectedError

router = APIRouter(prefix="/v1/auth", tags=["auth"])

# Modest per-user cap: erasure re-auths with the password, so bound the attempts a
# hijacked session could use to guess it. Export is a heavier read — cap it too.
_delete_rate = Depends(rate_limit("auth_delete_account", 10, 60, by="user"))
_export_rate = Depends(
    rate_limit("auth_export", settings.rate_limit_read_per_minute, 60, by="user")
)
_change_email_rate = Depends(rate_limit("auth_change_email", 10, 60, by="user"))
_confirm_email_rate = Depends(
    rate_limit("auth_confirm_email_change", settings.rate_limit_register_per_minute, 60, by="ip")
)


@router.post(
    "/delete-account",
    response_model=MessageResponse,
    dependencies=[_delete_rate],
)
async def delete_account(
    current_user: CurrentUserDep,
    service: AccountServiceDep,
    body: DeleteAccountRequest,
) -> MessageResponse:
    """Permanently erase the caller's account after password re-authentication."""
    if settings.single_user_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deletion is disabled in single-user mode",
        )
    try:
        await service.delete_account(current_user, body.password)
    except ReauthError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return MessageResponse(message="Account permanently deleted")


@router.get("/me/export", dependencies=[_export_rate])
async def export_account(
    current_user: CurrentUserDep,
    service: AccountServiceDep,
) -> dict[str, object]:
    """Return the caller's personal data as a portable JSON document."""
    return await service.export_data(current_user)


@router.post(
    "/change-email",
    response_model=MessageResponse,
    dependencies=[_change_email_rate],
)
async def change_email(
    current_user: CurrentUserDep,
    service: EmailChangeServiceDep,
    body: ChangeEmailRequest,
) -> MessageResponse:
    """Request an email change: re-auth, then send a confirm link to the new address."""
    try:
        await service.request_change(current_user, body.new_email, body.password)
    except ReauthError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except EmailRejectedError as exc:  # disposable / undeliverable (a ValueError subclass)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except ValueError as exc:  # same email, or already in use
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageResponse(message="Check your new email to confirm the change")


@router.post(
    "/confirm-email-change",
    response_model=MessageResponse,
    dependencies=[_confirm_email_rate],
)
async def confirm_email_change(
    service: EmailChangeServiceDep,
    body: ConfirmEmailChangeRequest,
) -> MessageResponse:
    """Apply an email change from the signed confirm token (anonymous — token-gated)."""
    try:
        await service.confirm_change(body.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageResponse(message="Email updated")
