"""Input sanitization helpers shared across request schemas.

These guard user-supplied strings that later flow, unescaped, into LLM prompts
(concierge / briefing) and the canonical catalog. Control characters and
newlines are the key prompt-injection vector — a title like
``"Doom\\n\\nIGNORE PREVIOUS INSTRUCTIONS"`` would otherwise be injected
verbatim into a prompt — so they are stripped/rejected at the edge.
"""

from __future__ import annotations

from urllib.parse import urlparse

# Control characters (C0 + DEL + C1) that must never survive into a prompt or
# the catalog. Tab/newline/CR are intentionally included: titles and slugs are
# single-line, so any newline is suspect.
_CONTROL_CHARS = frozenset(
    [*range(0x00, 0x20), 0x7F, *range(0x80, 0xA0)],
)


def has_control_chars(value: str) -> bool:
    """Return True if *value* contains any control character (incl. newlines)."""
    return any(ord(ch) in _CONTROL_CHARS for ch in value)


def reject_control_chars(value: str, *, field: str) -> str:
    """Reject *value* outright if it contains control characters.

    Used for single-line identifiers (title, slug) where a control character is
    never legitimate and almost always an injection attempt.
    """
    if has_control_chars(value):
        raise ValueError(f"{field} must not contain control characters or newlines.")
    return value


def strip_control_chars(value: str) -> str:
    """Drop control characters from *value*, collapsing them out silently.

    Used for free-text-ish fields (override titles) where we prefer to clean
    rather than reject the whole request.
    """
    return "".join(ch for ch in value if ord(ch) not in _CONTROL_CHARS)


def validate_cdn_url(value: str | None, allowed_hosts: list[str]) -> str | None:
    """Return *value* only if it is an ``https://`` URL on an allowed host.

    Anything else (http, a non-allowlisted host, a malformed URL) is nulled so
    poisoned cover URLs cannot reach the UI or an LLM prompt.
    """
    if value is None:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme != "https":
        return None
    if parsed.hostname not in allowed_hosts:
        return None
    return value
