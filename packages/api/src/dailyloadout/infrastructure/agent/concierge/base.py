"""Port for the Backlog Concierge chat agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from pydantic import BaseModel

from .streaming import ConciergeEvent, TokenEvent


@dataclass
class ConciergeTool:
    """A read-only tool the agent may call.

    ``coroutine`` already has the user/repos bound; it accepts only the
    LLM-facing arguments described by ``args_schema`` and returns text.
    """

    name: str
    description: str
    args_schema: type[BaseModel]
    coroutine: Callable[..., Awaitable[str]]


@dataclass
class ConciergeRequest:
    """One chat turn. ``tools`` are built per-request, scoped to the user."""

    thread_id: str
    message: str
    system: str
    tools: list[ConciergeTool]


@dataclass
class ConciergeReply:
    """The agent's raw answer for a turn (before the UUID guard runs)."""

    text: str


class AbstractConciergeAgent(ABC):
    """Contract for the conversational, tool-using backlog agent."""

    @abstractmethod
    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        """Run the tool-using loop for one turn and return the answer text."""
        ...

    async def astream(self, req: ConciergeRequest) -> AsyncIterator[ConciergeEvent]:
        """Stream one turn as typed events (prose tokens + tool calls).

        Emits ``TokenEvent`` for answer prose and ``ToolEvent`` for tool
        start/end. The caller runs the prose through the recommendation gate
        and validates any pick before surfacing it (ROADMAP Epic 16).

        Default: fall back to the buffered ``respond`` and emit the whole answer
        as one token, so agents that only implement ``respond`` still stream
        (just not token-by-token). Real agents override this.
        """
        reply = await self.respond(req)
        yield TokenEvent(text=reply.text)
