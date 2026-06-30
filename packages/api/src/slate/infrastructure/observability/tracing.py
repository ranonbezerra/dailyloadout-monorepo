"""Lightweight tracing for LLM calls and graph nodes (Epic 23, observability half).

A *span* is a named, timed unit of work with structured attributes (model, role,
tokens, latency, and — when enabled — a redacted prompt/completion preview).
Spans emit a structured log line and, when a trace is active (``start_trace``),
are collected for inspection. That capture is the substrate the eval harness and
a future judge-calibration set sample from.

Intentionally dependency-free (a ``structlog`` sink). The same ``span`` API can be
backed by an OpenTelemetry exporter later, behind ``otel_exporter_otlp_endpoint``,
without changing call sites.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class Span:
    """One timed unit of work and its structured attributes."""

    name: str
    attrs: dict[str, object] = field(default_factory=dict)
    duration_ms: float = 0.0


# The collecting trace (a list spans append to) and the currently-open span, both
# context-local so concurrent requests/graph runs never cross-contaminate.
_active_trace: ContextVar[list[Span] | None] = ContextVar("active_trace", default=None)
_current_span: ContextVar[Span | None] = ContextVar("current_span", default=None)


@contextmanager
def start_trace() -> Iterator[list[Span]]:
    """Begin a trace; spans opened within are collected into the yielded list."""
    spans: list[Span] = []
    token = _active_trace.set(spans)
    try:
        yield spans
    finally:
        _active_trace.reset(token)


def current_trace() -> list[Span] | None:
    """Return the active trace's span list, or ``None`` if none is active."""
    return _active_trace.get()


def add_span_attrs(**attrs: object) -> None:
    """Merge *attrs* into the currently-open span (no-op when there is none)."""
    span_ = _current_span.get()
    if span_ is not None:
        span_.attrs.update(attrs)


@asynccontextmanager
async def span(name: str, **attrs: object) -> AsyncIterator[Span]:
    """Open a timed span: record *attrs* + duration, then emit and collect it."""
    current = Span(name=name, attrs=dict(attrs))
    token = _current_span.set(current)
    start = time.monotonic()
    try:
        yield current
    finally:
        current.duration_ms = round((time.monotonic() - start) * 1000, 2)
        _current_span.reset(token)
        trace = _active_trace.get()
        if trace is not None:
            trace.append(current)
        logger.info("span", span=current.name, duration_ms=current.duration_ms, **current.attrs)


def redact(text: str, max_chars: int = 500) -> str:
    """Truncate text for safe capture (never persist unbounded user content)."""
    stripped = text.strip()
    return stripped if len(stripped) <= max_chars else stripped[:max_chars] + "…"
