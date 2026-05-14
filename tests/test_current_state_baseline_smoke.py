from __future__ import annotations

from scripts.current_state_baseline import load_fixtures, run_baseline


def test_fixture_catalog_loads_expected_public_safe_set() -> None:
    fixtures = load_fixtures()
    fixture_ids = {fixture["fixture_id"] for fixture in fixtures}
    assert fixture_ids == {
        "artifact-handoff",
        "convention-correction",
        "duplicate-conflict",
        "harmful-caution",
        "missing-memory-detection",
        "multi-step-resume",
        "noisy-cell-suppression",
        "preference-recall",
    }


def test_single_fixture_durable_run_is_repeatable_and_contract_shaped() -> None:
    first = run_baseline("durable", "preference-recall")
    second = run_baseline("durable", "preference-recall")

    assert first["output_schema_version"] == "current-state-baseline.v1"
    assert first["mode"] == "durable"
    assert first["fixture_count"] == 1
    assert first["fixtures_included"] == ["preference-recall"]
    assert set(first["mode_summaries"].keys()) == {"durable", "carry", "live"}
    assert first["mode_summaries"]["durable"]["fixture_count"] == 1
    assert first["mode_summaries"]["carry"]["fixture_count"] == 0
    assert first["mode_summaries"]["live"]["fixture_count"] == 0
    assert len(first["fixture_results"]["durable"]) == 1
    assert first["fixture_results"]["carry"] == []
    assert first["fixture_results"]["live"] == []
    assert first["behavior"] is None
    assert first["known_limitations"]
    assert first["git_sha"]
    assert first["timestamp"]

    first_result = first["fixture_results"]["durable"][0]
    second_result = second["fixture_results"]["durable"][0]
    assert first_result["fixture_id"] == "preference-recall"
    assert second_result["fixture_id"] == "preference-recall"
    assert first_result["surfaced_ids"] == second_result["surfaced_ids"]
    assert first_result["useful_memory_inclusion_rate"] == second_result["useful_memory_inclusion_rate"]
    assert first_result["missing_memory_rate"] == second_result["missing_memory_rate"]
    assert first_result["expectation_evaluation"] == second_result["expectation_evaluation"]
