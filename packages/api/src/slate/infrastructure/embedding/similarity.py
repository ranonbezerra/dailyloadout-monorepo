"""Cosine similarity + top-k ranking, in pure Python.

The recap retrieval is scoped to a single ``(user, library_entry)`` — one game's
sessions, a small set — so ranking the candidate vectors in Python is both correct
and cheap. No pgvector ANN index is needed at this scope; the stored ``vector``
column is just typed storage (and the substrate for any future global search).
"""

from __future__ import annotations

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine of the angle between *a* and *b* in ``[-1, 1]`` (0 if either is zero)."""
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} != {len(b)}")
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def rank_by_similarity(
    query: list[float],
    candidates: list[tuple[int, list[float]]],
    *,
    top_k: int,
) -> list[tuple[int, float]]:
    """Return ``(id, score)`` for the *top_k* candidates most similar to *query*.

    *candidates* is ``(id, vector)`` pairs; ties keep input order (stable sort).
    """
    scored = [(cid, cosine_similarity(query, vec)) for cid, vec in candidates]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def select_grounding_ids(candidates: list[tuple[int, list[float]]], top_k: int) -> list[int]:
    """Pick the ids to ground a recap on: the latest + the (top_k-1) most similar to it.

    *candidates* is ``(id, vector)`` **newest-first**. The first (latest) is always
    kept as the immediate "where I left off"; the remaining slots go to the sessions
    most similar to it. Pure so the DB retrieval and the eval A/B share one rule.
    """
    if not candidates:
        return []
    query_id, query_vector = candidates[0]
    older = candidates[1:]
    if not older or top_k <= 1:
        return [query_id]
    ranked = rank_by_similarity(query_vector, older, top_k=top_k - 1)
    return [query_id] + [cid for cid, _ in ranked]
