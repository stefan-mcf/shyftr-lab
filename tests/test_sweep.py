"""Tests for the ShyftR Sweep dry-run analysis module.

Tests use tmp_path to create ephemeral Cell directories with fixture ledger
files, then run the sweep and assert on the resulting report structure,
metrics, and proposed actions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from shyftr.ledger import read_jsonl
from shyftr.sweep import (
    PROPOSED_ACTION_TYPES,
    ProposedAction,
    SweepReport,
    TraceMetrics,
    compute_trace_metrics,
    propose_actions,
    run_sweep,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, records: list[Dict[str, Any]]) -> None:
    """Write records as newline-delimited JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n"
    path.write_text(lines, encoding="utf-8")


def _init_cell(cell: Path, cell_id: str = "test-cell") -> Path:
    """Create a minimal Cell directory with manifest."""
    manifest_dir = cell / "config"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"cell_id": cell_id, "cell_type": "domain"}
    (manifest_dir / "cell_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    return cell


# ---------------------------------------------------------------------------
# ProposedAction validation
# ---------------------------------------------------------------------------


class TestProposedAction:
    def test_valid_action_types(self) -> None:
        """All PROPOSED_ACTION_TYPES are accepted."""
        for atype in PROPOSED_ACTION_TYPES:
            action = ProposedAction(trace_id="trace-1", action_type=atype, rationale="test")
            assert action.action_type == atype

    def test_invalid_action_type_raises(self) -> None:
        """Invalid action type raises ValueError."""
        import pytest
        with pytest.raises(ValueError):
            ProposedAction(trace_id="trace-1", action_type="not_a_valid_type", rationale="test")

    def test_to_dict_omits_none_supporting_data(self) -> None:
        """to_dict() omits supporting_data field when None."""
        d = ProposedAction(trace_id="t1", action_type="manual_review", rationale="test").to_dict()
        assert "supporting_data" not in d

    def test_to_dict_includes_supporting_data(self) -> None:
        """to_dict() includes supporting_data when provided."""
        d = ProposedAction(
            trace_id="t1", action_type="manual_review", rationale="test",
            supporting_data={"count": 3},
        ).to_dict()
        assert d["supporting_data"] == {"count": 3}


# ---------------------------------------------------------------------------
# TraceMetrics
# ---------------------------------------------------------------------------


class TestTraceMetrics:
    def test_to_dict_roundtrip(self) -> None:
        m = TraceMetrics(
            trace_id="trace-abc",
            trace_kind="charge",
            retrieval_count=5,
            application_count=3,
            useful_count=2,
            harmful_count=1,
            miss_count=0,
            application_rate=0.6,
            useful_rate=0.6667,
            harmful_rate=0.3333,
            miss_rate=0.0,
        )
        d = m.to_dict()
        assert d["trace_id"] == "trace-abc"
        assert d["retrieval_count"] == 5
        assert d["application_rate"] == 0.6


# ---------------------------------------------------------------------------
# compute_trace_metrics
# ---------------------------------------------------------------------------


class TestComputeTraceMetrics:
    def test_empty_cell_returns_empty(self, tmp_path: Path) -> None:
        """An empty Cell returns empty metrics."""
        _init_cell(tmp_path)
        metrics = compute_trace_metrics(tmp_path)
        assert metrics == {}

    def test_retrieval_counts(self, tmp_path: Path) -> None:
        """Retrieval logs correctly count per-trace retrievals."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-a", "trace-b"]},
            {"loadout_id": "lo-2", "selected_ids": ["trace-a"]},
        ])
        metrics = compute_trace_metrics(cell)
        assert metrics["trace-a"].retrieval_count == 2
        assert metrics["trace-b"].retrieval_count == 1

    def test_outcome_counts(self, tmp_path: Path) -> None:
        """Outcomes correctly count applications, useful, harmful, misses."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-a", "trace-b"],
                "metadata": {
                    "useful_trace_ids": ["trace-a"],
                    "harmful_trace_ids": ["trace-b"],
                },
                "pack_misses": ["trace-c"],
                "pack_miss_details": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        assert metrics["trace-a"].application_count == 1
        assert metrics["trace-a"].useful_count == 1
        assert metrics["trace-b"].application_count == 1
        assert metrics["trace-b"].harmful_count == 1
        assert metrics["trace-c"].miss_count == 1

    def test_rates_computed(self, tmp_path: Path) -> None:
        """Rates are computed from raw counts."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-a", "trace-a"]},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-a"],
                "metadata": {
                    "useful_trace_ids": ["trace-a"],
                    "harmful_trace_ids": [],
                },
                "pack_misses": [],
                "pack_miss_details": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        m = metrics["trace-a"]
        assert m.retrieval_count == 1
        assert m.application_count == 1
        assert m.application_rate == 1.0  # 1/1
        assert m.useful_rate == 1.0  # 1/1
        assert m.harmful_rate == 0.0

    def test_no_retrievals_application_rate_none(self, tmp_path: Path) -> None:
        """Traces with 0 retrievals have None application_rate."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-a"],
                "metadata": {"useful_trace_ids": ["trace-a"]},
                "pack_misses": [],
                "pack_miss_details": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        m = metrics["trace-a"]
        assert m.retrieval_count == 0
        assert m.application_rate is None
        # useful_rate is computed from useful / application, not retrieval
        assert m.useful_rate == 1.0


# ---------------------------------------------------------------------------
# propose_actions
# ---------------------------------------------------------------------------


class TestProposeActions:
    def test_retrieval_affinity_decrease_on_high_misses(self, tmp_path: Path) -> None:
        """>=3 misses and miss_rate>0.5 produces retrieval_affinity_decrease."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-a"] * 5},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": [],
                "metadata": {},
                "pack_miss_details": [
                    {"charge_id": "trace-a", "missing_query": "q"},
                ] * 4,
                "pack_misses": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(metrics, [], [], [])
        matching = [a for a in actions if a.action_type == "retrieval_affinity_decrease"]
        assert len(matching) >= 1
        assert matching[0].trace_id == "trace-a"

    def test_confidence_decrease_on_harmful(self, tmp_path: Path) -> None:
        """>=1 harmful application produces confidence_decrease."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-a"]},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-a"],
                "metadata": {
                    "useful_trace_ids": [],
                    "harmful_trace_ids": ["trace-a"],
                },
                "pack_misses": [],
                "pack_miss_details": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(metrics, [], [], [])
        matching = [a for a in actions if a.action_type == "confidence_decrease"]
        assert len(matching) >= 1
        assert matching[0].trace_id == "trace-a"

    def test_confidence_increase_on_consistently_useful(self, tmp_path: Path) -> None:
        """>=3 useful with useful_rate>0.7 produces confidence_increase."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-a"] * 5},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": f"oc-{i}",
                "trace_ids": ["trace-a"],
                "metadata": {
                    "useful_trace_ids": ["trace-a"],
                    "harmful_trace_ids": [],
                },
                "pack_misses": [],
                "pack_miss_details": [],
            }
            for i in range(4)
        ])
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(metrics, [], [], [])
        matching = [a for a in actions if a.action_type == "confidence_increase"]
        assert len(matching) >= 1

    def test_manual_review_from_audit_sparks(self, tmp_path: Path) -> None:
        """Traces in audit sparks get manual_review proposal."""
        cell = _init_cell(tmp_path)
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(
            metrics, [], [],
            [{"trace_id": "trace-audit", "spark": "review_required"}],
        )
        matching = [a for a in actions if a.action_type == "manual_review"]
        assert any(a.trace_id == "trace-audit" for a in matching)

    def test_split_charge_on_mixed_signal(self, tmp_path: Path) -> None:
        """Traces in both useful and harmful get split_charge proposal."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-mixed"]},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-mixed"],
                "metadata": {
                    "useful_trace_ids": ["trace-mixed"],
                    "harmful_trace_ids": ["trace-mixed"],
                },
                "pack_misses": [],
                "pack_miss_details": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(metrics, [], [], [])
        matching = [a for a in actions if a.action_type == "split_charge"]
        assert len(matching) >= 1

    def test_supersession_candidate_deprecated_no_retrievals(self, tmp_path: Path) -> None:
        """Deprecated traces with 0 retrievals get supersession_candidate."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "traces" / "deprecated.jsonl", [
            {"trace_id": "trace-old", "status": "deprecated", "kind": "charge"},
        ])
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(metrics, [], [], [])
        matching = [a for a in actions if a.action_type == "supersession_candidate"]
        assert any(a.trace_id == "trace-old" for a in matching)

    def test_repeated_misses_produce_affinity_not_deprecation(self, tmp_path: Path) -> None:
        """Acceptance: repeated misses produce affinity proposals, not deprecation."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-repeated"] * 5},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": [],
                "metadata": {},
                "pack_misses": ["trace-repeated"] * 4,
                "pack_miss_details": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(metrics, [], [], [])
        types = {a.action_type for a in actions}
        assert "retrieval_affinity_decrease" in types
        assert "supersession_candidate" not in types  # not deprecated

    def test_harmful_applied_produces_confidence_decrease(self, tmp_path: Path) -> None:
        """Acceptance: harmful applied Traces produce confidence-decrease proposals."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-harmful"]},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-harmful"],
                "metadata": {
                    "useful_trace_ids": [],
                    "harmful_trace_ids": ["trace-harmful"],
                },
                "pack_misses": [],
                "pack_miss_details": [],
            },
        ])
        metrics = compute_trace_metrics(cell)
        actions = propose_actions(metrics, [], [], [])
        assert any(
            a.action_type == "confidence_decrease" and a.trace_id == "trace-harmful"
            for a in actions
        )


# ---------------------------------------------------------------------------
# run_sweep (integration)
# ---------------------------------------------------------------------------


class TestRunSweep:
    def test_dry_run_default(self, tmp_path: Path) -> None:
        """run_sweep defaults to dry_run=True and never writes ledgers."""
        cell = _init_cell(tmp_path)
        report = run_sweep(cell)
        assert report.dry_run is True
        assert isinstance(report, SweepReport)
        # Verify ledgers are untouched
        assert not (cell / "ledger" / "any_new_file.jsonl").exists()

    def test_deterministic_output(self, tmp_path: Path) -> None:
        """Repeated runs on same data produce identical reports (excluding timestamp)."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-a"]},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-a"],
                "metadata": {"useful_trace_ids": ["trace-a"]},
                "pack_misses": [],
                "pack_miss_details": [],
            },
        ])

        report1 = run_sweep(cell)
        report2 = run_sweep(cell)

        d1 = report1.to_dict()
        d2 = report2.to_dict()
        # Remove timestamp fields which always differ
        for d in (d1, d2):
            d.pop("scanned_at", None)
        assert d1 == d2

    def test_report_structure(self, tmp_path: Path) -> None:
        """Report dict has expected top-level keys."""
        cell = _init_cell(tmp_path)
        report = run_sweep(cell)
        d = report.to_dict()
        assert "cell_id" in d
        assert "scanned_at" in d
        assert "dry_run" in d
        assert "trace_count" in d
        assert "proposed_action_count" in d
        assert "summary" in d
        assert "proposed_actions" in d
        assert "trace_metrics" in d

    def test_multiple_traces_integration(self, tmp_path: Path) -> None:
        """Full integration with mixed traces produces sensible proposals."""
        cell = _init_cell(tmp_path)
        _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
            {"loadout_id": "lo-1", "selected_ids": ["trace-good", "trace-bad", "trace-miss"]},
            {"loadout_id": "lo-2", "selected_ids": ["trace-good", "trace-miss"]},
            {"loadout_id": "lo-3", "selected_ids": ["trace-miss"]},
        ])
        _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
            {
                "outcome_id": "oc-1",
                "trace_ids": ["trace-good", "trace-bad"],
                "metadata": {
                    "useful_trace_ids": ["trace-good"],
                    "harmful_trace_ids": ["trace-bad"],
                },
                "pack_misses": ["trace-miss"],
                "pack_miss_details": [],
            },
            {
                "outcome_id": "oc-2",
                "trace_ids": ["trace-good"],
                "metadata": {
                    "useful_trace_ids": ["trace-good"],
                    "harmful_trace_ids": [],
                },
                "pack_misses": ["trace-miss"],
                "pack_miss_details": [],
            },
            {
                "outcome_id": "oc-3",
                "trace_ids": ["trace-good"],
                "metadata": {
                    "useful_trace_ids": ["trace-good"],
                    "harmful_trace_ids": [],
                },
                "pack_misses": ["trace-miss"],
                "pack_miss_details": [],
            },
        ])
        _write_jsonl(cell / "traces" / "approved.jsonl", [
            {"trace_id": "trace-good", "status": "approved", "kind": "charge", "confidence": 0.8},
            {"trace_id": "trace-bad", "status": "approved", "kind": "charge", "confidence": 0.6},
        ])

        report = run_sweep(cell)
        d = report.to_dict()

        assert d["trace_count"] == 3
        assert d["cell_id"] == "test-cell"
        assert d["dry_run"] is True

        # trace-good: 2 retrievals (only in lo-1, lo-2), 3 applications, 3 useful
        good_metrics = d["trace_metrics"]["trace-good"]
        assert good_metrics["retrieval_count"] == 2
        assert good_metrics["application_count"] == 3
        assert good_metrics["useful_count"] == 3

        # trace-bad: 1 retrieval, 1 application, 1 harmful => confidence_decrease
        bad_metrics = d["trace_metrics"]["trace-bad"]
        assert bad_metrics["harmful_count"] == 1

        action_types = {a["action_type"] for a in d["proposed_actions"]}
        assert "confidence_increase" in action_types
        assert "confidence_decrease" in action_types

    def test_sweep_with_output_path(self, tmp_path: Path) -> None:
        """Output path gets the report JSON file written."""
        cell = _init_cell(tmp_path)
        out = tmp_path / "reports" / "sweep-out.json"
        report = run_sweep(cell, output_path=out)
        assert out.exists()
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded == report.to_dict()


# ---------------------------------------------------------------------------
# Regression: no mutations
# ---------------------------------------------------------------------------


class TestSweepReadOnly:
    def test_no_ledger_files_created(self, tmp_path: Path) -> None:
        """Sweep in dry-run mode creates no new ledger files."""
        cell = _init_cell(tmp_path)
        # Record state before
        before = sorted(str(p) for p in cell.rglob("*") if p.suffix == ".jsonl")
        run_sweep(cell)
        after = sorted(str(p) for p in cell.rglob("*") if p.suffix == ".jsonl")
        assert before == after

def test_event_history_is_surfaced_in_proposals(tmp_path: Path) -> None:
    cell = _init_cell(tmp_path)
    _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
        {"loadout_id": "lo-1", "selected_ids": ["trace-a"] * 5},
    ])
    _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
        {
            "outcome_id": "oc-1",
            "trace_ids": [],
            "metadata": {},
            "pack_miss_details": [{"charge_id": "trace-a"}] * 4,
            "pack_misses": [],
        },
    ])
    _write_jsonl(cell / "ledger" / "retrieval_affinity_events.jsonl", [
        {"affinity_event_id": "ae-1", "trace_id": "trace-a", "delta": -0.1},
        {"affinity_event_id": "ae-2", "charge_id": "trace-a", "delta": -0.2},
    ])

    report = run_sweep(cell).to_dict()
    action = next(
        item for item in report["proposed_actions"]
        if item["action_type"] == "retrieval_affinity_decrease"
    )

    assert action["supporting_data"]["retrieval_affinity_event_count"] == 2
    assert action["signal_strength"] > 0.6


def test_hygiene_sweep_report_delegates_to_read_only_sweep(tmp_path: Path) -> None:
    from shyftr.reports.hygiene import sweep_report

    cell = _init_cell(tmp_path, cell_id="hygiene-sweep")
    before = sorted(str(path.relative_to(cell)) for path in cell.rglob("*"))

    report = sweep_report(cell)

    after = sorted(str(path.relative_to(cell)) for path in cell.rglob("*"))
    assert report["cell_id"] == "hygiene-sweep"
    assert report["dry_run"] is True
    assert before == after

def test_charge_ledgers_are_included_in_metrics(tmp_path: Path) -> None:
    cell = _init_cell(tmp_path)
    _write_jsonl(cell / "charges" / "approved.jsonl", [
        {
            "charge_id": "charge-a",
            "cell_id": "cell-1",
            "statement": "Charge evidence",
            "source_fragment_ids": ["frag-a"],
            "status": "approved",
            "confidence": 0.8,
        }
    ])
    _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
        {"retrieval_id": "r-1", "selected_ids": ["charge-a"]},
    ])

    report = run_sweep(cell).to_dict()

    assert "charge-a" in report["trace_metrics"]
    assert report["trace_metrics"]["charge-a"]["trace_status"] == "approved"
    assert report["trace_metrics"]["charge-a"]["source_fragment_ids"] == ["frag-a"]


def test_canonical_event_fields_map_to_trace_metrics(tmp_path: Path) -> None:
    cell = _init_cell(tmp_path)
    _write_jsonl(cell / "traces" / "approved.jsonl", [
        {
            "trace_id": "trace-frag",
            "cell_id": "cell-1",
            "statement": "Trace with fragment-scoped events",
            "source_fragment_ids": ["fragment-a"],
            "status": "approved",
        },
        {
            "trace_id": "trace-result",
            "cell_id": "cell-1",
            "statement": "Trace with result-scoped events",
            "source_fragment_ids": ["fragment-b"],
            "status": "approved",
        },
    ])
    _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
        {"retrieval_id": "r-1", "selected_ids": ["trace-result"] * 5},
    ])
    _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
        {
            "outcome_id": "oc-1",
            "trace_ids": ["trace-frag"],
            "metadata": {"harmful_trace_ids": ["trace-frag"]},
            "pack_miss_details": [{"charge_id": "trace-result"}] * 4,
            "pack_misses": [],
        },
    ])
    _write_jsonl(cell / "ledger" / "retrieval_affinity_events.jsonl", [
        {"affinity_event_id": "ae-1", "result_id": "trace-result", "score": 0.2},
    ])
    _write_jsonl(cell / "ledger" / "confidence_events.jsonl", [
        {"confidence_event_id": "ce-1", "fragment_id": "fragment-a", "confidence": 0.1},
    ])
    _write_jsonl(cell / "ledger" / "audit_sparks.jsonl", [
        {"spark_id": "spark-1", "fragment_id": "fragment-a", "action": "review"},
    ])

    report = run_sweep(cell).to_dict()
    actions = report["proposed_actions"]
    result_action = next(
        item for item in actions
        if item["trace_id"] == "trace-result" and item["action_type"] == "retrieval_affinity_decrease"
    )
    assert result_action["supporting_data"]["retrieval_affinity_event_count"] == 1

    confidence_action = next(
        item for item in actions
        if item["trace_id"] == "trace-frag" and item["action_type"] == "confidence_decrease"
    )
    assert confidence_action["supporting_data"]["confidence_event_count"] == 1
    assert any(
        item["trace_id"] == "trace-frag" and item["action_type"] == "manual_review"
        for item in actions
    )

def test_retrieval_logs_count_selected_and_caution_once_per_log(tmp_path: Path) -> None:
    cell = _init_cell(tmp_path)
    _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
        {"retrieval_id": "r-1", "selected_ids": ["trace-a"], "caution_ids": ["trace-a"]},
    ])
    _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
        {
            "outcome_id": "oc-1",
            "trace_ids": [],
            "metadata": {},
            "pack_miss_details": [{"charge_id": "trace-a"}],
            "pack_misses": [],
        },
    ])

    report = run_sweep(cell).to_dict()

    assert report["trace_metrics"]["trace-a"]["retrieval_count"] == 1
    assert report["trace_metrics"]["trace-a"]["miss_rate"] == 1.0

def test_propose_appends_deterministic_events_and_deduplicates_open_proposals(tmp_path: Path) -> None:
    cell = _init_cell(tmp_path, "cell-propose")
    _write_jsonl(cell / "charges" / "approved.jsonl", [
        {"charge_id": "trace-a", "cell_id": "cell-propose", "source_fragment_ids": ["frag-a"], "status": "approved", "confidence": 0.6},
        {"charge_id": "trace-b", "cell_id": "cell-propose", "source_fragment_ids": ["frag-b"], "status": "approved", "confidence": 0.6},
    ])
    _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
        {"loadout_id": f"lo-{i}", "selected_ids": ["trace-a"]} for i in range(4)
    ])
    _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
        {"outcome_id": "oc-a", "trace_ids": ["trace-b"], "metadata": {"harmful_trace_ids": ["trace-b"]}, "pack_miss_details": [{"charge_id": "trace-a"}] * 4},
    ])

    report = run_sweep(cell, propose=True, dry_run=False)
    assert report.written_proposal_ids
    assert report.summary["proposal_events_written"] == len(report.written_proposal_ids)

    confidence_rows = [record for _, record in read_jsonl(cell / "ledger" / "confidence_events.jsonl")]
    retrieval_rows = [record for _, record in read_jsonl(cell / "ledger" / "retrieval_affinity_events.jsonl")]
    assert {row["event_status"] for row in confidence_rows + retrieval_rows} == {"proposed"}
    assert all("proposal_key" in row for row in confidence_rows + retrieval_rows)
    assert all(row["proposal_event_id"] in report.written_proposal_ids for row in confidence_rows + retrieval_rows)
    assert confidence_rows[0]["confidence"] is None
    assert retrieval_rows[0]["result_id"] == "trace-a"

    second = run_sweep(cell, propose=True, dry_run=False)
    assert second.written_proposal_ids == []
    assert sorted(second.skipped_proposal_ids) == sorted(report.written_proposal_ids)
    assert len([record for _, record in read_jsonl(cell / "ledger" / "confidence_events.jsonl")]) == len(confidence_rows)
    assert len([record for _, record in read_jsonl(cell / "ledger" / "retrieval_affinity_events.jsonl")]) == len(retrieval_rows)


def test_dry_run_with_propose_writes_no_proposal_events(tmp_path: Path) -> None:
    cell = _init_cell(tmp_path, "cell-dry")
    _write_jsonl(cell / "charges" / "approved.jsonl", [
        {"charge_id": "trace-a", "cell_id": "cell-dry", "source_fragment_ids": ["frag-a"], "status": "approved", "confidence": 0.6},
    ])
    _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
        {"loadout_id": f"lo-{i}", "selected_ids": ["trace-a"]} for i in range(4)
    ])
    _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
        {"outcome_id": "oc-a", "trace_ids": [], "metadata": {}, "pack_miss_details": [{"charge_id": "trace-a"}] * 4},
    ])

    report = run_sweep(cell, propose=True, dry_run=True)
    assert report.written_proposal_ids == []
    assert not (cell / "ledger" / "retrieval_affinity_events.jsonl").exists()


def test_apply_low_risk_only_marks_retrieval_affinity_decreases(tmp_path: Path) -> None:
    cell = _init_cell(tmp_path, "cell-low-risk")
    _write_jsonl(cell / "charges" / "approved.jsonl", [
        {"charge_id": "trace-a", "cell_id": "cell-low-risk", "source_fragment_ids": ["frag-a"], "status": "approved", "confidence": 0.6},
        {"charge_id": "trace-b", "cell_id": "cell-low-risk", "source_fragment_ids": ["frag-b"], "status": "approved", "confidence": 0.6},
    ])
    _write_jsonl(cell / "ledger" / "retrieval_logs.jsonl", [
        {"loadout_id": f"lo-{i}", "selected_ids": ["trace-a", "trace-b"]} for i in range(4)
    ])
    _write_jsonl(cell / "ledger" / "outcomes.jsonl", [
        {"outcome_id": "oc-a", "trace_ids": ["trace-b"], "metadata": {"harmful_trace_ids": ["trace-b"]}, "pack_miss_details": [{"charge_id": "trace-a"}] * 4},
    ])

    report = run_sweep(cell, propose=True, dry_run=False, apply_low_risk=True)
    retrieval_rows = [record for _, record in read_jsonl(cell / "ledger" / "retrieval_affinity_events.jsonl")]
    confidence_rows = [record for _, record in read_jsonl(cell / "ledger" / "confidence_events.jsonl")]
    assert retrieval_rows
    assert confidence_rows
    assert all(row["event_status"] == "applied_low_risk" for row in retrieval_rows if row["action_type"] == "retrieval_affinity_decrease")
    assert all(row["event_status"] == "proposed" for row in confidence_rows)
    assert sorted(report.apply_low_risk_written_ids) == sorted(row["proposal_event_id"] for row in retrieval_rows if row["action_type"] == "retrieval_affinity_decrease")
    assert not (cell / "charges" / "isolated.jsonl").exists()
