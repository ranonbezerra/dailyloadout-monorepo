"""Request schemas for the Backlog Concierge chat endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """One chat turn. ``thread_id`` ties turns into a conversation; omit it on the
    first turn and reuse the value the server returns in the ``done`` event."""

    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: str | None = Field(None, max_length=64)
