from __future__ import annotations

from pathlib import Path

import pytest

from shyftr.evolution import EvolutionProposal, append_evolution_proposal, read_evolution_proposals
from shyftr.layout import init_cell


def _proposal(**overrides):
    data = {
        "proposal_id": "evo-1",
        "proposal_type": "split_candidate",
        "candidate_ids": ["cand-1"],
        "evidence_refs": ["synthetic:fixture"],
        "rationale": "synthetic oversized candidate should be split before promotion",
        "confidence": 0.7,
        "risk_level": "medium",
        "projection_delta": {"proposed_child_count": 2},
    }
    data.update(overrides)
    return EvolutionProposal(**data)


def test_evolution_proposal_serializes_review_gated_defaults() -> None:
    proposal = _proposal()
    payload = proposal.to_dict()
    assert payload["proposal_id"] == "evo-1"
    assert payload["requires_review"] is True
    assert payload["auto_apply"] is False
    assert payload["candidate_ids"] == ["cand-1"]
    assert EvolutionProposal.from_dict(payload).to_dict() == payload


def test_invalid_proposal_type_and_missing_evidence_fail() -> None:
    with pytest.raises(ValueError, match="invalid proposal_type"):
        _proposal(proposal_type="rewrite_memory")
    with pytest.raises(ValueError, match="evidence_refs"):
        _proposal(evidence_refs=[])


def test_retrieval_affecting_proposals_require_simulation() -> None:
    with pytest.raises(ValueError, match="require simulation"):
        _proposal(proposal_type="forget_memory", target_ids=["mem-1"], candidate_ids=[])
    assert _proposal(proposal_type="forget_memory", target_ids=["mem-1"], candidate_ids=[], requires_simulation=True).requires_simulation is True


def test_append_evolution_proposal_is_append_only(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    path = cell / "ledger" / "evolution" / "proposals.jsonl"
    before = path.read_text(encoding="utf-8")
    append_evolution_proposal(cell, _proposal(proposal_id="evo-1"))
    append_evolution_proposal(cell, _proposal(proposal_id="evo-2"))
    after_lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert before == ""
    assert len(after_lines) == 2
    assert [row["proposal_id"] for row in read_evolution_proposals(cell)] == ["evo-1", "evo-2"]
