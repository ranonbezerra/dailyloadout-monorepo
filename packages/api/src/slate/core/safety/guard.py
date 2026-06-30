"""Sanitize-and-audit untrusted free text in one call (Epic 26).

For flag-and-proceed surfaces (capture): sanitize the text and structured-log any
injection match, but don't block — the prompt fence (<user_data>) + strict JSON
output already bound the blast radius. Blocking surfaces (the Concierge) inspect the
verdict themselves to refuse the turn.
"""

from __future__ import annotations

import structlog

from slate.core.safety.injection import detect_injection
from slate.core.sanitization import sanitize_untrusted_text

_logger = structlog.get_logger()


def sanitize_and_audit(text: str, *, surface: str, **context: object) -> str:
    """Sanitize untrusted free text; log (not block) any injection match. Returns clean text."""
    clean = sanitize_untrusted_text(text)
    verdict = detect_injection(clean)
    if verdict.flagged:
        _logger.warning(
            "injection_flagged", surface=surface, matches=list(verdict.matches), **context
        )
    return clean
