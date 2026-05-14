from __future__ import annotations

from pathlib import Path

from shyftr.evolution import EvolutionProposal, append_evolution_proposal, propose_forgetting_from_policies, review_evolution_proposal, simulate_evolution_proposal
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.mutations import active_charge_ids


def test_policy_marker_emits_logical_forgetting_proposal() -> None:
    proposals = propose_forgetting_from_policies([
        {"memory_id": "mem-1", "statement": "Synthetic retention-limited note.", "candidate_ids": ["cand-1"], "tags": ["retention_expired"]}
    ])
    assert len(proposals) == 1
    assert proposals[0]["proposal_type"] == "forget_memory"
    assert proposals[0]["projection_delta"]["physical_delete"] is False
    assert proposals[0]["auto_apply"] is False


def test_projection_excludes_memory_only_after_accepted_review(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-1", "cell_id": "evo-cell", "statement": "Synthetic retention-limited note.", "source_fragment_ids": ["cand-1"], "kind": "preference", "status": "approved", "tags": ["retention_expired"]})
    proposal = propose_forgetting_from_policies([{"memory_id": "mem-1", "statement": "Synthetic retention-limited note.", "candidate_ids": ["cand-1"], "tags": ["retention_expired"]}])[0]
    append_evolution_proposal(cell, proposal)
    assert "mem-1" in active_charge_ids(cell)
    sim = simulate_evolution_proposal(cell, proposal["proposal_id"])
    review_evolution_proposal(cell, proposal["proposal_id"], decision="accept", rationale="retention marker verified", simulation_ref=sim["simulation_id"], actor="test")
    assert "mem-1" not in active_charge_ids(cell)
    assert len(list(read_jsonl(cell / "traces" / "approved.jsonl"))) == 1


def test_accepting_missing_memory_promotion_appends_review_and_creates_memory(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    proposal = EvolutionProposal(
        proposal_id="evo-missing-1",
        proposal_type="promote_missing_memory",
        candidate_ids=["mmc-1"],
        evidence_refs=["synthetic:missing-memory"],
        rationale="Synthetic future detector says a missing memory could be promoted.",
        confidence=0.6,
        risk_level="medium",
        proposed_memory={"statement": "Synthetic missing memory placeholder.", "kind": "preference", "memory_type": "semantic"},
    ).to_dict()
    append_evolution_proposal(cell, proposal)
    review = review_evolution_proposal(cell, proposal["proposal_id"], decision="accept", rationale="operator checked placeholder", actor="test")
    assert review["decision"] == "accept"
    assert review["applied_events"][0]["action"] == "promote_missing_memory"
    assert len(list(read_jsonl(cell / "ledger" / "evolution" / "reviews.jsonl"))) == 1
    traces = list(read_jsonl(cell / "traces" / "approved.jsonl"))
    assert len(traces) == 1
    assert traces[0][1]["statement"] == "Synthetic missing memory placeholder."
    assert traces[0][1]["memory_type"] == "semantic"
