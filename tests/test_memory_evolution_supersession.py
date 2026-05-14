from __future__ import annotations

from pathlib import Path

from shyftr.evolution import append_evolution_proposal, propose_supersession_from_feedback, review_evolution_proposal, simulate_evolution_proposal
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.mutations import active_charge_ids


def _seed_memory(cell: Path) -> None:
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-1", "cell_id": "evo-cell", "statement": "Use model A for all review work.", "source_fragment_ids": ["cand-1"], "kind": "routing_heuristic", "status": "approved"})


def test_repeated_contradictory_feedback_emits_deprecation_proposal() -> None:
    memories = [{"memory_id": "mem-1", "statement": "Use model A for all review work.", "candidate_ids": ["cand-1"]}]
    feedback = [
        {"feedback_id": "fb-1", "verdict": "contradicted", "contradicted_memory_ids": ["mem-1"]},
        {"feedback_id": "fb-2", "verdict": "contradicted", "contradicted_memory_ids": ["mem-1"]},
    ]
    proposals = propose_supersession_from_feedback(feedback, memories)
    assert len(proposals) == 1
    assert proposals[0]["proposal_type"] == "deprecate_memory"
    assert proposals[0]["target_ids"] == ["mem-1"]
    assert proposals[0]["requires_simulation"] is True


def test_accepted_review_appends_lifecycle_event_through_mutations(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    _seed_memory(cell)
    proposal = propose_supersession_from_feedback(
        [
            {"feedback_id": "fb-1", "verdict": "contradicted", "contradicted_memory_ids": ["mem-1"]},
            {"feedback_id": "fb-2", "verdict": "contradicted", "contradicted_memory_ids": ["mem-1"]},
        ],
        [{"memory_id": "mem-1", "statement": "Use model A for all review work.", "candidate_ids": ["cand-1"]}],
    )[0]
    append_evolution_proposal(cell, proposal)
    assert "mem-1" in active_charge_ids(cell)
    sim = simulate_evolution_proposal(cell, proposal["proposal_id"])
    review = review_evolution_proposal(cell, proposal["proposal_id"], decision="accept", rationale="two verified contradictions", simulation_ref=sim["simulation_id"], actor="test")
    assert review["decision"] == "accept"
    assert review["applied_events"][0]["action"] == "deprecate"
    assert "mem-1" not in active_charge_ids(cell)
