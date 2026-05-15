from __future__ import annotations

from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.loadout import LoadoutTaskInput, assemble_loadout
from shyftr.models import Trace
from shyftr.mutations import record_conflict
from shyftr.provider.memory import remember, search


def _records(path: Path):
    return [record for _, record in read_jsonl(path)]


def test_rule_memory_direct_write_requires_explicit_allow_direct_flag(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "phase7-core", cell_type="memory")

    result = remember(
        cell,
        "Escalate destructive cleanup only after operator approval.",
        "escalation_rule",
        memory_type="rule",
    )

    assert result.status == "pending_review"
    assert result.memory_id is None
    assert result.charge_id is None

    sources = _records(cell / "ledger" / "sources.jsonl")
    fragments = _records(cell / "ledger" / "fragments.jsonl")
    assert len(sources) == 1
    assert len(fragments) == 1
    assert fragments[0]["review_status"] == "pending"
    assert _records(cell / "ledger" / "reviews.jsonl") == []
    assert _records(cell / "ledger" / "promotions.jsonl") == []
    assert _records(cell / "traces" / "approved.jsonl") == []


def test_rule_memory_direct_write_can_be_explicitly_allowed(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "phase7-core", cell_type="memory")

    result = remember(
        cell,
        "Escalate destructive cleanup only after operator approval.",
        "escalation_rule",
        memory_type="rule",
        allow_direct_durable_memory=True,
    )

    assert result.status == "approved"
    assert result.charge_id is not None
    reviews = _records(cell / "ledger" / "reviews.jsonl")
    assert reviews[0]["metadata"]["regulator_decision"]["authority"] == "reviewed_precedence"
    results = search(cell, "operator approval", kinds=["escalation_rule"])
    assert [row.charge_id for row in results] == [result.charge_id]


def test_workflow_memory_direct_write_still_succeeds_without_explicit_override(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "phase7-core", cell_type="memory")

    result = remember(
        cell,
        "Use focused pytest before full pytest for Python repos.",
        "workflow",
    )

    assert result.status == "approved"
    assert result.charge_id is not None
    assert [row.charge_id for row in search(cell, "focused pytest", kinds=["workflow"])] == [result.charge_id]


def test_rule_memory_search_rejects_unknown_hash_fields_from_append_only_rows() -> None:
    row = {
        "trace_id": "trace-rule-hash-row",
        "cell_id": "cell-alpha",
        "statement": "Operator approval remains required for destructive cleanup.",
        "source_fragment_ids": ["frag-rule-1"],
        "kind": "escalation_rule",
        "memory_type": "rule",
        "status": "approved",
        "confidence": 0.8,
        "tags": [],
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "row_hash": "sha256:123",
        "previous_row_hash": "sha256:000",
    }

    trace = Trace.from_dict({k: v for k, v in row.items() if k not in {"row_hash", "previous_row_hash"}})
    assert trace.trace_id == row["trace_id"]
    assert trace.kind == row["kind"]
    assert trace.memory_type == "rule"


def test_recorded_conflicts_do_not_break_search_or_pack(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "phase7-core", cell_type="memory")
    left = remember(cell, "Use focused pytest before full pytest for Python repos.", "workflow")
    right = remember(cell, "Use full pytest first when release risk is high.", "workflow")

    event = record_conflict(
        cell,
        left.charge_id,
        right.charge_id,
        reason="operator noted conflicting workflow guidance",
        actor="reviewer-1",
    )

    assert event.action == "conflict"

    results = search(cell, "pytest", kinds=["workflow"])
    result_ids = {row.charge_id for row in results}
    assert left.charge_id in result_ids
    assert right.charge_id in result_ids

    loadout = assemble_loadout(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="pytest",
            task_id="phase7-pack",
        )
    )
    loadout_ids = {item.item_id for item in loadout.items}
    assert left.charge_id in loadout_ids
    assert right.charge_id in loadout_ids


def test_legacy_phase6_trace_rows_still_load_and_preserve_phase6_fields() -> None:
    row = {
        "trace_id": "trace-phase6-legacy",
        "cell_id": "cell-alpha",
        "statement": "Release closeout is grounded in the canonical handoff artifact.",
        "source_fragment_ids": ["frag-1"],
        "kind": "tool_quirk",
        "memory_type": "resource",
        "resource_ref": {
            "ref_type": "file",
            "locator": "/synthetic/artifacts/closeout.md",
            "label": "Phase closeout markdown",
        },
        "grounding_refs": ["trace-supporting-1"],
        "sensitivity": "internal",
        "retention_hint": "durable_reference",
        "status": "approved",
        "confidence": 0.8,
        "tags": ["phase6"],
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
    }

    trace = Trace.from_dict(row)
    round_tripped = trace.to_dict()

    assert round_tripped["trace_id"] == row["trace_id"]
    assert round_tripped["memory_type"] == row["memory_type"]
    assert round_tripped["grounding_refs"] == row["grounding_refs"]
    assert round_tripped["sensitivity"] == row["sensitivity"]
    assert round_tripped["retention_hint"] == row["retention_hint"]
    assert round_tripped["resource_ref"]["locator"] == row["resource_ref"]["locator"]
    assert round_tripped["resource_ref"]["label"] == row["resource_ref"]["label"]
    assert Trace.from_dict(round_tripped) == trace
