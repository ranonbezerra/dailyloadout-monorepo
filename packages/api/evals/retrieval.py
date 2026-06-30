"""Retrieval A/B: does semantic grounding beat chronological last-N? (Epic 24)

The golden recap eval feeds wrap-ups straight in, so it measures *generation*, not
*which sessions get chosen*. This measures the choice: each case is a pool of a
game's sessions where the truly-relevant one is **older than the last-k** (so the
chronological path misses it) but topically matches the latest (so semantic catches
it). We score recall@k of the gold-relevant sessions under each mode.

Deterministic and model-free: the DummyEmbeddingClient is similarity-bearing, so the
A/B proves the retrieval delta offline — no Ollama, no flakiness. It exercises the
SAME selection rule the DB retrieval uses (``select_grounding_ids``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from slate.infrastructure.embedding.base import AbstractEmbeddingClient
from slate.infrastructure.embedding.similarity import select_grounding_ids


@dataclass(frozen=True)
class RetrievalCase:
    """A pool of a game's sessions + which ones *should* ground the recap."""

    id: str
    # (wrap-up text, days_ago) — days_ago orders recency (0 = the latest session).
    pool: tuple[tuple[str, int], ...]
    gold: frozenset[int]  # indices into pool that retrieval ought to surface
    top_k: int = 3


@dataclass
class RetrievalReport:
    rows: list[dict[str, object]] = field(default_factory=list)

    @property
    def recent_recall(self) -> float:
        return _mean([float(r["recent"]) for r in self.rows])

    @property
    def semantic_recall(self) -> float:
        return _mean([float(r["semantic"]) for r in self.rows])

    @property
    def delta(self) -> float:
        return self.semantic_recall - self.recent_recall


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _recall(selected: list[int], gold: frozenset[int]) -> float:
    if not gold:
        return 1.0
    return len(set(selected) & gold) / len(gold)


def retrieval_cases() -> list[RetrievalCase]:
    """Cases where the relevant context is buried older than the last-k."""
    return [
        # The quest you're mid-way through, last touched 6 sessions ago.
        RetrievalCase(
            id="buried_quest",
            pool=(
                ("Deep in the Forgotten Catacombs hunting the Grafted boss", 0),
                ("Spent the session sorting inventory and upgrading weapons", 1),
                ("Farming runes out in the Limgrave fields", 2),
                ("Exploring the Liurnia lake shore on horseback", 3),
                ("Back in the Forgotten Catacombs, still stuck on the Grafted boss", 6),
            ),
            gold=frozenset({4}),
        ),
        # Latest returns to a topic only one buried session shares.
        RetrievalCase(
            id="topic_return",
            pool=(
                ("Grinding the Bile Titan bug missions on Helldive difficulty", 0),
                ("Quick automaton defense mission, nothing notable", 1),
                ("Restocking samples and swapping stratagems", 2),
                ("First attempt at the Bile Titan bugs, got overwhelmed", 7),
            ),
            gold=frozenset({3}),
        ),
        # Two buried sessions are relevant; semantic should surface both.
        RetrievalCase(
            id="two_relevant_buried",
            pool=(
                ("Pushing through Konpeki Plaza to find Evelyn", 0),
                ("Driving around Night City buying clothes", 1),
                ("Ripperdoc visit for new cyberware", 2),
                ("Scoping out Konpeki Plaza for the Evelyn heist", 5),
                ("Planning the Konpeki Plaza job with the crew", 6),
            ),
            gold=frozenset({3, 4}),
            top_k=3,
        ),
        # Control: the relevant context IS recent — semantic must not regress.
        RetrievalCase(
            id="recency_sufficient",
            pool=(
                ("Storming Stormveil Castle toward Godrick", 0),
                ("Approaching Stormveil Castle gate past Margit", 1),
                ("Old farming run in the starting fields", 9),
            ),
            gold=frozenset({1}),
        ),
    ]


async def evaluate_retrieval(embedding_client: AbstractEmbeddingClient) -> RetrievalReport:
    """Score recall@k of the gold sessions for recent vs semantic over all cases."""
    report = RetrievalReport()
    for case in retrieval_cases():
        report.rows.append(await _evaluate_case(case, embedding_client))
    return report


async def _evaluate_case(
    case: RetrievalCase, embedding_client: AbstractEmbeddingClient
) -> dict[str, object]:
    # Order newest-first (smallest days_ago); keep the original pool index as the id.
    order = sorted(range(len(case.pool)), key=lambda i: case.pool[i][1])
    vectors = await embedding_client.embed([case.pool[i][0] for i in order])
    candidates = list(zip(order, vectors, strict=True))

    recent = [idx for idx, _ in candidates[: case.top_k]]
    semantic = select_grounding_ids(candidates, case.top_k)
    return {
        "id": case.id,
        "recent": _recall(recent, case.gold),
        "semantic": _recall(semantic, case.gold),
    }
