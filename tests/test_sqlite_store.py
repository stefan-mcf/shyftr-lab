"""Tests for ShyftR SQLite metadata store (Work slice 6)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_source
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.promote import promote_fragment
from shyftr.review import approve_fragment, reject_fragment
from shyftr.store.sqlite import (
    latest_review_for_fragment,
    open_sqlite,
    rebuild_from_cell,
    trace_lifecycle_view,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cell(tmp_path: Path) -> Path:
    """Create a Cell and return its path."""
    return init_cell(tmp_path, "test-cell")


def _ingest_and_extract(cell_path: Path, tmp_path: Path, text: str):
    """Ingest a source file and extract fragments. Return (source, fragments)."""
    source_path = tmp_path / "source.md"
    source_path.write_text(text, encoding="utf-8")
    source = ingest_source(cell_path, source_path, kind="lesson", metadata={})
    fragments = extract_fragments(cell_path, source)
    return source, fragments


def _promote_first_fragment(cell_path: Path, fragment):
    """Approve and promote a fragment. Return the trace."""
    approve_fragment(
        cell_path, fragment.fragment_id,
        reviewer="test-reviewer", rationale="durable and bounded",
    )
    return promote_fragment(
        cell_path, fragment.fragment_id, promoter="test-promoter",
    )


# ---------------------------------------------------------------------------
# Tests: open_sqlite
# ---------------------------------------------------------------------------

class TestOpenSqlite:
    def test_creates_database_file(self, tmp_path):
        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            assert db.exists()
        finally:
            conn.close()

    def test_wal_mode_is_enabled(self, tmp_path):
        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"
        finally:
            conn.close()

    def test_creates_parent_directories(self, tmp_path):
        db = tmp_path / "nested" / "deep" / "store.db"
        conn = open_sqlite(db)
        try:
            assert db.exists()
        finally:
            conn.close()

    def test_all_tables_exist(self, tmp_path):
        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            expected = {
                "sources", "fragments", "traces", "reviews",
                "promotions", "retrieval_logs", "outcomes",
                "confidence_events", "retrieval_affinity_events",
                "audit_sparks", "audit_reviews",
            }
            assert expected.issubset(tables)
        finally:
            conn.close()

    def test_views_exist(self, tmp_path):
        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            views = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='view'"
                ).fetchall()
            }
            assert "v_latest_fragment_review" in views
            assert "v_trace_lifecycle" in views
        finally:
            conn.close()

    def test_idempotent_open(self, tmp_path):
        db = tmp_path / "store.db"
        conn1 = open_sqlite(db)
        conn1.close()
        conn2 = open_sqlite(db)
        try:
            # Should not raise; schema is applied idempotently
            count = conn2.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            assert count >= 11
        finally:
            conn2.close()


# ---------------------------------------------------------------------------
# Tests: rebuild_from_cell
# ---------------------------------------------------------------------------

class TestRebuildFromCell:
    def test_rebuild_populates_sources(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        source, _ = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: always verify before deploying.",
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            rows = conn.execute("SELECT * FROM sources").fetchall()
            assert len(rows) == 1
            assert rows[0][0] == source.source_id  # source_id column
        finally:
            conn.close()

    def test_rebuild_populates_fragments(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: always verify before deploying.",
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            rows = conn.execute("SELECT * FROM fragments").fetchall()
            assert len(rows) >= 1
            fragment_ids = {row[0] for row in rows}
            assert fragments[0].fragment_id in fragment_ids
        finally:
            conn.close()

    def test_rebuild_populates_traces_after_promotion(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: always verify before deploying.",
        )
        trace = _promote_first_fragment(cell_path, fragments[0])

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            rows = conn.execute("SELECT * FROM traces").fetchall()
            assert len(rows) == 1
            assert rows[0][0] == trace.trace_id
        finally:
            conn.close()

    def test_rebuild_populates_reviews(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: always verify before deploying.",
        )
        approve_fragment(
            cell_path, fragments[0].fragment_id,
            reviewer="alice", rationale="solid",
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            rows = conn.execute("SELECT * FROM reviews").fetchall()
            assert len(rows) == 1
            assert rows[0][2] == "approve"  # review_action (col index 2)
        finally:
            conn.close()

    def test_rebuild_populates_promotions(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: always verify before deploying.",
        )
        _promote_first_fragment(cell_path, fragments[0])

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            rows = conn.execute("SELECT * FROM promotions").fetchall()
            assert len(rows) == 1
        finally:
            conn.close()

    def test_rebuild_tolerates_empty_ledgers(self, tmp_path):
        cell_path = _make_cell(tmp_path)

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            for table in ("sources", "fragments", "traces", "reviews",
                           "promotions", "retrieval_logs", "outcomes",
                           "confidence_events", "retrieval_affinity_events",
                           "audit_sparks", "audit_reviews"):
                assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        finally:
            conn.close()

    def test_rebuild_retrieval_logs_accepts_legacy_generated_at_alias(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        append_jsonl(
            cell_path / "ledger" / "retrieval_logs.jsonl",
            {
                "retrieval_id": "rl-legacy",
                "loadout_id": "lo-legacy",
                "query": "legacy query",
                "selected_ids": ["trace-1"],
                "score_traces": {"trace-1": {"semantic_score": 0.9}},
                "generated_at": "2026-05-07T00:00:00+00:00",
            },
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            row = conn.execute(
                "SELECT retrieval_id, cell_id, query, logged_at FROM retrieval_logs WHERE retrieval_id = ?",
                ("rl-legacy",),
            ).fetchone()
            assert row == ("rl-legacy", "test-cell", "legacy query", "2026-05-07T00:00:00+00:00")
        finally:
            conn.close()

    def test_rebuild_materializes_active_learning_ledgers(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        append_jsonl(
            cell_path / "ledger" / "confidence_events.jsonl",
            {
                "confidence_event_id": "ce-1",
                "cell_id": "test-cell",
                "fragment_id": "fragment-1",
                "confidence": 0.7,
                "reason": "successful reuse",
                "observed_at": "2026-04-25T00:00:00+00:00",
            },
        )
        append_jsonl(
            cell_path / "ledger" / "retrieval_affinity_events.jsonl",
            {
                "affinity_event_id": "ra-1",
                "cell_id": "test-cell",
                "query": "retry queue lock",
                "result_id": "trace-1",
                "score": 0.42,
                "observed_at": "2026-04-25T00:01:00+00:00",
            },
        )
        append_jsonl(
            cell_path / "ledger" / "audit_sparks.jsonl",
            {
                "spark_id": "as-1",
                "cell_id": "test-cell",
                "fragment_id": "fragment-1",
                "action": "challenge",
                "rationale": "counter-evidence found",
                "observed_at": "2026-04-25T00:02:00+00:00",
            },
        )
        append_jsonl(
            cell_path / "ledger" / "audit_reviews.jsonl",
            {
                "review_id": "ar-1",
                "cell_id": "test-cell",
                "spark_id": "as-1",
                "decision": "accepted",
                "reviewer": "regulator",
                "reviewed_at": "2026-04-25T00:03:00+00:00",
                "rationale": "valid audit finding",
            },
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)

            assert conn.execute(
                "SELECT fragment_id, confidence, reason FROM confidence_events"
            ).fetchone() == ("fragment-1", 0.7, "successful reuse")
            assert conn.execute(
                "SELECT query, result_id, score FROM retrieval_affinity_events"
            ).fetchone() == ("retry queue lock", "trace-1", 0.42)
            assert conn.execute(
                "SELECT fragment_id, action, rationale FROM audit_sparks"
            ).fetchone() == ("fragment-1", "challenge", "counter-evidence found")
            assert conn.execute(
                "SELECT spark_id, decision, reviewer FROM audit_reviews"
            ).fetchone() == ("as-1", "accepted", "regulator")
        finally:
            conn.close()

    def test_rebuild_is_deterministic(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: always verify before deploying.",
        )
        append_jsonl(
            cell_path / "ledger" / "confidence_events.jsonl",
            {
                "confidence_event_id": "ce-1",
                "cell_id": "test-cell",
                "confidence": 0.8,
            },
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            first_sources = conn.execute(
                "SELECT source_id FROM sources"
            ).fetchall()
            first_confidence_events = conn.execute(
                "SELECT confidence_event_id, confidence FROM confidence_events"
            ).fetchall()

            # Rebuild again
            rebuild_from_cell(conn, cell_path)
            second_sources = conn.execute(
                "SELECT source_id FROM sources"
            ).fetchall()
            second_confidence_events = conn.execute(
                "SELECT confidence_event_id, confidence FROM confidence_events"
            ).fetchall()

            assert first_sources == second_sources
            assert first_confidence_events == second_confidence_events
        finally:
            conn.close()

    def test_rebuild_clears_stale_rows(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: always verify before deploying.",
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            assert conn.execute("SELECT count(*) FROM sources").fetchone()[0] == 1

            # Manually insert a stale row with the same cell_id but a non-existent source_id
            conn.execute(
                "INSERT INTO sources (source_id, cell_id, kind, sha256, captured_at) "
                "VALUES ('stale-id', 'test-cell', 'x', '0', '2020-01-01')"
            )
            conn.commit()
            assert conn.execute("SELECT count(*) FROM sources").fetchone()[0] == 2

            # Rebuild should clear stale rows
            rebuild_from_cell(conn, cell_path)
            assert conn.execute("SELECT count(*) FROM sources").fetchone()[0] == 1
        finally:
            conn.close()

    def test_rebuild_preserves_json_payloads(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        source_path = tmp_path / "source.md"
        source_path.write_text("Durable lesson: test metadata preservation.", encoding="utf-8")
        source = ingest_source(
            cell_path, source_path, kind="lesson",
            metadata={"custom_key": "custom_value"},
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            row = conn.execute(
                "SELECT metadata FROM sources WHERE source_id = ?",
                (source.source_id,),
            ).fetchone()
            assert row is not None
            import json
            meta = json.loads(row[0])
            assert meta["custom_key"] == "custom_value"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Tests: latest review view
# ---------------------------------------------------------------------------

class TestLatestReviewView:
    def test_returns_latest_review_for_fragment(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: test review views.",
        )
        fid = fragments[0].fragment_id

        approve_fragment(
            cell_path, fid, reviewer="alice", rationale="first approve",
        )
        reject_fragment(
            cell_path, fid, reviewer="bob", rationale="superseded",
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            review = latest_review_for_fragment(conn, fid)
            assert review is not None
            assert review["review_action"] == "reject"
            assert review["reviewer"] == "bob"
        finally:
            conn.close()

    def test_uses_ledger_order_to_break_review_timestamp_ties(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: ledger order breaks review timestamp ties.",
        )
        fid = fragments[0].fragment_id
        timestamp = "2026-04-24T00:00:00+00:00"
        append_jsonl(
            cell_path / "ledger" / "reviews.jsonl",
            {
                "review_id": "rev-first",
                "fragment_id": fid,
                "review_action": "approve",
                "review_status": "approved",
                "reviewed_at": timestamp,
                "reviewer": "alice",
                "rationale": "first",
                "metadata": {},
            },
        )
        append_jsonl(
            cell_path / "ledger" / "reviews.jsonl",
            {
                "review_id": "rev-second",
                "fragment_id": fid,
                "review_action": "reject",
                "review_status": "rejected",
                "reviewed_at": timestamp,
                "reviewer": "bob",
                "rationale": "append latest",
                "metadata": {},
            },
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            rows = conn.execute(
                "SELECT * FROM v_latest_fragment_review WHERE fragment_id = ?",
                (fid,),
            ).fetchall()
            review = latest_review_for_fragment(conn, fid)
            assert len(rows) == 1
            assert review is not None
            assert review["review_action"] == "reject"
            assert review["reviewer"] == "bob"
        finally:
            conn.close()

    def test_returns_none_for_unreviewed_fragment(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: no review yet.",
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            review = latest_review_for_fragment(conn, fragments[0].fragment_id)
            assert review is None
        finally:
            conn.close()

    def test_returns_none_for_unknown_fragment(self, tmp_path):
        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            review = latest_review_for_fragment(conn, "nonexistent-fragment-id")
            assert review is None
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Tests: trace lifecycle view
# ---------------------------------------------------------------------------

class TestTraceLifecycleView:
    def test_approved_trace_shows_current(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: lifecycle state test.",
        )
        trace = _promote_first_fragment(cell_path, fragments[0])

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            view = trace_lifecycle_view(conn, cell_id="test-cell")
            assert len(view) == 1
            assert view[0]["trace_id"] == trace.trace_id
            assert view[0]["lifecycle_state"] == "current"
            assert view[0]["status"] == "approved"
        finally:
            conn.close()

    def test_empty_cell_returns_no_traces(self, tmp_path):
        cell_path = _make_cell(tmp_path)

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            view = trace_lifecycle_view(conn)
            assert view == []
        finally:
            conn.close()

    def test_filter_by_cell_id(self, tmp_path):
        cell_a = init_cell(tmp_path, "cell-a")
        cell_b = init_cell(tmp_path, "cell-b")

        # Create trace in cell-a
        source_a_path = tmp_path / "a.md"
        source_a_path.write_text("Durable lesson: cell a.", encoding="utf-8")
        src_a = ingest_source(cell_a, source_a_path, kind="lesson", metadata={})
        frags_a = extract_fragments(cell_a, src_a)
        _promote_first_fragment(cell_a, frags_a[0])

        # Create trace in cell-b
        source_b_path = tmp_path / "b.md"
        source_b_path.write_text("Durable lesson: cell b.", encoding="utf-8")
        src_b = ingest_source(cell_b, source_b_path, kind="lesson", metadata={})
        frags_b = extract_fragments(cell_b, src_b)
        _promote_first_fragment(cell_b, frags_b[0])

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_a)
            rebuild_from_cell(conn, cell_b)

            view_a = trace_lifecycle_view(conn, cell_id="cell-a")
            assert len(view_a) == 1
            assert view_a[0]["cell_id"] == "cell-a"

            view_b = trace_lifecycle_view(conn, cell_id="cell-b")
            assert len(view_b) == 1
            assert view_b[0]["cell_id"] == "cell-b"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Tests: SQLite is not canonical truth
# ---------------------------------------------------------------------------

class TestSqliteIsNotCanonical:
    def test_rebuild_after_deleting_db_restores_from_jsonl(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        source, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: rebuild proves JSONL is canonical.",
        )
        trace = _promote_first_fragment(cell_path, fragments[0])

        db = tmp_path / "store.db"

        # First build
        conn = open_sqlite(db)
        rebuild_from_cell(conn, cell_path)
        original_sources = conn.execute("SELECT count(*) FROM sources").fetchone()[0]
        original_traces = conn.execute("SELECT count(*) FROM traces").fetchone()[0]
        conn.close()

        # Delete the database
        db.unlink()
        assert not db.exists()

        # Rebuild from JSONL only
        conn = open_sqlite(db)
        rebuild_from_cell(conn, cell_path)
        restored_sources = conn.execute("SELECT count(*) FROM sources").fetchone()[0]
        restored_traces = conn.execute("SELECT count(*) FROM traces").fetchone()[0]
        conn.close()

        assert restored_sources == original_sources
        assert restored_traces == original_traces

        # Verify the trace is still correct
        conn = open_sqlite(db)
        row = conn.execute(
            "SELECT trace_id, statement FROM traces"
        ).fetchone()
        conn.close()
        assert row[0] == trace.trace_id
        assert row[1] == trace.statement

    def test_jsonl_ledgers_still_readable_after_sqlite_rebuild(self, tmp_path):
        cell_path = _make_cell(tmp_path)
        source, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: JSONL survives SQLite operations.",
        )

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        rebuild_from_cell(conn, cell_path)
        conn.close()

        # JSONL should still be readable and unchanged
        sources = list(read_jsonl(cell_path / "ledger" / "sources.jsonl"))
        assert len(sources) == 1
        assert sources[0][1].get("source_id") == source.source_id


# ---------------------------------------------------------------------------
# Tests: full integration flow
# ---------------------------------------------------------------------------

class TestFullRebuildFlow:
    def test_full_lifecycle_rebuild(self, tmp_path):
        """End-to-end: ingest -> extract -> review -> promote -> rebuild -> query."""
        cell_path = _make_cell(tmp_path)

        # Ingest multiple sources
        source1_path = tmp_path / "lesson1.md"
        source1_path.write_text(
            "Durable lesson: use focused tests before full-suite verification.",
            encoding="utf-8",
        )
        src1 = ingest_source(cell_path, source1_path, kind="lesson", metadata={})
        frags1 = extract_fragments(cell_path, src1)

        source2_path = tmp_path / "lesson2.md"
        source2_path.write_text(
            "Durable lesson: keep SQLite as acceleration only, not canonical truth.",
            encoding="utf-8",
        )
        src2 = ingest_source(cell_path, source2_path, kind="lesson", metadata={})
        frags2 = extract_fragments(cell_path, src2)

        # Review fragments (do NOT pre-approve frags1; _promote_first_fragment does it)
        reject_fragment(
            cell_path, frags2[0].fragment_id,
            reviewer="bob", rationale="too vague",
        )

        # Promote the first fragment (this also approves it)
        trace = _promote_first_fragment(cell_path, frags1[0])

        # Rebuild SQLite
        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)

            # Verify counts
            assert conn.execute("SELECT count(*) FROM sources").fetchone()[0] == 2
            assert conn.execute("SELECT count(*) FROM fragments").fetchone()[0] == 2
            assert conn.execute("SELECT count(*) FROM traces").fetchone()[0] == 1
            assert conn.execute("SELECT count(*) FROM reviews").fetchone()[0] == 2
            assert conn.execute("SELECT count(*) FROM promotions").fetchone()[0] == 1

            # Verify latest review view
            review1 = latest_review_for_fragment(conn, frags1[0].fragment_id)
            assert review1["review_action"] == "approve"
            assert review1["reviewer"] == "test-reviewer"

            review2 = latest_review_for_fragment(conn, frags2[0].fragment_id)
            assert review2["review_action"] == "reject"
            assert review2["reviewer"] == "bob"

            # Verify trace lifecycle view
            lifecycle = trace_lifecycle_view(conn, cell_id="test-cell")
            assert len(lifecycle) == 1
            assert lifecycle[0]["trace_id"] == trace.trace_id
            assert lifecycle[0]["lifecycle_state"] == "current"
        finally:
            conn.close()

    def test_multiple_approve_reject_cycle(self, tmp_path):
        """Test approve -> reject -> approve shows latest as approved."""
        cell_path = _make_cell(tmp_path)
        _, fragments = _ingest_and_extract(
            cell_path, tmp_path,
            "Durable lesson: review cycle test.",
        )
        fid = fragments[0].fragment_id

        approve_fragment(cell_path, fid, reviewer="alice", rationale="good")
        reject_fragment(cell_path, fid, reviewer="bob", rationale="needs work")
        approve_fragment(cell_path, fid, reviewer="carol", rationale="fixed")

        db = tmp_path / "store.db"
        conn = open_sqlite(db)
        try:
            rebuild_from_cell(conn, cell_path)
            review = latest_review_for_fragment(conn, fid)
            assert review["review_action"] == "approve"
            assert review["reviewer"] == "carol"
        finally:
            conn.close()
