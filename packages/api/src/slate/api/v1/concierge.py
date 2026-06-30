"""Backlog Concierge chat endpoint (Server-Sent Events).

Streams a turn as typed events as it is generated (ROADMAP Epic 16): ``token``
(prose, live), ``tool`` (a tool call starting/finishing), ``recommendation`` (a
*validated* pick), ``degrade`` (the pick failed the library guard), and a final
``done``. The trailing ``RECOMMEND`` marker is withheld and validated before any
recommendation reaches the client, so a non-existent game can never surface as a
real pick mid-stream.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from slate.api.v1._cost_guard import cost_guard
from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.concierge.schemas import ChatRequest
from slate.deps import RequireVerifiedUserDep
from slate.deps.concierge import ConciergeServiceDep

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/concierge", tags=["concierge"])

# Shown to the user when the agent fails (e.g. the model is unavailable). The
# real cause is logged server-side and never leaked over the wire.
_ERROR_MESSAGE = "The concierge is unavailable right now. Please try again in a moment."
_TIMEOUT_MESSAGE = "That took too long, so I stopped. Please try asking again."

# Hard ceiling on a single turn. A local multi-tool run is normally well under
# this; the timeout exists so a stalled/looping agent can never hang the stream.
_REPLY_TIMEOUT_SECONDS = 90.0


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post(
    "/chat",
    dependencies=[
        Depends(
            rate_limit(
                "concierge_chat",
                settings.rate_limit_concierge_chat_per_minute,
                60,
                by="user",
                fail_closed=True,
            )
        ),
        Depends(cost_guard("concierge")),
    ],
)
async def chat(
    body: ChatRequest,
    current_user: RequireVerifiedUserDep,
    concierge_service: ConciergeServiceDep,
) -> StreamingResponse:
    """Stream a guarded concierge reply as typed Server-Sent Events."""
    thread_id = body.thread_id or uuid4().hex

    async def event_stream() -> AsyncIterator[str]:
        try:
            async with asyncio.timeout(_REPLY_TIMEOUT_SECONDS):
                async for payload in concierge_service.reply_stream(
                    user_id=current_user.id,
                    user_created_at=current_user.created_at,
                    thread_id=thread_id,
                    message=body.message,
                ):
                    yield _sse(payload)
        except TimeoutError:
            # Bound the turn so a stalled/looping agent can't hang the stream.
            logger.warning(
                "concierge_reply_timeout",
                timeout_seconds=_REPLY_TIMEOUT_SECONDS,
                thread_id=thread_id,
            )
            yield _sse({"error": _TIMEOUT_MESSAGE})
        except asyncio.CancelledError:
            # Client disconnected mid-turn — let the cancellation propagate so
            # the agent run is torn down rather than left orphaned.
            logger.info("concierge_stream_cancelled", thread_id=thread_id)
            raise
        except Exception:
            # Never crash the stream — surface a clean error event instead of an
            # ASGI traceback (e.g. the LLM/model is unavailable).
            logger.exception("concierge_reply_failed", thread_id=thread_id)
            yield _sse({"error": _ERROR_MESSAGE})

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
