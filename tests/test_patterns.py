"""Tests for ShyftR Alloy distillation (Work slice 12).

Covers:
- Clustering by tags, kind, sparse overlap, and vector similarity
- Duplicate detection
- Conflict detection
- Alloy proposal generation with source Trace ID preservation
- Append-only ledger semantics for alloys/proposed.jsonl
- Alloys remain proposals and do not silently promote Doctrine
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from shyftr.distill.alloys import (
    Cluster,
    _cosine,
    _jaccard,
    _tokenize,
    append_alloys_to_proposed,
    cluster_traces,
    detect_conflicts,
    detect_duplicates,
    distill_alloys,
    propose_alloys,
    read_approved_traces,
)
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.models import Alloy, Trace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_trace(
    trace_id: str,
    cell_id: str = "test-cell",
    statement: str = "default statement",
    tags: list | None = None,
    status: str = "approved",
    confidence: float | None = None,
    rationale: str | None = None,
) -> Trace:
    return Trace(
        trace_id=trace_id,
        cell_id=cell_id,
        statement=statement,
        source_fragment_ids=[f"frag-{trace_id}"],
        rationale=rationale,
        status=status,
        confidence=confidence,
        tags=tags or [],
    )


@pytest.fixture
def cell_root(tmp_path: Path) -> Path:
    """Create a temporary Cell with seeded ledgers."""
    cell_path = init_cell(tmp_path, "test-cell")
    return cell_path


def _seed_approved_traces(cell_path: Path, traces: list[Trace]) -> None:
    """Write traces to traces/approved.jsonl."""
    ledger_path = cell_path / "traces" / "approved.jsonl"
    for trace in traces:
        append_jsonl(ledger_path, trace.to_dict())


# ---------------------------------------------------------------------------
# Tokenization and similarity helpers
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_basic_tokens(self):
        tokens = _tokenize("Hello World 123")
        assert tokens == {"hello", "world", "123"}

    def test_empty_string(self):
        assert _tokenize("") == set()

    def test_punctuation_stripped(self):
        tokens = _tokenize("foo-bar, baz!")
        assert tokens == {"foobar", "baz"}


class TestJaccard:
    def test_identical(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_partial(self):
        assert _jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)


class TestCosine:
    def test_identical(self):
        assert _cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_vector(self):
        assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    def test_no_duplicates(self):
        traces = [
            _make_trace("t1", statement="alpha"),
            _make_trace("t2", statement="beta"),
        ]
        assert detect_duplicates(traces) == []

    def test_exact_duplicates(self):
        traces = [
            _make_trace("t1", statement="use evidence links"),
            _make_trace("t2", statement="use evidence links"),
        ]
        dups = detect_duplicates(traces)
        assert len(dups) == 1
        assert ("t1", "t2") in dups or ("t2", "t1") in dups

    def test_case_insensitive(self):
        traces = [
            _make_trace("t1", statement="Prefer Evidence"),
            _make_trace("t2", statement="prefer evidence"),
        ]
        dups = detect_duplicates(traces)
        assert len(dups) == 1


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    def test_no_conflict_different_tags(self):
        traces = [
            _make_trace("t1", statement="never skip reviews", tags=["review"]),
            _make_trace("t2", statement="always skip reviews", tags=["testing"]),
        ]
        assert detect_conflicts(traces) == []

    def test_conflict_same_tags_opposite_polarity(self):
        traces = [
            _make_trace(
                "t1",
                statement="never skip reviews for memory fragments",
                tags=["review", "memory"],
            ),
            _make_trace(
                "t2",
                statement="always skip reviews for memory fragments",
                tags=["review", "memory"],
            ),
        ]
        conflicts = detect_conflicts(traces)
        assert len(conflicts) == 1
        assert ("t1", "t2") in conflicts or ("t2", "t1") in conflicts

    def test_no_conflict_same_polarity(self):
        traces = [
            _make_trace(
                "t1",
                statement="always review memory fragments carefully",
                tags=["review", "memory"],
            ),
            _make_trace(
                "t2",
                statement="always review memory fragments thoroughly",
                tags=["review", "memory"],
            ),
        ]
        assert detect_conflicts(traces) == []


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

class TestClustering:
    def test_cluster_by_shared_tags(self):
        traces = [
            _make_trace("t1", tags=["memory", "evidence"], statement="alpha beta"),
            _make_trace("t2", tags=["memory", "evidence"], statement="gamma delta"),
            _make_trace("t3", tags=["unrelated"], statement="epsilon zeta"),
        ]
        clusters = cluster_traces(traces)
        assert len(clusters) >= 1
        # t1 and t2 should be in the same cluster
        all_members = set()
        for c in clusters:
            all_members |= c.trace_ids
        assert "t1" in all_members
        assert "t2" in all_members

    def test_cluster_by_kind_and_overlap(self):
        traces = [
            _make_trace(
                "t1",
                statement="prefer evidence linked memories for review",
            ),
            _make_trace(
                "t2",
                statement="prefer evidence linked memories for testing",
            ),
        ]
        clusters = cluster_traces(
            traces, tag_overlap_threshold=1.0, sparse_overlap_threshold=0.3
        )
        assert len(clusters) >= 1
        member_ids = set(clusters[0].trace_ids)
        assert "t1" in member_ids
        assert "t2" in member_ids

    def test_cluster_by_vector_similarity(self):
        traces = [
            _make_trace("t1", statement="alpha"),
            _make_trace("t2", statement="beta"),
        ]
        vectors = {
            "t1": [1.0, 0.0, 0.0],
            "t2": [0.9, 0.1, 0.0],
        }
        clusters = cluster_traces(
            traces,
            tag_overlap_threshold=1.0,  # no shared tags
            sparse_overlap_threshold=1.0,  # no overlap
            vector_threshold=0.8,
            vectors=vectors,
        )
        assert len(clusters) >= 1
        member_ids = set(clusters[0].trace_ids)
        assert "t1" in member_ids
        assert "t2" in member_ids

    def test_singletons_skipped(self):
        traces = [
            _make_trace("t1", tags=["alpha"], statement="one"),
            _make_trace("t2", tags=["beta"], statement="two"),
        ]
        clusters = cluster_traces(traces)
        assert len(clusters) == 0

    def test_non_approved_traces_excluded(self):
        traces = [
            _make_trace("t1", status="approved", tags=["x"]),
            _make_trace("t2", status="approved", tags=["x"]),
            _make_trace("t3", status="proposed", tags=["x"]),
        ]
        clusters = cluster_traces(traces)
        for c in clusters:
            assert "t3" not in c.trace_ids


# ---------------------------------------------------------------------------
# Alloy proposal generation
# ---------------------------------------------------------------------------

class TestAlloyProposal:
    def test_proposal_preserves_source_trace_ids(self):
        traces = [
            _make_trace("t1", tags=["a", "b"], statement="stmt one"),
            _make_trace("t2", tags=["a", "b"], statement="stmt two"),
        ]
        clusters = cluster_traces(traces)
        assert len(clusters) == 1

        traces_by_id = {t.trace_id: t for t in traces}
        alloys = propose_alloys(clusters, traces_by_id)
        assert len(alloys) == 1
        assert set(alloys[0].source_trace_ids) == {"t1", "t2"}

    def test_singletons_produce_no_alloys(self):
        traces = [
            _make_trace("t1", tags=["unique"], statement="solo"),
        ]
        clusters = cluster_traces(traces)
        traces_by_id = {t.trace_id: t for t in traces}
        alloys = propose_alloys(clusters, traces_by_id)
        assert len(alloys) == 0

    def test_alloy_status_is_proposed(self):
        traces = [
            _make_trace("t1", tags=["x", "y"], statement="alpha"),
            _make_trace("t2", tags=["x", "y"], statement="beta"),
        ]
        clusters = cluster_traces(traces)
        traces_by_id = {t.trace_id: t for t in traces}
        alloys = propose_alloys(clusters, traces_by_id)
        assert alloys[0].proposal_status == "proposed"

    def test_alloy_deterministic_id(self):
        traces = [
            _make_trace("t1", tags=["x"], statement="a"),
            _make_trace("t2", tags=["x"], statement="b"),
        ]
        clusters = cluster_traces(traces)
        traces_by_id = {t.trace_id: t for t in traces}
        alloys_1 = propose_alloys(clusters, traces_by_id)
        alloys_2 = propose_alloys(clusters, traces_by_id)
        assert alloys_1[0].alloy_id == alloys_2[0].alloy_id


# ---------------------------------------------------------------------------
# Ledger integration
# ---------------------------------------------------------------------------

class TestLedgerIntegration:
    def test_append_to_proposed_jsonl(self, cell_root: Path):
        alloy = Alloy(
            alloy_id="alloy-test-001",
            cell_id="test-cell",
            theme="test theme",
            summary="test summary",
            source_trace_ids=["t1", "t2"],
            proposal_status="proposed",
        )
        count = append_alloys_to_proposed(cell_root, [alloy])
        assert count == 1

        ledger_path = cell_root / "alloys" / "proposed.jsonl"
        lines = ledger_path.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["alloy_id"] == "alloy-test-001"
        assert record["source_trace_ids"] == ["t1", "t2"]

    def test_append_only_semantics(self, cell_root: Path):
        alloy_1 = Alloy(
            alloy_id="alloy-a",
            cell_id="test-cell",
            theme="t1",
            summary="s1",
            source_trace_ids=["t1"],
        )
        alloy_2 = Alloy(
            alloy_id="alloy-b",
            cell_id="test-cell",
            theme="t2",
            summary="s2",
            source_trace_ids=["t2"],
        )
        append_alloys_to_proposed(cell_root, [alloy_1])
        append_alloys_to_proposed(cell_root, [alloy_2])

        ledger_path = cell_root / "alloys" / "proposed.jsonl"
        lines = ledger_path.read_text().strip().split("\n")
        assert len(lines) == 2
        ids = [json.loads(line)["alloy_id"] for line in lines]
        assert ids == ["alloy-a", "alloy-b"]

    def test_read_approved_traces(self, cell_root: Path):
        traces = [
            _make_trace("t1", statement="alpha"),
            _make_trace("t2", statement="beta"),
        ]
        _seed_approved_traces(cell_root, traces)
        loaded = read_approved_traces(cell_root)
        assert len(loaded) == 2
        assert loaded[0].trace_id == "t1"


# ---------------------------------------------------------------------------
# Safety: Alloys do not promote Doctrine
# ---------------------------------------------------------------------------

class TestSafetyNoDoctrinePromotion:
    def test_alloys_do_not_write_to_doctrine(self, cell_root: Path):
        """Alloys must never write to doctrine/approved.jsonl."""
        traces = [
            _make_trace("t1", tags=["x"], statement="alpha"),
            _make_trace("t2", tags=["x"], statement="beta"),
        ]
        _seed_approved_traces(cell_root, traces)
        result = distill_alloys(cell_root)

        doctrine_path = cell_root / "doctrine" / "approved.jsonl"
        assert not doctrine_path.exists() or doctrine_path.stat().st_size == 0

    def test_alloys_do_not_write_to_alloys_approved(self, cell_root: Path):
        """Alloys must never write to alloys/approved.jsonl."""
        traces = [
            _make_trace("t1", tags=["x"], statement="alpha"),
            _make_trace("t2", tags=["x"], statement="beta"),
        ]
        _seed_approved_traces(cell_root, traces)
        distill_alloys(cell_root)

        approved_path = cell_root / "alloys" / "approved.jsonl"
        assert not approved_path.exists() or approved_path.stat().st_size == 0

    def test_alloys_do_not_mutate_trace_status(self, cell_root: Path):
        """Alloys must not change Trace status in traces/approved.jsonl."""
        traces = [
            _make_trace("t1", tags=["x"], statement="alpha", status="approved"),
            _make_trace("t2", tags=["x"], statement="beta", status="approved"),
        ]
        _seed_approved_traces(cell_root, traces)
        distill_alloys(cell_root)

        loaded = read_approved_traces(cell_root)
        for trace in loaded:
            assert trace.status == "approved"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestDistillAlloys:
    def test_full_pipeline(self, cell_root: Path):
        traces = [
            _make_trace(
                "t1",
                tags=["memory", "review"],
                statement="always review memory fragments",
                confidence=0.8,
            ),
            _make_trace(
                "t2",
                tags=["memory", "review"],
                statement="review memory fragments before promotion",
                confidence=0.7,
            ),
            _make_trace(
                "t3",
                tags=["testing"],
                statement="run tests before commit",
                confidence=0.9,
            ),
        ]
        _seed_approved_traces(cell_root, traces)
        result = distill_alloys(cell_root)

        assert result["trace_count"] == 3
        assert result["cluster_count"] >= 1
        assert result["alloy_count"] >= 1

        # Verify alloys were written
        ledger_path = cell_root / "alloys" / "proposed.jsonl"
        lines = ledger_path.read_text().strip().split("\n")
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert record["proposal_status"] == "proposed"
        assert len(record["source_trace_ids"]) >= 2

    def test_pipeline_with_no_approved_traces(self, cell_root: Path):
        result = distill_alloys(cell_root)
        assert result["trace_count"] == 0
        assert result["cluster_count"] == 0
        assert result["alloy_count"] == 0

    def test_pipeline_detects_duplicates(self, cell_root: Path):
        traces = [
            _make_trace("t1", tags=["x"], statement="identical statement"),
            _make_trace("t2", tags=["x"], statement="identical statement"),
        ]
        _seed_approved_traces(cell_root, traces)
        result = distill_alloys(cell_root)
        assert len(result["duplicates"]) == 1
