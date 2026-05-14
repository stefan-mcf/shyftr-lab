from __future__ import annotations

import pytest

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.observability import read_diagnostic_logs, summarize_diagnostics
from shyftr.provider.memory import MemoryProvider
from shyftr.readiness import (
    default_replacement_fixture,
    import_managed_memory_records,
    replacement_pilot_readiness,
    run_replacement_replay,
)


def _records(path):
    return [record for _, record in read_jsonl(path)]


def test_provider_full_replacement_lifecycle_logs_pack_signal_and_snapshot(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    provider = MemoryProvider(cell)
    remembered = provider.remember("Run tests before replacing a managed memory backend.", "workflow")

    pack = provider.pack("tests replacing memory backend", task_id="task-1", runtime_id="pytest")
    assert pack["pack_id"] == pack["loadout_id"]
    assert remembered.charge_id in pack["selected_ids"]
    assert pack["items"][0]["score_trace"]["selection_reason"]

    signal = provider.record_signal(
        pack["pack_id"],
        result="success",
        applied_charge_ids=[remembered.charge_id],
        useful_charge_ids=[remembered.charge_id],
        missing_memory_notes=["Need fallback archive proof."],
        runtime_id="pytest",
        task_id="task-1",
    )
    assert signal["accepted"] is True

    snapshot = provider.export_snapshot()
    assert snapshot["fallback_archive_preserved"] is True
    restored = init_cell(tmp_path, "restored", cell_type="user")
    imported = MemoryProvider(restored).import_snapshot(snapshot)
    assert imported["record_count"] >= 1
    with pytest.raises(ValueError, match="non-empty append-only ledger"):
        MemoryProvider(restored).import_snapshot(snapshot)

    logs = read_diagnostic_logs(cell)
    assert {log["operation"] for log in logs} >= {"pack", "signal", "export_snapshot"}
    assert read_diagnostic_logs(restored, operation="import_snapshot")
    pack_log = next(log for log in logs if log["operation"] == "pack")
    assert pack_log["selected_charge_ids"] == [remembered.charge_id]
    assert pack_log["token_estimate"] > 0
    assert summarize_diagnostics(cell)["diagnostic_count"] >= 3


def test_managed_memory_import_rejects_operational_state_and_readiness_replay_passes(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    imported = import_managed_memory_records(
        cell,
        [
            {"id": "good", "kind": "preference", "memory": "User prefers concise terminal updates."},
            {"id": "noise", "kind": "workflow", "memory": "Queue item task-123 is in_progress on branch tmp/demo."},
            {"id": "secret", "kind": "preference", "memory": "OpenAI API key is sk-1234567890abcdef."},
        ],
    )
    assert len(imported["imported_charge_ids"]) == 1
    assert imported["rejected"][0]["external_id"] == "noise"
    assert imported["rejected"][1]["external_id"] == "secret"
    assert len(_records(cell / "traces" / "approved.jsonl")) == 1

    report = run_replacement_replay(cell, default_replacement_fixture())
    assert report["status"] == "passed"
    assert report["deterministic_pack"] is True
    assert report["fallback_archive_preserved"] is True

    readiness = replacement_pilot_readiness(cell).to_dict()
    assert readiness["ready"] is True
    assert readiness["status"] == "passed"
    assert not readiness["blockers"]
    assert {check["name"] for check in readiness["checks"]} >= {
        "review_gated_promotions",
        "pack_retrieval_logs",
        "signal_linkage",
        "diagnostic_logs",
        "fallback_export",
    }


def test_replacement_pilot_readiness_replay_uses_shadow_cell(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    readiness = replacement_pilot_readiness(cell, run_replay=True).to_dict()

    assert readiness["ready"] is True
    assert readiness["replay_report"]["status"] == "passed"
    assert _records(cell / "traces" / "approved.jsonl") == []
    logs = read_diagnostic_logs(cell, operation="replacement_readiness")
    assert logs[-1]["metadata"]["replay_mode"] == "shadow"
