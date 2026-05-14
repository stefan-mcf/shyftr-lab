from __future__ import annotations

import json
from pathlib import Path

from shyftr.distill.doctrine import (
    append_doctrine_proposals,
    approve_doctrine,
    distill_doctrine,
    propose_doctrine,
    propose_doctrine_from_resonance,
    read_approved_doctrines,
    read_proposed_doctrines,
)
from shyftr.layout import init_cell
from shyftr.models import Alloy, DoctrineProposal
from shyftr.resonance import ResonanceScore


def _alloy(
    alloy_id: str,
    cell_id: str,
    summary: str,
    *,
    confidence: float | None = None,
) -> Alloy:
    return Alloy(
        alloy_id=alloy_id,
        cell_id=cell_id,
        theme="review",
        summary=summary,
        source_trace_ids=[f"trace-{alloy_id}"],
        confidence=confidence,
    )


def _score(alloy_id: str, score: float, *, cells: int = 2) -> ResonanceScore:
    return ResonanceScore(
        alloy_id=alloy_id,
        recurrence_count=3,
        cell_diversity=cells,
        avg_confidence=0.8,
        success_ratio=0.9,
        score=score,
    )


def test_propose_doctrine_creates_pending_review_gated_record() -> None:
    alloys = [
        _alloy("a1", "cell-a", "Alloy: review memory before promotion"),
        _alloy("a2", "cell-b", "Alloy: memory review before promotion"),
    ]

    proposals = propose_doctrine(alloys, scope="global-doctrine")

    assert len(proposals) == 1
    proposal = proposals[0]
    assert isinstance(proposal, DoctrineProposal)
    assert proposal.review_status == "pending"
    assert proposal.scope == "global-doctrine"
    assert proposal.source_alloy_ids == ["a1", "a2"]
    assert proposal.statement.startswith("Doctrine proposal (global-doctrine):")


def test_propose_doctrine_requires_minimum_alloys() -> None:
    assert propose_doctrine([], require_min_alloys=1) == []
    assert propose_doctrine([_alloy("a1", "cell-a", "summary")], require_min_alloys=2) == []


def test_propose_doctrine_from_resonance_filters_low_or_single_cell_scores() -> None:
    alloys = [
        _alloy("a1", "cell-a", "high resonance"),
        _alloy("a2", "cell-b", "low resonance"),
        _alloy("a3", "cell-c", "same cell only"),
    ]
    scores = [_score("a1", 0.80), _score("a2", 0.20), _score("a3", 0.90, cells=1)]

    proposals = propose_doctrine_from_resonance(alloys, scores, min_resonance=0.50)

    assert len(proposals) == 1
    assert proposals[0].source_alloy_ids == ["a1"]


def test_doctrine_ids_are_deterministic_regardless_of_input_order() -> None:
    first = propose_doctrine(
        [_alloy("a2", "cell-b", "b"), _alloy("a1", "cell-a", "a")],
        scope="cross-cell",
    )
    second = propose_doctrine(
        [_alloy("a1", "cell-a", "a"), _alloy("a2", "cell-b", "b")],
        scope="cross-cell",
    )

    assert first[0].doctrine_id == second[0].doctrine_id
    assert first[0].source_alloy_ids == second[0].source_alloy_ids == ["a1", "a2"]


def test_append_proposed_doctrine_is_append_only(tmp_path: Path) -> None:
    cell_path = init_cell(tmp_path, "core")
    first = propose_doctrine([_alloy("a1", "cell-a", "summary one")])[0]
    second = propose_doctrine([_alloy("a2", "cell-b", "summary two")])[0]

    assert append_doctrine_proposals(cell_path, [first]) == 1
    assert append_doctrine_proposals(cell_path, [second]) == 1

    records = read_proposed_doctrines(cell_path)
    assert [record.doctrine_id for record in records] == [first.doctrine_id, second.doctrine_id]
    proposed_lines = (cell_path / "doctrine" / "proposed.jsonl").read_text().strip().splitlines()
    assert len(proposed_lines) == 2


def test_distill_doctrine_never_writes_approved_ledger(tmp_path: Path) -> None:
    cell_path = init_cell(tmp_path, "core")
    approved_path = cell_path / "doctrine" / "approved.jsonl"
    before = approved_path.read_text()

    summary = distill_doctrine(cell_path, [_alloy("a1", "cell-a", "summary")])

    assert summary["proposal_count"] == 1
    assert summary["approved_count_delta"] == 0
    assert approved_path.read_text() == before
    assert len(read_proposed_doctrines(cell_path)) == 1
    assert read_approved_doctrines(cell_path) == []


def test_explicit_approve_doctrine_writes_approved_copy_and_is_idempotent(tmp_path: Path) -> None:
    cell_path = init_cell(tmp_path, "core")
    proposal = propose_doctrine([_alloy("a1", "cell-a", "summary")])[0]
    append_doctrine_proposals(cell_path, [proposal])

    first = approve_doctrine(cell_path, proposal.doctrine_id)
    second = approve_doctrine(cell_path, proposal.doctrine_id)

    assert first is not None
    assert second is not None
    assert first.review_status == "approved"
    approved = read_approved_doctrines(cell_path)
    assert len(approved) == 1
    assert approved[0].doctrine_id == proposal.doctrine_id
    assert read_proposed_doctrines(cell_path)[0].review_status == "pending"


def test_approve_unknown_doctrine_returns_none(tmp_path: Path) -> None:
    cell_path = init_cell(tmp_path, "core")
    assert approve_doctrine(cell_path, "doctrine-missing") is None


def test_proposed_ledger_json_uses_existing_model_schema(tmp_path: Path) -> None:
    cell_path = init_cell(tmp_path, "core")
    proposal = propose_doctrine([_alloy("a1", "cell-a", "summary")])[0]
    append_doctrine_proposals(cell_path, [proposal])

    line = (cell_path / "doctrine" / "proposed.jsonl").read_text().strip()
    record = json.loads(line)
    assert sorted(k for k in record if k not in {"row_hash", "previous_row_hash"}) == [
        "doctrine_id",
        "review_status",
        "scope",
        "source_alloy_ids",
        "statement",
    ]
    assert record["previous_row_hash"] == ""
    assert len(record["row_hash"]) == 64
    assert record["review_status"] == "pending"
