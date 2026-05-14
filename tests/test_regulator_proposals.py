import pytest

from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.regulator_proposals import generate_regulator_proposals, review_regulator_proposal


def test_regulator_proposals_generated_from_repeated_synthetic_events(tmp_path):
    cell = init_cell(tmp_path, "core")
    for i in range(2):
        append_jsonl(cell / "ledger" / "regulator_events.jsonl", {"event_id": f"e{i}", "event_type": "false_approval", "impacted_area": "sensitivity", "memory_id": f"m{i}"})
    proposals = generate_regulator_proposals(cell)
    assert len(proposals) == 1
    assert proposals[0]["requires_human_review"] is True
    assert proposals[0]["auto_apply"] is False
    assert proposals[0]["examples"] == ["m0", "m1"]


def test_false_rejection_events_generate_review_gated_proposals(tmp_path):
    cell = init_cell(tmp_path, "core")
    for i in range(2):
        append_jsonl(cell / "ledger" / "regulator_events.jsonl", {"event_id": f"fr{i}", "event_type": "false_rejection", "impacted_area": "recall", "candidate_id": f"c{i}", "counterexample_id": f"ok{i}"})
    proposals = generate_regulator_proposals(cell)
    assert len(proposals) == 1
    assert proposals[0]["impacted_area"] == "recall"
    assert proposals[0]["examples"] == ["c0", "c1"]
    assert proposals[0]["counterexamples"] == ["ok0", "ok1"]
    assert proposals[0]["requires_simulation_before_policy_change"] is True


def test_regulator_proposal_approval_requires_simulation(tmp_path):
    cell = init_cell(tmp_path, "core")
    with pytest.raises(ValueError):
        review_regulator_proposal(cell, "rp-1", "approve", "operator", "ok")
    event = review_regulator_proposal(cell, "rp-1", "approve", "operator", "ok", simulation_report_ref="sim-1")
    assert event["policy_mutated"] is False
