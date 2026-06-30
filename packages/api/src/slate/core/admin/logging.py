"""Structured operational logs for audited backoffice mutations."""

from __future__ import annotations

from uuid import UUID

import structlog

from slate.infrastructure.db.models import User

logger = structlog.get_logger()


def log_admin_event(
    event: str,
    *,
    actor: User,
    action: str,
    target_user: User | None = None,
    target_user_id: int | None = None,
    target_public_id: UUID | None = None,
    resource_type: str | None = None,
    resource_public_id: UUID | None = None,
    **fields: object,
) -> None:
    payload = {
        "admin_user_id": actor.id,
        "admin_public_id": str(actor.public_id),
        "admin_action": action,
        **fields,
    }
    if target_user is not None:
        payload["target_user_id"] = target_user.id
        payload["target_public_id"] = str(target_user.public_id)
    elif target_user_id is not None:
        payload["target_user_id"] = target_user_id
    if target_public_id is not None:
        payload["target_public_id"] = str(target_public_id)
    if resource_type is not None:
        payload["resource_type"] = resource_type
    if resource_public_id is not None:
        payload["resource_public_id"] = str(resource_public_id)
    logger.warning(event, **payload)
