from __future__ import annotations

from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.pack import LoadoutTaskInput, assemble_loadout
from shyftr.store.sqlite import open_sqlite, rebuild_from_cell


def _make_trace(trace_id: str = "t1", **overrides) -> dict:
    base = {
        "trace_id": trace_id,
        "cell_id": "test-cell",
        "statement": f"Statement for {trace_id}",
        "rationale": f"Rationale for {trace_id}",
        "source_fragment_ids": ["f1"],
        "status": "approved",
        "confidence": 0.8,
        "tags": ["python"],
        "kind": "guidance",
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
    }
    base.update(overrides)
    return base


def test_fresh_retrieval_log_projects_cell_id_and_logged_at(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "test-cell")
    append_jsonl(cell / "traces" / "approved.jsonl", _make_trace())

    assembled = assemble_loadout(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="statement",
            task_id="task-1",
        )
    )

    conn = open_sqlite(tmp_path / "store.db")
    try:
        rebuild_from_cell(conn, cell)
        row = conn.execute(
            "SELECT retrieval_id, cell_id, query, selected_ids, logged_at FROM retrieval_logs WHERE retrieval_id = ?",
            (assembled.retrieval_log.retrieval_id,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == assembled.retrieval_log.retrieval_id
    assert row[1] == "test-cell"
    assert row[2] == "statement"
    assert row[3]
    assert row[4] == assembled.retrieval_log.logged_at


def test_legacy_generated_at_only_log_projects_to_logged_at(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "test-cell")
    append_jsonl(
        cell / "ledger" / "retrieval_logs.jsonl",
        {
            "retrieval_id": "rl-legacy",
            "loadout_id": "lo-legacy",
            "query": "legacy",
            "selected_ids": ["t1"],
            "score_traces": {"t1": {"semantic_score": 0.9}},
            "generated_at": "2026-05-07T00:00:00+00:00",
        },
    )

    conn = open_sqlite(tmp_path / "store.db")
    try:
        rebuild_from_cell(conn, cell)
        row = conn.execute(
            "SELECT retrieval_id, cell_id, logged_at FROM retrieval_logs WHERE retrieval_id = ?",
            ("rl-legacy",),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "rl-legacy"
    assert row[1] == "test-cell"
    assert row[2] == "2026-05-07T00:00:00+00:00"
