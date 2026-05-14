from __future__ import annotations

import pytest

from shyftr.confidence import adjust_confidence
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.provider.memory import (
    MemoryProvider,
    deprecate,
    forget,
    profile,
    remember,
    replace,
    search,
)
from shyftr.policy import BoundaryPolicyError


def _records(path):
    return [record for _, record in read_jsonl(path)]


def test_remember_promotes_explicit_preference_with_provenance(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    result = remember(
        cell,
        "User prefers concise terminal updates.",
        "preference",
        pulse_context={"channel": "cli", "actor": "user"},
        metadata={"scope": "assistant_profile"},
    )

    assert result.status == "approved"
    assert result.trust_tier == "memory"
    assert result.charge_id.startswith("trace-")
    assert result.pulse_id.startswith("src-")
    assert result.spark_id.startswith("frag-")

    sources = _records(cell / "ledger" / "sources.jsonl")
    fragments = _records(cell / "ledger" / "fragments.jsonl")
    reviews = _records(cell / "ledger" / "reviews.jsonl")
    promotions = _records(cell / "ledger" / "promotions.jsonl")
    traces = _records(cell / "traces" / "approved.jsonl")

    assert sources[0]["metadata"]["provider_api"] == "remember"
    assert sources[0]["metadata"]["pulse_context"] == {"channel": "cli", "actor": "user"}
    assert fragments[0]["source_id"] == result.pulse_id
    assert reviews[0]["candidate_id"] == result.spark_id
    assert reviews[0]["review_status"] == "approved"
    assert reviews[0]["metadata"]["regulator_decision"]["trusted_direct_promotion"] is True
    assert reviews[0]["metadata"]["regulator_decision"]["review_required"] is False
    assert promotions[0]["source_id"] == result.pulse_id
    assert promotions[0]["source_fragment_ids"] == [result.spark_id]
    assert traces[0]["trace_id"] == result.charge_id
    assert traces[0]["source_fragment_ids"] == [result.spark_id]
    assert traces[0]["kind"] == "preference"


def test_remember_rejects_operational_state_pollution(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    with pytest.raises(BoundaryPolicyError):
        remember(cell, "Queue item task-123 is in_progress on branch feature/x", "workflow")

    assert _records(cell / "ledger" / "sources.jsonl") == []
    assert _records(cell / "traces" / "approved.jsonl") == []


def test_search_returns_trust_labels_charge_ids_and_filters_kinds(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    preference = remember(cell, "User prefers concise terminal updates.", "preference")
    remember(cell, "Use pytest before pushing Python changes.", "workflow")

    results = search(cell, "concise updates", kinds=["preference"])

    assert [item.charge_id for item in results] == [preference.charge_id]
    assert results[0].trust_tier == "memory"
    assert results[0].kind == "preference"
    assert results[0].lifecycle_status == "approved"
    assert results[0].selection_rationale == "lexical_overlap"
    assert results[0].statement == "User prefers concise terminal updates."
    assert results[0].provenance["source_fragment_ids"] == [preference.spark_id]


def test_profile_projects_reviewed_memory_without_becoming_truth(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "User prefers precise ShyftR vocabulary.", "preference")

    projected = profile(cell, max_tokens=20)

    assert "# ShyftR Memory Profile" in projected.markdown
    assert "User prefers precise ShyftR vocabulary." in projected.markdown
    assert remembered.charge_id in projected.markdown
    assert projected.projection_id.startswith("profile-")
    assert projected.source_charge_ids == [remembered.charge_id]
    assert not (cell / "summaries" / "profile.md").exists()


def test_forget_deprecate_and_replace_append_lifecycle_events(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    old = remember(cell, "User prefers long narrative updates.", "preference")

    forgotten = forget(cell, old.charge_id, reason="user requested removal", actor="user")
    assert forgotten.action == "forget"
    assert search(cell, "narrative updates") == []

    deprecated = deprecate(cell, old.charge_id, reason="superseded style preference", actor="user")
    assert deprecated.action == "deprecate"

    new = replace(
        cell,
        old.charge_id,
        "User prefers concise terminal updates.",
        reason="user corrected preference",
        actor="user",
    )
    assert new.replacement_charge_id.startswith("trace-")
    replacement_results = search(cell, "concise terminal updates")
    assert [result.charge_id for result in replacement_results] == [new.replacement_charge_id]

    status_events = _records(cell / "ledger" / "status_events.jsonl")
    supersession_events = _records(cell / "ledger" / "supersession_events.jsonl")
    deprecation_events = _records(cell / "ledger" / "deprecation_events.jsonl")
    assert [event["action"] for event in status_events] == ["forget", "deprecate", "replace"]
    assert supersession_events[-1]["old_charge_id"] == old.charge_id
    assert supersession_events[-1]["replacement_charge_id"] == new.replacement_charge_id
    assert deprecation_events[0]["status"] == "deprecated"
    assert status_events[0]["include_in_retrieval"] is False
    assert status_events[-1]["include_in_profile"] is False
    assert _records(cell / "ledger" / "sources.jsonl")[-1]["metadata"]["operation_origin"] == "replace"


def test_search_collapses_append_only_trace_updates_to_latest_charge_row(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "Use pytest before pushing Python changes.", "workflow")

    adjust_confidence(
        cell,
        outcome_id="outcome-1",
        useful_trace_ids=[remembered.charge_id],
        harmful_trace_ids=[],
        result="success",
    )

    results = search(cell, "pytest pushing", kinds=["workflow"])

    assert [result.charge_id for result in results] == [remembered.charge_id]
    assert results[0].confidence == pytest.approx(0.85)


def test_memory_provider_class_wraps_function_api(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    provider = MemoryProvider(cell)

    remembered = provider.remember("User likes local-first memory.", "preference")

    assert provider.search("local-first")[0].charge_id == remembered.charge_id
    assert remembered.charge_id in provider.profile().markdown


def test_search_can_filter_by_memory_type(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remember(cell, "User prefers concise updates.", "preference")
    remember(cell, "Use pytest before pushing.", "workflow")

    semantic = search(cell, "updates", memory_types=["semantic"])
    procedural = search(cell, "pytest", memory_types=["procedural"])

    assert semantic and semantic[0].memory_type == "semantic"
    assert procedural and procedural[0].memory_type == "procedural"
