"""PII scan + redaction for model output echoed back to the user (Epic 26).

A conservative, high-precision redactor for the few PII shapes a chat reply might
echo — emails, formatted phone numbers, 16-digit card numbers. Conservative on
purpose: gaming text is full of bare numbers ("level 99", "Final Fantasy 7",
"played 3 hours"), so only *clearly-formatted* PII is masked, never a lone integer.
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")

# A phone number needs ≥3 digit-groups (so ~8+ digits) with explicit separators,
# optionally a + country code — enough to exclude "level 99" / "year 2023".
_PHONE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})(?:[\s.-]\d{2,4}){2,}(?!\w)"
)

# 16 digits in four separated groups — a card number, not a score.
_CARD = re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b")

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_EMAIL, "[redacted-email]"),
    (_CARD, "[redacted-card]"),
    (_PHONE, "[redacted-phone]"),
)


def redact_pii(text: str) -> str:
    """Mask emails, formatted phone numbers, and card numbers in *text*."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text
