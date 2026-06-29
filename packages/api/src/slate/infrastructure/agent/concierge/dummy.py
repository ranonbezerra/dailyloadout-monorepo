"""Deterministic Concierge agent for tests and offline development.

Exercises the tool path (calls search_library) and emits a recommendation using
a real library id, so the service's UUID guard runs against real data without a
model. Include ``[invalid]`` in the message to force an out-of-library id and
exercise the reroll/degrade path.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

from .base import AbstractConciergeAgent, ConciergeReply, ConciergeRequest
from .streaming import ConciergeEvent, TokenEvent, ToolEvent

_ID_RE = re.compile(r"id:\s*([0-9a-fA-F-]{36})")
_FAKE_ID = "00000000-0000-0000-0000-000000000000"


class DummyConciergeAgent(AbstractConciergeAgent):
    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        listing = await self._search(req)
        return ConciergeReply(text=self._answer(req, listing))

    async def astream(self, req: ConciergeRequest) -> AsyncIterator[ConciergeEvent]:
        # Exercise the tool affordance + token streaming + the gate: a tool
        # call, then the answer (incl. the RECOMMEND tail) word by word.
        yield ToolEvent(name="search_library", phase="start")
        listing = await self._search(req)
        yield ToolEvent(name="search_library", phase="end")
        for chunk in _word_chunks(self._answer(req, listing)):
            yield TokenEvent(text=chunk)

    async def _search(self, req: ConciergeRequest) -> str:
        for tool in req.tools:
            if tool.name == "search_library":
                return await tool.coroutine()
        return ""

    def _answer(self, req: ConciergeRequest, listing: str) -> str:
        if "[invalid]" in req.message.lower():
            return f"You should jump back into that one.\nRECOMMEND: {_FAKE_ID}"
        match = _ID_RE.search(listing)
        if match:
            return (
                "Based on your library and the time you have, give this a go.\n"
                f"RECOMMEND: {match.group(1)}"
            )
        return "I couldn't find anything in your library to suggest right now."


def _word_chunks(text: str) -> list[str]:
    words = text.split(" ")
    return [w if i == len(words) - 1 else w + " " for i, w in enumerate(words)]
