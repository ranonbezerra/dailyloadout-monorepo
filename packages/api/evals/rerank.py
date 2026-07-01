"""Rerank A/B: does relevance reranking beat raw search order? (Epic 25)

Epic 10 grounds ``synthesize`` (and scrapes) on the *first* results SearXNG returns —
raw search-engine order, which buries the on-topic passage under SEO noise. Epic 25
inserts a rerank node that reorders candidates by task relevance before synthesis. This
measures that choice: each case is a pool of search results for a play session where the
truly-relevant ones sit **below the top-n** in raw order (so snippet-order grounding
misses them) but clearly match the player's situation (so reranking surfaces them). We
score recall@n of the gold-relevant results under each ordering.

Deterministic and model-free: the "relevance signal" is token overlap between each
result and the player's context — the same thing an LLM reranker approximates — so the
A/B proves the ordering delta offline, no Ollama, no flakiness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RerankCase:
    """A pool of search results (raw order) + which ones *should* ground the recap."""

    id: str
    context: str  # the player's situation (game + area + quest) — the rerank target
    # (title, snippet) in raw search-engine order; gold indices are buried below top_n.
    results: tuple[tuple[str, str], ...]
    gold: frozenset[int]  # indices into results that reranking ought to surface
    top_n: int = 2


@dataclass
class RerankReport:
    rows: list[dict[str, object]] = field(default_factory=list)

    @property
    def raw_recall(self) -> float:
        return _mean([float(r["raw"]) for r in self.rows])

    @property
    def reranked_recall(self) -> float:
        return _mean([float(r["reranked"]) for r in self.rows])

    @property
    def delta(self) -> float:
        return self.reranked_recall - self.raw_recall


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _recall(selected: list[int], gold: frozenset[int]) -> float:
    if not gold:
        return 1.0
    return len(set(selected) & gold) / len(gold)


def _relevance(result: tuple[str, str], ctx_tokens: set[str]) -> int:
    """Model-free relevance: token overlap of (title + snippet) with the context."""
    return len(_tokens(f"{result[0]} {result[1]}") & ctx_tokens)


def rerank_cases() -> list[RerankCase]:
    """Cases where the on-topic result is buried below the raw-order top_n."""
    return [
        # The Greenpath area guide sits at #3; two generic pages rank above it.
        RerankCase(
            id="buried_area_guide",
            context="Hollow Knight Greenpath find Cornifer map",
            results=(
                ("Hollow Knight review", "our verdict on the acclaimed metroidvania"),
                ("Hollow Knight all endings", "every ending and how to unlock them"),
                ("Greenpath area guide", "where to go in Greenpath and finding Cornifer's map"),
            ),
            gold=frozenset({2}),
        ),
        # Two relevant Konpeki pages are buried under shopping/cyberware noise.
        RerankCase(
            id="two_relevant_buried",
            context="Cyberpunk 2077 Konpeki Plaza Evelyn heist where to go",
            results=(
                ("Best clothing stores", "where to buy the coolest outfits in Night City"),
                ("Cyberware upgrades", "ripperdoc guide to the best implants"),
                ("Konpeki Plaza walkthrough", "navigating Konpeki Plaza toward Evelyn"),
                ("Evelyn heist prep", "how to plan the Konpeki Plaza job with the crew"),
            ),
            gold=frozenset({2, 3}),
            top_n=2,
        ),
        # Control: the relevant result is ALREADY in the raw top_n — rerank must not regress.
        RerankCase(
            id="already_top",
            context="Elden Ring Stormveil Castle Godrick where to go next",
            results=(
                ("Stormveil Castle guide", "path through Stormveil Castle to reach Godrick"),
                ("Elden Ring lore recap", "the story so far, spoilers ahead"),
                ("Best early weapons", "top starting weapons for any build"),
            ),
            gold=frozenset({0}),
            top_n=2,
        ),
    ]


def _evaluate_case(case: RerankCase) -> dict[str, object]:
    ctx_tokens = _tokens(case.context)
    raw = list(range(len(case.results)))[: case.top_n]
    # Stable sort by relevance desc; ties keep raw order (Python sort is stable).
    reranked_order = sorted(
        range(len(case.results)),
        key=lambda i: _relevance(case.results[i], ctx_tokens),
        reverse=True,
    )
    reranked = reranked_order[: case.top_n]
    return {
        "id": case.id,
        "raw": _recall(raw, case.gold),
        "reranked": _recall(reranked, case.gold),
    }


def evaluate_rerank() -> RerankReport:
    """Score recall@n of the gold results for raw vs reranked order over all cases."""
    report = RerankReport()
    for case in rerank_cases():
        report.rows.append(_evaluate_case(case))
    return report
