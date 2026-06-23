"""Anti-hallucination validator for LLM-generated briefings.

Extracts "interesting tokens" (proper nouns and numbers) from the LLM
output and verifies that at least 40% of them also appear in the input
context.  If not, the briefing is flagged as suspicious.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

# Tokens shorter than this are ignored (articles, prepositions, etc.).
_MIN_TOKEN_LENGTH = 3

# Threshold: fraction of output tokens that must appear in the input.
# Set lower (0.40) because the briefing prompt encourages the LLM to
# reference real game areas/zones the player hasn't explicitly mentioned.
_OVERLAP_THRESHOLD = 0.40

# Pattern for "interesting" tokens: capitalised words or numbers.
_INTERESTING_RE = re.compile(r"\b(?:[A-Z][a-z]{2,}|[A-Z]{2,}|\d+)\b")


@dataclass
class ValidationResult:
    """Result of anti-hallucination check."""

    is_suspicious: bool
    overlap_ratio: float
    missing_tokens: list[str]


def validate_briefing(briefing_text: str, context_text: str) -> ValidationResult:
    """Check whether *briefing_text* is grounded in *context_text*.

    Returns a ``ValidationResult`` indicating whether the briefing is
    suspicious and which tokens from the output are not present in the
    input context.
    """
    output_tokens = set(_INTERESTING_RE.findall(briefing_text))
    if not output_tokens:
        # Nothing to validate — the briefing has no proper nouns or numbers.
        return ValidationResult(is_suspicious=False, overlap_ratio=1.0, missing_tokens=[])

    # Build the set of tokens present in the context.
    context_tokens = set(_INTERESTING_RE.findall(context_text))
    # Also include lowercase versions for case-insensitive matching.
    context_lower = {t.lower() for t in context_tokens}

    missing: list[str] = []
    for token in output_tokens:
        if token not in context_tokens and token.lower() not in context_lower:
            missing.append(token)

    overlap_count = len(output_tokens) - len(missing)
    overlap_ratio = overlap_count / len(output_tokens) if output_tokens else 1.0

    is_suspicious = overlap_ratio < _OVERLAP_THRESHOLD

    if is_suspicious:
        logger.warning(
            "suspicious_briefing",
            overlap_ratio=round(overlap_ratio, 2),
            missing_tokens=missing[:10],
        )

    return ValidationResult(
        is_suspicious=is_suspicious,
        overlap_ratio=round(overlap_ratio, 4),
        missing_tokens=missing,
    )
