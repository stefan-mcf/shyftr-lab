from __future__ import annotations

import json
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.loadout import LoadoutTaskInput, assemble_loadout


def _make_cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "phase6-pack-cell")


def _append_trace(cell: Path, row: dict) -> dict:
    path = cell / "traces" / "approved.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _resource_trace(trace_id: str = "trace-resource-1", **overrides) -> dict:
    row = {
        "trace_id": trace_id,
        "cell_id": "phase6-pack-cell",
        "statement": "Release artifact reference for deployment verification.",
        "source_fragment_ids": ["frag-resource-1"],
        "status": "approved",
        "kind": "workflow",
        "memory_type": "resource",
        "confidence": 0.83,
        "tags": ["artifact", "deployment"],
        "resource_ref": {
            "ref_type": "artifact",
            "locator": "artifact://phase6/release-handoff",
            "label": "release handoff artifact",
        },
        "grounding_refs": [],
        "sensitivity": "internal",
        "retention_hint": "project",
    }
    row.update(overrides)
    return row


def _grounded_trace(trace_id: str = "trace-grounded-1", **overrides) -> dict:
    row = {
        "trace_id": trace_id,
        "cell_id": "phase6-pack-cell",
        "statement": "Deployment verification should consult the handoff artifact before rollout.",
        "source_fragment_ids": ["frag-grounded-1"],
        "status": "approved",
        "kind": "workflow",
        "memory_type": "semantic",
        "confidence": 0.79,
        "tags": ["deployment", "verification"],
        "grounding_refs": ["trace-resource-1"],
        "sensitivity": "internal",
        "retention_hint": "project",
    }
    row.update(overrides)
    return row


def test_pack_uses_resource_label_for_query_matching_and_preserves_resource_identity(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    _append_trace(cell, _resource_trace())

    loadout = assemble_loadout(LoadoutTaskInput(
        cell_path=str(cell),
        query="handoff artifact",
        task_id="phase6-pack-resource",
        max_items=5,
        runtime_id="runtime-a",
        user_id="reviewer-1",
        project_id="shyftr",
    ))

    assert [item.item_id for item in loadout.items] == ["trace-resource-1"]
    item = loadout.items[0]
    assert item.memory_type == "resource"
    assert item.resource_ref is not None
    assert item.resource_ref["label"] == "release handoff artifact"
    assert item.resource_ref["locator"] == "artifact://phase6/release-handoff"
    assert item.score_trace["resource_ref"]["label"] == "release handoff artifact"


def test_pack_preserves_grounding_refs_for_grounded_memory_items(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    _append_trace(cell, _resource_trace())
    _append_trace(cell, _grounded_trace())

    loadout = assemble_loadout(LoadoutTaskInput(
        cell_path=str(cell),
        query="rollout verification",
        task_id="phase6-pack-grounding",
        max_items=5,
        runtime_id="runtime-a",
        user_id="reviewer-1",
        project_id="shyftr",
    ))

    grounded = next(item for item in loadout.items if item.item_id == "trace-grounded-1")
    assert grounded.grounding_refs == ["trace-resource-1"]
    assert grounded.score_trace["grounding_refs"] == ["trace-resource-1"]
    assert grounded.sensitivity == "internal"
    assert grounded.retention_hint == "project"
