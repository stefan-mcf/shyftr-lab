import pytest

from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_source
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.models import Trace
from shyftr.promote import PromotionError, promote_fragment
from shyftr.review import approve_fragment, reject_fragment


def _fragment(cell_path, source_path, text="Durable lesson: use focused tests before full-suite verification."):
    source_path.write_text(text, encoding="utf-8")
    source = ingest_source(cell_path, source_path, kind="lesson", metadata={})
    return source, extract_fragments(cell_path, source)[0]


def test_unapproved_fragment_cannot_be_promoted(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    _, fragment = _fragment(cell_path, tmp_path / "source.md")

    with pytest.raises(PromotionError, match="approved"):
        promote_fragment(cell_path, fragment.fragment_id, promoter="reviewer-1")

    assert list(read_jsonl(cell_path / "traces" / "approved.jsonl")) == []
    assert list(read_jsonl(cell_path / "ledger" / "promotions.jsonl")) == []


def test_latest_review_must_be_approved_to_promote(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    _, fragment = _fragment(cell_path, tmp_path / "source.md")
    approve_fragment(cell_path, fragment.fragment_id, reviewer="reviewer-1", rationale="useful")
    reject_fragment(cell_path, fragment.fragment_id, reviewer="reviewer-1", rationale="superseded")

    with pytest.raises(PromotionError, match="approved"):
        promote_fragment(cell_path, fragment.fragment_id, promoter="reviewer-1")


def test_promote_approved_fragment_appends_trace_and_promotion_event(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    source, fragment = _fragment(cell_path, tmp_path / "source.md")
    approve_fragment(cell_path, fragment.fragment_id, reviewer="reviewer-1", rationale="durable and bounded")

    trace = promote_fragment(cell_path, fragment.fragment_id, promoter="reviewer-1")

    assert isinstance(trace, Trace)
    assert trace.cell_id == "core"
    assert trace.statement == fragment.text
    assert trace.source_fragment_ids == [fragment.fragment_id]
    assert trace.status == "approved"
    assert trace.tags == fragment.tags

    trace_records = [record for _, record in read_jsonl(cell_path / "traces" / "approved.jsonl")]
    assert trace_records == [trace.to_dict()]
    promotion_records = [record for _, record in read_jsonl(cell_path / "ledger" / "promotions.jsonl")]
    assert promotion_records[0]["candidate_id"] == fragment.fragment_id
    assert promotion_records[0]["trace_id"] == trace.trace_id
    assert promotion_records[0]["source_id"] == source.source_id
    assert promotion_records[0]["source_fragment_ids"] == [fragment.fragment_id]


def test_promote_is_idempotent_for_same_fragment(tmp_path):
    cell_path = init_cell(tmp_path, "core")
    _, fragment = _fragment(cell_path, tmp_path / "source.md")
    approve_fragment(cell_path, fragment.fragment_id, reviewer="reviewer-1", rationale="durable")

    first = promote_fragment(cell_path, fragment.fragment_id, promoter="reviewer-1")
    second = promote_fragment(cell_path, fragment.fragment_id, promoter="reviewer-1")

    assert second == first
    assert len([record for _, record in read_jsonl(cell_path / "traces" / "approved.jsonl")]) == 1
    assert len([record for _, record in read_jsonl(cell_path / "ledger" / "promotions.jsonl")]) == 1
