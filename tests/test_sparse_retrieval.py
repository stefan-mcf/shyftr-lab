"""Tests for ShyftR sparse retrieval Mesh (Work slice 7)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_source
from shyftr.layout import init_cell
from shyftr.promote import promote_fragment
from shyftr.review import approve_fragment
from shyftr.retrieval.sparse import (
    SparseResult,
    open_sparse_index,
    query_sparse,
    rebuild_sparse_index,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cell(tmp_path: Path, cell_id: str = "test-cell") -> Path:
    """Create a Cell and return its path."""
    return init_cell(tmp_path, cell_id)


def _ingest_and_promote(cell_path: Path, tmp_path: Path, text: str):
    """Ingest a source, extract fragments, approve and promote the first one.
    Returns the trace.
    """
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


def _promote_with_tags(cell_path: Path, tmp_path: Path, text: str, tags: list[str]):
    """Ingest, extract, approve with tags, and promote."""
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
# Tests: open_sparse_index
# ---------------------------------------------------------------------------

class TestOpenSparseIndex:
    def test_creates_fts_table(self, tmp_path):
        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "traces_fts" in tables
        finally:
            conn.close()

    def test_includes_standard_tables(self, tmp_path):
        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "traces" in tables
            assert "sources" in tables
        finally:
            conn.close()

    def test_idempotent_open(self, tmp_path):
        db = tmp_path / "sparse.db"
        conn1 = open_sparse_index(db)
        conn1.close()
        conn2 = open_sparse_index(db)
        try:
            count = conn2.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            assert count >= 8  # 7 standard + traces_fts
        finally:
            conn2.close()


# ---------------------------------------------------------------------------
# Tests: rebuild_sparse_index
# ---------------------------------------------------------------------------

class TestRebuildSparseIndex:
    def test_indexes_approved_traces(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Always verify before deploying.")

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(conn, cell_path)
            assert count == 1
            rows = conn.execute("SELECT * FROM traces_fts").fetchall()
            assert len(rows) == 1
        finally:
            conn.close()

    def test_rebuild_idempotent(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Idempotent rebuild test.")

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            rebuild_sparse_index(conn, cell_path)
            rows = conn.execute("SELECT * FROM traces_fts").fetchall()
            assert len(rows) == 1
        finally:
            conn.close()

    def test_excludes_deprecated_traces(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        # Ingest and promote, then manually deprecate in JSONL
        trace = _ingest_and_promote(cell_path, tmp_path, "Deprecated lesson text.")

        # Manually write a deprecated trace
        from shyftr.ledger import append_jsonl
        deprecated_trace = {
            "trace_id": "trace-deprecated-1",
            "cell_id": "test-cell",
            "statement": "This should not appear in sparse results.",
            "source_fragment_ids": ["frag-x"],
            "status": "deprecated",
            "tags": ["deprecated"],
        }
        append_jsonl(cell_path / "traces" / "approved.jsonl", deprecated_trace)

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(conn, cell_path)
            # Only the approved trace should be indexed
            assert count == 1
            rows = conn.execute("SELECT trace_id FROM traces_fts").fetchall()
            trace_ids = {row[0] for row in rows}
            assert trace.trace_id in trace_ids
            assert "trace-deprecated-1" not in trace_ids
        finally:
            conn.close()

    def test_include_statuses_override(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        trace = _ingest_and_promote(cell_path, tmp_path, "Override status test.")

        from shyftr.ledger import append_jsonl
        deprecated_trace = {
            "trace_id": "trace-dep-2",
            "cell_id": "test-cell",
            "statement": "Deprecated but included.",
            "source_fragment_ids": ["frag-y"],
            "status": "deprecated",
            "tags": [],
        }
        append_jsonl(cell_path / "traces" / "approved.jsonl", deprecated_trace)

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(
                conn, cell_path, include_statuses=["approved", "deprecated"]
            )
            assert count == 2
        finally:
            conn.close()

    def test_empty_cell_returns_zero(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(conn, cell_path)
            assert count == 0
        finally:
            conn.close()

    def test_indexes_tags(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        # Manually append a trace with tags
        from shyftr.ledger import append_jsonl
        trace = {
            "trace_id": "trace-tagged-1",
            "cell_id": "test-cell",
            "statement": "Python type hints improve code clarity.",
            "source_fragment_ids": ["frag-z"],
            "status": "approved",
            "tags": ["python", "typing", "best-practice"],
        }
        append_jsonl(cell_path / "traces" / "approved.jsonl", trace)

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(conn, cell_path)
            assert count == 1
            # Verify tags are stored
            row = conn.execute(
                "SELECT tags FROM traces_fts WHERE trace_id = ?",
                ("trace-tagged-1",),
            ).fetchone()
            assert "python" in row[0]
            assert "typing" in row[0]
        finally:
            conn.close()

    def test_rebuild_sparse_index_fills_missing_cell_id_from_manifest(self, tmp_path):
        cell_path = _make_cell(tmp_path, "manifest-cell")

        from shyftr.ledger import append_jsonl
        append_jsonl(cell_path / "traces" / "approved.jsonl", {
            "trace_id": "trace-missing-cell-id",
            "statement": "Manifest cell id should be used when ledger row omits it.",
            "source_fragment_ids": ["frag-missing-cell-id"],
            "status": "approved",
            "tags": ["manifest"],
        })

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(conn, cell_path)
            assert count == 1
            row = conn.execute(
                "SELECT cell_id FROM traces_fts WHERE trace_id = ?",
                ("trace-missing-cell-id",),
            ).fetchone()
            assert row is not None
            assert row[0] == "manifest-cell"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Tests: query_sparse
# ---------------------------------------------------------------------------

class TestQuerySparse:
    def test_exact_keyword_retrieval(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        trace = _ingest_and_promote(
            cell_path, tmp_path,
            "Always verify before deploying to production.",
        )

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "verify")
            assert len(results) >= 1
            assert any(r.trace_id == trace.trace_id for r in results)
        finally:
            conn.close()

    def test_bm25_ordering_more_relevant_first(self, tmp_path):
        cell_path = _make_cell(tmp_path)

        # Create two traces where both match "error" but one is more relevant
        from shyftr.ledger import append_jsonl
        trace_a = {
            "trace_id": "trace-error-1",
            "cell_id": "test-cell",
            "statement": "Error handling is critical for production reliability.",
            "source_fragment_ids": ["frag-a"],
            "status": "approved",
            "tags": ["error", "handling"],
        }
        trace_b = {
            "trace_id": "trace-general-1",
            "cell_id": "test-cell",
            "statement": "General software engineering error prevention.",
            "source_fragment_ids": ["frag-b"],
            "status": "approved",
            "tags": ["general"],
        }
        append_jsonl(cell_path / "traces" / "approved.jsonl", trace_a)
        append_jsonl(cell_path / "traces" / "approved.jsonl", trace_b)

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "error")
            assert len(results) >= 2
            # The trace with "Error" appearing more prominently should rank higher
            assert results[0].trace_id == "trace-error-1"
        finally:
            conn.close()

    def test_tags_participate_in_search(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        from shyftr.ledger import append_jsonl
        trace = {
            "trace_id": "trace-tagged-search",
            "cell_id": "test-cell",
            "statement": "Use context managers for resource management.",
            "source_fragment_ids": ["frag-t"],
            "status": "approved",
            "tags": ["python", "context-manager", "resource"],
        }
        append_jsonl(cell_path / "traces" / "approved.jsonl", trace)

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            # Search by tag
            results = query_sparse(conn, "context-manager")
            assert len(results) >= 1
            assert results[0].trace_id == "trace-tagged-search"
        finally:
            conn.close()

    def test_deprecated_traces_excluded_by_default(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        from shyftr.ledger import append_jsonl

        approved = {
            "trace_id": "trace-ok",
            "cell_id": "test-cell",
            "statement": "Approved lesson about testing.",
            "source_fragment_ids": ["frag-ok"],
            "status": "approved",
            "tags": ["testing"],
        }
        deprecated = {
            "trace_id": "trace-dep",
            "cell_id": "test-cell",
            "statement": "Deprecated lesson about testing.",
            "source_fragment_ids": ["frag-dep"],
            "status": "deprecated",
            "tags": ["testing"],
        }
        append_jsonl(cell_path / "traces" / "approved.jsonl", approved)
        append_jsonl(cell_path / "traces" / "approved.jsonl", deprecated)

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "testing")
            trace_ids = {r.trace_id for r in results}
            assert "trace-ok" in trace_ids
            assert "trace-dep" not in trace_ids
        finally:
            conn.close()

    def test_empty_query_returns_no_results(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Some lesson text.")

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "")
            assert results == []
        finally:
            conn.close()

    def test_no_match_returns_empty(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Python testing best practices.")

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "xyznonexistent")
            assert results == []
        finally:
            conn.close()

    def test_cell_id_filter(self, tmp_path):
        cell_a = _make_cell(tmp_path, "cell-a")
        cell_b = _make_cell(tmp_path, "cell-b")

        from shyftr.ledger import append_jsonl
        append_jsonl(cell_a / "traces" / "approved.jsonl", {
            "trace_id": "trace-a",
            "cell_id": "cell-a",
            "statement": "Cell A lesson about databases.",
            "source_fragment_ids": ["frag-a"],
            "status": "approved",
            "tags": ["database"],
        })
        append_jsonl(cell_b / "traces" / "approved.jsonl", {
            "trace_id": "trace-b",
            "cell_id": "cell-b",
            "statement": "Cell B lesson about databases.",
            "source_fragment_ids": ["frag-b"],
            "status": "approved",
            "tags": ["database"],
        })

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_a)
            rebuild_sparse_index(conn, cell_b)

            results_a = query_sparse(conn, "databases", cell_id="cell-a")
            assert len(results_a) == 1
            assert results_a[0].cell_id == "cell-a"

            results_b = query_sparse(conn, "databases", cell_id="cell-b")
            assert len(results_b) == 1
            assert results_b[0].cell_id == "cell-b"
        finally:
            conn.close()

    def test_query_sparse_handles_quotes_without_sqlite_fts_error(self, tmp_path):
        cell_path = _make_cell(tmp_path)

        from shyftr.ledger import append_jsonl
        append_jsonl(cell_path / "traces" / "approved.jsonl", {
            "trace_id": "trace-quoted",
            "cell_id": "test-cell",
            "statement": 'Prefer the literal token "quoted" in search examples.',
            "source_fragment_ids": ["frag-quoted"],
            "status": "approved",
            "tags": ["quoted"],
        })

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, '"quoted"')
            assert len(results) == 1
            assert results[0].trace_id == "trace-quoted"
        finally:
            conn.close()

    def test_limit_respects_max_results(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        from shyftr.ledger import append_jsonl
        for i in range(5):
            append_jsonl(cell_path / "traces" / "approved.jsonl", {
                "trace_id": f"trace-{i}",
                "cell_id": "test-cell",
                "statement": f"Lesson about Python testing number {i}.",
                "source_fragment_ids": [f"frag-{i}"],
                "status": "approved",
                "tags": ["testing"],
            })

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "Python testing", limit=3)
            assert len(results) <= 3
        finally:
            conn.close()

    def test_result_has_provenance_fields(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        trace = _ingest_and_promote(
            cell_path, tmp_path,
            "Provenance field test for sparse results.",
        )

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "provenance")
            assert len(results) >= 1
            r = results[0]
            assert isinstance(r, SparseResult)
            assert r.trace_id == trace.trace_id
            assert r.cell_id == "test-cell"
            assert r.statement
            assert isinstance(r.tags, list)
            assert isinstance(r.bm25_score, float)
            assert hasattr(r, "kind")
        finally:
            conn.close()

    def test_kind_participates_in_search(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        from shyftr.ledger import append_jsonl

        append_jsonl(cell_path / "traces" / "approved.jsonl", {
            "trace_id": "trace-kind-tool-error",
            "cell_id": "test-cell",
            "statement": "Prefer focused verification before closing the task.",
            "source_fragment_ids": ["frag-kind"],
            "kind": "tool-error",
            "status": "approved",
            "tags": [],
        })

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "tool error")
            assert len(results) == 1
            assert results[0].trace_id == "trace-kind-tool-error"
            assert results[0].kind == "tool-error"
        finally:
            conn.close()

    def test_result_preserves_tag_list(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        from shyftr.ledger import append_jsonl

        append_jsonl(cell_path / "traces" / "approved.jsonl", {
            "trace_id": "trace-tags-preserved",
            "cell_id": "test-cell",
            "statement": "Use context managers for resource handling.",
            "source_fragment_ids": ["frag-tags"],
            "status": "approved",
            "tags": ["context-manager", "resource"],
        })

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "context manager")
            assert len(results) == 1
            assert results[0].tags == ["context-manager", "resource"]
        finally:
            conn.close()

    def test_include_statuses_override_in_query(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        from shyftr.ledger import append_jsonl

        append_jsonl(cell_path / "traces" / "approved.jsonl", {
            "trace_id": "trace-dep-query",
            "cell_id": "test-cell",
            "statement": "Deprecated query override test.",
            "source_fragment_ids": ["frag-dq"],
            "status": "deprecated",
            "tags": [],
        })

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(
                conn, cell_path, include_statuses=["approved", "deprecated"]
            )
            results = query_sparse(
                conn, "deprecated",
                include_statuses=["approved", "deprecated"],
            )
            assert len(results) >= 1
            assert results[0].trace_id == "trace-dep-query"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Tests: rebuild from JSONL (end-to-end)
# ---------------------------------------------------------------------------

class TestRebuildFromJsonl:
    def test_full_lifecycle_sparse_search(self, tmp_path):
        """End-to-end: ingest -> extract -> approve -> promote -> search."""
        cell_path = _make_cell(tmp_path)

        # Ingest multiple sources and promote traces
        source_path_1 = tmp_path / "s1.md"
        source_path_1.write_text(
            "Always handle exceptions gracefully in production code.",
            encoding="utf-8",
        )
        src1 = ingest_source(cell_path, source_path_1, kind="lesson", metadata={})
        frags1 = extract_fragments(cell_path, src1)
        approve_fragment(
            cell_path, frags1[0].fragment_id,
            reviewer="alice", rationale="good",
        )
        trace1 = promote_fragment(
            cell_path, frags1[0].fragment_id, promoter="alice",
        )

        source_path_2 = tmp_path / "s2.md"
        source_path_2.write_text(
            "Use type hints to improve code readability and catch errors early.",
            encoding="utf-8",
        )
        src2 = ingest_source(cell_path, source_path_2, kind="lesson", metadata={})
        frags2 = extract_fragments(cell_path, src2)
        approve_fragment(
            cell_path, frags2[0].fragment_id,
            reviewer="bob", rationale="solid",
        )
        trace2 = promote_fragment(
            cell_path, frags2[0].fragment_id, promoter="bob",
        )

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(conn, cell_path)
            assert count == 2

            # Search for exception-related content
            results = query_sparse(conn, "exception")
            assert len(results) >= 1
            assert any(r.trace_id == trace1.trace_id for r in results)

            # Search for type-hint content
            results = query_sparse(conn, "type hints")
            assert len(results) >= 1
            assert any(r.trace_id == trace2.trace_id for r in results)
        finally:
            conn.close()

    def test_rebuild_after_db_delete_restores_index(self, tmp_path):
        """Sparse index is rebuildable from JSONL after DB deletion."""
        cell_path = _make_cell(tmp_path)
        _ingest_and_promote(cell_path, tmp_path, "Rebuild after delete test.")

        db = tmp_path / "sparse.db"
        conn = open_sparse_index(db)
        try:
            rebuild_sparse_index(conn, cell_path)
            results = query_sparse(conn, "rebuild")
            assert len(results) >= 1
        finally:
            conn.close()

        # Delete and rebuild
        db.unlink()
        conn2 = open_sparse_index(db)
        try:
            count = rebuild_sparse_index(conn2, cell_path)
            assert count == 1
            results = query_sparse(conn2, "rebuild")
            assert len(results) >= 1
        finally:
            conn2.close()
