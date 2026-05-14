from __future__ import annotations

import json
import shutil
from pathlib import Path

from shyftr.ingest import ingest_from_adapter
from shyftr.integrations.config import InputDefinition, RuntimeAdapterConfig
from shyftr.integrations.file_adapter import FileAdapterError, FileSourceAdapter
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "integrations" / "generic_runtime"


def _runtime_copy(tmp_path: Path) -> Path:
    runtime_root = tmp_path / "runtime"
    shutil.copytree(FIXTURE_ROOT, runtime_root)
    return runtime_root


def _config(runtime_root: Path, **overrides: object) -> RuntimeAdapterConfig:
    config = RuntimeAdapterConfig(
        adapter_id="generic-file-adapter",
        cell_id="cell-main",
        external_system="generic-runtime",
        external_scope="runtime-session",
        source_root=str(runtime_root),
        identity_mapping={
            "external_run_id": "external_run_id",
            "external_task_id": "task_id",
        },
        inputs=[
            InputDefinition(kind="file", path="closeout-task-42.md", source_kind="closeout"),
            InputDefinition(kind="glob", path="*.log", source_kind="log"),
            InputDefinition(
                kind="jsonl",
                path="outcomes.jsonl",
                source_kind="outcome",
                identity_mapping={"external_task_id": "task_id"},
            ),
            InputDefinition(kind="directory", path="subdir", source_kind="note"),
        ],
        ingest_options={"deduplicate": True, "recursive": True},
    )
    values = config.to_dict() if hasattr(config, "to_dict") else dict(config.__dict__)
    values.update(overrides)
    return RuntimeAdapterConfig(**values)


def test_discovers_file_glob_jsonl_rows_and_directory_tree(tmp_path: Path) -> None:
    runtime_root = _runtime_copy(tmp_path)
    adapter = FileSourceAdapter(_config(runtime_root))

    refs = adapter.discover_sources()

    by_kind = {}
    for ref in refs:
        by_kind[ref.source_kind] = by_kind.get(ref.source_kind, 0) + 1
    assert by_kind["closeout"] == 1
    assert by_kind["log"] == 1
    assert by_kind["outcome"] == 4
    assert by_kind["note"] == 1
    assert len(refs) == 7


def test_jsonl_row_refs_preserve_line_identity_hash_and_external_ids(tmp_path: Path) -> None:
    runtime_root = _runtime_copy(tmp_path)
    adapter = FileSourceAdapter(
        RuntimeAdapterConfig(
            adapter_id="jsonl-adapter",
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
    )

    refs = adapter.discover_sources()

    assert [ref.source_line_offset for ref in refs] == [1, 2, 3, 4]
    first = refs[0]
    assert first.metadata is not None
    assert len(first.metadata["row_hash"]) == 64
    assert first.external_ids == {
        "external_run_id": "run-alpha",
        "external_task_id": "task-42",
    }
    payload = adapter.read_source(first)
    assert payload.kind == "json"
    assert payload.external_refs[0] == first
    assert len(payload.content_hash) == 64


def test_dry_run_summary_is_deterministic_and_does_not_mutate_cell(tmp_path: Path) -> None:
    runtime_root = _runtime_copy(tmp_path)
    cell = init_cell(tmp_path / "cells", "cell-main")
    adapter_config = _config(runtime_root)

    first = ingest_from_adapter(cell, adapter_config, dry_run=True)
    second = ingest_from_adapter(cell, adapter_config, dry_run=True)

    assert first == second
    assert first["sources_ingested"] == 0
    assert first["discovery_summary"]["total_sources"] == 7
    assert list(read_jsonl(cell / "ledger" / "sources.jsonl")) == []


def test_ingest_from_adapter_appends_sources_and_is_idempotent(tmp_path: Path) -> None:
    runtime_root = _runtime_copy(tmp_path)
    cell = init_cell(tmp_path / "cells", "cell-main")
    adapter_config = _config(runtime_root)

    first = ingest_from_adapter(cell, adapter_config)
    second = ingest_from_adapter(cell, adapter_config)
    rows = [record for _, record in read_jsonl(cell / "ledger" / "sources.jsonl")]

    assert first["errors"] == []
    assert first["sources_ingested"] == 7
    assert first["sources_skipped"] == 0
    assert second["errors"] == []
    assert second["sources_ingested"] == 0
    assert second["sources_skipped"] == 7
    assert len(rows) == 7
    assert all(row["metadata"]["adapter_id"] == "generic-file-adapter" for row in rows)
    assert all(row["metadata"]["external_refs"] for row in rows)
    outcome_rows = [row for row in rows if row["kind"] == "outcome"]
    assert len(outcome_rows) == 4
    assert all(
        row["metadata"]["external_refs"][0]["source_line_offset"] is not None
        for row in outcome_rows
    )


def test_missing_source_root_raises_useful_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing-runtime"
    config = RuntimeAdapterConfig(
        adapter_id="missing-root-adapter",
        cell_id="cell-main",
        external_system="generic-runtime",
        external_scope="runtime-session",
        source_root=str(missing),
        inputs=[InputDefinition(kind="file", path="closeout.md", source_kind="closeout")],
    )

    try:
        FileSourceAdapter(config)
    except FileAdapterError as exc:
        assert "source_root does not exist" in str(exc)
        assert exc.details["adapter_id"] == "missing-root-adapter"
    else:
        raise AssertionError("missing source_root should raise FileAdapterError")


def test_file_adapter_public_helpers_match_jsonl_discovery(tmp_path: Path) -> None:
    runtime_root = _runtime_copy(tmp_path)
    config = _config(runtime_root)
    adapter = FileSourceAdapter(config)
    inp = config.inputs[2]

    resolved = adapter.resolve_source_path(inp.path)
    ids = adapter.external_ids_for_input(inp, '{"external_run_id":"run-x","task_id":"task-x"}')

    assert resolved == runtime_root / "outcomes.jsonl"
    assert ids == {"external_run_id": "run-x", "external_task_id": "task-x"}
