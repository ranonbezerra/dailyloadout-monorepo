"""Dependency-free HTML-to-text extraction for scraped research pages.

Not a full readability implementation — just enough to feed an LLM: drop
script/style/non-content tags, keep visible text, collapse whitespace. The LLM
tolerates the remaining noise.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_SKIP_TAGS = {"script", "style", "head", "noscript", "template", "svg"}
_BLOCK_TAGS = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section"}
_WS_RE = re.compile(r"[ \t\f\v]+")
_NL_RE = re.compile(r"\n{3,}")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._parts.append(_WS_RE.sub(" ", data))

    def text(self) -> str:
        joined = "".join(self._parts)
        lines = [line.strip() for line in joined.splitlines()]
        return _NL_RE.sub("\n\n", "\n".join(line for line in lines if line)).strip()


def extract_text(html: str, *, max_chars: int = 4000) -> str:
    """Extract visible text from *html*, truncated to *max_chars*."""
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except (ValueError, AssertionError):
        return ""
    return parser.text()[:max_chars]
