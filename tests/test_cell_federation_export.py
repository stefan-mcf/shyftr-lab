from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.federation import export_cell, validate_export_package
from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell


def _cell(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "project-alpha")
    append_jsonl(cell / "traces" / "approved.jsonl", {
        "trace_id": "mem-approved",
        "cell_id": "project-alpha",
        "statement": "approved public memory",
        "source_fragment_ids": ["frag-approved"],
        "status": "approved",
        "sensitivity": "public",
    })
    append_jsonl(cell / "ledger" / "fragments.jsonl", {"fragment_id": "frag-pending", "cell_id": "project-alpha", "text": "pending candidate", "review_status": "pending"})
    append_jsonl(cell / "ledger" / "feedback.jsonl", {"feedback_id": "fb-1", "cell_id": "project-alpha", "pack_id": "pack", "task_id": "task", "verdict": "success"})
    append_jsonl(cell / "ledger" / "patterns" / "approved.jsonl", {"pattern_id": "pat-approved", "cell_id": "project-alpha", "theme": "workflow", "summary": "approved pattern", "memory_ids": ["mem-approved"], "proposal_status": "approved"})
    append_jsonl(cell / "ledger" / "rules" / "approved.jsonl", {"rule_id": "rule-approved", "scope": "project-alpha", "statement": "approved rule", "pattern_ids": ["pat-approved"], "review_status": "approved"})
    (cell / "grid" / "vector.bin").write_text("grid data", encoding="utf-8")
    return cell


def test_export_cell_approved_memories_creates_export_file(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    out = tmp_path / "export.json"
    package = export_cell(cell, out)
    assert out.exists()
    assert package["records"]
    assert package["source_cell_id"] == "project-alpha"


def test_export_excludes_pending_and_rejected_candidates(tmp_path: Path) -> None:
    package = export_cell(_cell(tmp_path), tmp_path / "export.json")
    encoded = json.dumps(package)
    assert "frag-pending" not in encoded
    assert "pending candidate" not in encoded


def test_export_redacts_sensitive_memories_based_on_policy(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "secret", "cell_id": "project-alpha", "statement": "secret text", "source_fragment_ids": ["frag-secret"], "status": "approved", "sensitivity": "secret"})
    package = export_cell(cell, tmp_path / "export.json")
    encoded = json.dumps(package)
    assert "secret text" not in encoded
    assert any(row["record_id"] == "secret" for row in package["redaction_summary"]["excluded"])


def test_export_excludes_feedback_and_confidence_events(tmp_path: Path) -> None:
    package = export_cell(_cell(tmp_path), tmp_path / "export.json")
    encoded = json.dumps(package)
    assert "fb-1" not in encoded
    assert "feedback" not in encoded.lower()


def test_export_round_trip_schema_validates(tmp_path: Path) -> None:
    out = tmp_path / "export.json"
    export_cell(_cell(tmp_path), out)
    payload = validate_export_package(json.loads(out.read_text(encoding="utf-8")))
    assert payload["schema_version"].startswith("federation")


def test_export_records_source_cell_id_and_record_ids(tmp_path: Path) -> None:
    package = export_cell(_cell(tmp_path), tmp_path / "export.json")
    assert {record["record_id"] for record in package["records"]} >= {"mem-approved", "pat-approved", "rule-approved"}
    assert all(package["source_cell_id"] == "project-alpha" for _ in package["records"])


def test_export_does_not_include_grid_files(tmp_path: Path) -> None:
    package = export_cell(_cell(tmp_path), tmp_path / "export.json")
    assert "vector.bin" not in json.dumps(package)
    assert "grid data" not in json.dumps(package)


def test_export_rejects_unknown_record_kind(tmp_path: Path) -> None:
    package = export_cell(_cell(tmp_path), tmp_path / "export.json")
    package["records"].append({"record_kind": "unknown", "record_id": "x", "payload": {}, "trust_label": "local"})
    with pytest.raises(ValueError, match="Unknown"):
        validate_export_package(package)
