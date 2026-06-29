"""Streaming protocol for the Backlog Concierge (ROADMAP Epic 16).

Two concerns live here:

* the typed events an agent emits while a turn streams (`TokenEvent`,
  `ToolEvent`), and
* the `RecommendationGate` — the filter that lets prose tokens through live but
  **withholds the trailing ``RECOMMEND: <id>`` marker** until the turn ends, so
  the UUID guard can validate the pick before it ever reaches the user.

The marker is a line of the form ``RECOMMEND: <library_entry id>``. Both the
agent prompt and the service guard depend on this shape, so the regex and the
split helper live here, shared.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Marker the model appends when recommending one game. Matched at a line start.
_MARKER = "recommend:"
_RECOMMEND_RE = re.compile(r"^\s*RECOMMEND:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)
# A (possibly still-forming) marker line anywhere in the buffer.
_MARKER_LINE_RE = re.compile(r"(?im)^[ \t]*recommend:.*$")


@dataclass
class TokenEvent:
    """A chunk of user-facing prose to append live."""

    text: str


@dataclass
class ToolEvent:
    """A tool call starting or finishing — surfaced as a chat affordance."""

    name: str
    phase: str  # "start" | "end"


ConciergeEvent = TokenEvent | ToolEvent


def split_recommendation(text: str) -> tuple[str, str | None]:
    """Return (prose without the RECOMMEND marker, recommended id or None)."""
    match = _RECOMMEND_RE.search(text)
    rec_id = match.group(1) if match else None
    prose = _RECOMMEND_RE.sub("", text).strip()
    return prose, rec_id


def _could_be_marker(stripped_line: str) -> bool:
    """True if a line (already left-stripped) might still become the marker."""
    lowered = stripped_line.lower()
    return _MARKER.startswith(lowered) or lowered.startswith(_MARKER)


class RecommendationGate:
    """Forwards prose tokens but holds back a forming/complete RECOMMEND tail.

    Feed raw text deltas; ``feed`` returns the slice that is safe to emit now
    (guaranteed prose). ``finish`` flushes any remaining prose and returns the
    parsed recommendation id, which the caller validates before surfacing.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._emitted = 0

    def feed(self, delta: str) -> str:
        """Append *delta*; return the newly-safe prose to stream (may be "")."""
        self._buffer += delta
        safe = max(self._emitted, self._safe_index())
        out = self._buffer[self._emitted : safe]
        self._emitted = safe
        return out

    def finish(self) -> tuple[str, str | None]:
        """Return (trailing prose not yet emitted, recommendation id or None)."""
        prose, rec_id = split_recommendation(self._buffer)
        already = self._buffer[: self._emitted]
        # The clean prose minus what we already streamed; rstrip the dangling
        # newline that separated prose from the withheld marker.
        tail = prose[len(already.rstrip()) :] if prose.startswith(already.rstrip()) else ""
        return tail, rec_id

    def _safe_index(self) -> int:
        buf = self._buffer
        marker = _MARKER_LINE_RE.search(buf)
        if marker:
            return marker.start()  # hold from the marker line start
        line_start = buf.rfind("\n") + 1
        if _could_be_marker(buf[line_start:].lstrip()):
            return line_start  # the final line might still become the marker
        return len(buf)
