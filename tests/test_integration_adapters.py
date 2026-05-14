"""integration adapters track generic evidence, closeout adapter, and retrieval usage contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_sources_from_adapter
from shyftr.integrations.closeout_adapter import CloseoutArtifactAdapter
from shyftr.integrations.evidence_adapters import GenericEvidenceAdapter
from shyftr.integrations.plugins import adapter_plugins_payload
from shyftr.integrations.retrieval_logs import list_retrieval_logs
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.models import Source


def test_generic_evidence_adapter_ingests_idempotently_and_extracts(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "integration-cell", cell_type="user")
    adapter = GenericEvidenceAdapter.from_markdown_note(
        tmp_path / "snapshots",
        "# Durable preference\n\nPrefer deterministic adapter evidence with stable provenance.\n",
        title="durable-preference",
        adapter_id="integration-generic",
        external_system="test-runtime",
        external_scope="adapter-contract",
    )

    first = ingest_sources_from_adapter(cell, adapter)
    second = ingest_sources_from_adapter(cell, adapter)

    assert first["sources_ingested"] == 1
    assert first["sources_skipped"] == 0
    assert first["errors"] == []
    assert second["sources_ingested"] == 0
    assert second["sources_skipped"] == 1

    source_rows = [row for _, row in read_jsonl(cell / "ledger" / "sources.jsonl")]
    assert len(source_rows) == 1
    assert source_rows[0]["metadata"]["adapter_id"] == "integration-generic"
    assert source_rows[0]["metadata"]["external_system"] == "test-runtime"
    assert source_rows[0]["metadata"]["external_refs"][0]["source_kind"] == "markdown_note"

    fragments = extract_fragments(cell, Source.from_dict(source_rows[0]))
    assert fragments
    assert fragments[0].source_id == source_rows[0]["source_id"]


def test_generic_evidence_adapter_boundary_failure_does_not_append(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "integration-boundary", cell_type="user")
    adapter = GenericEvidenceAdapter.from_raw_text(
        tmp_path / "snapshots",
        "queue status should stay out of durable memory",
        title="unsafe-status",
    )

    result = ingest_sources_from_adapter(cell, adapter)

    assert result["sources_ingested"] == 0
    assert result["sources_skipped"] == 0
    assert result["errors"]
    assert "boundary policy" in result["errors"][0]
    assert list(read_jsonl(cell / "ledger" / "sources.jsonl")) == []


def test_closeout_artifact_adapter_preserves_artifact_and_ingests(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "integration-artifact", cell_type="user")
    closeouts = tmp_path / "closeouts"
    closeouts.mkdir()
    artifact = closeouts / "summary.md"
    original = "# Durable handoff\n\nReusable adapter guidance belongs in versioned source files.\n"
    artifact.write_text(original, encoding="utf-8")

    adapter = CloseoutArtifactAdapter(closeouts, external_system="external-runtime", external_scope="integration")
    result = ingest_sources_from_adapter(cell, adapter)

    assert result["sources_ingested"] == 1
    assert result["errors"] == []
    assert artifact.read_text(encoding="utf-8") == original
    source_rows = [row for _, row in read_jsonl(cell / "ledger" / "sources.jsonl")]
    assert source_rows[0]["kind"] == "task_closeout"
    assert source_rows[0]["metadata"]["external_system"] == "external-runtime"


def test_retrieval_usage_logs_are_filtered_and_sanitized(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "integration-logs", cell_type="user")
    append_jsonl(
        cell / "ledger" / "retrieval_logs.jsonl",
        {
            "retrieval_id": "ret-1",
            "loadout_id": "lo-1",
            "query": "adapter evidence",
            "selected_ids": ["mem-1"],
            "candidate_ids": ["mem-1", "mem-2"],
            "score_traces": {"mem-1": {"score": 0.9}, "mem-2": {"score": 0.1}},
            "raw_operational_payload": {"branch": "should-not-leak"},
        },
    )
    append_jsonl(
        cell / "ledger" / "retrieval_logs.jsonl",
        {
            "retrieval_id": "ret-2",
            "loadout_id": "lo-2",
            "query": "other",
            "selected_ids": ["mem-3"],
            "score_traces": {"mem-3": {"score": 0.8}},
        },
    )

    payload = list_retrieval_logs(cell, selected_memory_id="mem-1", limit=10)

    assert payload["status"] == "ok"
    assert payload["usage_evidence_only"] is True
    assert payload["total_matched"] == 1
    assert payload["logs"][0]["loadout_id"] == "lo-1"
    assert "raw_operational_payload" not in payload["logs"][0]
    assert set(payload["logs"][0]["score_traces"]) == {"mem-1"}

    append_jsonl(
        cell / "ledger" / "retrieval_logs.jsonl",
        {
            "retrieval_id": "ret-empty",
            "loadout_id": "lo-empty",
            "query": "empty retrieval",
            "selected_ids": [],
            "score_traces": {"candidate-only": {"score": 0.5}},
        },
    )
    empty_payload = list_retrieval_logs(cell, loadout_id="lo-empty", limit=10)
    assert empty_payload["logs"][0]["score_traces"] == {}


def test_integration_built_in_adapters_are_listed() -> None:
    payload = adapter_plugins_payload(entry_point_provider=lambda: [])
    names = {plugin["name"] for plugin in payload["plugins"]}
    assert {"file", "generic-evidence", "closeout-artifact"}.issubset(names)
    assert payload["builtin_count"] >= 3
