from pathlib import Path

from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_source
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.models import Fragment, Source

FIXTURES = Path(__file__).parent / "fixtures" / "sources"


def test_extract_explicit_memory_fragment_fields(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source = ingest_source(cell_path, FIXTURES / "explicit_fragments.md", kind="note", metadata={})

    fragments = extract_fragments(cell_path, source)

    assert len(fragments) == 1
    fragment = fragments[0]
    assert isinstance(fragment, Fragment)
    assert fragment.source_id == source.source_id
    assert fragment.cell_id == "core"
    assert fragment.kind == "lesson"
    assert fragment.text == "Use deterministic test embeddings so retrieval tests never need network access."
    assert fragment.source_excerpt == "deterministic test embeddings"
    assert fragment.confidence == 0.82
    assert fragment.tags == ["tests", "retrieval", "deterministic"]
    assert fragment.boundary_status == "pending"
    assert fragment.review_status == "pending"

    records = [record for _, record in read_jsonl(cell_path / "ledger" / "fragments.jsonl")]
    assert records == [fragment.to_dict()]


def test_extracts_bounded_prose_sections_as_untrusted_fragments(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source = ingest_source(cell_path, FIXTURES / "prose_lessons.md", kind="note", metadata={})

    fragments = extract_fragments(cell_path, source)

    assert [fragment.kind for fragment in fragments] == ["note", "note"]
    assert [fragment.review_status for fragment in fragments] == ["pending", "pending"]
    assert [fragment.boundary_status for fragment in fragments] == ["pending", "pending"]
    assert any("gated lesson stalls" in fragment.text for fragment in fragments)
    assert all(fragment.source_excerpt for fragment in fragments)
    assert all(len(fragment.text) < 400 for fragment in fragments)


def test_extract_fragments_deduplicates_by_source_and_text(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source = ingest_source(cell_path, FIXTURES / "explicit_fragments.md", kind="note", metadata={})

    first = extract_fragments(cell_path, source)
    second = extract_fragments(cell_path, source)

    assert second == first
    records = [record for _, record in read_jsonl(cell_path / "ledger" / "fragments.jsonl")]
    assert len(records) == 1


def test_extract_does_not_promote_source_directly_to_trace(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source = ingest_source(cell_path, FIXTURES / "prose_lessons.md", kind="note", metadata={})

    extract_fragments(cell_path, source)

    assert list(read_jsonl(cell_path / "traces" / "approved.jsonl")) == []
    assert list(read_jsonl(cell_path / "ledger" / "promotions.jsonl")) == []


def test_polluted_fragments_are_marked_boundary_failed_and_not_appended(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source_path = FIXTURES / "polluted_status.md"
    source = Source(
        source_id="src-manual-polluted",
        cell_id="core",
        kind="note",
        uri=str(source_path),
        sha256="0" * 64,
        captured_at="2026-04-24T00:00:00+00:00",
        metadata={},
    )
    append_jsonl(cell_path / "ledger" / "sources.jsonl", source.to_dict())

    fragments = extract_fragments(cell_path, source)

    assert any(fragment.boundary_status == "boundary_failed" for fragment in fragments)
    records = [record for _, record in read_jsonl(cell_path / "ledger" / "fragments.jsonl")]
    assert all(record["boundary_status"] != "boundary_failed" for record in records)
    assert all("Queue item" not in record["text"] for record in records)
