from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.provider.memory import remember, search
from shyftr.mutations import deprecate_charge, restore_charge
from shyftr.store.sqlite import open_sqlite, rebuild_from_cell, trace_lifecycle_view


def _seed_cell_with_duplicate_trace(tmp_path: Path) -> tuple[Path, str, str]:
    cell = init_cell(tmp_path, "core")
    manifest = json.loads((cell / "config" / "cell_manifest.json").read_text(encoding="utf-8"))
    cell_id = manifest["cell_id"]

    trace_id = "mem-dup-1"

    # Initial approved row.
    append_jsonl(
        cell / "traces" / "approved.jsonl",
        {
            "trace_id": trace_id,
            "cell_id": cell_id,
            "statement": "Initial statement.",
            "status": "approved",
            "confidence": 0.6,
            "source_fragment_ids": ["frag-old"],
        },
    )

    # Later append-only row for the same logical id: status changes away from approved.
    append_jsonl(
        cell / "traces" / "approved.jsonl",
        {
            "trace_id": trace_id,
            "cell_id": cell_id,
            "statement": "Later statement, but deprecated.",
            "status": "deprecated",
            "confidence": 0.2,
            "source_fragment_ids": ["frag-old"],
        },
    )

    return cell, cell_id, trace_id


def test_confidence_reads_latest_row_and_respects_approved_status(tmp_path: Path) -> None:
    """Confidence adjustment must not treat superseded/deprecated rows as approved.

    Contract pinned (P9-2): append-only reads are latest-row-wins by logical id,
    and effective "approved" state must not be derived from stale historical rows.
    """

    cell, _cell_id, trace_id = _seed_cell_with_duplicate_trace(tmp_path)

    from shyftr.confidence import adjust_confidence

    # Attempting to adjust a deprecated trace should perform no adjustment.
    adjustments = adjust_confidence(
        cell_path=cell,
        outcome_id="out-1",
        useful_trace_ids=[trace_id],
        harmful_trace_ids=[],
        result="success",
    )

    assert adjustments == []

    # No new rows should be appended.
    rows = [record for _, record in __import__("shyftr.ledger", fromlist=["read_jsonl"]).read_jsonl(cell / "traces" / "approved.jsonl")]
    assert len(rows) == 2


def test_ledger_state_latest_record_by_key_is_latest_row_wins() -> None:
    from shyftr.ledger_state import latest_record_by_key

    records = [
        {"trace_id": "a", "v": 1},
        {"trace_id": "b", "v": 2},
        {"trace_id": "a", "v": 3},
    ]
    assert latest_record_by_key(records, "trace_id", "a") == {"trace_id": "a", "v": 3}


def test_sqlite_lifecycle_projection_uses_latest_restore_event(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "Prefer latest append-only state.", "preference")
    memory_id = remembered.memory_id
    assert memory_id is not None

    deprecate_charge(cell, memory_id, reason="old state", actor="test")
    restore_charge(cell, memory_id, reason="latest state wins", actor="test")

    assert [item.memory_id for item in search(cell, "latest append-only")] == [memory_id]

    db = open_sqlite(tmp_path / "projection.sqlite")
    rebuild_from_cell(db, cell)
    projected = {
        row["trace_id"]: row
        for row in trace_lifecycle_view(db)
    }

    assert projected[memory_id]["lifecycle_state"] == "current"
    assert projected[memory_id]["include_in_retrieval"] == 1
    assert projected[memory_id]["include_in_pack"] == 1
