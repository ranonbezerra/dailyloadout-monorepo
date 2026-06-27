"""Pydantic schemas for the backoffice admin surface."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminMeResponse(BaseModel):
    """The authenticated admin's identity — used by the backoffice to confirm
    that the current session holds admin rights before rendering the panel.
    """

    model_config = ConfigDict(from_attributes=True)

    public_id: UUID
    email: str
    display_name: str
