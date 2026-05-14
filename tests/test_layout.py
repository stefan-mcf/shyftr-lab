from pathlib import Path

import pytest

from shyftr.layout import init_cell


EXPECTED_DIRECTORIES = {
    "ledger",
    "traces",
    "alloys",
    "doctrine",
    "indexes",
    "summaries",
    "reports",
    "config",
}

EXPECTED_FILES = {
    "ledger/sources.jsonl",
    "ledger/fragments.jsonl",
    "ledger/reviews.jsonl",
    "ledger/promotions.jsonl",
    "ledger/retrieval_logs.jsonl",
    "ledger/outcomes.jsonl",
    # AL-1 active-learning ledgers
    "ledger/confidence_events.jsonl",
    "ledger/retrieval_affinity_events.jsonl",
    "ledger/audit_sparks.jsonl",
    "ledger/audit_reviews.jsonl",
    "traces/approved.jsonl",
    "traces/deprecated.jsonl",
    "alloys/proposed.jsonl",
    "alloys/approved.jsonl",
    "doctrine/proposed.jsonl",
    "doctrine/approved.jsonl",
}


def test_init_cell_creates_expected_directories_and_empty_ledgers(tmp_path):
    cell_path = init_cell(tmp_path, "cell-alpha")

    assert cell_path == tmp_path / "cell-alpha"
    assert cell_path.is_dir()
    for relative_path in EXPECTED_DIRECTORIES:
        assert (cell_path / relative_path).is_dir()
    for relative_path in EXPECTED_FILES:
        seeded_file = cell_path / relative_path
        assert seeded_file.is_file()
        assert seeded_file.read_text(encoding="utf-8") == ""


def test_init_cell_is_idempotent_and_preserves_existing_records(tmp_path):
    cell_path = init_cell(tmp_path, "cell-alpha")
    source_ledger = cell_path / "ledger" / "sources.jsonl"
    source_ledger.write_text('{"source_id":"src-001"}\n', encoding="utf-8")

    second_path = init_cell(tmp_path, "cell-alpha")

    assert second_path == cell_path
    assert source_ledger.read_text(encoding="utf-8") == '{"source_id":"src-001"}\n'


def test_init_cell_writes_deterministic_manifest(tmp_path):
    cell_path = init_cell(tmp_path, "cell-alpha", cell_type="project")

    manifest = (cell_path / "config" / "cell_manifest.json").read_text(encoding="utf-8")

    assert manifest == '{"cell_id":"cell-alpha","cell_type":"project"}\n'


def test_init_cell_rejects_path_like_cell_ids(tmp_path):
    for unsafe_cell_id in ("../outside", "nested/cell", ".", ""):
        with pytest.raises(ValueError, match="cell_id"):
            init_cell(tmp_path, unsafe_cell_id)

    assert not (tmp_path.parent / "outside").exists()
