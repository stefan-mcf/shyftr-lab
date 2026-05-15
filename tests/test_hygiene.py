from __future__ import annotations

from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.models import Fragment, Source, Trace
from shyftr.reports.hygiene import (
    conflicting_traces,
    duplicate_traces,
    fragment_status_counts,
    hygiene_report,
    missing_source_references,
    trace_confidence_distribution,
)
from shyftr.audit import append_audit_review, append_audit_spark


def _source(source_id: str = "s1") -> Source:
    return Source(
        source_id=source_id,
        cell_id="core",
        kind="note",
        sha256="0" * 64,
        captured_at="2026-04-24T00:00:00+00:00",
    )


def _fragment(fragment_id: str, source_id: str, *, boundary: str = "accepted", review: str = "approved") -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        source_id=source_id,
        cell_id="core",
        kind="note",
        text=f"fragment {fragment_id}",
        boundary_status=boundary,
        review_status=review,
    )


def _trace(
    trace_id: str,
    statement: str,
    source_fragment_ids: list[str],
    *,
    confidence: float | None = None,
    status: str = "approved",
    tags: list[str] | None = None,
) -> Trace:
    return Trace(
        trace_id=trace_id,
        cell_id="core",
        statement=statement,
        source_fragment_ids=source_fragment_ids,
        status=status,
        confidence=confidence,
        tags=tags or [],
    )


def _cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "core")


def test_fragment_status_counts_reports_boundary_and_review_defaults(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1", "s1").to_dict())
    append_jsonl(
        cell / "ledger" / "fragments.jsonl",
        _fragment("f2", "s1", boundary="rejected", review="rejected").to_dict(),
    )
    append_jsonl(cell / "ledger" / "fragments.jsonl", {"fragment_id": "f3", "source_id": "s1", "cell_id": "core", "text": "x"})

    assert fragment_status_counts(cell) == {
        "boundary_status": {"accepted": 1, "pending": 1, "rejected": 1},
        "review_status": {"approved": 1, "pending": 1, "rejected": 1},
    }


def test_trace_confidence_distribution_reads_trace_ledgers_without_mutating(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t1", "a", ["f1"], confidence=0.2).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t2", "b", ["f2"], confidence=0.8).to_dict())
    append_jsonl(cell / "traces" / "deprecated.jsonl", _trace("t3", "c", ["f3"], status="deprecated").to_dict())

    report = trace_confidence_distribution(cell)

    assert report["total"] == 3
    assert report["status_counts"] == {"approved": 2, "deprecated": 1}
    assert report["confidence_bands"]["approved"] == {"none": 0, "low": 1, "medium": 0, "high": 1}
    assert report["confidence_bands"]["deprecated"] == {"none": 1, "low": 0, "medium": 0, "high": 0}
    assert (cell / "traces" / "approved.jsonl").read_text().count("\n") == 2


def test_missing_source_references_reports_fragment_and_trace_gaps(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "sources.jsonl", _source("s1").to_dict())
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1", "s1").to_dict())
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f2", "missing-source").to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t1", "ok", ["f1", "missing-fragment"]).to_dict())

    report = missing_source_references(cell)

    assert report["fragments_with_missing_sources"] == [
        {"fragment_id": "f2", "source_id": "missing-source", "cell_id": "core"}
    ]
    assert report["traces_with_missing_fragments"] == [
        {
            "trace_id": "t1",
            "status": "approved",
            "ledger_status": "approved",
            "unresolved_fragment_ids": ["missing-fragment"],
        }
    ]


def test_duplicate_and_conflicting_traces_are_reported_deterministically(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t1", "Always review memory fragments", ["f1"], tags=["review"]).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t2", "always review memory fragments", ["f2"], tags=["review"]).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t3", "Never review memory fragments", ["f3"], tags=["review"]).to_dict())

    duplicates = duplicate_traces(cell)
    conflicts = conflicting_traces(cell)

    assert len(duplicates) == 1
    assert [item["trace_id"] for item in duplicates[0]["trace_ids"]] == ["t1", "t2"]
    assert [conflict["trace_ids"] for conflict in conflicts] == [["t1", "t3"], ["t2", "t3"]]


def test_combined_hygiene_report_is_read_only(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "sources.jsonl", _source("s1").to_dict())
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1", "s1").to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t1", "review memory", ["f1"], confidence=0.9).to_dict())
    before = (cell / "traces" / "approved.jsonl").read_text()

    report = hygiene_report(cell)

    assert set(report) == {
        "fragment_status_counts",
        "trace_confidence_distribution",
        "missing_source_references",
        "duplicate_traces",
        "conflicting_traces",
        "audit_findings",
        "miss_summary",
        "misses_by_category",
        "most_missed_charges",
        "most_over_retrieved_charges",
        "high_confidence_missed_charges",
        "charges_with_mixed_signal",
    }
    assert (cell / "traces" / "approved.jsonl").read_text() == before

def test_hygiene_report_surfaces_pack_miss_learning_summaries(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "sources.jsonl", _source("s1").to_dict())
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1", "s1").to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t-high", "High confidence guidance", ["f1"], confidence=0.9).to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t-low", "Low confidence guidance", ["f1"], confidence=0.2).to_dict())
    append_jsonl(
        cell / "ledger" / "outcomes.jsonl",
        {
            "outcome_id": "oc-1",
            "pack_miss_details": [
                {"charge_id": "t-high", "miss_type": "not_relevant"},
                {"charge_id": "t-low", "miss_type": "unknown"},
            ],
            "over_retrieved_charge_ids": ["t-high"],
            "metadata": {"useful_trace_ids": ["t-high"], "harmful_trace_ids": ["t-high"]},
        },
    )

    report = hygiene_report(cell)

    assert report["miss_summary"]["total_misses"] == 2
    assert report["misses_by_category"]["not_relevant"] == 1
    assert report["most_missed_charges"][0] == {"charge_id": "t-high", "miss_count": 1}
    assert report["most_over_retrieved_charges"] == [
        {"charge_id": "t-high", "over_retrieved_count": 1}
    ]
    assert report["high_confidence_missed_charges"] == [
        {
            "charge_id": "t-high",
            "miss_count": 1,
            "confidence": 0.9,
            "ledger_status": "approved",
            "status": "approved",
        }
    ]


def test_hygiene_report_surfaces_audit_visibility_summary(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "ledger" / "sources.jsonl", _source("s1").to_dict())
    append_jsonl(cell / "ledger" / "fragments.jsonl", _fragment("f1", "s1").to_dict())
    append_jsonl(cell / "traces" / "approved.jsonl", _trace("t1", "Review memory", ["f1"], confidence=0.9).to_dict())

    append_audit_spark(
        cell,
        trace_id="t1",
        classification="policy_conflict",
        challenger="challenger-bot",
        rationale="policy issue",
        counter_evidence_source="ledger/sparks.jsonl:sp-1",
        cell_id="core",
        spark_id="spark-1",
        proposed_at="2026-05-15T00:00:00+00:00",
    )
    append_audit_review(
        cell,
        audit_id="spark-1",
        resolution="accept",
        reviewer="reviewer-bot",
        rationale="confirmed",
        review_actions=["no_action"],
        review_id="review-1",
        reviewed_at="2026-05-15T00:00:01+00:00",
    )

    report = hygiene_report(cell)
    assert report["audit_findings"]["counts"]["policy_conflict"] == 1
    assert report["audit_findings"]["review_state_counts"]["reviewed"] == 1
    assert report["audit_findings"]["findings"][0]["latest_resolution"] == "accept"
