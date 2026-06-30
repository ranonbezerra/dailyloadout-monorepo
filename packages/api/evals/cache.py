"""Semantic capture-cache experiment: hit-rate gain vs false-hit risk (Epic 27).

The honest part of a semantic cache is the *trade-off*: a lower cosine threshold
catches more near-duplicate spellings (hit-rate gain over exact-match) but starts
serving the WRONG parse for confusable inputs ("Final Fantasy VII" vs "XVI"). This
sweeps the threshold over a small corpus and reports both, so the threshold is set
with eyes open instead of guessed.

It simulates the cache's matching — the exact-key + nearest-above-threshold cosine
the repo uses — so it stays deterministic and offline (DummyEmbeddingClient by
default; --real uses the configured embedding model for a faithful calibration).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from slate.infrastructure.embedding.base import AbstractEmbeddingClient
from slate.infrastructure.embedding.similarity import cosine_similarity

_WS = re.compile(r"\s+")

_THRESHOLDS = (0.60, 0.75, 0.90, 0.95)


@dataclass(frozen=True)
class CacheCase:
    text: str  # what the user typed
    true_title: str  # the parse a fresh model call would return


def cache_corpus() -> list[CacheCase]:
    """Near-duplicate spellings (should reuse) + confusables (must NOT reuse)."""
    return [
        CacheCase("Elden Ring", "Elden Ring"),
        CacheCase("elden ring", "Elden Ring"),  # case variant
        CacheCase("Elden Ring PC", "Elden Ring"),  # near-dup (extra token)
        CacheCase("Hollow Knight", "Hollow Knight"),
        CacheCase("hollow   knight", "Hollow Knight"),  # whitespace variant
        CacheCase("Final Fantasy VII", "Final Fantasy VII"),
        CacheCase("Final Fantasy XVI", "Final Fantasy XVI"),  # CONFUSABLE with VII
        CacheCase("Helldivers 2", "Helldivers 2"),
    ]


@dataclass
class ThresholdResult:
    threshold: float
    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0
    false_hits: int = 0  # a hit that returned the wrong game

    @property
    def total(self) -> int:
        return self.exact_hits + self.semantic_hits + self.misses

    @property
    def hit_rate(self) -> float:
        return (self.exact_hits + self.semantic_hits) / self.total if self.total else 0.0

    @property
    def semantic_gain(self) -> float:
        return self.semantic_hits / self.total if self.total else 0.0

    @property
    def false_hit_rate(self) -> float:
        return self.false_hits / self.total if self.total else 0.0


def _normalize(text: str) -> str:
    return _WS.sub(" ", text.strip().lower())


async def _evaluate_at(threshold: float, client: AbstractEmbeddingClient) -> ThresholdResult:
    result = ThresholdResult(threshold)
    seen_exact: dict[str, str] = {}  # normalized text → cached title
    seen_semantic: list[tuple[list[float], str]] = []  # (embedding, cached title)

    for case in cache_corpus():
        norm = _normalize(case.text)
        if norm in seen_exact:
            result.exact_hits += 1
            served = seen_exact[norm]
        else:
            embedding = await client.embed_one(norm)
            best_title, best_sim = None, -1.0
            for stored_embedding, title in seen_semantic:
                sim = cosine_similarity(embedding, stored_embedding)
                if sim > best_sim:
                    best_sim, best_title = sim, title
            if best_title is not None and best_sim >= threshold:
                result.semantic_hits += 1
                served = best_title
            else:
                result.misses += 1
                served = case.true_title  # the fresh parse
                seen_semantic.append((embedding, served))
            seen_exact[norm] = served
        if served != case.true_title:
            result.false_hits += 1
    return result


async def evaluate_cache(client: AbstractEmbeddingClient) -> list[ThresholdResult]:
    """Sweep the cosine threshold and report hit-rate gain vs false-hit risk."""
    return [await _evaluate_at(threshold, client) for threshold in _THRESHOLDS]
