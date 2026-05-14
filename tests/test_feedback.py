"""Tests for Outcome learning loop (Work slice 11).

Covers outcome ledger append, missing-memory candidate emission,
provenance, and boundary rejection.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.outcomes import (
    MissingMemoryCandidate,
    TraceUsageCounters,
    compute_trace_usage_counters,
    get_trace_counters_as_dicts,
    record_outcome,
)


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


# ---------------------------------------------------------------------------
# Outcome ledger append
# ---------------------------------------------------------------------------

class TestOutcomeLedgerAppend:
    def test_record_outcome_appends_to_ledger(self, tmp_path):
        cell = _make_cell(tmp_path)
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-test123",
            result="success",
            applied_trace_ids=["t1", "t2"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        ledger = cell / "ledger" / "outcomes.jsonl"
        assert ledger.exists()
        rows = list(read_jsonl(ledger))
        assert len(rows) == 1
        row = rows[0][1]
        assert row["outcome_id"] == outcome.outcome_id
        assert row["loadout_id"] == "lo-test123"
        assert row["verdict"] == "success"
        assert row["trace_ids"] == ["t1", "t2"]

    def test_record_outcome_preserves_active_learning_feedback(self, tmp_path):
        cell = _make_cell(tmp_path)
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-feedback",
            result="partial",
            applied_trace_ids=["t1"],
            useful_trace_ids=[],
            harmful_trace_ids=["t1"],
            missing_memory=[],
            ignored_charge_ids=["t2"],
            ignored_caution_ids=["t3"],
            contradicted_charge_ids=["t4"],
            over_retrieved_charge_ids=["t5"],
            pack_misses=["missing recovery example"],
        )

        assert outcome.ignored_charge_ids == ["t2"]
        assert outcome.ignored_caution_ids == ["t3"]
        assert outcome.contradicted_charge_ids == ["t4"]
        assert outcome.over_retrieved_charge_ids == ["t5"]
        assert outcome.pack_misses == ["missing recovery example"]
        ledger = cell / "ledger" / "outcomes.jsonl"
        row = list(read_jsonl(ledger))[-1][1]
        assert row["ignored_charge_ids"] == ["t2"]
        assert row["ignored_caution_ids"] == ["t3"]
        assert row["contradicted_charge_ids"] == ["t4"]
        assert row["over_retrieved_charge_ids"] == ["t5"]
        assert row["pack_misses"] == ["missing recovery example"]

    def test_record_outcome_returns_outcome_model(self, tmp_path):
        cell = _make_cell(tmp_path)
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-x",
            result="failure",
            applied_trace_ids=["t1"],
            useful_trace_ids=[],
            harmful_trace_ids=["t1"],
            missing_memory=[],
        )
        assert outcome.outcome_id.startswith("oc-")
        assert outcome.cell_id == "test-cell"
        assert outcome.verdict == "failure"

    def test_multiple_outcomes_append_without_overwrite(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-1",
            result="success",
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        record_outcome(
            cell_path=cell,
            loadout_id="lo-2",
            result="failure",
            applied_trace_ids=["t2"],
            useful_trace_ids=[],
            harmful_trace_ids=["t2"],
            missing_memory=[],
        )
        ledger = cell / "ledger" / "outcomes.jsonl"
        rows = list(read_jsonl(ledger))
        assert len(rows) == 2
        assert rows[0][1]["loadout_id"] == "lo-1"
        assert rows[1][1]["loadout_id"] == "lo-2"

    def test_outcome_metadata_stores_useful_and_harmful(self, tmp_path):
        cell = _make_cell(tmp_path)
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-meta",
            result="partial",
            applied_trace_ids=["t1", "t2", "t3"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=["t3"],
            missing_memory=[],
            verification_evidence={"checks": ["lint"]},
        )
        ledger = cell / "ledger" / "outcomes.jsonl"
        rows = list(read_jsonl(ledger))
        meta = rows[0][1]["metadata"]
        assert meta["useful_trace_ids"] == ["t1"]
        assert meta["harmful_trace_ids"] == ["t3"]
        assert meta["verification_evidence"] == {"checks": ["lint"]}


# ---------------------------------------------------------------------------
# Missing-memory candidate emission
# ---------------------------------------------------------------------------

class TestMissingMemoryCandidates:
    def test_missing_memory_emits_candidates(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-mem",
            result="failure",
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            missing_memory=["How to handle async timeouts in Python"],
        )
        ledger = cell / "ledger" / "missing_memory_candidates.jsonl"
        assert ledger.exists()
        rows = list(read_jsonl(ledger))
        assert len(rows) == 1
        row = rows[0][1]
        assert row["source_text"] == "How to handle async timeouts in Python"
        assert row["missing_from_loadout_id"] == "lo-mem"
        assert row["review_status"] == "pending"

    def test_multiple_missing_items_emit_separate_candidates(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-multi",
            result="failure",
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            missing_memory=["Item A", "Item B", "Item C"],
        )
        ledger = cell / "ledger" / "missing_memory_candidates.jsonl"
        rows = list(read_jsonl(ledger))
        assert len(rows) == 3
        texts = {r[1]["source_text"] for r in rows}
        assert texts == {"Item A", "Item B", "Item C"}

    def test_operational_state_missing_memory_rejected(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-poll",
            result="failure",
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            missing_memory=[
                "queue item status is pending",
                "branch task/xyz is active",
                "Python async context managers prevent leaks",
            ],
        )
        ledger = cell / "ledger" / "missing_memory_candidates.jsonl"
        rows = list(read_jsonl(ledger))
        # Only the durable lesson should be accepted
        assert len(rows) == 1
        assert rows[0][1]["source_text"] == "Python async context managers prevent leaks"

    def test_empty_missing_memory_no_candidate_file(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-empty",
            result="success",
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        ledger = cell / "ledger" / "missing_memory_candidates.jsonl"
        assert not ledger.exists()


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

class TestProvenance:
    def test_outcome_links_to_loadout(self, tmp_path):
        cell = _make_cell(tmp_path)
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-prov",
            result="success",
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        assert outcome.loadout_id == "lo-prov"
        assert outcome.cell_id == "test-cell"

    def test_outcome_has_timestamp(self, tmp_path):
        cell = _make_cell(tmp_path)
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-ts",
            result="success",
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        assert outcome.observed_at is not None
        assert "T" in outcome.observed_at  # ISO format

    def test_candidate_links_to_loadout(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-link",
            result="failure",
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            missing_memory=["Some missing knowledge"],
        )
        ledger = cell / "ledger" / "missing_memory_candidates.jsonl"
        rows = list(read_jsonl(ledger))
        assert rows[0][1]["missing_from_loadout_id"] == "lo-link"


# ---------------------------------------------------------------------------
# Boundary rejection
# ---------------------------------------------------------------------------

class TestBoundaryRejection:
    def test_pollution_in_missing_memory_rejected(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-bound",
            result="failure",
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            missing_memory=[
                "completed successfully with exit code 0",
                "worker-artifacts at local-runtime/artifacts",
            ],
        )
        ledger = cell / "ledger" / "missing_memory_candidates.jsonl"
        assert not ledger.exists()

    def test_clean_missing_memory_accepted(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-clean",
            result="failure",
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            missing_memory=["SQL injection prevention requires parameterized queries"],
        )
        ledger = cell / "ledger" / "missing_memory_candidates.jsonl"
        rows = list(read_jsonl(ledger))
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# Trace usage counters
# ---------------------------------------------------------------------------

class TestTraceUsageCounters:
    def test_empty_outcomes_returns_empty(self, tmp_path):
        cell = _make_cell(tmp_path)
        counters = compute_trace_usage_counters(cell)
        assert counters == {}

    def test_single_outcome_increments_counters(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-c1",
            result="success",
            applied_trace_ids=["t1", "t2"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        counters = compute_trace_usage_counters(cell)
        assert counters["t1"].use_count == 1
        assert counters["t1"].success_count == 1
        assert counters["t1"].failure_count == 0
        assert counters["t2"].use_count == 1
        assert counters["t2"].success_count == 0
        assert counters["t2"].failure_count == 0

    def test_multiple_outcomes_accumulate(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-a",
            result="success",
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        record_outcome(
            cell_path=cell,
            loadout_id="lo-b",
            result="failure",
            applied_trace_ids=["t1"],
            useful_trace_ids=[],
            harmful_trace_ids=["t1"],
            missing_memory=[],
        )
        counters = compute_trace_usage_counters(cell)
        assert counters["t1"].use_count == 2
        assert counters["t1"].success_count == 1
        assert counters["t1"].failure_count == 1

    def test_harmful_traces_counted_separately(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-h",
            result="failure",
            applied_trace_ids=["t1", "t2", "t3"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=["t2", "t3"],
            missing_memory=[],
        )
        counters = compute_trace_usage_counters(cell)
        assert counters["t1"].success_count == 1
        assert counters["t1"].failure_count == 0
        assert counters["t2"].failure_count == 1
        assert counters["t3"].failure_count == 1

    def test_get_trace_counters_as_dicts(self, tmp_path):
        cell = _make_cell(tmp_path)
        record_outcome(
            cell_path=cell,
            loadout_id="lo-d",
            result="success",
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
        )
        dicts = get_trace_counters_as_dicts(cell)
        assert len(dicts) == 1
        assert dicts[0]["trace_id"] == "t1"
        assert dicts[0]["use_count"] == 1


# ---------------------------------------------------------------------------
# MissingMemoryCandidate model
# ---------------------------------------------------------------------------

class TestMissingMemoryCandidateModel:
    def test_serialization_roundtrip(self):
        candidate = MissingMemoryCandidate(
            candidate_id="mmc-abc",
            cell_id="cell-1",
            source_text="Some text",
            missing_from_loadout_id="lo-1",
            emitted_at="2026-01-01T00:00:00+00:00",
        )
        d = candidate.to_dict()
        assert d["candidate_id"] == "mmc-abc"
        assert d["review_status"] == "pending"


# ---------------------------------------------------------------------------
# PackMiss model
# ---------------------------------------------------------------------------

class TestPackMissModel:
    def test_valid_miss_types(self):
        from shyftr.outcomes import PackMiss, VALID_MISS_TYPES

        for mt in sorted(VALID_MISS_TYPES):
            pm = PackMiss(charge_id="ch-1", miss_type=mt)
            assert pm.miss_type == mt
            assert pm.charge_id == "ch-1"
            assert pm.reason is None

    def test_with_reason(self):
        from shyftr.outcomes import PackMiss

        pm = PackMiss(charge_id="ch-1", miss_type="not_relevant", reason="not in context")
        assert pm.reason == "not in context"
        d = pm.to_dict()
        assert d["reason"] == "not in context"

    def test_invalid_miss_type_raises(self):
        from shyftr.outcomes import PackMiss

        with pytest.raises(ValueError, match="Invalid miss_type"):
            PackMiss(charge_id="ch-1", miss_type="invalid_type")

    def test_to_dict_without_reason(self):
        from shyftr.outcomes import PackMiss

        pm = PackMiss(charge_id="ch-1", miss_type="contradicted")
        d = pm.to_dict()
        assert d == {"charge_id": "ch-1", "miss_type": "contradicted"}
        assert "reason" not in d

    def test_to_dict_with_reason(self):
        from shyftr.outcomes import PackMiss

        pm = PackMiss(charge_id="ch-1", miss_type="not_actionable", reason="bypassed")
        d = pm.to_dict()
        assert d["reason"] == "bypassed"


# ---------------------------------------------------------------------------
# derive_pack_misses
# ---------------------------------------------------------------------------

class TestDerivePackMisses:
    def test_all_applied_no_misses(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1", "t2"],
            applied_trace_ids=["t1", "t2"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
        )
        assert misses == []

    def test_contradicted_charge(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1", "t2"],
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            contradicted_charge_ids=["t2"],
        )
        assert len(misses) == 1
        assert misses[0].charge_id == "t2"
        assert misses[0].miss_type == "contradicted"

    def test_over_retrieved_as_not_relevant(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1", "t2"],
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            over_retrieved_charge_ids=["t2"],
        )
        assert len(misses) == 1
        assert misses[0].charge_id == "t2"
        assert misses[0].miss_type == "not_relevant"

    def test_ignored_charge_as_not_actionable(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1", "t2"],
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            ignored_charge_ids=["t2"],
        )
        assert len(misses) == 1
        assert misses[0].charge_id == "t2"
        assert misses[0].miss_type == "not_actionable"

    def test_ignored_caution_as_not_actionable(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1", "t2"],
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            ignored_caution_ids=["t2"],
        )
        assert len(misses) == 1
        assert misses[0].charge_id == "t2"
        assert misses[0].miss_type == "not_actionable"

    def test_duplicative_useful_and_harmful(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1", "t2"],
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1", "t2"],
            harmful_trace_ids=["t2"],
        )
        assert len(misses) == 1
        assert misses[0].charge_id == "t2"
        assert misses[0].miss_type == "duplicative"

    def test_unknown_miss_type(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1", "t2", "t3"],
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
        )
        assert len(misses) == 2
        for m in misses:
            assert m.miss_type == "unknown"
        assert {m.charge_id for m in misses} == {"t2", "t3"}

    def test_contradicted_takes_priority(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["t1"],
            applied_trace_ids=[],
            useful_trace_ids=[],
            harmful_trace_ids=[],
            contradicted_charge_ids=["t1"],
            over_retrieved_charge_ids=["t1"],
            ignored_charge_ids=["t1"],
        )
        assert len(misses) == 1
        assert misses[0].miss_type == "contradicted"


class TestPackMissHelpers:
    def test_pack_misses_to_details(self):
        from shyftr.outcomes import PackMiss, pack_misses_to_details

        misses = [PackMiss("ch-1", "not_relevant"), PackMiss("ch-2", "contradicted", reason="nope")]
        details = pack_misses_to_details(misses)
        assert len(details) == 2
        assert details[0] == {"charge_id": "ch-1", "miss_type": "not_relevant"}
        assert details[1] == {"charge_id": "ch-2", "miss_type": "contradicted", "reason": "nope"}

    def test_pack_misses_to_ids(self):
        from shyftr.outcomes import PackMiss, pack_misses_to_ids

        misses = [PackMiss("ch-a", "unknown"), PackMiss("ch-b", "duplicative")]
        ids = pack_misses_to_ids(misses)
        assert ids == ["ch-a", "ch-b"]


# ---------------------------------------------------------------------------
# Outcome with pack_miss_details
# ---------------------------------------------------------------------------

class TestOutcomePackMissDetails:
    def test_record_outcome_with_pack_miss_details(self, tmp_path):
        from shyftr.outcomes import record_outcome
        from shyftr.layout import init_cell

        cell = init_cell(tmp_path, "test-cell-pmd")
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-1",
            result="partial",
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=["t2"],
            missing_memory=[],
            pack_miss_details=[
                {"charge_id": "t2", "miss_type": "contradicted"},
                {"charge_id": "t3", "miss_type": "not_relevant", "reason": "off-topic"},
            ],
        )
        assert len(outcome.pack_miss_details) == 2
        assert outcome.pack_miss_details[0]["charge_id"] == "t2"
        assert outcome.pack_miss_details[0]["miss_type"] == "contradicted"
        assert outcome.pack_miss_details[1]["reason"] == "off-topic"
        # Backward compat: pack_misses should be populated from details
        assert len(outcome.pack_misses) == 2
        assert "t2" in outcome.pack_misses
        assert "t3" in outcome.pack_misses

    def test_record_outcome_with_pack_misses_only(self, tmp_path):
        from shyftr.outcomes import record_outcome
        from shyftr.layout import init_cell

        cell = init_cell(tmp_path, "test-cell-pm")
        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-1",
            result="success",
            applied_trace_ids=["t1"],
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            missing_memory=[],
            pack_misses=["t2"],
        )
        assert outcome.pack_misses == ["t2"]
        assert outcome.pack_miss_details == [
            {"charge_id": "t2", "miss_type": "unknown"}
        ]

    def test_record_outcome_derives_pack_misses_from_retrieval_log(self, tmp_path):
        from shyftr.layout import init_cell
        from shyftr.outcomes import record_outcome

        cell = init_cell(tmp_path, "test-cell-derived")
        append_jsonl(
            cell / "ledger" / "retrieval_logs.jsonl",
            {
                "retrieval_id": "rl-1",
                "loadout_id": "lo-derived",
                "selected_ids": ["guide-applied", "guide-ignored", "guide-contradicted", "caution-only"],
                "caution_ids": ["caution-only"],
            },
        )

        outcome = record_outcome(
            cell_path=cell,
            loadout_id="lo-derived",
            result="partial",
            applied_trace_ids=["guide-applied"],
            useful_trace_ids=["guide-applied"],
            harmful_trace_ids=[],
            missing_memory=[],
            ignored_charge_ids=["guide-ignored"],
            ignored_caution_ids=["caution-only"],
            contradicted_charge_ids=["guide-contradicted"],
        )

        assert outcome.pack_misses == ["guide-ignored", "guide-contradicted"]
        assert outcome.pack_miss_details == [
            {"charge_id": "guide-ignored", "miss_type": "not_actionable"},
            {"charge_id": "guide-contradicted", "miss_type": "contradicted"},
        ]


class TestComputeMissSummary:
    def test_empty_outcomes(self):
        from shyftr.outcomes import compute_miss_summary

        result = compute_miss_summary([])
        assert result["total_misses"] == 0
        assert result["misses_by_type"] == {}
        assert result["misses_by_charge"] == {}
        assert result["over_retrieved_by_charge"] == {}

    def test_with_misses(self):
        from shyftr.outcomes import compute_miss_summary

        outcomes = [
            {
                "pack_miss_details": [
                    {"charge_id": "t2", "miss_type": "contradicted"}
                ]
            },
            {
                "pack_miss_details": [
                    {"charge_id": "t3", "miss_type": "not_relevant"},
                    {"charge_id": "t4", "miss_type": "unknown"},
                ]
            },
        ]
        result = compute_miss_summary(outcomes)
        assert result["total_misses"] == 3
        assert result["misses_by_type"]["contradicted"] == 1
        assert result["misses_by_type"]["not_relevant"] == 1
        assert result["misses_by_type"]["unknown"] == 1
        assert result["misses_by_charge"]["t2"] == 1
        assert result["misses_by_charge"]["t3"] == 1

    def test_useful_or_harmful_feedback_is_not_unknown_miss(self):
        from shyftr.outcomes import derive_pack_misses

        misses = derive_pack_misses(
            pack_trace_ids=["applied", "useful-only", "harmful-only", "silent"],
            applied_trace_ids=["applied"],
            useful_trace_ids=["useful-only"],
            harmful_trace_ids=["harmful-only"],
        )

        assert [miss.charge_id for miss in misses] == ["silent"]
        assert misses[0].miss_type == "unknown"

    def test_mixed_signal_detection(self):
        from shyftr.outcomes import compute_miss_summary

        outcomes = [
            {"metadata": {"useful_trace_ids": ["t1", "t2"], "harmful_trace_ids": ["t2", "t3"]}},
        ]
        result = compute_miss_summary(outcomes)
        assert "t2" in result["charges_with_mixed_signal"]
