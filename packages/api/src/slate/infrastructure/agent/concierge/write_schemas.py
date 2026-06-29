"""LLM-facing argument schemas for the Concierge write tools (ROADMAP Epic 12).

Split out from ``tools_write.py`` to keep that module focused on behaviour. Each
schema describes one write tool's arguments for the model's function-calling.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StartPlaySessionArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    recap: str = Field(
        "none",
        description="'quick' to start with a short recap, or 'none' to start without one.",
    )


class GenerateRecapArgs(BaseModel):
    mode: str = Field(
        "quick",
        description="'quick' for a fast recap, or 'deep' for web-researched (slower).",
    )


class RetroactiveWrapUpArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    wrap_up_text: str = Field(
        ..., description="What the player did in their past, untracked session."
    )


class SetStatusArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    status: str = Field(
        ...,
        description="New status: backlog, playing, paused, completed, or dropped.",
    )
