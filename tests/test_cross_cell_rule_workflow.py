from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.distill.rules import approve_rule_proposal, list_rule_proposals, propose_rule_from_resonance, reject_rule_proposal
from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.loadout import LoadoutTaskInput, assemble_loadout


def _resonance() -> list[dict]:
    return [{
        "resonance_id": "res-1",
        "source_cell_ids": ["project-alpha", "project-beta"],
        "source_record_ids": ["mem-alpha", "mem-beta"],
        "source_record_kinds": ["memory", "memory"],
        "score": 0.82,
        "provenance": {"source_cell_ids": ["project-alpha", "project-beta"], "source_record_ids": ["mem-alpha", "mem-beta"]},
    }]


def test_rule_proposal_from_high_resonance_pattern(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta", statement="Use bounded backoff for retryable api calls")
    assert proposal["review_status"] == "pending"
    assert proposal["source_cell_ids"] == ["project-alpha", "project-beta"]


def test_rule_proposal_requires_review_before_promotion(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")
    assert proposal["review_status"] == "pending"
    assert (cell / "ledger" / "rules" / "approved.jsonl").read_text(encoding="utf-8") == ""


def test_rule_proposal_review_writes_append_only_event(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")
    before = (cell / "ledger" / "rules" / "proposed.jsonl").stat().st_size
    event = approve_rule_proposal(cell, proposal["rule_id"], reviewer_id="operator", rationale="synthetic proof")
    assert event["review_status"] == "approved"
    assert (cell / "ledger" / "rules" / "proposed.jsonl").stat().st_size > before


def test_approved_rule_is_retrievable_in_packs_for_scoped_cells(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha", statement="Use bounded backoff for retryable api calls")
    approve_rule_proposal(cell, proposal["rule_id"], reviewer_id="operator", rationale="ok")
    pack = assemble_loadout(LoadoutTaskInput(str(cell), "bounded backoff api", "task-1", max_items=5))
    assert proposal["rule_id"] in [item.item_id for item in pack.items]


def test_rule_scope_constrains_retrieval(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha", statement="Use bounded backoff for retryable api calls")
    approve_rule_proposal(cell, proposal["rule_id"], reviewer_id="operator", rationale="ok")
    approved = json.loads((cell / "ledger" / "rules" / "approved.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert approved["scope"] == "project-alpha"


def test_rule_promotion_does_not_mutate_local_cell_memories(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "local", "cell_id": "review-cell", "statement": "local truth", "source_fragment_ids": ["f"], "status": "approved"})
    before = (cell / "traces" / "approved.jsonl").read_text(encoding="utf-8")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")
    approve_rule_proposal(cell, proposal["rule_id"], reviewer_id="operator", rationale="ok")
    assert (cell / "traces" / "approved.jsonl").read_text(encoding="utf-8") == before


def test_rule_promotion_records_provenance_with_source_pattern_ids(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    res = _resonance()
    res[0]["source_record_ids"] = ["pat-alpha", "pat-beta"]
    proposal = propose_rule_from_resonance(cell, res, scope="project-alpha,project-beta")
    event = approve_rule_proposal(cell, proposal["rule_id"], reviewer_id="operator", rationale="ok")
    assert event["source_pattern_ids"] == ["pat-alpha", "pat-beta"]
    assert event["provenance"]["source_record_ids"] == ["pat-alpha", "pat-beta"]


def test_rule_from_single_weak_source_cannot_create_global_policy(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    weak = [{"resonance_id": "res-weak", "source_cell_ids": ["project-alpha"], "source_record_ids": ["mem-alpha"], "score": 0.2}]
    with pytest.raises(ValueError, match="minimum cell diversity"):
        propose_rule_from_resonance(cell, weak, scope="global")


def test_rule_proposals_are_deduplicated(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    first = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")
    second = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")
    assert second["rule_id"] == first["rule_id"]


def test_rejected_rule_proposal_blocks_duplicate_from_same_evidence(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")
    reject_rule_proposal(cell, proposal["rule_id"], reviewer_id="operator", rationale="too broad")
    with pytest.raises(ValueError, match="rejected duplicate"):
        propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")


def test_rule_promotion_provenance_includes_source_cell_ids(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    proposal = propose_rule_from_resonance(cell, _resonance(), scope="project-alpha,project-beta")
    event = approve_rule_proposal(cell, proposal["rule_id"], reviewer_id="operator", rationale="ok")
    assert event["provenance"]["source_cell_ids"] == ["project-alpha", "project-beta"]


def test_global_rule_requires_minimum_cell_diversity(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "review-cell")
    with pytest.raises(ValueError):
        propose_rule_from_resonance(cell, [{"source_cell_ids": ["one"], "source_record_ids": ["mem"], "score": 0.9}], scope="global")
