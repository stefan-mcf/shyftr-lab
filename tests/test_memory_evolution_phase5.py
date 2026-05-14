from __future__ import annotations

from pathlib import Path

from shyftr.evolution import (
    append_evolution_proposal,
    generate_rehearsal_fixtures,
    propose_challenges_from_feedback,
    propose_missing_memory_promotions,
    rehearse_cell,
    review_evolution_proposal,
    simulate_evolution_proposal,
)
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.mutations import active_charge_ids, effective_state_for_charge


def _seed_trace(cell: Path, trace_id: str, statement: str, *, kind: str = "workflow") -> None:
    append_jsonl(
        cell / "traces" / "approved.jsonl",
        {
            "trace_id": trace_id,
            "cell_id": "evo-cell",
            "statement": statement,
            "source_fragment_ids": [f"cand-{trace_id}"],
            "kind": kind,
            "status": "approved",
        },
    )


def test_missing_memory_candidates_emit_semantic_and_procedural_promotion_proposals(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    append_jsonl(
        cell / "ledger" / "missing_memory_candidates.jsonl",
        {
            "candidate_id": "mmc-sem-1",
            "cell_id": "evo-cell",
            "source_text": "The project prefers additive review-gated durable memory updates.",
            "missing_from_loadout_id": "loadout-1",
            "emitted_at": "2026-05-14T00:00:00Z",
            "review_status": "pending",
        },
    )
    append_jsonl(
        cell / "ledger" / "missing_memory_candidates.jsonl",
        {
            "candidate_id": "mmc-proc-1",
            "cell_id": "evo-cell",
            "source_text": "Run the alpha gate before tester outreach and record the outcome.",
            "missing_from_loadout_id": "loadout-1",
            "emitted_at": "2026-05-14T00:00:01Z",
            "review_status": "pending",
        },
    )

    proposals = propose_missing_memory_promotions(cell)

    assert len(proposals) == 2
    by_candidate = {proposal["candidate_ids"][0]: proposal for proposal in proposals}
    semantic = by_candidate["mmc-sem-1"]
    procedural = by_candidate["mmc-proc-1"]

    assert semantic["proposal_type"] == "promote_missing_memory"
    assert semantic["requires_review"] is True
    assert semantic["auto_apply"] is False
    assert semantic["requires_simulation"] is False
    assert semantic["proposed_memory"]["memory_type"] == "semantic"
    assert semantic["proposed_memory"]["kind"] == "preference"

    assert procedural["proposal_type"] == "promote_missing_memory"
    assert procedural["proposed_memory"]["memory_type"] == "procedural"
    assert procedural["proposed_memory"]["kind"] == "workflow"
    assert procedural["projection_delta"]["active_memory_delta"] == 1


def test_accepting_missing_memory_promotion_creates_active_memory_and_review_event(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    append_jsonl(
        cell / "ledger" / "missing_memory_candidates.jsonl",
        {
            "candidate_id": "mmc-proc-1",
            "cell_id": "evo-cell",
            "source_text": "Run the alpha gate before tester outreach and record the outcome.",
            "missing_from_loadout_id": "loadout-1",
            "emitted_at": "2026-05-14T00:00:01Z",
            "review_status": "pending",
        },
    )
    proposal = propose_missing_memory_promotions(cell)[0]
    append_evolution_proposal(cell, proposal)

    review = review_evolution_proposal(
        cell,
        proposal["proposal_id"],
        decision="accept",
        rationale="operator confirmed the missing procedural memory",
        actor="test",
    )

    traces = list(read_jsonl(cell / "traces" / "approved.jsonl"))
    assert len(traces) == 1
    trace = traces[0][1]
    assert trace["statement"] == proposal["proposed_memory"]["statement"]
    assert trace["memory_type"] == "procedural"
    assert trace["kind"] == "workflow"
    assert trace["trace_id"] in active_charge_ids(cell)

    reviews = list(read_jsonl(cell / "ledger" / "evolution" / "reviews.jsonl"))
    assert len(reviews) == 1
    assert reviews[0][1]["decision"] == "accept"
    assert review["applied_events"][0]["action"] == "promote_missing_memory"


def test_repeated_questioning_feedback_emits_challenge_proposal_and_acceptance_marks_memory_challenged(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    _seed_trace(cell, "mem-1", "Use model A for all review work.", kind="routing_heuristic")
    memories = [{"memory_id": "mem-1", "statement": "Use model A for all review work.", "candidate_ids": ["cand-1"], "kind": "routing_heuristic"}]
    feedback = [
        {"feedback_id": "fb-1", "verdict": "questioned", "challenged_memory_ids": ["mem-1"]},
        {"feedback_id": "fb-2", "verdict": "questioned", "challenged_memory_ids": ["mem-1"]},
    ]

    proposals = propose_challenges_from_feedback(feedback, memories)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["proposal_type"] == "challenge_memory"
    assert proposal["target_ids"] == ["mem-1"]
    assert proposal["requires_simulation"] is True
    assert proposal["projection_delta"]["status_transition"] == "approved -> challenged"

    append_evolution_proposal(cell, proposal)
    sim = simulate_evolution_proposal(cell, proposal["proposal_id"])
    review = review_evolution_proposal(
        cell,
        proposal["proposal_id"],
        decision="accept",
        rationale="operator confirmed conflicting evidence requires challenge status",
        actor="test",
        simulation_ref=sim["simulation_id"],
    )

    state = effective_state_for_charge(cell, "mem-1")
    assert state.lifecycle_status == "challenged"
    assert "mem-1" in active_charge_ids(cell)
    assert review["applied_events"][0]["action"] == "challenge"


def test_rehearsal_fixtures_and_report_are_deterministic_and_append_only(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    _seed_trace(cell, "mem-1", "Run the alpha gate before tester outreach and record the outcome.")
    append_jsonl(cell / "ledger" / "retrieval_logs.jsonl", {"pack_id": "pack-1", "memory_ids": ["mem-1"], "query": "alpha gate tester outreach"})
    append_jsonl(
        cell / "ledger" / "outcomes.jsonl",
        {
            "outcome_id": "oc-1",
            "cell_id": "evo-cell",
            "loadout_id": "pack-1",
            "task_id": "task-1",
            "result": "success",
            "applied_trace_ids": ["mem-1"],
            "useful_trace_ids": ["mem-1"],
            "harmful_trace_ids": [],
            "missing_memory": [],
        },
    )

    fixtures = generate_rehearsal_fixtures(cell)
    assert len(fixtures) == 1
    assert fixtures[0]["expected_memory_id"] == "mem-1"
    assert fixtures[0]["query"] == "alpha gate tester outreach"

    report = rehearse_cell(cell, append_report=True)
    assert report["read_only"] is False
    assert report["fixture_count"] == 1
    assert report["hit_count"] == 1
    assert report["hit_rate"] == 1.0
    assert report["fixtures"][0]["matched"] is True

    rehearsal_rows = list(read_jsonl(cell / "ledger" / "evolution" / "rehearsal_reports.jsonl"))
    assert len(rehearsal_rows) == 1
    assert rehearsal_rows[0][1]["report_id"] == report["report_id"]
