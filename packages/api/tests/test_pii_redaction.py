"""PII redaction: clear PII masked, gaming numbers untouched (Epic 26)."""

from __future__ import annotations

import pytest

from slate.core.safety.pii import redact_pii


class TestRedactPii:
    @pytest.mark.parametrize(
        ("text", "needle"),
        [
            ("email me at player@example.com please", "[redacted-email]"),
            ("call +1 415 555 2671 tonight", "[redacted-phone]"),
            ("number (415) 555-2671 works", "[redacted-phone]"),
            ("card 4111 1111 1111 1111 on file", "[redacted-card]"),
        ],
    )
    def test_masks_pii(self, text: str, needle: str) -> None:
        assert needle in redact_pii(text)

    @pytest.mark.parametrize(
        "text",
        [
            "you're at level 99 in Final Fantasy 7",
            "played for 3 hours, year 2023",
            "Elden Ring, beat Margit at the gate",
            "got to chapter 12, save at slot 4",
            "Hollow Knight 1.5 update notes",
        ],
    )
    def test_keeps_gaming_numbers(self, text: str) -> None:
        # No false positives on the bare numbers gaming text is full of.
        assert redact_pii(text) == text

    def test_redacts_multiple(self) -> None:
        out = redact_pii("a@b.com and +44 20 7946 0958")
        assert "[redacted-email]" in out and "[redacted-phone]" in out
