from __future__ import annotations

import json

from shyftr.integrations.retrieval_logs import list_retrieval_logs, sanitize_retrieval_log
from shyftr.layout import init_cell
from shyftr.pack import PackTaskInput, assemble_pack
from shyftr.provider.memory import remember
from shyftr.store.sqlite import open_sqlite, rebuild_from_cell


def test_retrieval_log_contract_survives_public_projection_and_sqlite_rebuild(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "Use bounded retry backoff for API calls.", "workflow")

    assembled = assemble_pack(
        PackTaskInput(
            cell_path=str(cell),
            query="retry backoff",
            task_id="phase9-retrieval-log",
            runtime_id="phase9-test",
            max_items=5,
            max_tokens=500,
            dry_run=False,
        )
    )

    ledger_logs = list_retrieval_logs(cell, loadout_id=assembled.pack_id)["logs"]
    assert len(ledger_logs) == 1
    public_log = ledger_logs[0]
    assert public_log["pack_id"] == assembled.pack_id
    assert public_log["loadout_id"] == assembled.pack_id
    assert public_log["generated_at"] == assembled.generated_at
    assert public_log["logged_at"] == assembled.generated_at
    assert public_log["cell_id"] == assembled.cell_id
    assert remembered.memory_id in public_log["selected_ids"]

    db = open_sqlite(tmp_path / "projection.sqlite")
    rebuild_from_cell(db, cell)
    row = db.execute(
        "SELECT retrieval_id, cell_id, pack_id, loadout_id, query, selected_ids, score_traces, logged_at, generated_at "
        "FROM retrieval_logs WHERE retrieval_id = ?",
        (assembled.retrieval_log.retrieval_id,),
    ).fetchone()

    assert row is not None
    columns = [
        "retrieval_id",
        "cell_id",
        "pack_id",
        "loadout_id",
        "query",
        "selected_ids",
        "score_traces",
        "logged_at",
        "generated_at",
    ]
    projected = dict(zip(columns, row))
    assert projected["cell_id"] == assembled.cell_id
    assert projected["pack_id"] == assembled.pack_id
    assert projected["loadout_id"] == assembled.pack_id
    assert projected["logged_at"] == assembled.generated_at
    assert projected["generated_at"] == assembled.generated_at
    assert remembered.memory_id in json.loads(projected["selected_ids"])
    assert remembered.memory_id in json.loads(projected["score_traces"])


def test_legacy_retrieval_log_public_projection_backfills_pack_aliases() -> None:
    public_log = sanitize_retrieval_log(
        {
            "retrieval_id": "rl-legacy",
            "loadout_id": "lo-legacy",
            "query": "legacy query",
            "generated_at": "2026-05-16T00:00:00+00:00",
            "selected_ids": ["mem-1"],
        }
    )

    assert public_log["pack_id"] == "lo-legacy"
    assert public_log["loadout_id"] == "lo-legacy"
    assert public_log["logged_at"] == "2026-05-16T00:00:00+00:00"
    assert public_log["generated_at"] == "2026-05-16T00:00:00+00:00"
    assert public_log["selected_ids"] == ["mem-1"]
