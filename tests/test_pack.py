"""Tests for bounded memory Loadout assembly (Work slice 10).

All tests are dependency-free and network-free.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.loadout import (
    LOADOUT_ROLES,
    AssembledLoadout,
    LoadoutItem,
    LoadoutTaskInput,
    RetrievalLog,
    assemble_loadout,
    estimate_tokens,
    is_operational_state,
)
from shyftr.retrieval.hybrid import CandidateItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cell(tmp: Path, cell_id: str = "test-cell") -> Path:
    """Create a minimal Cell with seeded ledgers."""
    return init_cell(tmp, cell_id)


def _seed_traces(cell_path: Path, traces: list[dict]) -> None:
    """Append trace records to traces/approved.jsonl."""
    ledger = cell_path / "traces" / "approved.jsonl"
    for t in traces:
        append_jsonl(ledger, t)


def _seed_alloys(cell_path: Path, alloys: list[dict]) -> None:
    """Append alloy records to alloys/approved.jsonl."""
    ledger = cell_path / "alloys" / "approved.jsonl"
    for a in alloys:
        append_jsonl(ledger, a)


def _seed_doctrine(cell_path: Path, doctrines: list[dict]) -> None:
    """Append doctrine records to doctrine/approved.jsonl."""
    ledger = cell_path / "doctrine" / "approved.jsonl"
    for d in doctrines:
        append_jsonl(ledger, d)


def _seed_fragments(cell_path: Path, fragments: list[dict]) -> None:
    """Append fragment records to ledger/fragments.jsonl."""
    ledger = cell_path / "ledger" / "fragments.jsonl"
    for f in fragments:
        append_jsonl(ledger, f)


def _make_trace(trace_id: str = "t1", **overrides) -> dict:
    base = {
        "trace_id": trace_id,
        "cell_id": "test-cell",
        "statement": f"Statement for {trace_id}",
        "rationale": f"Rationale for {trace_id}",
        "source_fragment_ids": ["f1"],
        "status": "approved",
        "confidence": 0.8,
        "tags": ["python"],
        "kind": "error",
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
    }
    base.update(overrides)
    return base


def _make_alloy(alloy_id: str = "a1", **overrides) -> dict:
    base = {
        "alloy_id": alloy_id,
        "cell_id": "test-cell",
        "theme": f"Theme for {alloy_id}",
        "summary": f"Summary for {alloy_id}",
        "source_trace_ids": ["t1"],
        "proposal_status": "approved",
        "confidence": 0.7,
    }
    base.update(overrides)
    return base


def _make_doctrine(doctrine_id: str = "d1", **overrides) -> dict:
    base = {
        "doctrine_id": doctrine_id,
        "source_alloy_ids": ["a1"],
        "scope": "global",
        "statement": f"Doctrine statement for {doctrine_id}",
        "review_status": "approved",
    }
    base.update(overrides)
    return base


def _make_fragment(fragment_id: str = "f1", **overrides) -> dict:
    base = {
        "fragment_id": fragment_id,
        "source_id": "s1",
        "cell_id": "test-cell",
        "kind": "observation",
        "text": f"Fragment text for {fragment_id}",
        "boundary_status": "passed",
        "review_status": "approved",
        "confidence": 0.6,
        "tags": ["python"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Task input schema validation / defaults
# ---------------------------------------------------------------------------

class TestLoadoutTaskInput:
    def test_required_fields(self):
        inp = LoadoutTaskInput(
            cell_path="/tmp/cell",
            query="test query",
            task_id="task-1",
        )
        assert inp.cell_path == "/tmp/cell"
        assert inp.query == "test query"
        assert inp.task_id == "task-1"

    def test_defaults(self):
        inp = LoadoutTaskInput(
            cell_path="/tmp/cell",
            query="q",
            task_id="t1",
        )
        assert inp.max_items == 20
        assert inp.max_tokens == 4000
        assert inp.include_fragments is False
        assert inp.query_kind is None
        assert inp.query_tags is None

    def test_custom_limits(self):
        inp = LoadoutTaskInput(
            cell_path="/tmp/cell",
            query="q",
            task_id="t1",
            max_items=5,
            max_tokens=1000,
            include_fragments=True,
            query_kind="error",
            query_tags=["python"],
        )
        assert inp.max_items == 5
        assert inp.max_tokens == 1000
        assert inp.include_fragments is True
        assert inp.query_kind == "error"
        assert inp.query_tags == ["python"]

    def test_serialization_roundtrip(self):
        inp = LoadoutTaskInput(
            cell_path="/tmp/cell",
            query="q",
            task_id="t1",
            max_items=5,
        )
        d = inp.to_dict()
        inp2 = LoadoutTaskInput.from_dict(d)
        assert inp2.cell_path == inp.cell_path
        assert inp2.max_items == inp.max_items


# ---------------------------------------------------------------------------
# Selected Loadout items are trust-tier labeled
# ---------------------------------------------------------------------------

class TestTrustTierLabeling:
    def test_items_have_trust_tier(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        for item in loadout.items:
            assert item.trust_tier in ("doctrine", "trace", "alloy", "fragment", "source")

    def test_doctrine_items_labeled_correctly(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_doctrine(cell, [_make_doctrine("d1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        doctrine_items = [i for i in loadout.items if i.trust_tier == "doctrine"]
        assert len(doctrine_items) == 1
        assert doctrine_items[0].item_id == "d1"


# ---------------------------------------------------------------------------
# Doctrine/Trace/Alloy/Fragment/Source-summary inputs can be assembled
# ---------------------------------------------------------------------------

class TestAssemblyFromMultipleSources:
    def test_assembles_traces_and_alloys(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1"), _make_trace("t2")])
        _seed_alloys(cell, [_make_alloy("a1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        tiers = {i.trust_tier for i in loadout.items}
        assert "trace" in tiers
        assert "alloy" in tiers

    def test_assembles_doctrine(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_doctrine(cell, [_make_doctrine("d1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        assert any(i.trust_tier == "doctrine" for i in loadout.items)

    def test_fragments_included_when_flag_set(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_fragments(cell, [_make_fragment("f1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
            include_fragments=True,
        )
        loadout = assemble_loadout(task)
        fragment_items = [i for i in loadout.items if i.trust_tier == "fragment"]
        assert len(fragment_items) == 1

    def test_fragments_excluded_by_default(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_fragments(cell, [_make_fragment("f1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        fragment_items = [i for i in loadout.items if i.trust_tier == "fragment"]
        assert len(fragment_items) == 0


# ---------------------------------------------------------------------------
# Item and token limits are enforced deterministically
# ---------------------------------------------------------------------------

class TestLimits:
    def test_max_items_enforced(self, tmp_path):
        cell = _make_cell(tmp_path)
        traces = [_make_trace(f"t{i}", statement=f"Statement {i}") for i in range(10)]
        _seed_traces(cell, traces)

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
            max_items=3,
        )
        loadout = assemble_loadout(task)
        assert len(loadout.items) <= 3
        assert loadout.total_items <= 3

    def test_max_tokens_enforced(self, tmp_path):
        cell = _make_cell(tmp_path)
        # Create traces with long statements to exceed token limit
        traces = [
            _make_trace(f"t{i}", statement="word " * 500)
            for i in range(5)
        ]
        _seed_traces(cell, traces)

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
            max_tokens=100,
            max_items=50,
        )
        loadout = assemble_loadout(task)
        assert loadout.total_tokens <= 100

    def test_limits_applied_in_priority_order(self, tmp_path):
        """Items are added in score order; limits truncate from the bottom."""
        cell = _make_cell(tmp_path)
        traces = [_make_trace(f"t{i}") for i in range(5)]
        _seed_traces(cell, traces)

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
            max_items=2,
        )
        loadout = assemble_loadout(task)
        assert len(loadout.items) == 2


# ---------------------------------------------------------------------------
# Retrieval log is appended with selected IDs and score traces
# ---------------------------------------------------------------------------

class TestRetrievalLog:
    def test_retrieval_log_created(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test query",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        log = loadout.retrieval_log
        assert isinstance(log, RetrievalLog)
        assert log.query == "test query"
        assert log.retrieval_id.startswith("rl-")
        assert log.pack_id == loadout.pack_id
        assert log.loadout_id == loadout.loadout_id
        assert log.logged_at == loadout.generated_at
        assert len(log.selected_ids) > 0

    def test_retrieval_log_has_score_traces(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        for item_id in loadout.retrieval_log.selected_ids:
            assert item_id in loadout.retrieval_log.score_traces

    def test_retrieval_log_appended_to_ledger(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)

        log_path = cell / "ledger" / "retrieval_logs.jsonl"
        assert log_path.exists()
        lines = list(read_jsonl(log_path))
        assert len(lines) >= 1
        last_record = lines[-1][1]
        assert "retrieval_id" in last_record
        assert last_record["pack_id"] == loadout.pack_id
        assert last_record["loadout_id"] == loadout.loadout_id
        assert last_record["logged_at"] == loadout.generated_at
        assert last_record["generated_at"] == loadout.generated_at
        assert "selected_ids" in last_record
        assert "score_traces" in last_record

    def test_retrieval_log_deterministic(self, tmp_path):
        """Running assemble_loadout twice produces identical logs."""
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout1 = assemble_loadout(task)
        loadout2 = assemble_loadout(task)
        assert loadout1.retrieval_log.selected_ids == loadout2.retrieval_log.selected_ids
        assert loadout1.retrieval_log.score_traces == loadout2.retrieval_log.score_traces

    def test_loadout_item_records_role_and_pack_role_alias(self):
        item = LoadoutItem(
            item_id="trace:t1",
            kind="trace",
            statement="Use caution for brittle examples.",
            rationale="Evidence from prior failures.",
            tags=["failure"],
            trust_tier="high",
            confidence=0.9,
            score=0.8,
            score_trace={"keyword_overlap": 1},
            loadout_role="caution",
        )

        assert item.to_dict()["loadout_role"] == "caution"
        restored = LoadoutItem.from_dict({**item.to_dict(), "pack_role": "guidance", "loadout_role": None})
        assert restored.loadout_role is None
        alias_restored = LoadoutItem.from_dict({**item.to_dict(), "pack_role": "guidance"})
        assert alias_restored.loadout_role == "caution"
        legacy_restored = LoadoutItem.from_dict({k: v for k, v in item.to_dict().items() if k != "loadout_role"} | {"pack_role": "guidance"})
        assert legacy_restored.loadout_role == "guidance"


# ---------------------------------------------------------------------------
# Raw operational state examples are rejected/excluded from Loadout
# ---------------------------------------------------------------------------

class TestOperationalStateRejection:
    def test_queue_status_rejected(self):
        assert is_operational_state("queue item status is pending_manager_pickup") is True

    def test_branch_state_rejected(self):
        assert is_operational_state("branch task/dmq-20260424 is active") is True

    def test_artifact_path_rejected(self):
        assert is_operational_state("worker-artifacts at local-runtime/artifacts") is True

    def test_closeout_log_rejected(self):
        assert is_operational_state("completed successfully with exit code 0") is True

    def test_verification_claim_rejected(self):
        assert is_operational_state("tests passed and verification is complete") is True

    def test_durable_lesson_accepted(self):
        assert is_operational_state("Python async context managers prevent resource leaks") is False

    def test_error_pattern_accepted(self):
        assert is_operational_state("KeyError occurs when dict key is missing") is False

    def test_loadout_excludes_operational_items(self, tmp_path):
        """Items whose statements contain operational state are excluded."""
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("t1", statement="queue item status is pending"),
            _make_trace("t2", statement="Python async prevents leaks"),
        ])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        item_ids = {i.item_id for i in loadout.items}
        assert "t1" not in item_ids
        assert "t2" in item_ids


# ---------------------------------------------------------------------------
# Fragments are background-only unless explicitly included
# ---------------------------------------------------------------------------

class TestFragmentBackgroundOnly:
    def test_fragment_not_in_loadout_by_default(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_fragments(cell, [_make_fragment("f1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        assert not any(i.trust_tier == "fragment" for i in loadout.items)

    def test_fragment_in_loadout_when_explicit(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_fragments(cell, [_make_fragment("f1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
            include_fragments=True,
        )
        loadout = assemble_loadout(task)
        assert any(i.trust_tier == "fragment" for i in loadout.items)


# ---------------------------------------------------------------------------
# Empty input / no-match behaviour is safe
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_cell_returns_empty_loadout(self, tmp_path):
        cell = _make_cell(tmp_path)

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        assert loadout.items == []
        assert loadout.total_items == 0
        assert loadout.total_tokens == 0

    def test_empty_query_returns_empty(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        assert loadout.items == []


# ---------------------------------------------------------------------------
# Output serialization is deterministic enough for tests
# ---------------------------------------------------------------------------

class TestDeterministicOutput:
    def test_loadout_to_dict_roundtrip(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        d = loadout.to_dict()
        assert "loadout_id" in d
        assert "items" in d
        assert "retrieval_log" in d

    def test_loadout_item_to_dict(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        if loadout.items:
            d = loadout.items[0].to_dict()
            assert "item_id" in d
            assert "trust_tier" in d
            assert "score" in d

    def test_loadout_json_roundtrip(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        json_str = loadout.to_json()
        loadout2 = AssembledLoadout.from_json(json_str)
        assert loadout2.loadout_id == loadout.loadout_id
        assert len(loadout2.items) == len(loadout.items)


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

class TestTokenEstimation:
    def test_whitespace_token_count(self):
        assert estimate_tokens("hello world") == 2
        assert estimate_tokens("") == 0
        assert estimate_tokens("  spaced  ") == 1
        assert estimate_tokens("one two three four five") == 5

    def test_loadout_reports_total_tokens(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", statement="hello world")])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="test",
            task_id="task-1",
        )
        loadout = assemble_loadout(task)
        assert loadout.total_tokens >= 0
        assert isinstance(loadout.total_tokens, int)


# ===========================================================================
# AL-2 Negative-Space Loadout Tests
# ===========================================================================


class TestNegativeSpaceCandidateBuilding:
    """Traces and fragments with negative-space kinds are correctly
    converted to CandidateItems with negative_space_kind set."""

    def test_trace_failure_signature_has_negative_space_kind(self):
        from shyftr.retrieval.hybrid import NEGATIVE_SPACE_KINDS
        from shyftr.loadout import _build_candidate_from_trace

        record = {
            "trace_id": "fs1",
            "cell_id": "c1",
            "statement": "Memory leak detected in cache layer",
            "kind": "failure_signature",
            "status": "approved",
        }
        candidate = _build_candidate_from_trace(record)
        assert candidate.negative_space_kind == "failure_signature"
        assert candidate.kind == "failure_signature"

    def test_trace_anti_pattern_has_negative_space_kind(self):
        from shyftr.loadout import _build_candidate_from_trace

        record = {
            "trace_id": "ap1",
            "cell_id": "c1",
            "statement": "Nested callbacks in async code",
            "kind": "anti_pattern",
            "status": "approved",
        }
        candidate = _build_candidate_from_trace(record)
        assert candidate.negative_space_kind == "anti_pattern"

    def test_trace_normal_kind_no_negative_space(self):
        from shyftr.loadout import _build_candidate_from_trace

        record = {
            "trace_id": "g1",
            "cell_id": "c1",
            "statement": "Use context managers",
            "kind": "guidance",
            "status": "approved",
        }
        candidate = _build_candidate_from_trace(record)
        assert candidate.negative_space_kind is None

    def test_fragment_anti_pattern_has_negative_space_kind(self):
        from shyftr.loadout import _build_candidate_from_fragment

        record = {
            "fragment_id": "fap1",
            "cell_id": "c1",
            "text": "Excessive logging pattern",
            "kind": "anti_pattern",
        }
        candidate = _build_candidate_from_fragment(record)
        assert candidate.negative_space_kind == "anti_pattern"

    def test_trace_related_positive_ids_preserved(self):
        from shyftr.loadout import _build_candidate_from_trace

        record = {
            "trace_id": "neg1",
            "cell_id": "c1",
            "statement": "Warning pattern",
            "kind": "anti_pattern",
            "related_positive_ids": ["pos1", "pos2"],
        }
        candidate = _build_candidate_from_trace(record)
        assert candidate.related_positive_ids == ["pos1", "pos2"]

    def test_trace_no_related_positive_ids_defaults_empty(self):
        from shyftr.loadout import _build_candidate_from_trace

        record = {
            "trace_id": "t1",
            "cell_id": "c1",
            "statement": "Normal trace",
            "kind": "guidance",
        }
        candidate = _build_candidate_from_trace(record)
        assert candidate.related_positive_ids == []


class TestNegativeSpaceLoadoutAssembly:
    """Assemble loadout with negative-space traces results in correct
    selection_reason propagation."""

    def test_positive_and_caution_both_in_loadout(self, tmp_path):
        from shyftr.loadout import assemble_loadout, LoadoutTaskInput
        from shyftr.retrieval.hybrid import SELECTION_CAUTION, SELECTION_POSITIVE

        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("pos1", kind="guidance", statement="Use async context managers"),
            _make_trace("neg1", kind="anti_pattern",
                        statement="Async nested callbacks deadlock",
                        related_positive_ids=["pos1"]),
        ])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="async patterns",
            task_id="task-al2-1",
            max_items=10,
        )
        loadout = assemble_loadout(task)
        item_ids = {i.item_id for i in loadout.items}
        assert "pos1" in item_ids
        assert "neg1" in item_ids

    def test_loadout_score_trace_includes_selection_reason(self, tmp_path):
        from shyftr.loadout import assemble_loadout, LoadoutTaskInput

        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("t1", kind="error", statement="Some error pattern"),
        ])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="error",
            task_id="task-al2-2",
        )
        loadout = assemble_loadout(task)
        assert len(loadout.items) >= 1
        item = loadout.items[0]
        assert "selection_reason" in item.score_trace
        assert item.score_trace["selection_reason"] in (
            "positive_guidance", "caution", "suppressed", "filtered", "conflict"
        )

    def test_negative_space_trace_has_caution_reason(self, tmp_path):
        from shyftr.loadout import assemble_loadout, LoadoutTaskInput

        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("neg1", kind="failure_signature",
                        statement="Cache stampede pattern detected"),
        ])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="cache",
            task_id="task-al2-3",
        )
        loadout = assemble_loadout(task)
        assert len(loadout.items) >= 1
        assert loadout.items[0].score_trace["selection_reason"] == "caution"

    def test_excluded_status_trace_not_in_loadout(self, tmp_path):
        from shyftr.loadout import assemble_loadout, LoadoutTaskInput

        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("pos1", kind="guidance", statement="Good pattern"),
            _make_trace("dep1", kind="guidance", statement="Old pattern",
                        status="deprecated"),
        ])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="pattern",
            task_id="task-al2-4",
        )
        loadout = assemble_loadout(task)
        item_ids = {i.item_id for i in loadout.items}
        assert "pos1" in item_ids
        assert "dep1" not in item_ids

    def test_loadout_with_only_caution_items(self, tmp_path):
        from shyftr.loadout import assemble_loadout, LoadoutTaskInput

        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("neg1", kind="anti_pattern",
                        statement="Anti-pattern in async code"),
        ])

        task = LoadoutTaskInput(
            cell_path=str(cell),
            query="async",
            task_id="task-al2-5",
        )
        loadout = assemble_loadout(task)
        assert len(loadout.items) >= 1
        assert loadout.items[0].score_trace["selection_reason"] == "caution"

class TestRoleLabeledLoadoutAssembly:
    def test_assembled_loadout_exposes_role_accessors(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("guide1", kind="guidance", statement="Use async context managers for cleanup"),
            _make_trace("warn1", kind="anti_pattern", statement="Avoid unbounded async task fanout"),
        ])
        _seed_alloys(cell, [_make_alloy("coil1", summary="Async cleanup patterns cluster")])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="async cleanup patterns",
            task_id="task-al3-roles",
            max_items=6,
        ))

        assert {item.item_id for item in loadout.guidance_items} >= {"guide1"}
        assert {item.item_id for item in loadout.caution_items} >= {"warn1"}
        assert all(item.loadout_role == "guidance" for item in loadout.guidance_items)
        assert all(item.loadout_role == "caution" for item in loadout.caution_items)
        assert all(item.loadout_role == "background" for item in loadout.background_items)
        assert loadout.conflict_items == []

    def test_caution_budget_preserves_guidance(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("guide1", kind="guidance", statement="Use deterministic retry wrappers"),
            _make_trace("warn1", kind="anti_pattern", statement="Avoid hidden retry loops one"),
            _make_trace("warn2", kind="anti_pattern", statement="Avoid hidden retry loops two"),
            _make_trace("warn3", kind="failure_signature", statement="Retry storm failure signature"),
        ])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="retry loops",
            task_id="task-al3-budget",
            max_items=3,
            caution_max_items=1,
        ))

        assert len(loadout.caution_items) == 1
        assert any(item.item_id == "guide1" for item in loadout.guidance_items)
        assert loadout.total_items <= 3
        assert len(loadout.retrieval_log.caution_ids) == 1
        assert set(loadout.retrieval_log.suppressed_ids) & {"warn1", "warn2", "warn3"}

    def test_default_caution_budget_cannot_fill_all_slots_when_guidance_exists(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("guide1", kind="guidance", statement="Use bounded queues"),
            _make_trace("warn1", kind="anti_pattern", statement="Unbounded queues hide overload one"),
            _make_trace("warn2", kind="failure_signature", statement="Unbounded queues hide overload two"),
        ])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="unbounded queues",
            task_id="task-al3-default-budget",
            max_items=2,
        ))

        assert len(loadout.items) == 2
        assert len(loadout.caution_items) == 1
        assert [item.item_id for item in loadout.guidance_items] == ["guide1"]

    def test_retrieval_log_records_candidate_selected_caution_and_suppressed_ids(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("guide1", kind="guidance", statement="Use bounded worker pools"),
            _make_trace("warn1", kind="failure_signature", statement="Unbounded pools exhaust file descriptors"),
            _make_trace("warn2", kind="anti_pattern", statement="Unbounded pools hide backpressure"),
        ])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="bounded pools",
            task_id="task-al3-log",
            max_items=3,
            caution_max_items=1,
        ))

        log = loadout.retrieval_log
        assert {"guide1", "warn1", "warn2"}.issubset(set(log.candidate_ids))
        assert log.selected_ids == [item.item_id for item in loadout.items]
        assert log.caution_ids == [item.item_id for item in loadout.caution_items]
        assert log.suppressed_ids
        for item in loadout.items:
            assert log.score_traces[item.item_id]["selection_reason"]
            assert log.score_traces[item.item_id]["loadout_role"] in LOADOUT_ROLES

    def test_conflict_item_is_selected_not_logged_as_suppressed(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("guide1", kind="guidance", statement="Use bounded worker pools"),
            _make_trace(
                "warn1",
                kind="anti_pattern",
                statement="Worker pools can deadlock when nested without limits",
                related_positive_ids=["guide1"],
            ),
        ])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="worker pools",
            task_id="task-phase4-conflict",
            max_items=4,
            caution_max_items=1,
        ))

        assert [item.item_id for item in loadout.conflict_items] == ["guide1"]
        assert "guide1" in loadout.retrieval_log.selected_ids
        assert "guide1" not in loadout.retrieval_log.suppressed_ids
        assert loadout.retrieval_log.score_traces["guide1"]["selection_reason"] == "conflict"

    def test_suppressed_item_is_selected_not_logged_as_suppressed(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("guide1", kind="guidance", statement="Use legacy retry wrapper"),
            _make_trace(
                "warn1",
                kind="supersession",
                statement="Legacy retry wrapper is superseded by bounded retry policies",
                related_positive_ids=["guide1"],
            ),
        ])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="retry wrapper",
            task_id="task-phase4-suppressed",
            max_items=4,
            caution_max_items=1,
        ))

        guide = next(item for item in loadout.items if item.item_id == "guide1")
        assert guide.score_trace["selection_reason"] == "suppressed"
        assert guide.loadout_role == "background"
        assert "guide1" in loadout.retrieval_log.selected_ids
        assert "guide1" not in loadout.retrieval_log.suppressed_ids

    def test_operational_state_rejected_from_every_role_accessor(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("guide1", kind="guidance", statement="Use deterministic cleanup hooks"),
            _make_trace("warn1", kind="anti_pattern", statement="queue item status is awaiting_manager_review"),
            _make_trace("conflict1", kind="conflict", statement="branch task/dmq-example is active"),
        ])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="cleanup hooks",
            task_id="task-al3-pollution",
            max_items=5,
        ))

        all_role_items = loadout.guidance_items + loadout.caution_items + loadout.background_items + loadout.conflict_items
        assert [item.item_id for item in all_role_items] == ["guide1"]
        assert {"warn1", "conflict1"}.issubset(set(loadout.retrieval_log.suppressed_ids))

    def test_role_labeled_loadout_serialization_roundtrip(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("warn1", kind="anti_pattern", statement="Avoid circular retries")])

        loadout = assemble_loadout(LoadoutTaskInput(
            cell_path=str(cell),
            query="retries",
            task_id="task-al3-roundtrip",
        ))
        restored = AssembledLoadout.from_json(loadout.to_json())

        assert [item.item_id for item in restored.caution_items] == [item.item_id for item in loadout.caution_items]
        assert restored.retrieval_log.caution_ids == loadout.retrieval_log.caution_ids
        assert restored.retrieval_log.candidate_ids == loadout.retrieval_log.candidate_ids
