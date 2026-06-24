"""Backlog Concierge chat endpoint (Server-Sent Events).

v1 streams the *guarded* answer: the service runs the agent to completion and
validates any recommendation, then this endpoint chunks the final text over SSE.
Token-level streaming with an in-stream guard is a later epic (ROADMAP Epic 16).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from dailyloadout.core.concierge.schemas import ChatRequest
from dailyloadout.deps import CurrentUserDep
from dailyloadout.deps.concierge import ConciergeServiceDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/concierge", tags=["concierge"])

# Shown to the user when the agent fails (e.g. the model is unavailable). The
# real cause is logged server-side and never leaked over the wire.
_ERROR_MESSAGE = "The concierge is unavailable right now. Please try again in a moment."
_TIMEOUT_MESSAGE = "That took too long, so I stopped. Please try asking again."

# Hard ceiling on a single turn. A local multi-tool run is normally well under
# this; the timeout exists so a stalled/looping agent can never hang the stream
# (which would otherwise wedge the client's loading state indefinitely).
_REPLY_TIMEOUT_SECONDS = 90.0


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _word_chunks(text: str) -> list[str]:
    """Split into word-sized chunks (spaces preserved) for a typing effect."""
    if not text:
        return []
    words = text.split(" ")
    return [w if i == len(words) - 1 else w + " " for i, w in enumerate(words)]


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: CurrentUserDep,
    concierge_service: ConciergeServiceDep,
) -> StreamingResponse:
    """Stream a guarded concierge reply as Server-Sent Events."""
    thread_id = body.thread_id or uuid4().hex

    async def event_stream() -> AsyncIterator[str]:
        try:
            text = await asyncio.wait_for(
                concierge_service.reply(
                    user_id=current_user.id,
                    user_created_at=current_user.created_at,
                    thread_id=thread_id,
                    message=body.message,
                ),
                timeout=_REPLY_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            # Bound the turn so a stalled/looping agent can't hang the stream.
            logger.warning(
                "Concierge reply timed out after %ss (thread %s)",
                _REPLY_TIMEOUT_SECONDS,
                thread_id,
            )
            yield _sse({"error": _TIMEOUT_MESSAGE})
            yield _sse({"done": True, "thread_id": thread_id})
            return
        except Exception:
            # Never crash the stream — surface a clean error event instead of an
            # ASGI traceback (e.g. the LLM/model is unavailable).
            logger.exception("Concierge reply failed for thread %s", thread_id)
            yield _sse({"error": _ERROR_MESSAGE})
            yield _sse({"done": True, "thread_id": thread_id})
            return

        for chunk in _word_chunks(text):
            yield _sse({"delta": chunk})
        yield _sse({"done": True, "thread_id": thread_id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering so chunks flush
        },
    )
