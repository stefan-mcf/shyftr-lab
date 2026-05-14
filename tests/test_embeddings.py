"""Tests for ShyftR embedding providers (Work slice 8)."""
from __future__ import annotations

import math

from shyftr.retrieval.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    cosine_similarity,
)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

class TestEmbeddingProviderProtocol:
    def test_deterministic_provider_is_protocol(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        assert isinstance(provider, EmbeddingProvider)

    def test_dimension_property(self):
        provider = DeterministicEmbeddingProvider(dim=16)
        assert provider.dimension == 16


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_text_same_embedding(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        a = provider.embed("hello world")
        b = provider.embed("hello world")
        assert a == b

    def test_different_text_different_embedding(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        a = provider.embed("hello world")
        b = provider.embed("goodbye world")
        assert a != b

    def test_embed_batch_matches_individual(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        texts = ["alpha", "beta", "gamma"]
        batch = provider.embed_batch(texts)
        individual = [provider.embed(t) for t in texts]
        assert batch == individual

    def test_empty_text_produces_vector(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        vec = provider.embed("")
        assert len(vec) == 32
        # Empty text should produce a zero vector (no tokens to hash)
        assert all(v == 0.0 for v in vec)


# ---------------------------------------------------------------------------
# Dimensionality
# ---------------------------------------------------------------------------

class TestDimensionality:
    def test_custom_dimension(self):
        provider = DeterministicEmbeddingProvider(dim=128)
        vec = provider.embed("test")
        assert len(vec) == 128

    def test_small_dimension(self):
        provider = DimensionCheckProvider(dim=4)
        vec = provider.embed("test")
        assert len(vec) == 4

    def test_minimal_dimension(self):
        provider = DeterministicEmbeddingProvider(dim=2)
        vec = provider.embed("test")
        assert len(vec) == 2

    def test_invalid_dimension_raises(self):
        try:
            DeterministicEmbeddingProvider(dim=1)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Unit length (L2 normalisation)
# ---------------------------------------------------------------------------

class TestNormalisation:
    def test_output_is_unit_length(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        vec = provider.embed("some meaningful text here")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_batch_outputs_are_unit_length(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        batch = provider.embed_batch(["alpha", "beta", "gamma"])
        for vec in batch:
            norm = math.sqrt(sum(v * v for v in vec))
            assert abs(norm - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(cosine_similarity(a, b)) < 1e-9

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-9

    def test_length_mismatch_raises(self):
        try:
            cosine_similarity([1.0], [1.0, 2.0])
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == 0.0


# ---------------------------------------------------------------------------
# Semantic ordering with deterministic provider
# ---------------------------------------------------------------------------

class TestSemanticOrdering:
    def test_lexically_closer_text_ranks_first(self):
        """With the deterministic provider, texts sharing more tokens
        should produce higher cosine similarity."""
        provider = DeterministicEmbeddingProvider(dim=64)
        base = provider.embed("python exception handling best practices")
        close = provider.embed("python exception handling patterns")
        far = provider.embed("java database connection pooling")
        sim_close = cosine_similarity(base, close)
        sim_far = cosine_similarity(base, far)
        assert sim_close > sim_far


# ---------------------------------------------------------------------------
# Helper for dimension check
# ---------------------------------------------------------------------------

class DimensionCheckProvider:
    """Minimal provider for dimension tests."""

    def __init__(self, dim: int = 32):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        return [0.0] * self._dim

    def embed_batch(self, texts):
        return [self.embed(t) for t in texts]
