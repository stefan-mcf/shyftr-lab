"""Tests for ShyftR vector retrieval Mesh (Work slice 8)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_source
from shyftr.layout import init_cell
from shyftr.promote import promote_fragment
from shyftr.review import approve_fragment
from shyftr.retrieval.embeddings import DeterministicEmbeddingProvider
from shyftr.retrieval.vector import (
    InMemoryVectorIndex,
    SqliteVecVectorIndex,
    VectorResult,
    query_vector,
    rebuild_vector_index,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cell(tmp_path: Path, cell_id: str = "test-cell") -> Path:
    """Create a Cell and return its path."""
    return init_cell(tmp_path, cell_id)


def _ingest_and_promote(cell_path: Path, tmp_path: Path, text: str):
    """Ingest a source, extract fragments, approve and promote the first one."""
    source_path = tmp_path / "source.md"
    source_path.write_text(text, encoding="utf-8")
    source = ingest_source(cell_path, source_path, kind="lesson", metadata={})
    fragments = extract_fragments(cell_path, source)
    approve_fragment(
        cell_path, fragments[0].fragment_id,
        reviewer="test-reviewer", rationale="durable and bounded",
    )
    return promote_fragment(
        cell_path, fragments[0].fragment_id, promoter="test-promoter",
    )


# ---------------------------------------------------------------------------
# InMemoryVectorIndex basics
# ---------------------------------------------------------------------------

class TestInMemoryVectorIndex:
    def test_add_and_size(self):
        idx = InMemoryVectorIndex()
        assert idx.size() == 0
        idx.add("doc1", [1.0, 0.0])
        assert idx.size() == 1
        idx.add("doc2", [0.0, 1.0])
        assert idx.size() == 2

    def test_query_returns_sorted(self):
        idx = InMemoryVectorIndex()
        idx.add("doc1", [1.0, 0.0])
        idx.add("doc2", [0.0, 1.0])
        results = idx.query([1.0, 0.0], top_k=2)
        assert len(results) == 2
        # doc1 should be first (exact match)
        assert results[0][0] == "doc1"
        assert results[0][1] > results[1][1]

    def test_query_respects_top_k(self):
        idx = InMemoryVectorIndex()
        for i in range(5):
            idx.add(f"doc{i}", [float(i), 0.0])
        results = idx.query([1.0, 0.0], top_k=3)
        assert len(results) == 3

    def test_query_with_filter(self):
        idx = InMemoryVectorIndex()
        idx.add("doc1", [1.0, 0.0], {"cell_id": "cell-a"})
        idx.add("doc2", [1.0, 0.0], {"cell_id": "cell-b"})
        results = idx.query(
            [1.0, 0.0], top_k=10, filter_metadata={"cell_id": "cell-a"}
        )
        assert len(results) == 1
        assert results[0][2]["cell_id"] == "cell-a"

    def test_clear(self):
        idx = InMemoryVectorIndex()
        idx.add("doc1", [1.0, 0.0])
        idx.clear()
        assert idx.size() == 0

    def test_empty_index_query(self):
        idx = InMemoryVectorIndex()
        results = idx.query([1.0, 0.0], top_k=5)
        assert results == []


# ---------------------------------------------------------------------------
# Rebuild from Cell
# ---------------------------------------------------------------------------

class TestRebuildVectorIndex:
    def test_rebuild_from_approved_traces(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Python exception handling best practices")
        _ingest_and_promote(cell_path, tmp_path, "Database connection pooling strategies")

        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        count = rebuild_vector_index(idx, cell_path, provider)
        assert count == 2
        assert idx.size() == 2

    def test_rebuild_excludes_deprecated(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        trace = _ingest_and_promote(cell_path, tmp_path, "Some durable lesson")

        # Manually add a deprecated trace
        deprecated_path = cell_path / "traces" / "deprecated.jsonl"
        deprecated_trace = {
            "trace_id": "trace-deprecated-1",
            "cell_id": "test-cell",
            "statement": "Deprecated operational note",
            "source_fragment_ids": ["frag-1"],
            "status": "deprecated",
            "tags": ["deprecated"],
        }
        with deprecated_path.open("a") as f:
            f.write(json.dumps(deprecated_trace, sort_keys=True) + "\n")

        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        count = rebuild_vector_index(idx, cell_path, provider)
        # Only the approved trace should be indexed
        assert count == 1

    def test_rebuild_empty_ledger(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        count = rebuild_vector_index(idx, cell_path, provider)
        assert count == 0
        assert idx.size() == 0

    def test_rebuild_with_include_statuses(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Approved lesson text")

        # Add a deprecated trace into approved.jsonl (same file, different status)
        approved_path = cell_path / "traces" / "approved.jsonl"
        deprecated_trace = {
            "trace_id": "trace-dep-1",
            "cell_id": "test-cell",
            "statement": "Deprecated note",
            "source_fragment_ids": ["frag-1"],
            "status": "deprecated",
            "tags": [],
        }
        with approved_path.open("a") as f:
            f.write(json.dumps(deprecated_trace, sort_keys=True) + "\n")

        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        count = rebuild_vector_index(
            idx, cell_path, provider,
            include_statuses=["approved", "deprecated"],
        )
        assert count == 2


# ---------------------------------------------------------------------------
# Query vector
# ---------------------------------------------------------------------------

class TestQueryVector:
    def test_query_returns_results(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Python exception handling")
        _ingest_and_promote(cell_path, tmp_path, "Database connection pooling")

        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        rebuild_vector_index(idx, cell_path, provider)

        results = query_vector(idx, "exception handling", provider, top_k=2)
        assert len(results) > 0
        assert all(isinstance(r, VectorResult) for r in results)

    def test_query_empty_text_returns_empty(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Some lesson")

        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        rebuild_vector_index(idx, cell_path, provider)

        results = query_vector(idx, "", provider)
        assert results == []

    def test_query_no_match_returns_empty(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        # Empty index
        results = query_vector(idx, "anything", provider)
        assert results == []

    def test_query_respects_cell_filter(self, tmp_path: Path):
        cell_a = _make_cell(tmp_path / "a", cell_id="cell-a")
        cell_b = _make_cell(tmp_path / "b", cell_id="cell-b")
        _ingest_and_promote(cell_a, tmp_path, "Python exception handling")
        _ingest_and_promote(cell_b, tmp_path, "Java exception handling")

        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        rebuild_vector_index(idx, cell_a, provider)
        rebuild_vector_index(idx, cell_b, provider)

        results = query_vector(
            idx, "exception handling", provider,
            cell_id="cell-a", top_k=10,
        )
        assert all(r.cell_id == "cell-a" for r in results)

    def test_query_result_has_provenance(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Test trace statement")

        provider = DeterministicEmbeddingProvider(dim=32)
        idx = InMemoryVectorIndex()
        rebuild_vector_index(idx, cell_path, provider)

        results = query_vector(idx, "test trace", provider, top_k=1)
        assert len(results) == 1
        r = results[0]
        assert r.trace_id  # non-empty
        assert r.cell_id == "test-cell"
        assert r.statement  # non-empty
        assert r.status == "approved"
        assert isinstance(r.cosine_score, float)


# ---------------------------------------------------------------------------
# Cosine ordering
# ---------------------------------------------------------------------------

class TestCosineOrdering:
    def test_closer_text_ranks_first(self, tmp_path: Path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(
            cell_path, tmp_path,
            "Python exception handling best practices for production",
        )
        _ingest_and_promote(
            cell_path, tmp_path,
            "Java database connection pooling configuration",
        )

        provider = DeterministicEmbeddingProvider(dim=64)
        idx = InMemoryVectorIndex()
        rebuild_vector_index(idx, cell_path, provider)

        results = query_vector(
            idx, "python exception handling patterns", provider, top_k=2,
        )
        assert len(results) == 2
        # The exception handling trace should rank first
        assert "exception" in results[0].statement.lower()


# ---------------------------------------------------------------------------
# sqlite-vec placeholder
# ---------------------------------------------------------------------------

class TestSqliteVecPlaceholder:
    def test_unavailable_raises_on_add(self):
        idx = SqliteVecVectorIndex()
        with pytest.raises(RuntimeError, match="sqlite-vec is not installed"):
            idx.add("doc1", [1.0, 0.0])

    def test_unavailable_raises_on_query(self):
        idx = SqliteVecVectorIndex()
        with pytest.raises(RuntimeError, match="sqlite-vec is not installed"):
            idx.query([1.0, 0.0])

    def test_size_returns_zero(self):
        idx = SqliteVecVectorIndex()
        assert idx.size() == 0

    def test_clear_is_noop(self):
        idx = SqliteVecVectorIndex()
        idx.clear()  # should not raise
