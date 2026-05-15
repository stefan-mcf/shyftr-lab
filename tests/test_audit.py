from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.audit import (
    audit_summary,
    append_audit_review,
    append_audit_row,
    append_audit_spark,
    build_audit_review,
    build_audit_row,
    build_audit_spark,
    read_audit_reviews,
    read_audit_reviews_for_audit,
    read_audit_rows,
    read_audit_rows_by_action,
    read_audit_rows_for_target,
    read_audit_sparks,
)
from shyftr.layout import init_cell


def _cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "core")


def test_build_audit_row_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="action is required"):
        build_audit_row(
            action="",
            target_type="trace",
            target_id="t1",
            actor="reviewer",
            rationale="because",
        )


def test_build_audit_spark_requires_cell_id() -> None:
    with pytest.raises(ValueError, match="cell_id is required"):
        build_audit_spark(
            trace_id="t1",
            classification="direct_contradiction",
            challenger="challenger-bot",
            rationale="because",
            counter_evidence_source="ledger/outcomes.jsonl:oc-1",
            cell_id="",
        )


def test_append_audit_spark_round_trips_with_compatibility_fields(tmp_path: Path) -> None:
    cell = _cell(tmp_path)

    spark = append_audit_spark(
        cell,
        trace_id="t1",
        classification="direct_contradiction",
        challenger="challenger-bot",
        rationale="counter-evidence found",
        counter_evidence_source="ledger/outcomes.jsonl:oc-1",
        cell_id="core",
        fragment_id="fragment-1",
        spark_id="spark-fixed",
        proposed_at="2026-04-24T00:00:00+00:00",
    )

    assert spark["action"] == "challenge"
    assert spark["observed_at"] == "2026-04-24T00:00:00+00:00"
    assert spark["proposed_at"] == "2026-04-24T00:00:00+00:00"
    assert read_audit_sparks(cell) == [spark]


def test_append_audit_row_round_trips_with_deterministic_fields(tmp_path: Path) -> None:
    cell = _cell(tmp_path)

    row = append_audit_row(
        cell,
        action="propose_deprecation",
        target_type="trace",
        target_id="t1",
        actor="tester",
        rationale="trace is unsupported",
        metadata={"reasons": ["unsupported"]},
        audit_id="audit-fixed",
        recorded_at="2026-04-24T00:00:00+00:00",
    )

    assert row == {
        "audit_id": "audit-fixed",
        "action": "propose_deprecation",
        "target_type": "trace",
        "target_id": "t1",
        "actor": "tester",
        "rationale": "trace is unsupported",
        "metadata": {"reasons": ["unsupported"]},
        "recorded_at": "2026-04-24T00:00:00+00:00",
    }
    assert read_audit_rows(cell) == [row]


def test_audit_rows_are_append_only(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    first = append_audit_row(
        cell,
        action="first",
        target_type="trace",
        target_id="t1",
        actor="tester",
        rationale="one",
        audit_id="audit-1",
        recorded_at="t1",
    )
    second = append_audit_row(
        cell,
        action="second",
        target_type="trace",
        target_id="t2",
        actor="tester",
        rationale="two",
        audit_id="audit-2",
        recorded_at="t2",
    )

    rows = read_audit_rows(cell)
    assert rows == [first, second]
    lines = (cell / "ledger" / "audit.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["audit_id"] for line in lines] == ["audit-1", "audit-2"]


def test_read_audit_rows_filters_by_target_and_action(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_audit_row(cell, action="review", target_type="trace", target_id="t1", actor="a", rationale="r", audit_id="a1", recorded_at="1")
    append_audit_row(cell, action="review", target_type="trace", target_id="t2", actor="a", rationale="r", audit_id="a2", recorded_at="2")
    append_audit_row(cell, action="approve", target_type="trace", target_id="t1", actor="a", rationale="r", audit_id="a3", recorded_at="3")

    assert [row["audit_id"] for row in read_audit_rows_for_target(cell, "t1")] == ["a1", "a3"]
    assert [row["audit_id"] for row in read_audit_rows_by_action(cell, "review")] == ["a1", "a2"]


def test_missing_audit_ledger_reads_as_empty(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    (cell / "ledger" / "audit.jsonl").unlink(missing_ok=True)

    assert read_audit_rows(cell) == []


# ---------------------------------------------------------------------------
# Audit review tests
# ---------------------------------------------------------------------------


def test_build_audit_review_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="audit_id is required"):
        build_audit_review(audit_id="", resolution="accept", reviewer="alice", rationale="ok")
    with pytest.raises(ValueError, match="resolution is required"):
        build_audit_review(audit_id="a1", resolution="", reviewer="alice", rationale="ok")
    with pytest.raises(ValueError, match="reviewer is required"):
        build_audit_review(audit_id="a1", resolution="accept", reviewer="", rationale="ok")
    with pytest.raises(ValueError, match="rationale is required"):
        build_audit_review(audit_id="a1", resolution="accept", reviewer="alice", rationale="")


def test_build_audit_review_validates_resolution() -> None:
    with pytest.raises(ValueError, match="Invalid resolution"):
        build_audit_review(audit_id="a1", resolution="invalid", reviewer="alice", rationale="ok")


def test_build_audit_review_validates_review_actions() -> None:
    with pytest.raises(ValueError, match="Invalid review action"):
        build_audit_review(
            audit_id="a1", resolution="accept", reviewer="alice",
            rationale="ok", review_actions=["bogus_action"],
        )


def test_build_audit_review_with_valid_actions() -> None:
    review = build_audit_review(
        audit_id="a1", resolution="accept", reviewer="alice",
        rationale="Looks good",
        review_actions=["mark_challenged", "no_action"],
    )
    assert review["audit_id"] == "a1"
    assert review["resolution"] == "accept"
    assert review["reviewer"] == "alice"
    assert "review_id" in review
    assert "reviewed_at" in review
    assert review["review_actions"] == ["mark_challenged", "no_action"]


def test_build_audit_review_with_deterministic_fields() -> None:
    review = build_audit_review(
        audit_id="a1", resolution="reject", reviewer="bob",
        rationale="Not supported",
        review_actions=[],
        review_id="review-fixed-1",
        reviewed_at="2026-04-25T00:00:00+00:00",
    )
    assert review == {
        "review_id": "review-fixed-1",
        "audit_id": "a1",
        "resolution": "reject",
        "reviewer": "bob",
        "rationale": "Not supported",
        "review_actions": [],
        "reviewed_at": "2026-04-25T00:00:00+00:00",
    }


def test_append_audit_review_round_trips(tmp_path: Path) -> None:
    cell = _cell(tmp_path)

    review = append_audit_review(
        cell,
        audit_id="spark-1",
        resolution="accept",
        reviewer="reviewer-bot",
        rationale="Evidence supports the finding",
        review_actions=["mark_challenged", "propose_isolation"],
        review_id="rev-1",
        reviewed_at="2026-04-25T00:00:00+00:00",
    )

    assert review == {
        "review_id": "rev-1",
        "audit_id": "spark-1",
        "resolution": "accept",
        "reviewer": "reviewer-bot",
        "rationale": "Evidence supports the finding",
        "review_actions": ["mark_challenged", "propose_isolation"],
        "reviewed_at": "2026-04-25T00:00:00+00:00",
    }
    assert read_audit_reviews(cell) == [review]


def test_read_audit_reviews_append_only(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    first = append_audit_review(
        cell, audit_id="a1", resolution="accept", reviewer="r1",
        rationale="ok", review_id="rev-1", reviewed_at="t1",
    )
    second = append_audit_review(
        cell, audit_id="a2", resolution="reject", reviewer="r2",
        rationale="no", review_id="rev-2", reviewed_at="t2",
    )

    reviews = read_audit_reviews(cell)
    assert reviews == [first, second]
    lines = (cell / "ledger" / "audit_reviews.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["review_id"] for line in lines] == ["rev-1", "rev-2"]


def test_read_audit_reviews_for_audit_filters_by_audit_id(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_audit_review(
        cell, audit_id="a1", resolution="accept", reviewer="r1",
        rationale="ok", review_id="rv-a1-1", reviewed_at="1",
    )
    append_audit_review(
        cell, audit_id="a2", resolution="accept", reviewer="r2",
        rationale="ok", review_id="rv-a2-1", reviewed_at="2",
    )
    append_audit_review(
        cell, audit_id="a1", resolution="reject", reviewer="r3",
        rationale="nope", review_id="rv-a1-2", reviewed_at="3",
    )

    for_a1 = read_audit_reviews_for_audit(cell, "a1")
    assert [r["review_id"] for r in for_a1] == ["rv-a1-1", "rv-a1-2"]

    for_a3 = read_audit_reviews_for_audit(cell, "a3")
    assert for_a3 == []


def test_missing_audit_reviews_ledger_reads_as_empty(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    ledger = cell / "ledger" / "audit_reviews.jsonl"
    ledger.unlink(missing_ok=True)

    assert read_audit_reviews(cell) == []


def test_audit_summary_surfaces_policy_conflict_and_review_state(tmp_path: Path) -> None:
    cell = _cell(tmp_path)

    # Seed two sparks: one policy_conflict and one direct_contradiction.
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
    append_audit_spark(
        cell,
        trace_id="t2",
        classification="direct_contradiction",
        challenger="challenger-bot",
        rationale="contradiction",
        counter_evidence_source="ledger/outcomes.jsonl:oc-1",
        cell_id="core",
        spark_id="spark-2",
        proposed_at="2026-05-15T00:00:01+00:00",
    )

    # Review only the policy spark.
    append_audit_review(
        cell,
        audit_id="spark-1",
        resolution="accept",
        reviewer="alice",
        rationale="confirmed",
        review_actions=["no_action"],
        review_id="rev-1",
        reviewed_at="2026-05-15T00:00:02+00:00",
    )

    summary = audit_summary(cell)
    assert summary["counts"]["policy_conflict"] == 1
    assert summary["counts"]["direct_contradiction"] == 1
    assert summary["review_state_counts"]["reviewed"] == 1
    assert summary["review_state_counts"]["unreviewed"] == 1
    assert {f["audit_id"] for f in summary["findings"]} == {"spark-1", "spark-2"}
    finding_by_id = {f["audit_id"]: f for f in summary["findings"]}
    assert finding_by_id["spark-1"]["review_state"] == "reviewed"
    assert finding_by_id["spark-2"]["review_state"] == "unreviewed"
