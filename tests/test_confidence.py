"""Tests for confidence adjustment (Work slice 11).

Covers confidence increase after verified success/useful application
and confidence decrease after harmful/failed/contradicted outcomes.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from shyftr.confidence import (
    CONTRADICTED_DELTA,
    HARMFUL_FAILURE_DELTA,
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    USEFUL_SUCCESS_DELTA,
    ConfidenceAdjustment,
    adjust_confidence,
    adjust_confidence_from_outcome,
)
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl


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


def _make_trace(trace_id: str = "t1", confidence: float = 0.5, **overrides) -> dict:
    base = {
        "trace_id": trace_id,
        "cell_id": "test-cell",
        "statement": f"Statement for {trace_id}",
        "rationale": f"Rationale for {trace_id}",
        "source_fragment_ids": ["f1"],
        "status": "approved",
        "confidence": confidence,
        "tags": ["python"],
        "kind": "error",
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Confidence increase after verified success
# ---------------------------------------------------------------------------

class TestConfidenceIncrease:
    def test_useful_trace_confidence_increases(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-1",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )
        assert len(adjustments) == 1
        adj = adjustments[0]
        assert adj.trace_id == "t1"
        assert adj.old_confidence == 0.5
        assert adj.new_confidence == pytest.approx(0.55)
        assert adj.delta == USEFUL_SUCCESS_DELTA
        assert adj.reason == "useful_after_success"

    def test_useful_trace_clamped_at_max(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.98)])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-2",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )
        assert adjustments[0].new_confidence == MAX_CONFIDENCE

    def test_multiple_useful_traces_all_increased(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("t1", confidence=0.5),
            _make_trace("t2", confidence=0.6),
        ])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-3",
            useful_trace_ids=["t1", "t2"],
            harmful_trace_ids=[],
            result="success",
        )
        assert len(adjustments) == 2
        by_id = {a.trace_id: a for a in adjustments}
        assert by_id["t1"].new_confidence == pytest.approx(0.55)
        assert by_id["t2"].new_confidence == pytest.approx(0.65)

    def test_repeated_useful_adjustments_compound_from_latest_trace_row(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

        first = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-latest-1",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )
        second = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-latest-2",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )

        assert first[0].old_confidence == 0.5
        assert first[0].new_confidence == pytest.approx(0.55)
        assert second[0].old_confidence == pytest.approx(0.55)
        assert second[0].new_confidence == pytest.approx(0.60)


    def test_legacy_useful_trace_without_status_still_increases(self, tmp_path):
        cell = _make_cell(tmp_path)
        legacy = _make_trace("t1", confidence=0.5)
        legacy.pop("status")
        _seed_traces(cell, [legacy])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-legacy-status",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )

        assert len(adjustments) == 1
        assert adjustments[0].new_confidence == pytest.approx(0.55)


# ---------------------------------------------------------------------------
# Confidence decrease after harmful/failed/contradicted
# ---------------------------------------------------------------------------

class TestConfidenceDecrease:
    def test_harmful_trace_confidence_decreases(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.7)])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-4",
            useful_trace_ids=[],
            harmful_trace_ids=["t1"],
            result="failure",
        )
        assert len(adjustments) == 1
        adj = adjustments[0]
        assert adj.trace_id == "t1"
        assert adj.old_confidence == 0.7
        assert adj.new_confidence == pytest.approx(0.6)
        assert adj.delta == HARMFUL_FAILURE_DELTA

    def test_harmful_trace_clamped_at_min(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.02)])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-5",
            useful_trace_ids=[],
            harmful_trace_ids=["t1"],
            result="failure",
        )
        assert adjustments[0].new_confidence == MIN_CONFIDENCE

    def test_contradicted_uses_larger_penalty(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.8)])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-6",
            useful_trace_ids=[],
            harmful_trace_ids=["t1"],
            result="contradicted",
        )
        adj = adjustments[0]
        assert adj.delta == CONTRADICTED_DELTA
        assert adj.new_confidence == pytest.approx(0.8 + CONTRADICTED_DELTA)

    def test_multiple_harmful_traces_all_decreased(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("t1", confidence=0.7),
            _make_trace("t2", confidence=0.6),
        ])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-7",
            useful_trace_ids=[],
            harmful_trace_ids=["t1", "t2"],
            result="failure",
        )
        assert len(adjustments) == 2
        by_id = {a.trace_id: a for a in adjustments}
        assert by_id["t1"].new_confidence == pytest.approx(0.6)
        assert by_id["t2"].new_confidence == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Contradicted takes priority over useful
# ---------------------------------------------------------------------------

class TestContradictedPriority:
    def test_trace_in_both_lists_treated_as_harmful(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-8",
            useful_trace_ids=["t1"],
            harmful_trace_ids=["t1"],
            result="contradicted",
        )
        # Should only appear once, as harmful
        assert len(adjustments) == 1
        adj = adjustments[0]
        assert adj.delta == CONTRADICTED_DELTA
        assert adj.new_confidence == pytest.approx(0.5 + CONTRADICTED_DELTA)
        assert adj.reason == "contradicted_after_contradicted"

    def test_trace_in_both_lists_gets_contradicted_penalty_without_contradicted_verdict(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-8b",
            useful_trace_ids=["t1"],
            harmful_trace_ids=["t1"],
            result="failure",
        )

        assert len(adjustments) == 1
        adj = adjustments[0]
        assert adj.delta == CONTRADICTED_DELTA
        assert adj.new_confidence == pytest.approx(0.5 + CONTRADICTED_DELTA)
        assert adj.reason == "contradicted_after_failure"


# ---------------------------------------------------------------------------
# Append-only: updated traces appended, not mutated
# ---------------------------------------------------------------------------

class TestAppendOnlyBehavior:
    def test_adjusted_trace_appended_not_replaced(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

        adjust_confidence(
            cell_path=cell,
            outcome_id="oc-9",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )

        ledger = cell / "traces" / "approved.jsonl"
        rows = list(read_jsonl(ledger))
        # Original + updated = 2 rows
        assert len(rows) == 2
        # Original still has old confidence
        assert rows[0][1]["confidence"] == 0.5
        # Updated has new confidence
        assert rows[1][1]["confidence"] == pytest.approx(0.55)

    def test_adjustment_ledger_appended(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

        adjust_confidence(
            cell_path=cell,
            outcome_id="oc-10",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )

        adj_ledger = cell / "ledger" / "confidence_adjustments.jsonl"
        assert adj_ledger.exists()
        rows = list(read_jsonl(adj_ledger))
        assert len(rows) == 1
        assert rows[0][1]["trace_id"] == "t1"
        assert rows[0][1]["reason"] == "useful_after_success"


# ---------------------------------------------------------------------------
# ConfidenceAdjustment model
# ---------------------------------------------------------------------------

class TestConfidenceAdjustmentModel:
    def test_serialization(self):
        adj = ConfidenceAdjustment(
            trace_id="t1",
            old_confidence=0.5,
            new_confidence=0.55,
            reason="useful_after_success",
            delta=0.05,
            adjusted_at="2026-01-01T00:00:00+00:00",
        )
        d = adj.to_dict()
        assert d["trace_id"] == "t1"
        assert d["old_confidence"] == 0.5
        assert d["new_confidence"] == 0.55


# ---------------------------------------------------------------------------
# adjust_confidence_from_outcome convenience
# ---------------------------------------------------------------------------

class TestAdjustFromOutcome:
    def test_adjust_from_outcome_record(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

        outcome = {
            "outcome_id": "oc-conv",
            "cell_id": "test-cell",
            "loadout_id": "lo-1",
            "task_id": "task-1",
            "verdict": "success",
            "trace_ids": ["t1"],
            "metadata": {
                "useful_trace_ids": ["t1"],
                "harmful_trace_ids": [],
            },
        }
        adjustments = adjust_confidence_from_outcome(cell, outcome)
        assert len(adjustments) == 1
        assert adjustments[0].new_confidence == pytest.approx(0.55)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_no_traces_no_adjustments(self, tmp_path):
        cell = _make_cell(tmp_path)
        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-empty",
            useful_trace_ids=[],
            harmful_trace_ids=[],
            result="success",
        )
        assert adjustments == []

    def test_nonexistent_trace_skipped(self, tmp_path):
        cell = _make_cell(tmp_path)
        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-miss",
            useful_trace_ids=["nonexistent"],
            harmful_trace_ids=[],
            result="success",
        )
        assert adjustments == []

    def test_trace_with_no_confidence_defaults_to_05(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])  # confidence=0.5 default

        adjustments = adjust_confidence(
            cell_path=cell,
            outcome_id="oc-def",
            useful_trace_ids=["t1"],
            harmful_trace_ids=[],
            result="success",
        )
        assert adjustments[0].old_confidence == 0.5


# ---------------------------------------------------------------------------
# Pack miss exemption
# ---------------------------------------------------------------------------

class TestPackMissExemption:
    def test_pack_miss_exempt_delta_is_zero(self):
        from shyftr.confidence import PACK_MISS_EXEMPT_DELTA

        assert PACK_MISS_EXEMPT_DELTA == 0.0

    def test_adjust_confidence_not_called_with_pack_misses(self, tmp_path):
        """Verify that pack misses are never passed to adjust_confidence.

        The function signature has no pack_misses parameter, so they
        cannot influence confidence. This test asserts that invariant.
        """
        from inspect import signature
        from shyftr.confidence import adjust_confidence

        sig = signature(adjust_confidence)
        param_names = list(sig.parameters.keys())
        assert "pack_misses" not in param_names
        assert "pack_miss_details" not in param_names
        assert "useful_trace_ids" in param_names
        assert "harmful_trace_ids" in param_names
