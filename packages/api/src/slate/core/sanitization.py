"""Input sanitization helpers shared across request schemas.

These guard user-supplied strings that later flow, unescaped, into LLM prompts
(concierge / recap) and the canonical catalog. Control characters and
newlines are the key prompt-injection vector — a title like
``"Doom\\n\\nIGNORE PREVIOUS INSTRUCTIONS"`` would otherwise be injected
verbatim into a prompt — so they are stripped/rejected at the edge.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

# Sentinel that delimits untrusted user/shared/library content inside an LLM
# prompt. Everything between the open and close tag is DATA, never instructions
# (the SYSTEM prompts state this rule explicitly). The wrapper neutralizes any
# attempt by the user to forge a closing tag and "break out" of the block.
USER_DATA_OPEN = "<user_data>"
USER_DATA_CLOSE = "</user_data>"

# Matches any case-variant / whitespace-padded forgery of the closing tag
# (e.g. ``</USER_DATA >`` or ``< / user_data >``) so a crafted title can't end
# the data block early and have the rest read as instructions.
_CLOSE_TAG_RE = re.compile(r"<\s*/\s*user_data\s*>", re.IGNORECASE)
_CLOSE_TAG_REPLACEMENT = "<​/user_data>"

# Control characters (C0 + DEL + C1) that must never survive into a prompt or
# the catalog. Tab/newline/CR are intentionally included: titles and slugs are
# single-line, so any newline is suspect.
_CONTROL_CHARS = frozenset(
    [*range(0x00, 0x20), 0x7F, *range(0x80, 0xA0)],
)


# Invisible/format characters outside the C0/C1 range that are never legitimate
# in a single-line display name: zero-width joiners/spaces, the BOM, and the
# Unicode bidi-override controls (LRO/RLO/PDF/LRI/RLI/FSI/PDI/LRM/RLM/ALM).
# These are the classic homoglyph / Trustwave-style "RLO spoofing" vectors —
# they let a name render as something other than its code points.
_INVISIBLE_FORMAT_CHARS = frozenset(
    {
        0x200B,  # zero-width space
        0x200C,  # zero-width non-joiner
        0x200D,  # zero-width joiner
        0x200E,  # left-to-right mark
        0x200F,  # right-to-left mark
        0x202A,  # left-to-right embedding
        0x202B,  # right-to-left embedding
        0x202C,  # pop directional formatting
        0x202D,  # left-to-right override
        0x202E,  # right-to-left override
        0x2060,  # word joiner
        0x2066,  # left-to-right isolate
        0x2067,  # right-to-left isolate
        0x2068,  # first strong isolate
        0x2069,  # pop directional isolate
        0x061C,  # arabic letter mark
        0xFEFF,  # zero-width no-break space / BOM
    }
)


def has_control_chars(value: str) -> bool:
    """Return True if *value* contains any control character (incl. newlines)."""
    return any(ord(ch) in _CONTROL_CHARS for ch in value)


def has_unsafe_format_chars(value: str) -> bool:
    """Return True if *value* contains control chars OR invisible/bidi formatters."""
    return any(ord(ch) in _CONTROL_CHARS or ord(ch) in _INVISIBLE_FORMAT_CHARS for ch in value)


def sanitize_display_name(value: str, *, field: str = "display_name") -> str:
    """Normalise + validate a user-set display name.

    1. NFKC-normalise so homoglyph/compatibility variants collapse to their
       canonical form (matching how catalog identifiers are handled), then trim
       surrounding whitespace.
    2. Reject any control character, newline, or invisible/bidi format character
       (zero-width, RLO/LRO, BOM, …) — the homoglyph-spoofing vector.
    3. Reject a name that is empty after normalisation/trim.

    Returns the cleaned value; raises ``ValueError`` on rejection.
    """
    normalized = unicodedata.normalize("NFKC", value).strip()
    if has_unsafe_format_chars(normalized):
        raise ValueError(f"{field} must not contain control, bidi, or zero-width characters.")
    if not normalized:
        raise ValueError(f"{field} must not be empty.")
    return normalized


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


def sanitize_catalog_text(value: str) -> str:
    """NFKC-normalise and DROP control/bidi/zero-width chars from catalog text.

    Non-raising cleaner for globally-visible manual catalogue fields (title,
    genres): once a manual game is promoted to the shared catalogue its text is
    shown to OTHER users, so a poisoned row must not carry homoglyph/RLO-bidi or
    control-char payloads. Unlike :func:`sanitize_display_name` this strips
    rather than rejects, so a borderline title still resolves to *something*.
    """
    normalized = unicodedata.normalize("NFKC", value)
    cleaned = "".join(
        ch
        for ch in normalized
        if ord(ch) not in _CONTROL_CHARS and ord(ch) not in _INVISIBLE_FORMAT_CHARS
    )
    return cleaned.strip()


def validate_https_url(value: str | None) -> str | None:
    """Return *value* only if it is a well-formed ``https://`` URL, else ``None``.

    For stored-but-not-fetched URLs (OAuth avatars): https-only nulls
    ``javascript:`` / ``data:`` / ``http:`` and malformed values before they are
    persisted or later rendered as an ``<img src>``.
    """
    if value is None:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    return value if parsed.scheme == "https" and parsed.hostname else None


def neutralize_close_sentinel(value: str) -> str:
    """Defang any forged ``</user_data>`` so the user can't escape the data block.

    A zero-width space is inserted after the ``<`` of every close-tag variant.
    The text stays human-readable to the model (it reads the same) but is no
    longer the literal sentinel the wrapper uses, so the block can't be ended
    early to smuggle in instructions.
    """
    return _CLOSE_TAG_RE.sub(_CLOSE_TAG_REPLACEMENT, value)


def wrap_user_data(value: object) -> str:
    """Wrap untrusted *value* in a delimited ``<user_data>`` block for prompts.

    All user/shared/library text interpolated into an LLM prompt MUST pass
    through here so the model can tell DATA from INSTRUCTIONS. The value is
    stringified, any forged closing sentinel is neutralized, and the result is
    fenced between the open/close tags. The SYSTEM prompts carry the standing
    rule that text inside this block is never to be obeyed as a directive.
    """
    text = "" if value is None else str(value)
    return f"{USER_DATA_OPEN}{neutralize_close_sentinel(text)}{USER_DATA_CLOSE}"
