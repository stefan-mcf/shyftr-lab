from shyftr.layout import init_cell
from shyftr.reputation import ReputationEvent, append_reputation_event, reputation_summary


def test_empty_reputation_summary_is_review_gated(tmp_path):
    cell = init_cell(tmp_path, "core")
    summary = reputation_summary(cell)
    assert summary == {"status": "ok", "summaries": [], "total": 0}


def test_reputation_summary_rates_and_review_priority(tmp_path):
    cell = init_cell(tmp_path, "core")
    append_reputation_event(cell, ReputationEvent("reviewer", "alice", "approved", {"review_id": "r1"}))
    append_reputation_event(cell, ReputationEvent("reviewer", "alice", "rejected", {"review_id": "r2"}))
    append_reputation_event(cell, ReputationEvent("reviewer", "alice", "harmful_feedback", {"feedback_id": "f1"}))
    summary = reputation_summary(cell, target_type="reviewer", target_id="alice")["summaries"][0]
    assert abs(summary["approval_rate"] - (1 / 3)) < 0.001
    assert abs(summary["rejection_rate"] - (1 / 3)) < 0.001
    assert summary["review_priority_score"] > 0
    assert summary["can_bypass_review"] is False
