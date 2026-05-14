from __future__ import annotations

from pathlib import Path

from shyftr.decay import (
    append_deprecation_proposals,
    cell_decay_report,
    decay_summary,
    propose_deprecations,
    score_memory_decay,
)
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.models import Fragment, Trace


def _cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "core")


def _fragment(fragment_id: str) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        source_id="s1",
        cell_id="core",
        kind="note",
        text="fragment",
        review_status="approved",
    )


def _trace(
    trace_id: str,
    statement: str,
    source_fragment_ids: list[str],
    *,
    use_count: int = 1,
    success_count: int = 1,
    failure_count: int = 0,
    confidence: float | None = 0.8,
) -> Trace:
    return Trace(
        trace_id=trace_id,
        cell_id="core",
        statement=statement,
        source_fragment_ids=source_fragment_ids,
        status="approved",
        confidence=confidence,
        use_count=use_count,
        success_count=success_count,
        failure_count=failure_count,
    )


def test_propose_deprecations_reports_stale_harmful_underperforming_and_unsupported(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1").to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("healthy", "healthy", ["f1"]).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("stale", "stale", ["f1"], use_count=0, success_count=0).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("bad", "bad", ["f1"], use_count=5, success_count=1, failure_count=4).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("unsupported", "unsupported", ["missing"], use_count=1).to_dict())

    proposals = propose_deprecations(cell, proposed_at="2026-04-24T00:00:00+00:00")
    by_id = {proposal["trace_id"]: proposal for proposal in proposals}

    assert "healthy" not in by_id
    assert by_id["stale"]["reasons"] == ["stale"]
    assert by_id["bad"]["reasons"] == ["harmful", "underperforming"]
    assert by_id["bad"]["details"]["success_rate"] == 0.2
    assert by_id["unsupported"]["reasons"] == ["unsupported"]
    assert by_id["unsupported"]["details"]["missing_fragment_ids"] == ["missing"]
    assert all(proposal["proposal_status"] == "proposed" for proposal in proposals)


def test_superseded_duplicate_trace_keeps_best_ranked_trace(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1").to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("better", "same rule", ["f1"], confidence=0.9, success_count=3).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("weaker", "same rule", ["f1"], confidence=0.4, success_count=1).to_dict())

    proposals = propose_deprecations(cell, proposed_at="2026-04-24T00:00:00+00:00")
    by_id = {proposal["trace_id"]: proposal for proposal in proposals}

    assert "better" not in by_id
    assert "superseded" in by_id["weaker"]["reasons"]


def test_proposals_are_deterministic_when_timestamp_is_supplied(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t1", "unused", ["missing"], use_count=0, success_count=0).to_dict())

    first = propose_deprecations(cell, proposed_at="fixed")
    second = propose_deprecations(cell, proposed_at="fixed")

    assert first == second


def test_append_deprecation_proposals_is_append_only_and_does_not_mutate_traces(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t1", "unused", ["missing"], use_count=0, success_count=0).to_dict())
    before = (cell / "traces" / "approved.jsonl").read_text()
    proposals = propose_deprecations(cell, proposed_at="fixed")

    assert append_deprecation_proposals(cell, proposals) == 1
    assert append_deprecation_proposals(cell, proposals) == 1

    proposal_lines = (cell / "ledger" / "deprecation_proposals.jsonl").read_text().strip().splitlines()
    assert len(proposal_lines) == 2
    assert (cell / "traces" / "approved.jsonl").read_text() == before


def test_decay_summary_counts_reasons(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1").to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("stale", "stale", ["f1"], use_count=0, success_count=0).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("unsupported", "unsupported", ["missing"], use_count=1).to_dict())

    summary = decay_summary(cell)

    assert summary["total_approved"] == 2
    assert summary["total_deprecation_proposals"] == 2
    assert summary["stale_count"] == 1
    assert summary["unsupported_count"] == 1


def test_score_memory_decay_combines_age_failure_confidence_and_supersession() -> None:
    score = score_memory_decay(
        {
            "trace_id": "old-bad",
            "created_at": "2025-05-06T00:00:00+00:00",
            "success_count": 1,
            "failure_count": 3,
            "confidence": 0.2,
        },
        reference_time="2026-05-06T00:00:00+00:00",
        half_life_days=90,
        superseded_ids={"old-bad"},
    )

    assert score.memory_id == "old-bad"
    assert score.age_decay > 0.9
    assert score.failure_decay == 0.75
    assert score.confidence_decay == 0.8
    assert score.supersession_decay == 1.0
    assert score.combined > 0.8
    assert set(score.reasons) == {"stale", "failed_reuse", "low_confidence", "superseded"}


def test_cell_decay_report_is_read_only_and_explainable(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(
        cell / "traces" / "approved.jsonl",
        {
            **_trace("old", "same", ["f1"], use_count=4, success_count=1, failure_count=3, confidence=0.2).to_dict(),
            "created_at": "2025-05-06T00:00:00+00:00",
        },
    )
    append_jsonl(
        cell / "traces" / "approved.jsonl",
        {
            **_trace("new", "same", ["f1"], use_count=2, success_count=2, failure_count=0, confidence=0.9).to_dict(),
            "created_at": "2026-05-01T00:00:00+00:00",
        },
    )
    before = (cell / "traces" / "approved.jsonl").read_text()

    report = cell_decay_report(cell, reference_time="2026-05-06T00:00:00+00:00")

    assert report["memory_count"] == 2
    assert report["high_decay_count"] >= 1
    assert "scores" in report
    assert (cell / "traces" / "approved.jsonl").read_text() == before
