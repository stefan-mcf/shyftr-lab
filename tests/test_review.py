from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_source
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.review import approve_fragment, reject_fragment, split_fragment, merge_fragments, latest_review


def _fragment(cell_path, source_path):
    source_path.write_text("Durable lesson: keep reviewed memory separate from raw evidence.", encoding="utf-8")
    source = ingest_source(cell_path, source_path, kind="lesson", metadata={})
    return extract_fragments(cell_path, source)[0]


def test_approve_and_reject_fragment_append_review_events_without_mutating_fragment(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    fragment = _fragment(cell_path, tmp_path / "source.md")
    original_fragment_rows = list(read_jsonl(cell_path / "ledger" / "fragments.jsonl"))

    approval = approve_fragment(cell_path, fragment.fragment_id, reviewer="reviewer-1", rationale="durable")
    rejection = reject_fragment(cell_path, fragment.fragment_id, reviewer="reviewer-1", rationale="superseded")

    reviews = [record for _, record in read_jsonl(cell_path / "ledger" / "reviews.jsonl")]
    assert reviews == [approval, rejection]
    assert approval["review_status"] == "approved"
    assert rejection["review_status"] == "rejected"
    assert rejection["candidate_id"] == fragment.fragment_id
    assert list(read_jsonl(cell_path / "ledger" / "fragments.jsonl")) == original_fragment_rows
    assert latest_review(cell_path, fragment.fragment_id)["review_status"] == "rejected"


def test_split_and_merge_reviews_are_events_not_fragment_mutations(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    first = _fragment(cell_path, tmp_path / "first.md")
    second_source = tmp_path / "second.md"
    second_source.write_text("Durable lesson: preserve provenance across review gates.", encoding="utf-8")
    second = extract_fragments(cell_path, ingest_source(cell_path, second_source, kind="lesson", metadata={}))[0]
    original_fragment_rows = list(read_jsonl(cell_path / "ledger" / "fragments.jsonl"))

    split_event = split_fragment(
        cell_path,
        first.fragment_id,
        reviewer="reviewer-1",
        proposed_texts=["keep reviewed memory separate", "keep raw evidence immutable"],
        rationale="two ideas",
    )
    merge_event = merge_fragments(
        cell_path,
        [first.fragment_id, second.fragment_id],
        reviewer="reviewer-1",
        proposed_text="Keep reviewed memory separate while preserving provenance.",
        rationale="same theme",
    )

    reviews = [record for _, record in read_jsonl(cell_path / "ledger" / "reviews.jsonl")]
    assert reviews == [split_event, merge_event]
    assert split_event["review_action"] == "split"
    assert split_event["metadata"]["proposed_texts"] == ["keep reviewed memory separate", "keep raw evidence immutable"]
    assert merge_event["review_action"] == "merge"
    assert merge_event["metadata"]["source_fragment_ids"] == [first.fragment_id, second.fragment_id]
    assert list(read_jsonl(cell_path / "ledger" / "fragments.jsonl")) == original_fragment_rows
