from __future__ import annotations

from scripts.current_state_baseline import run_baseline

REQUIRED_TOP_LEVEL_FIELDS = {
    "run_id",
    "timestamp",
    "git_sha",
    "fixture_count",
    "fixtures_included",
    "mode",
    "mode_summaries",
    "fixture_results",
    "behavior",
    "known_limitations",
    "output_schema_version",
}

REQUIRED_RESULT_FIELDS = {
    "fixture_id",
    "mode",
    "surfaced_ids",
    "expected_useful_ids",
    "expected_required_ids",
    "matched_useful_count",
    "stale_count",
    "harmful_count",
    "ignored_count",
    "missing_required_count",
    "useful_memory_inclusion_rate",
    "stale_memory_inclusion_rate",
    "harmful_memory_inclusion_rate",
    "ignored_memory_inclusion_rate",
    "missing_memory_rate",
    "duplicate_or_redundant_inclusion_rate",
    "duplicate_count",
    "redundant_ids",
    "raw_item_count",
    "total_tokens",
    "resume_state_score",
    "preserved_constraint_rate",
    "preserved_decision_rate",
    "preserved_artifact_ref_rate",
    "preserved_open_loop_rate",
    "notes",
    "expectation_evaluation",
}

REQUIRED_MODE_SUMMARY_FIELDS = {
    "fixture_count",
    "average_useful_memory_inclusion_rate",
    "average_stale_memory_inclusion_rate",
    "average_harmful_memory_inclusion_rate",
    "average_ignored_memory_inclusion_rate",
    "average_missing_memory_rate",
    "average_resume_state_score",
    "total_raw_items",
}


def test_current_state_baseline_summary_matches_metrics_contract() -> None:
    summary = run_baseline("all", "preference-recall")

    assert REQUIRED_TOP_LEVEL_FIELDS <= set(summary.keys())
    assert summary["output_schema_version"] == "current-state-baseline.v1"
    assert summary["fixture_count"] == 1
    assert summary["fixtures_included"] == ["preference-recall"]
    assert summary["behavior"]["mode"] == "behavior"

    for mode in ("durable", "carry", "live"):
        assert REQUIRED_MODE_SUMMARY_FIELDS <= set(summary["mode_summaries"][mode].keys())
        assert summary["mode_summaries"][mode]["fixture_count"] == 1
        assert len(summary["fixture_results"][mode]) == 1
        result = summary["fixture_results"][mode][0]
        assert REQUIRED_RESULT_FIELDS <= set(result.keys())
        assert result["mode"] == mode
        assert result["fixture_id"] == "preference-recall"
        assert set(result["expectation_evaluation"].keys()) == {"mode", "checked", "pass"}
