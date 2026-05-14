import json

import pytest

from shyftr.ingest import ingest_source
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.models import Source
from shyftr.policy import BoundaryPolicyError


def test_ingest_source_appends_source_with_hash_and_provenance(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source_path = tmp_path / "lesson.md"
    source_path.write_text(
        "When browser automation stalls on gated lessons, click Play until Continue unlocks.",
        encoding="utf-8",
    )

    source = ingest_source(
        cell_path,
        source_path,
        kind="lesson",
        metadata={"captured_by": "test"},
    )

    assert isinstance(source, Source)
    assert source.cell_id == "core"
    assert source.kind == "lesson"
    assert source.uri == str(source_path)
    assert len(source.sha256) == 64
    assert source.metadata == {"captured_by": "test"}

    records = [record for _, record in read_jsonl(cell_path / "ledger" / "sources.jsonl")]
    assert records == [source.to_dict()]


def test_ingest_source_deduplicates_identical_hash_within_cell(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_text("Durable lesson: retry transient network failures with backoff.", encoding="utf-8")
    second_path.write_text("Durable lesson: retry transient network failures with backoff.", encoding="utf-8")

    first = ingest_source(cell_path, first_path, kind="lesson", metadata={"source": "first"})
    second = ingest_source(cell_path, second_path, kind="lesson", metadata={"source": "second"})

    assert second == first
    records = [record for _, record in read_jsonl(cell_path / "ledger" / "sources.jsonl")]
    assert len(records) == 1
    assert records[0]["uri"] == str(first_path)


def test_ingest_source_rejects_pollution_before_appending(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source_path = tmp_path / "status.md"
    source_path.write_text("Queue item dmq-123 is in_progress and branch task/foo is green.", encoding="utf-8")

    with pytest.raises(BoundaryPolicyError):
        ingest_source(cell_path, source_path, kind="task_status", metadata={})

    records = [record for _, record in read_jsonl(cell_path / "ledger" / "sources.jsonl")]
    assert records == []


def test_ingest_source_requires_existing_seeded_cell(tmp_path):
    source_path = tmp_path / "lesson.md"
    source_path.write_text("Durable lesson: keep file-backed provenance.", encoding="utf-8")

    with pytest.raises(ValueError, match="sources ledger"):
        ingest_source(tmp_path / "missing-cell", source_path, kind="lesson", metadata={})
