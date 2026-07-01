"""Email-change flow: re-auth → verify the new address → apply, notify the old one.

Changing the login email is a takeover-relevant action, so it is gated three ways:
1. **Re-auth** at request time (the account password; OAuth-only accounts are
   gated by the authenticated session).
2. **Proof of control of the new address** — nothing changes until the confirm
   link sent to the new email is opened (a signed, purpose-scoped token carrying
   the target address, so the confirm applies exactly what was requested).
3. **Notice to the old address** at request time, so a hijack is visible.

The token helpers live here (not ``security.py``, which is at its size budget) but
reuse that module's shared JWT config so issuer/audience/algorithm stay identical.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import PyJWTError

from slate.config import settings
from slate.core.auth.account import ReauthError
from slate.core.auth.security import _ALGORITHM, _DECODE_KW, _ISS_AUD, verify_password
from slate.infrastructure.db.models import User
from slate.infrastructure.db.repositories.user import UserRepository
from slate.infrastructure.email.mailer import (
    Mailer,
    get_mailer,
    send_email_change_notice,
    send_email_change_verification,
)
from slate.infrastructure.email.validation import assert_email_acceptable

_EMAIL_CHANGE_PURPOSE = "email_change"
_INVALID = "Invalid or expired email-change token"


def create_email_change_token(public_id: str, new_email: str) -> str:
    """Signed, purpose-scoped token confirming a change of *public_id*'s email."""
    now = datetime.now(UTC)
    payload = {
        "sub": public_id,
        "purpose": _EMAIL_CHANGE_PURPOSE,
        "new_email": new_email,
        "exp": now + timedelta(hours=settings.email_verification_ttl_hours),
        "iat": now,
        **_ISS_AUD,
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM))


def decode_email_change_token(token: str) -> tuple[str, str]:
    """Decode an email-change token → ``(public_id, new_email)``. Raises on bad token."""
    try:
        payload = jwt.decode(token, settings.secret_key, **_DECODE_KW)
    except PyJWTError as exc:
        raise ValueError(_INVALID) from exc
    subject = payload.get("sub")
    new_email = payload.get("new_email")
    if (
        payload.get("purpose") != _EMAIL_CHANGE_PURPOSE
        or not isinstance(subject, str)
        or not subject
        or not isinstance(new_email, str)
        or not new_email
    ):
        raise ValueError(_INVALID)
    return subject, new_email


class EmailChangeService:
    """Request + confirm a login-email change."""

    def __init__(self, user_repo: UserRepository, mailer: Mailer | None = None) -> None:
        self._user_repo = user_repo
        self._mailer = mailer or get_mailer()

    async def request_change(self, user: User, new_email: str, password: str) -> None:
        """Re-auth, validate the new address, and send the confirm + old-email notice."""
        if user.password_hash is not None:  # noqa: SIM102 — nested `if` narrows the type
            if not password or not verify_password(password, user.password_hash):
                raise ReauthError("Password is incorrect")
        if new_email.strip().lower() == user.email.lower():
            raise ValueError("That is already your email")
        await assert_email_acceptable(new_email)  # disposable / undeliverable gate
        if await self._user_repo.email_exists(new_email):
            raise ValueError("Email already in use")
        token = create_email_change_token(str(user.public_id), new_email)
        send_email_change_verification(self._mailer, to=new_email, token=token)
        send_email_change_notice(self._mailer, to=user.email)

    async def confirm_change(self, token: str) -> None:
        """Apply a confirmed change: set the new email (verified). Raises on any issue."""
        public_id_str, new_email = decode_email_change_token(token)
        try:
            public_id = UUID(public_id_str)
        except ValueError as exc:
            raise ValueError(_INVALID) from exc
        user = await self._user_repo.get_by_public_id(public_id)
        if user is None:
            raise ValueError(_INVALID)
        # Re-check availability: the address may have been taken since the request.
        if await self._user_repo.email_exists(new_email):
            raise ValueError("Email already in use")
        await self._user_repo.set_email(user, new_email)
