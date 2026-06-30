"""Deterministic eval checks — run first, free, and not model-graded.

These encode the correctness properties we can verify without a judge: output is
non-empty, grounded in its context (stopword-aware token overlap), spoiler-free,
valid JSON, and (for picks) references a real candidate. The LLM-as-judge only
scores what determinism can't.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from evals.schema import CheckResult, EvalCase

# "Interesting" tokens for grounding: capitalised words or numbers — the things a
# recap can hallucinate. Same idea as the Epic 6 anti-hallucination guard, but as
# an *eval metric* it must be cleaner than that binary runtime guard.
_INTERESTING_RE = re.compile(r"\b(?:[A-Z][a-z]{2,}|[A-Z]{2,}|\d+)\b")

# Capitalised COMMON words that are not proper nouns — they fire on the regex when
# they start a sentence ("Welcome", "You", "Head", "Previously") and silently sink
# the overlap ratio even when nothing was invented. Excluded so grounding reflects
# real entities, not boilerplate. (The production guard keeps its simpler heuristic;
# this divergence is intentional and eval-only.)
_GROUNDING_STOPWORDS = frozenset(
    {
        "the",
        "you",
        "your",
        "yours",
        "this",
        "that",
        "these",
        "those",
        "what",
        "when",
        "where",
        "while",
        "with",
        "from",
        "into",
        "then",
        "there",
        "here",
        "now",
        "next",
        "also",
        "still",
        "welcome",
        "head",
        "begin",
        "continue",
        "focus",
        "last",
        "get",
        "consider",
        "keep",
        "try",
        "note",
        "explore",
        "previously",
        "look",
        "find",
        "return",
        "make",
        "take",
        "check",
        "remember",
        "and",
        "but",
        "for",
        "back",
    }
)


def _ref_str(case: EvalCase, key: str) -> str:
    value = case.reference.get(key, "")
    return value if isinstance(value, str) else str(value)


def _singular(word: str) -> str:
    """Naive plural→singular: drop a trailing 's' so 'Terminids' == 'Terminid'.

    Guards keep 'ss' words (boss, grass) and very short words intact. Just enough
    to stop morphological variants from being false negatives — not a real stemmer.
    """
    w = word.lower()
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _mentioned(term: str, text_lower: str) -> bool:
    """True if *term* appears in *text_lower* on word boundaries (plural-tolerant).

    Word-boundary match (not substring) so a short term never fires inside a longer
    word ('ending' not on 'depending', 'camp' not on 'campaign'), but the singular
    stem + an optional trailing 's' is allowed so 'Terminids' matches 'Terminid'.
    """
    return re.search(rf"\b{re.escape(_singular(term))}s?\b", text_lower) is not None


# Lowercase the first letter-led word of each line/sentence — it is capitalised by
# grammar, not because it's a proper noun ('Carefully', 'Welcome', bullet '- You').
# Catches the whole class instead of whack-a-mole stopwords. Applied to the OUTPUT
# only: the context keeps all caps, so a real entity that merely *starts* a note is
# not lost (which would falsely sink the overlap).
_SENTENCE_START_RE = re.compile(r"""(^|[.!?]\s+|\n)([\s\-*•>"'()]*)([A-Z]\w*)""")


def _interesting(text: str, *, drop_sentence_initial: bool = False) -> set[str]:
    """Singularised proper-noun-ish tokens in *text*, minus boilerplate.

    With *drop_sentence_initial*, lowercase each sentence's leading word first so a
    grammar-capitalised common word ('Carefully') can't masquerade as a proper noun.
    """
    if drop_sentence_initial:
        text = _SENTENCE_START_RE.sub(lambda m: m.group(1) + m.group(2) + m.group(3).lower(), text)
    out: set[str] = set()
    for token in _INTERESTING_RE.findall(text):
        low = token.lower()
        if low not in _GROUNDING_STOPWORDS:
            out.add(_singular(low))
    return out


def check_non_empty(output: str, case: EvalCase) -> CheckResult:
    """The output must be non-empty after stripping."""
    ok = bool(output.strip())
    return CheckResult(name="non_empty", passed=ok, score=1.0 if ok else 0.0)


def check_grounding(output: str, case: EvalCase) -> CheckResult:
    """Fraction of the output's proper-noun-ish tokens present in the context.

    Low overlap = the recap brought in names/numbers absent from the notes — a
    hallucination signal. ``reference['overlap_threshold']`` overrides the pass
    floor (default 0.40). Only meaningful for the quick path, where the recap
    must ground on the notes; deep recaps ground on web research, so they omit
    this check (the in-graph anti_hallucination node guards them instead).
    """
    out_tokens = _interesting(output, drop_sentence_initial=True)
    if not out_tokens:
        return CheckResult(name="grounding", passed=True, score=1.0)
    ctx_tokens = _interesting(_ref_str(case, "context"))
    missing = [t for t in out_tokens if t not in ctx_tokens]
    ratio = (len(out_tokens) - len(missing)) / len(out_tokens)
    threshold = case.reference.get("overlap_threshold")
    floor = float(threshold) if isinstance(threshold, (int, float)) else 0.40
    return CheckResult(
        name="grounding",
        passed=ratio >= floor,
        score=round(ratio, 4),
        detail=f"overlap={ratio:.2f}, missing={missing[:5]}",
    )


def check_spoiler_free(output: str, case: EvalCase) -> CheckResult:
    """Output must contain none of ``reference['forbidden']`` (spoiler terms)."""
    forbidden = case.reference.get("forbidden", [])
    terms = forbidden if isinstance(forbidden, list) else []
    low = output.lower()
    hits = [t for t in terms if isinstance(t, str) and _mentioned(t, low)]
    return CheckResult(
        name="spoiler_free",
        passed=not hits,
        score=1.0 if not hits else 0.0,
        detail=f"leaked={hits}" if hits else "",
    )


def check_mentions(output: str, case: EvalCase) -> CheckResult:
    """Output should mention each term in ``reference['mentions']`` (recall)."""
    mentions = case.reference.get("mentions", [])
    terms = [t for t in mentions if isinstance(t, str)] if isinstance(mentions, list) else []
    if not terms:
        return CheckResult(name="mentions", passed=True, score=1.0)
    low = output.lower()
    missing = [t for t in terms if not _mentioned(t, low)]
    return CheckResult(
        name="mentions",
        passed=not missing,
        score=(len(terms) - len(missing)) / len(terms),
        detail=f"missing={missing}" if missing else "",
    )


def check_json_valid(output: str, case: EvalCase) -> CheckResult:
    """The output must parse as JSON (structured tasks)."""
    try:
        json.loads(output)
        return CheckResult(name="json_valid", passed=True, score=1.0)
    except (json.JSONDecodeError, TypeError) as exc:
        return CheckResult(name="json_valid", passed=False, score=0.0, detail=str(exc))


def check_uuid_in_candidates(output: str, case: EvalCase) -> CheckResult:
    """A pick's ``library_entry_public_id`` must exist in the candidate set."""
    candidates = case.reference.get("candidate_ids", [])
    valid = (
        {c for c in candidates if isinstance(c, str)} if isinstance(candidates, list) else set()
    )
    try:
        chosen = json.loads(output).get("library_entry_public_id")
    except (json.JSONDecodeError, AttributeError, TypeError):
        chosen = None
    ok = isinstance(chosen, str) and chosen in valid
    return CheckResult(
        name="uuid_in_candidates",
        passed=ok,
        score=1.0 if ok else 0.0,
        detail="" if ok else f"chosen={chosen!r} not in candidates",
    )


# Name → check function. Cases list the checks they want by name.
REGISTRY: dict[str, Callable[[str, EvalCase], CheckResult]] = {
    "non_empty": check_non_empty,
    "grounding": check_grounding,
    "spoiler_free": check_spoiler_free,
    "mentions": check_mentions,
    "json_valid": check_json_valid,
    "uuid_in_candidates": check_uuid_in_candidates,
}


def run_checks(output: str, case: EvalCase) -> list[CheckResult]:
    """Run the checks named on *case* (unknown names are skipped, not fatal)."""
    return [REGISTRY[name](output, case) for name in case.checks if name in REGISTRY]
