"""LLM-facing argument schemas for the Concierge write tools (ROADMAP Epic 12).

Split out from ``tools_write.py`` to keep that module focused on behaviour. Each
schema describes one write tool's arguments for the model's function-calling.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StartMissionArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    briefing: str = Field(
        "none",
        description="'quick' to start with a short briefing, or 'none' to start without one.",
    )


class GenerateBriefingArgs(BaseModel):
    mode: str = Field(
        "quick",
        description="'quick' for a fast briefing, or 'deep' for web-researched (slower).",
    )


class RetroactiveDebriefArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    debrief_text: str = Field(
        ..., description="What the player did in their past, untracked session."
    )


class SetStatusArgs(BaseModel):
    library_entry_public_id: str = Field(..., description="The game's id (from search_library).")
    status: str = Field(
        ...,
        description="New status: backlog, playing, paused, completed, or dropped.",
    )
