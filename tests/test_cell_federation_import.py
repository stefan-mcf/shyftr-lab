from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.federation import approve_import, export_cell, import_package, list_imports, reject_import
from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.loadout import LoadoutTaskInput, assemble_loadout


def _package(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = init_cell(tmp_path, "source-cell")
    target = init_cell(tmp_path, "target-cell")
    append_jsonl(source / "traces" / "approved.jsonl", {"trace_id": "mem-source", "cell_id": "source-cell", "statement": "shared retry backoff memory", "source_fragment_ids": ["frag-source"], "status": "approved", "sensitivity": "public"})
    package = tmp_path / "package.json"
    export_cell(source, package)
    return source, target, package


def test_import_into_cell_starts_with_imported_trust_label(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    result = import_package(target, package)
    assert result["imports"][0]["trust_label"] == "imported"


def test_imported_memory_requires_review_before_local_truth_treatment(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    import_package(target, package)
    assert (target / "traces" / "approved.jsonl").read_text(encoding="utf-8") == ""


def test_import_review_approval_changes_trust_label_to_verified(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    import_id = import_package(target, package)["imports"][0]["import_id"]
    event = approve_import(target, import_id, reviewer="operator", rationale="ok")
    assert event["trust_label"] == "verified"
    assert "verified" in (target / "traces" / "approved.jsonl").read_text(encoding="utf-8")


def test_import_review_rejection_excludes_import_from_packs(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    import_id = import_package(target, package)["imports"][0]["import_id"]
    reject_import(target, import_id, reviewer="operator", rationale="no")
    pack = assemble_loadout(LoadoutTaskInput(str(target), "retry backoff", "task"))
    assert pack.items == []


def test_import_without_review_is_not_discoverable_via_default_search(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    import_package(target, package)
    pack = assemble_loadout(LoadoutTaskInput(str(target), "retry backoff", "task"))
    assert pack.items == []


def test_federated_trust_label_does_not_bypass_policy_by_default(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    import_package(target, package, trust_label="federated")
    pack = assemble_loadout(LoadoutTaskInput(str(target), "retry backoff", "task"))
    assert pack.items == []


def test_federation_provenance_includes_source_cell_id(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    candidate = import_package(target, package)["imports"][0]
    assert candidate["provenance"]["source_cell_id"] == "source-cell"


def test_federation_is_selective_cell_can_import_single_memories_not_entire_cell(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    result = import_package(target, package, record_ids=["mem-source"])
    assert result["imported_count"] == 1


def test_federation_audit_log_records_all_imports(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    import_package(target, package)
    assert "imported" in (target / "ledger" / "federation_events.jsonl").read_text(encoding="utf-8")


def test_no_silent_local_truth_mutation_on_import(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    before = (target / "traces" / "approved.jsonl").read_text(encoding="utf-8")
    import_package(target, package)
    assert (target / "traces" / "approved.jsonl").read_text(encoding="utf-8") == before


def test_import_provenance_chain_is_preserved(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    candidate = import_package(target, package)["imports"][0]
    assert candidate["provenance"]["source_export_id"] == json.loads(package.read_text(encoding="utf-8"))["export_id"]


def test_import_from_untrusted_cell_starts_as_imported_not_verified(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    candidate = import_package(target, package)["imports"][0]
    assert candidate["trust_label"] == "imported"
    assert candidate["trust_label"] != "verified"


def test_federation_with_nonexistent_source_cell_raises(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    payload = json.loads(package.read_text(encoding="utf-8"))
    payload.pop("source_cell_id")
    package.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="source_cell_id"):
        import_package(target, package)


def test_list_imports_merges_latest_review(tmp_path: Path) -> None:
    _source, target, package = _package(tmp_path)
    import_id = import_package(target, package)["imports"][0]["import_id"]
    approve_import(target, import_id, reviewer="operator", rationale="ok")
    assert list_imports(target, status="approved")[0]["trust_label"] == "verified"
