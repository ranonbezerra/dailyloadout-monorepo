"""Observability: structured logs, Sentry, and lightweight tracing."""

from slate.infrastructure.observability.jobs import job_context
from slate.infrastructure.observability.logging import configure_logging
from slate.infrastructure.observability.sentry import init_sentry
from slate.infrastructure.observability.tracing import (
    Span,
    add_span_attrs,
    current_trace,
    redact,
    span,
    start_trace,
)

__all__ = [
    "Span",
    "add_span_attrs",
    "configure_logging",
    "current_trace",
    "init_sentry",
    "job_context",
    "redact",
    "span",
    "start_trace",
]
