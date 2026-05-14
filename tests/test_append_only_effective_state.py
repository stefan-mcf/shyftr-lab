from __future__ import annotations

from pathlib import Path

import pytest

from shyftr.confidence import adjust_confidence
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.ledger_state import latest_by_key, latest_record_by_key
from shyftr.pack import LoadoutTaskInput, assemble_loadout


def _records(path: Path) -> list[dict]:
    return [record for _, record in read_jsonl(path)]


def _make_trace(trace_id: str = "t1", confidence: float = 0.5, **overrides) -> dict:
    base = {
        "trace_id": trace_id,
        "memory_id": trace_id,
        "cell_id": "test-cell",
        "statement": f"Statement for {trace_id}",
        "rationale": f"Rationale for {trace_id}",
        "source_fragment_ids": ["f1"],
        "status": "approved",
        "confidence": confidence,
        "tags": ["python"],
        "kind": "guidance",
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
    }
    base.update(overrides)
    return base


def test_latest_by_key_keeps_first_seen_order_and_latest_values() -> None:
    records = [
        {"trace_id": "t1", "confidence": 0.5, "statement": "first t1"},
        {"trace_id": "t2", "confidence": 0.4, "statement": "first t2"},
        {"trace_id": "t1", "confidence": 0.7, "statement": "latest t1"},
    ]

    deduped = latest_by_key(records, "trace_id")

    assert [row["trace_id"] for row in deduped] == ["t1", "t2"]
    assert deduped[0]["confidence"] == 0.7
    assert deduped[0]["statement"] == "latest t1"
    assert deduped[1]["confidence"] == 0.4


def test_latest_record_by_key_returns_last_matching_row() -> None:
    records = [
        {"trace_id": "t1", "confidence": 0.5},
        {"trace_id": "t1", "confidence": 0.6},
        {"trace_id": "t2", "confidence": 0.7},
    ]

    latest = latest_record_by_key(records, "trace_id", "t1")

    assert latest is not None
    assert latest["confidence"] == 0.6


def test_confidence_adjustment_reads_latest_trace_row(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "test-cell")
    approved = cell / "traces" / "approved.jsonl"
    append_jsonl(approved, _make_trace("t1", confidence=0.50))
    append_jsonl(approved, _make_trace("t1", confidence=0.55, use_count=1, success_count=1))

    adjustments = adjust_confidence(
        cell_path=cell,
        outcome_id="oc-1",
        useful_trace_ids=["t1"],
        harmful_trace_ids=[],
        result="success",
    )

    assert len(adjustments) == 1
    assert adjustments[0].old_confidence == 0.55
    assert adjustments[0].new_confidence == pytest.approx(0.60)

    rows = _records(approved)
    assert rows[-1]["trace_id"] == "t1"
    assert rows[-1]["confidence"] == pytest.approx(0.60)


def test_pack_assembly_deduplicates_latest_trace_rows(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "test-cell")
    approved = cell / "traces" / "approved.jsonl"
    append_jsonl(approved, _make_trace("t1", confidence=0.40, statement="older row"))
    append_jsonl(approved, _make_trace("t1", confidence=0.80, statement="latest row"))

    assembled = assemble_loadout(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="latest row",
            task_id="task-1",
            max_items=10,
        )
    )

    matching_items = [item for item in assembled.items if item.item_id == "t1"]
    assert len(matching_items) == 1
    assert matching_items[0].statement == "latest row"
    assert assembled.retrieval_log.selected_ids.count("t1") == 1
