"""Tests for the embedding port: dummy vectors, cosine ranking, factory wiring."""

from __future__ import annotations

import math

import pytest

from slate.config import Settings
from slate.infrastructure.embedding import (
    DummyEmbeddingClient,
    OllamaEmbeddingClient,
    cosine_similarity,
    get_embedding_client,
    rank_by_similarity,
    select_grounding_ids,
)


class TestDummyEmbeddingClient:
    async def test_dimensions_and_shape(self) -> None:
        client = DummyEmbeddingClient(dimensions=64)
        vectors = await client.embed(["hello world", "another"])
        assert len(vectors) == 2
        assert all(len(v) == 64 for v in vectors)

    async def test_is_deterministic(self) -> None:
        client = DummyEmbeddingClient(dimensions=64)
        first = await client.embed_one("Stormveil Castle, beat Margit")
        second = await client.embed_one("Stormveil Castle, beat Margit")
        assert first == second

    async def test_vectors_are_l2_normalised(self) -> None:
        client = DummyEmbeddingClient(dimensions=128)
        vec = await client.embed_one("running bug missions with the breaker")
        assert math.isclose(math.sqrt(sum(x * x for x in vec)), 1.0, rel_tol=1e-9)

    async def test_empty_text_is_defined_not_nan(self) -> None:
        client = DummyEmbeddingClient(dimensions=32)
        vec = await client.embed_one("!!! ???")  # no alphanumeric tokens
        assert math.isclose(math.sqrt(sum(x * x for x in vec)), 1.0, rel_tol=1e-9)
        assert not any(math.isnan(x) for x in vec)

    async def test_shared_tokens_raise_cosine(self) -> None:
        # The vector for text about the same game should be closer to a related
        # note than to an unrelated one — what makes retrieval meaningful.
        client = DummyEmbeddingClient(dimensions=256)
        anchor = await client.embed_one("Elden Ring Stormveil Castle Margit boss")
        related = await client.embed_one("back at Stormveil Castle to fight Margit")
        unrelated = await client.embed_one("Helldivers bug missions railgun chargers")
        assert cosine_similarity(anchor, related) > cosine_similarity(anchor, unrelated)


class TestCosineSimilarity:
    def test_identical_is_one(self) -> None:
        assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_orthogonal_is_zero(self) -> None:
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_is_minus_one(self) -> None:
        assert cosine_similarity([1.0, 1.0], [-1.0, -1.0]) == pytest.approx(-1.0)

    def test_zero_vector_is_zero(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            cosine_similarity([1.0, 2.0], [1.0])


class TestRankBySimilarity:
    def test_ranks_most_similar_first_and_caps_top_k(self) -> None:
        query = [1.0, 0.0]
        candidates = [
            (10, [0.0, 1.0]),  # orthogonal
            (20, [1.0, 0.1]),  # closest
            (30, [-1.0, 0.0]),  # opposite
        ]
        ranked = rank_by_similarity(query, candidates, top_k=2)
        assert [cid for cid, _ in ranked] == [20, 10]

    def test_empty_candidates(self) -> None:
        assert rank_by_similarity([1.0, 0.0], [], top_k=3) == []


class TestSelectGroundingIds:
    def test_latest_first_plus_most_similar(self) -> None:
        # Newest-first: latest=0; id1 is close to it, id2 is orthogonal.
        candidates = [(0, [1.0, 0.0]), (1, [1.0, 0.1]), (2, [0.0, 1.0])]
        assert select_grounding_ids(candidates, top_k=2) == [0, 1]

    def test_top_k_one_keeps_only_latest(self) -> None:
        candidates = [(0, [1.0, 0.0]), (1, [1.0, 0.1])]
        assert select_grounding_ids(candidates, top_k=1) == [0]

    def test_empty(self) -> None:
        assert select_grounding_ids([], top_k=3) == []

    def test_single_candidate(self) -> None:
        assert select_grounding_ids([(5, [1.0, 0.0])], top_k=3) == [5]


class TestFactory:
    def test_testing_env_returns_dummy(self) -> None:
        settings = Settings(app_env="testing", embedding_provider="ollama")
        assert isinstance(get_embedding_client(settings), DummyEmbeddingClient)

    def test_ollama_provider(self) -> None:
        settings = Settings(app_env="development", embedding_provider="ollama")
        assert isinstance(get_embedding_client(settings), OllamaEmbeddingClient)

    def test_dummy_provider_outside_testing(self) -> None:
        settings = Settings(app_env="development", embedding_provider="dummy")
        assert isinstance(get_embedding_client(settings), DummyEmbeddingClient)

    def test_unknown_provider_raises(self) -> None:
        settings = Settings(app_env="development", embedding_provider="pinecone")
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            get_embedding_client(settings)

    def test_dummy_dimensions_follow_settings(self) -> None:
        settings = Settings(app_env="testing", embedding_dimensions=256)
        client = get_embedding_client(settings)
        assert client.dimensions == 256
