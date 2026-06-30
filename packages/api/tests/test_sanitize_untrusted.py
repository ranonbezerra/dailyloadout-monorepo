"""Tests for sanitize_untrusted_text — the free-text edge cleaner (Epic 26)."""

from __future__ import annotations

from slate.core.sanitization import sanitize_untrusted_text


class TestSanitizeUntrustedText:
    def test_keeps_plain_text(self) -> None:
        assert sanitize_untrusted_text("got Hollow Knight") == "got Hollow Knight"

    def test_keeps_newlines_and_tabs(self) -> None:
        # Multi-line free text is legitimate (a capture listing several games).
        assert sanitize_untrusted_text("Hollow Knight\nElden Ring") == "Hollow Knight\nElden Ring"

    def test_strips_control_chars(self) -> None:
        assert sanitize_untrusted_text("Doom\x00\x07 II") == "Doom II"

    def test_strips_bidi_and_zero_width(self) -> None:
        # RLO override (U+202E) + zero-width space (U+200B) — homoglyph/spoofing vectors.
        assert sanitize_untrusted_text("ab‮cd​ef") == "abcdef"

    def test_nfkc_normalises_fullwidth(self) -> None:
        # Fullwidth "Elden" (U+FF25…) collapses to ASCII (homoglyph evasion).
        assert sanitize_untrusted_text("Ｅｌｄｅｎ") == "Elden"  # noqa: RUF001

    def test_length_cap(self) -> None:
        assert len(sanitize_untrusted_text("a" * 5000, max_length=100)) == 100

    def test_strips_surrounding_whitespace(self) -> None:
        assert sanitize_untrusted_text("   spaced   ") == "spaced"

    def test_all_unsafe_collapses_to_empty(self) -> None:
        assert sanitize_untrusted_text("\x00\x01​") == ""
