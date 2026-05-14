from __future__ import annotations

from scripts.current_state_baseline import run_baseline


def test_current_state_baseline_phase2_exposes_checkpoint_and_resume_metrics() -> None:
    summary = run_baseline("all", "preference-recall")

    carry_result = summary["fixture_results"]["carry"][0]
    assert carry_result["carry_state_present"] is True
    assert carry_result["carry_candidate_count"] >= 1
    assert carry_result["memory_candidate_count"] >= 1

    live_result = summary["fixture_results"]["live"][0]
    assert live_result["carry_state_checkpoint_count"] >= 1
    assert live_result["carry_state_checkpoint_tokens"] >= 1
    assert live_result["checkpoint_total_items"] >= 1
    assert live_result["checkpoint_total_tokens"] >= 1
    assert live_result["resume_validation"]["status"] == "ok"
    assert live_result["resume_state_score"] >= 0.5
