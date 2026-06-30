"""Structured security/authentication log events."""

from __future__ import annotations

from hashlib import sha256

import structlog

from slate.infrastructure.db.models import User

logger = structlog.get_logger()


def _email_hash(email: str) -> str:
    normalized = email.strip().lower()
    return sha256(normalized.encode("utf-8")).hexdigest()[:16]


def register_rejected(email: str, *, reason: str) -> None:
    logger.warning("auth_register_rejected", reason=reason, email_hash=_email_hash(email))


def register_succeeded(user: User, *, auto_verified: bool) -> None:
    logger.info(
        "auth_register_succeeded",
        user_id=user.id,
        user_public_id=str(user.public_id),
        auto_verified=auto_verified,
    )


def login_failed(email: str) -> None:
    logger.warning(
        "auth_login_failed",
        reason="invalid_credentials",
        email_hash=_email_hash(email),
    )


def login_succeeded(user: User, *, device_label_present: bool) -> None:
    logger.info(
        "auth_login_succeeded",
        user_id=user.id,
        user_public_id=str(user.public_id),
        device_label_present=device_label_present,
    )


def refresh_rotated(user: User) -> None:
    logger.info(
        "auth_refresh_rotated",
        user_id=user.id,
        user_public_id=str(user.public_id),
    )


def logout(user_id: int) -> None:
    logger.info("auth_logout", user_id=user_id)


def sessions_revoked(user_id: int) -> None:
    logger.warning("auth_sessions_revoked", user_id=user_id)


def user_banned(user_id: int) -> None:
    logger.warning("auth_user_banned", user_id=user_id)


def refresh_token_benign_race(user_id: int) -> None:
    logger.info("refresh_token_benign_race", user_id=user_id)


def refresh_token_reuse_detected(user_id: int) -> None:
    logger.warning("refresh_token_reuse_detected", user_id=user_id)
