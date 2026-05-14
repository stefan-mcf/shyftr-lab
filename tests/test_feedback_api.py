"""Runtime Outcome API tests for RI-6."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.integrations.outcome_api import (
    RuntimeOutcomeReport,
    RuntimeOutcomeResponse,
    process_runtime_outcome_report,
)
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl


def _cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "runtime-outcome-cell")


def _report(cell: Path, **overrides) -> RuntimeOutcomeReport:
    payload = {
        "cell_path_or_id": str(cell),
        "loadout_id": "lo-runtime-001",
        "result": "success",
        "external_system": "runtime-example",
        "external_scope": "workspace/default",
        "external_run_id": "run-001",
        "external_task_id": "task-001",
        "applied_trace_ids": ["tr-guidance", "tr-background"],
        "useful_trace_ids": ["tr-guidance"],
        "harmful_trace_ids": [],
        "ignored_trace_ids": ["tr-background"],
        "violated_caution_ids": ["tr-caution"],
        "missing_memory_notes": ["Document how to roll back the deployment safely."],
        "verification_evidence": {"tests": "passed"},
        "runtime_metadata": {"duration_seconds": 42},
        "tags": ["runtime", "outcome"],
    }
    payload.update(overrides)
    return RuntimeOutcomeReport.from_dict(payload)


def _ledger_rows(path: Path):
    return [row for _, row in read_jsonl(path)]


def test_runtime_outcome_report_round_trips_all_contract_fields(tmp_path):
    report = _report(_cell(tmp_path))

    decoded = RuntimeOutcomeReport.from_json(report.to_json())

    assert decoded == report
    payload = decoded.to_dict()
    assert payload["external_run_id"] == "run-001"
    assert payload["ignored_trace_ids"] == ["tr-background"]
    assert payload["violated_caution_ids"] == ["tr-caution"]
    assert payload["missing_memory_notes"] == ["Document how to roll back the deployment safely."]


def test_runtime_outcome_response_round_trips():
    response = RuntimeOutcomeResponse(
        status="accepted",
        accepted=True,
        outcome_id="oc-123",
        trace_counters=[{"trace_id": "tr-1", "use_count": 1}],
        warnings=["kept result as supplied"],
    )

    assert RuntimeOutcomeResponse.from_json(response.to_json()) == response


def test_process_runtime_outcome_report_records_success_append_only_with_external_refs(tmp_path):
    cell = _cell(tmp_path)
    report = _report(cell)

    response = process_runtime_outcome_report(report)

    assert response.accepted is True
    assert response.status == "accepted"
    outcomes = _ledger_rows(cell / "ledger" / "outcomes.jsonl")
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome["loadout_id"] == "lo-runtime-001"
    assert outcome["trace_ids"] == ["tr-guidance", "tr-background"]
    metadata = outcome["metadata"]
    assert metadata["useful_trace_ids"] == ["tr-guidance"]
    evidence = metadata["verification_evidence"]
    assert evidence["external_system"] == "runtime-example"
    assert evidence["external_scope"] == "workspace/default"
    assert evidence["external_run_id"] == "run-001"
    assert evidence["external_task_id"] == "task-001"
    assert evidence["ignored_trace_ids"] == ["tr-background"]
    assert evidence["violated_caution_ids"] == ["tr-caution"]
    assert evidence["runtime_metadata"] == {"duration_seconds": 42}

    missing = _ledger_rows(cell / "ledger" / "missing_memory_candidates.jsonl")
    assert len(missing) == 1
    assert "roll back" in missing[0]["source_text"]


def test_process_runtime_outcome_report_records_failure_partial_and_unknown(tmp_path):
    cell = _cell(tmp_path)

    failure = process_runtime_outcome_report(
        _report(cell, result="failure", useful_trace_ids=[], harmful_trace_ids=["tr-guidance"])
    )
    partial = process_runtime_outcome_report(_report(cell, result="partial", loadout_id="lo-runtime-002"))
    unknown = process_runtime_outcome_report(_report(cell, result="unknown", loadout_id="lo-runtime-003"))

    assert failure.accepted is True
    assert partial.accepted is True
    assert unknown.accepted is True
    rows = _ledger_rows(cell / "ledger" / "outcomes.jsonl")
    assert [row["verdict"] for row in rows] == ["failure", "partial", "unknown"]


def test_process_runtime_outcome_report_rejects_missing_required_fields_and_missing_cell(tmp_path):
    cell = _cell(tmp_path)

    missing_result = process_runtime_outcome_report(_report(cell, result=""))
    missing_external_scope = process_runtime_outcome_report(_report(cell, external_scope=""))
    missing_cell = process_runtime_outcome_report(_report(tmp_path / "missing-cell"))

    assert missing_result.accepted is False
    assert "result is required" in missing_result.warnings
    assert missing_external_scope.accepted is False
    assert "external_scope is required" in missing_external_scope.warnings
    assert missing_cell.accepted is False
    assert "Cell path does not exist" in missing_cell.warnings[0]


def test_trace_counters_track_useful_and_harmful_reports(tmp_path):
    cell = _cell(tmp_path)

    process_runtime_outcome_report(_report(cell, applied_trace_ids=["tr-a"], useful_trace_ids=["tr-a"]))
    response = process_runtime_outcome_report(
        _report(
            cell,
            loadout_id="lo-runtime-002",
            result="failure",
            applied_trace_ids=["tr-a"],
            useful_trace_ids=[],
            harmful_trace_ids=["tr-a"],
            missing_memory_notes=[],
        )
    )

    counter = next(item for item in response.trace_counters if item["trace_id"] == "tr-a")
    assert counter["use_count"] == 2
    assert counter["success_count"] == 1
    assert counter["failure_count"] == 1


def test_outcome_cli_report_json_writes_append_only_outcome(tmp_path):
    cell = _cell(tmp_path)
    report_path = tmp_path / "outcome-report.json"
    report_path.write_text(json.dumps(_report(cell).to_dict()), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "shyftr.cli",
            "outcome",
            "--report-json",
            str(report_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "accepted"
    assert payload["accepted"] is True
    assert len(_ledger_rows(cell / "ledger" / "outcomes.jsonl")) == 1


def test_outcome_cli_positional_mode_still_requires_positional_args(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    result = subprocess.run(
        [sys.executable, "-m", "shyftr.cli", "outcome"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "unless --report-json is provided" in result.stderr
