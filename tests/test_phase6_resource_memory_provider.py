from __future__ import annotations

from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.provider.memory import remember, search
from shyftr.store.sqlite import open_sqlite, rebuild_from_cell


def _records(path: Path):
    return [record for _, record in read_jsonl(path)]


def test_remember_resource_memory_persists_typed_resource_ref_and_grounding_refs(tmp_path: Path):
    cell = init_cell(tmp_path, "memory-cell", cell_type="memory")

    result = remember(
        cell,
        "Release handoff artifact is grounded in the final markdown packet.",
        "tool_quirk",
        metadata={
            "resource_ref": {
                "ref_type": "file",
                "locator": "artifact://phase6/final-handoff",
                "label": "Final handoff markdown",
                "span": {"start_line": 3, "end_line": 12},
                "content_digest": "sha256:def456",
                "origin": "pytest",
                "mime_type": "text/markdown",
                "size_bytes": 256,
            },
            "grounding_refs": ["trace-supporting-2"],
            "sensitivity": "internal",
            "retention_hint": "durable_reference",
        },
        memory_type="resource",
    )

    traces = _records(cell / "traces" / "approved.jsonl")
    assert traces[0]["trace_id"] == result.memory_id
    assert traces[0]["memory_type"] == "resource"
    assert traces[0]["resource_ref"]["locator"] == "artifact://phase6/final-handoff"
    assert traces[0]["resource_ref"]["label"] == "Final handoff markdown"
    assert traces[0]["grounding_refs"] == ["trace-supporting-2"]
    assert traces[0]["sensitivity"] == "internal"
    assert traces[0]["retention_hint"] == "durable_reference"

    results = search(cell, "handoff artifact", memory_types=["resource"])
    assert [row.memory_id for row in results] == [result.memory_id]
    assert results[0].provenance["resource_ref"]["label"] == "Final handoff markdown"
    assert results[0].provenance["grounding_refs"] == ["trace-supporting-2"]


def test_sqlite_rebuild_preserves_resource_ref_fields_for_resource_traces(tmp_path: Path):
    cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    remember(
        cell,
        "Debugging evidence is grounded in the canonical log excerpt.",
        "tool_quirk",
        metadata={
            "resource_ref": {
                "ref_type": "log_span",
                "locator": "artifact://phase6/app-log-excerpt",
                "label": "Application log excerpt",
                "span": {"start_line": 40, "end_line": 88},
            },
            "grounding_refs": ["trace-runbook-1"],
        },
        memory_type="resource",
    )

    db = tmp_path / "resource.db"
    conn = open_sqlite(db)
    try:
        rebuild_from_cell(conn, cell)
        row = conn.execute(
            "SELECT resource_ref, grounding_refs, sensitivity, retention_hint FROM traces"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert '"locator": "artifact://phase6/app-log-excerpt"' in row[0]
    assert row[1] == '["trace-runbook-1"]'
    assert row[2] is None
    assert row[3] is None


def test_resource_memory_search_can_match_safe_label_without_matching_raw_locator(tmp_path: Path):
    cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    result = remember(
        cell,
        "Canonical proof artifact for the release checklist.",
        "tool_quirk",
        metadata={
            "resource_ref": {
                "ref_type": "file",
                "locator": "artifact://private/final-proof",
                "label": "Release proof checklist",
            }
        },
        memory_type="resource",
    )

    by_label = search(cell, "release proof checklist", memory_types=["resource"])
    by_locator = search(cell, "top-secret", memory_types=["resource"])

    assert [row.memory_id for row in by_label] == [result.memory_id]
    assert by_locator == []
