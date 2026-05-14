from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.ingest import sync_from_adapter
from shyftr.integrations.config import InputDefinition, RuntimeAdapterConfig
from shyftr.integrations.sync_state import (
    SYNC_STATE_FILENAME,
    SyncStateEntry,
    SyncStateStore,
    SyncStateError,
    SyncTruncationError,
    build_file_content_hash,
    check_file_truncation,
    count_file_jsonl_rows,
    count_lines,
    new_sync_entry,
    read_new_lines,
)
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl


def _runtime_with_jsonl(tmp_path: Path) -> Path:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "outcomes.jsonl").write_text(
        '{"task_id":"t1","external_run_id":"r1","verdict":"success"}\n'
        '{"task_id":"t2","external_run_id":"r2","verdict":"failure"}\n',
        encoding="utf-8",
    )
    return runtime


def _config(runtime_root: Path) -> RuntimeAdapterConfig:
    return RuntimeAdapterConfig(
        adapter_id="sync-adapter",
        cell_id="cell-main",
        external_system="generic-runtime",
        external_scope="runtime-session",
        source_root=str(runtime_root),
        identity_mapping={"external_run_id": "external_run_id"},
        inputs=[
            InputDefinition(
                kind="jsonl",
                path="outcomes.jsonl",
                source_kind="outcome",
                identity_mapping={"external_task_id": "task_id"},
            )
        ],
        ingest_options={"deduplicate": True},
    )


def test_sync_state_store_load_save_round_trip(tmp_path: Path) -> None:
    cell = tmp_path / "cell"
    cell.mkdir()
    store = SyncStateStore.load(cell)
    entry = SyncStateEntry(
        adapter_id="a",
        source_path="/tmp/source.jsonl",
        last_byte_offset=100,
        last_line_number=4,
        last_content_hash="h",
        last_sync_time="2026-04-24T00:00:00+00:00",
    )
    store.upsert_entry(entry)
    store.save()

    reloaded = SyncStateStore.load(cell)

    assert (cell / "indexes" / SYNC_STATE_FILENAME).exists()
    assert reloaded.get_entry("/tmp/source.jsonl") == entry
    assert reloaded.list_entries() == [entry]


def test_sync_state_load_corrupted_file_raises(tmp_path: Path) -> None:
    cell = tmp_path / "cell"
    indexes = cell / "indexes"
    indexes.mkdir(parents=True)
    (indexes / SYNC_STATE_FILENAME).write_text("{not-json", encoding="utf-8")

    with pytest.raises(SyncStateError):
        SyncStateStore.load(cell)


def test_check_file_truncation_allows_unchanged_and_appended(tmp_path: Path) -> None:
    source = tmp_path / "events.jsonl"
    source.write_text('{"a":1}\n', encoding="utf-8")
    entry = new_sync_entry(
        adapter_id="a",
        source_path=str(source),
        file_size=source.stat().st_size,
        line_count=1,
        content_hash=build_file_content_hash(source),
    )

    check_file_truncation(source, entry)
    with source.open("a", encoding="utf-8") as handle:
        handle.write('{"a":2}\n')
    check_file_truncation(source, entry)


def test_check_file_truncation_detects_smaller_and_same_size_rotation(tmp_path: Path) -> None:
    source = tmp_path / "events.jsonl"
    source.write_text("alpha\n", encoding="utf-8")
    entry = new_sync_entry("a", str(source), source.stat().st_size, 1, build_file_content_hash(source))

    source.write_text("beta!\n", encoding="utf-8")
    with pytest.raises(SyncTruncationError, match="rotated"):
        check_file_truncation(source, entry)

    source.write_text("x\n", encoding="utf-8")
    with pytest.raises(SyncTruncationError, match="truncated"):
        check_file_truncation(source, entry)


def test_read_new_lines_and_counts(tmp_path: Path) -> None:
    source = tmp_path / "events.jsonl"
    source.write_text('{"a":1}\n\n{"a":2}\n{"a":3}\n', encoding="utf-8")

    assert read_new_lines(source, 2) == ['{"a":2}', '{"a":3}']
    assert count_lines(source) == 4
    assert count_file_jsonl_rows(source) == 4


def test_sync_from_adapter_is_idempotent_and_writes_state(tmp_path: Path) -> None:
    runtime = _runtime_with_jsonl(tmp_path)
    cell = init_cell(tmp_path / "cells", "cell-main")
    config = _config(runtime)

    first = sync_from_adapter(cell, config)
    second = sync_from_adapter(cell, config)
    rows = [record for _, record in read_jsonl(cell / "ledger" / "sources.jsonl")]
    state = SyncStateStore.load(cell).get_entry(str(runtime / "outcomes.jsonl"))

    assert first["errors"] == []
    assert first["sources_ingested"] == 2
    assert second["errors"] == []
    assert second["sources_ingested"] == 0
    assert len(rows) == 2
    assert state is not None
    assert state.last_line_number == 2
    assert state.last_byte_offset == (runtime / "outcomes.jsonl").stat().st_size
    assert all(row["metadata"]["sync_state_path"].endswith(SYNC_STATE_FILENAME) for row in rows)


def test_sync_from_adapter_ingests_only_appended_jsonl_rows(tmp_path: Path) -> None:
    runtime = _runtime_with_jsonl(tmp_path)
    cell = init_cell(tmp_path / "cells", "cell-main")
    config = _config(runtime)

    first = sync_from_adapter(cell, config)
    with (runtime / "outcomes.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"task_id":"t3","external_run_id":"r3","verdict":"success"}\n')
    second = sync_from_adapter(cell, config)
    rows = [record for _, record in read_jsonl(cell / "ledger" / "sources.jsonl")]
    offsets = [row["metadata"]["external_refs"][0]["source_line_offset"] for row in rows]

    assert first["sources_ingested"] == 2
    assert second["sources_ingested"] == 1
    assert len(rows) == 3
    assert offsets == [1, 2, 3]
    assert second["synced_files"][0]["start_line"] == 2


def test_sync_from_adapter_blocks_rotation_until_reset(tmp_path: Path) -> None:
    runtime = _runtime_with_jsonl(tmp_path)
    cell = init_cell(tmp_path / "cells", "cell-main")
    config = _config(runtime)

    sync_from_adapter(cell, config)
    # Same byte length as original but different content means rotation/rewrite.
    original = (runtime / "outcomes.jsonl").read_text(encoding="utf-8")
    replacement = original.replace("success", "blocked", 1)
    if len(replacement.encode("utf-8")) != len(original.encode("utf-8")):
        replacement = "x" * len(original.encode("utf-8"))
    (runtime / "outcomes.jsonl").write_text(replacement, encoding="utf-8")

    with pytest.raises(SyncTruncationError):
        sync_from_adapter(cell, config)
