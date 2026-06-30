"""Heuristic prompt-injection / jailbreak detection (Epic 26).

A small, **high-precision** pattern set for the obvious attempts against an
instruction-following model: instruction-override ("ignore previous instructions"),
role/mode jailbreaks, system-prompt exfiltration, data-fence escapes, and
chat-driven bulk tool abuse ("set every game to completed").

This deliberately is NOT a classifier and NOT the primary defense — the load-bearing
guard is the deterministic tool allowlist (a successful injection still can't drive
an unsafe write). Detection is cheap defense-in-depth: it flags the script-kiddie
attempts so the caller can block and log them. Precision over recall on purpose, so
a normal "mark this game as completed" chat turn is never tripped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# (label, pattern). Labels are stable — they're what gets logged/audited.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}"
            r"\b(previous|prior|earlier|above|all|any|your)\b[^.\n]{0,24}"
            r"\b(instruction|instructions|prompt|prompts|rule|rules|context|directive)",
            re.IGNORECASE,
        ),
    ),
    (
        "role_jailbreak",
        re.compile(
            r"\b(developer mode|jailbreak|do anything now|unfiltered mode|without restrictions)\b"
            r"|\bDAN\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_exfiltration",
        re.compile(
            r"\b(reveal|print|show|repeat|output|tell me)\b[^.\n]{0,30}"
            r"\b(system prompt|your instructions|your prompt|the prompt above|initial prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "new_instructions",
        re.compile(
            r"\bnew (instructions|rules|task|system prompt|directive)s?\s*:", re.IGNORECASE
        ),
    ),
    # A forged data-fence tag — sanitize_untrusted_text already defangs it, but the
    # attempt is a strong signal worth flagging/auditing.
    ("fence_escape", re.compile(r"</?\s*user_data\s*>", re.IGNORECASE)),
    (
        "bulk_tool_abuse",
        re.compile(
            r"\b(set|mark|change|update|move)\b[^.\n]{0,20}"
            r"\b(all|every|each|everything)\b[^.\n]{0,30}"
            r"\b(completed|dropped|paused|playing|backlog|status|games?)\b",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class InjectionVerdict:
    """Whether *text* looks like an injection, and which patterns it tripped."""

    flagged: bool
    matches: tuple[str, ...]


def detect_injection(text: str) -> InjectionVerdict:
    """Flag *text* if it matches a known injection / jailbreak pattern."""
    matches = tuple(label for label, pattern in _PATTERNS if pattern.search(text))
    return InjectionVerdict(flagged=bool(matches), matches=matches)
