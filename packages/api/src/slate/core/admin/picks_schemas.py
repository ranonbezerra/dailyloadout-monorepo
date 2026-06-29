"""Pydantic schemas for the backoffice picks (read-only) surface.

Split out of ``core/admin/schemas.py`` to keep that module within the 300-line
file budget as the backoffice grows; new admin domains add their schemas in a
sibling module like this one.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminPickSummary(BaseModel):
    """A pick suggestion as shown in the backoffice read-only table."""

    public_id: UUID
    user_email: str | None
    game_title: str | None
    action: str
    mood: str
    available_minutes: int
    mental_energy: str
    created_at: datetime


class PickActionCount(BaseModel):
    """A single ``(action, count)`` tally for the picks overview."""

    action: str
    count: int


class AdminPickList(BaseModel):
    """A page of picks plus the total count and per-action tallies."""

    items: list[AdminPickSummary]
    total: int
    limit: int
    offset: int
    action_counts: list[PickActionCount]


class AdminPickDetail(AdminPickSummary):
    """The full backoffice view of one pick suggestion.

    ``led_to_play_session`` reports whether the user accepted the pick into a play_session
    (the pick's ``play_session_id`` is set).
    """

    platform_label: str | None
    context: str | None
    reasoning: str | None
    led_to_play_session: bool
