from __future__ import annotations

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.loadout import LoadoutTaskInput, assemble_loadout
from shyftr.mutations import (
    effective_state_for_charge,
    forget_charge,
    get_effective_charge_states,
    isolation_charge,
    record_conflict,
    redact_charge,
)
from shyftr.provider.memory import MemoryProvider
from shyftr.store.sqlite import open_sqlite, rebuild_from_cell, trace_lifecycle_view


def _records(path):
    return [record for _, record in read_jsonl(path)]


def test_forget_replacement_and_deprecation_are_append_only_effective_state(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    provider = MemoryProvider(cell)
    old = provider.remember("User prefers long narrative updates.", "preference")

    forgotten = provider.forget(old.charge_id, reason="user asked to forget it", actor="user")
    assert forgotten.action == "forget"
    assert provider.search("narrative updates") == []
    assert old.charge_id not in provider.profile().source_charge_ids

    replaced = provider.replace(
        old.charge_id,
        "User prefers concise terminal updates.",
        reason="user supplied replacement",
        actor="user",
    )
    deprecated = provider.deprecate(old.charge_id, reason="old style is stale", actor="user")

    assert replaced.replacement_charge_id
    assert deprecated.action == "deprecate"
    assert _records(cell / "traces" / "approved.jsonl")[0]["trace_id"] == old.charge_id
    assert _records(cell / "ledger" / "status_events.jsonl")
    assert _records(cell / "ledger" / "supersession_events.jsonl")[0]["old_charge_id"] == old.charge_id
    assert _records(cell / "ledger" / "deprecation_events.jsonl")[0]["charge_id"] == old.charge_id

    states = get_effective_charge_states(cell)
    assert states[old.charge_id].include_in_retrieval is False
    assert states[old.charge_id].include_in_profile is False
    assert states[old.charge_id].include_in_pack is False
    assert states[old.charge_id].replacement_charge_id == replaced.replacement_charge_id
    assert states[replaced.replacement_charge_id].include_in_retrieval is True
    assert [item.charge_id for item in provider.search("concise terminal updates")] == [replaced.replacement_charge_id]


def test_isolation_and_redaction_exclude_from_profile_search_and_pack(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    provider = MemoryProvider(cell)
    normal = provider.remember("Use pytest before pushing Python changes.", "workflow")
    sensitive = provider.remember("Sensitive profile token is never exposed.", "preference")
    isolated = provider.remember("Conflicting workflow should stay isolated.", "workflow")

    isolation_charge(cell, isolated.charge_id, reason="conflicting evidence", actor="reviewer")
    redact_charge(cell, sensitive.charge_id, reason="contains sensitive content", actor="reviewer")

    assert [item.charge_id for item in provider.search("pytest pushing workflow")] == [normal.charge_id]
    assert provider.search("Sensitive token") == []
    assert isolated.charge_id not in provider.profile().source_charge_ids
    assert sensitive.charge_id not in provider.profile().source_charge_ids

    loadout = assemble_loadout(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="pytest sensitive conflicting workflow",
            task_id="task-1",
            max_items=10,
        )
    )
    ids = [item.item_id for item in loadout.items]
    assert normal.charge_id in ids
    assert sensitive.charge_id not in ids
    assert isolated.charge_id not in ids
    assert _records(cell / "ledger" / "isolation_events.jsonl")[0]["status"] == "isolated"
    assert _records(cell / "ledger" / "redaction_events.jsonl")[0]["sensitive_excluded"] is True
    assert effective_state_for_charge(cell, sensitive.charge_id).sensitive_excluded is True


def test_conflict_recording_preserves_both_sides_without_choosing_winner(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    provider = MemoryProvider(cell)
    left = provider.remember("Use compact replies for terminal work.", "preference")
    right = provider.remember("Use detailed replies for planning work.", "preference")

    conflict = record_conflict(
        cell,
        left.charge_id,
        right.charge_id,
        reason="scope-specific style preferences conflict",
        actor="reviewer",
    )

    conflict_event = _records(cell / "ledger" / "conflict_events.jsonl")[0]
    assert conflict.event_id == conflict_event["event_id"]
    assert conflict_event["charge_ids"] == [left.charge_id, right.charge_id]
    assert conflict_event["winner_charge_id"] is None
    assert {item.charge_id for item in provider.search("replies work")} == {left.charge_id, right.charge_id}
    states = get_effective_charge_states(cell)
    assert states[left.charge_id].conflict_charge_ids == [right.charge_id]
    assert states[right.charge_id].conflict_charge_ids == [left.charge_id]


def test_sqlite_materialization_derives_latest_lifecycle_state(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    provider = MemoryProvider(cell)
    forgotten = provider.remember("Forget this preference from projections.", "preference")
    isolated = provider.remember("Isolate this workflow from normal packs.", "workflow")

    forget_charge(cell, forgotten.charge_id, reason="user request", actor="user")
    isolation_charge(cell, isolated.charge_id, reason="review wall", actor="reviewer")

    conn = open_sqlite(tmp_path / "shyftr.sqlite")
    try:
        rebuild_from_cell(conn, cell)
        rows = {row["trace_id"]: row for row in trace_lifecycle_view(conn)}
    finally:
        conn.close()

    assert rows[forgotten.charge_id]["lifecycle_state"] == "forgotten"
    assert rows[forgotten.charge_id]["include_in_retrieval"] == 0
    assert rows[isolated.charge_id]["lifecycle_state"] == "isolated"
    assert rows[isolated.charge_id]["include_in_profile"] == 0
