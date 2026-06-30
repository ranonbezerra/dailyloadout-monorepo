"""Deterministic eval checks — run first, free, and not model-graded.

These encode the correctness properties we can verify without a judge: output is
non-empty, grounded in its context (reusing the Epic 6 anti-hallucination
validator), spoiler-free, valid JSON, and (for picks) references a real
candidate. The LLM-as-judge only scores what determinism can't.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from slate.core.eval.schema import CheckResult, EvalCase
from slate.core.play_session.anti_hallucination import validate_recap


def _ref_str(case: EvalCase, key: str) -> str:
    value = case.reference.get(key, "")
    return value if isinstance(value, str) else str(value)


def check_non_empty(output: str, case: EvalCase) -> CheckResult:
    """The output must be non-empty after stripping."""
    ok = bool(output.strip())
    return CheckResult(name="non_empty", passed=ok, score=1.0 if ok else 0.0)


def check_grounding(output: str, case: EvalCase) -> CheckResult:
    """Output is grounded in ``reference['context']`` (token-overlap validator).

    Score is the overlap ratio; the check passes when the recap is *not* flagged
    suspicious. ``reference['overlap_threshold']`` overrides the floor (deep
    recaps ground on research text and use a more tolerant value).
    """
    context = _ref_str(case, "context")
    threshold = case.reference.get("overlap_threshold")
    floor = threshold if isinstance(threshold, (int, float)) else None
    result = validate_recap(output, context, threshold=floor)
    return CheckResult(
        name="grounding",
        passed=not result.is_suspicious,
        score=result.overlap_ratio,
        detail=f"overlap={result.overlap_ratio}, missing={result.missing_tokens[:5]}",
    )


def check_spoiler_free(output: str, case: EvalCase) -> CheckResult:
    """Output must contain none of ``reference['forbidden']`` (spoiler terms)."""
    forbidden = case.reference.get("forbidden", [])
    terms = forbidden if isinstance(forbidden, list) else []
    low = output.lower()
    hits = [t for t in terms if isinstance(t, str) and t.lower() in low]
    return CheckResult(
        name="spoiler_free",
        passed=not hits,
        score=1.0 if not hits else 0.0,
        detail=f"leaked={hits}" if hits else "",
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
    "json_valid": check_json_valid,
    "uuid_in_candidates": check_uuid_in_candidates,
}


def run_checks(output: str, case: EvalCase) -> list[CheckResult]:
    """Run the checks named on *case* (unknown names are skipped, not fatal)."""
    return [REGISTRY[name](output, case) for name in case.checks if name in REGISTRY]
