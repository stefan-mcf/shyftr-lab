import json

import pytest

from shyftr.models import (
    Alloy,
    Candidate,
    DoctrineProposal,
    Evidence,
    Feedback,
    Fragment,
    Loadout,
    Memory,
    Outcome,
    Pack,
    Pattern,
    RuleProposal,
    Source,
    Trace,
)


def assert_round_trips(instance):
    as_dict = instance.to_dict()
    assert list(as_dict) == sorted(as_dict)
    restored = type(instance).from_dict(as_dict)
    assert restored == instance
    as_json = instance.to_json()
    assert json.loads(as_json) == as_dict
    assert type(instance).from_json(as_json) == instance


def test_source_round_trips_through_ordered_dict_and_json():
    source = Source(
        source_id="src-001",
        cell_id="cell-alpha",
        kind="note",
        uri="file://research-note",
        sha256="0" * 64,
        captured_at="2026-04-24T00:00:00Z",
        metadata={"page": 1},
    )

    assert_round_trips(source)


def test_fragment_round_trips_through_ordered_dict_and_json():
    fragment = Fragment(
        fragment_id="frag-001",
        source_id="src-001",
        cell_id="cell-alpha",
        kind="lesson",
        text="Prefer evidence-linked memories.",
        source_excerpt="The source says to keep evidence links.",
        boundary_status="accepted",
        review_status="pending",
        confidence=0.4,
        tags=["memory", "evidence"],
    )

    assert_round_trips(fragment)


def test_trace_round_trips_through_ordered_dict_and_json():
    trace = Trace(
        trace_id="trace-001",
        cell_id="cell-alpha",
        statement="Keep durable memories linked to evidence.",
        rationale="The supporting Fragment describes evidence-linked memories.",
        source_fragment_ids=["frag-001"],
        kind="verification_heuristic",
        status="approved",
        confidence=0.75,
        tags=["memory"],
        use_count=2,
        success_count=1,
        failure_count=0,
    )

    assert_round_trips(trace)


def test_alloy_round_trips_through_ordered_dict_and_json():
    alloy = Alloy(
        alloy_id="alloy-001",
        cell_id="cell-alpha",
        theme="evidence-linked recall",
        summary="Durable memories should preserve provenance.",
        source_trace_ids=["trace-001"],
        proposal_status="proposed",
        confidence=1.0,
    )

    assert_round_trips(alloy)


def test_doctrine_proposal_round_trips_through_ordered_dict_and_json():
    proposal = DoctrineProposal(
        doctrine_id="doctrine-001",
        source_alloy_ids=["alloy-001"],
        scope="cell",
        statement="Promote only evidence-linked memory rules.",
        review_status="pending",
    )

    assert_round_trips(proposal)


def test_loadout_round_trips_through_ordered_dict_and_json():
    loadout = Loadout(
        loadout_id="loadout-001",
        cell_id="cell-alpha",
        trace_ids=["trace-001"],
        alloy_ids=["alloy-001"],
        doctrine_ids=["doctrine-001"],
        trust_label="reviewed",
        generated_at="2026-04-24T01:00:00Z",
        metadata={"purpose": "agent context"},
    )

    assert_round_trips(loadout)


def test_outcome_round_trips_through_ordered_dict_and_json():
    outcome = Outcome(
        outcome_id="outcome-001",
        cell_id="cell-alpha",
        loadout_id="loadout-001",
        task_id="task-001",
        verdict="success",
        trace_ids=["trace-001"],
        ignored_charge_ids=["trace-ignored"],
        ignored_caution_ids=["trace-caution"],
        contradicted_charge_ids=["trace-contradicted"],
        over_retrieved_charge_ids=["trace-over"],
        pack_misses=["needed counterexample trace"],
        score=0.5,
        observed_at="2026-04-24T02:00:00Z",
        metadata={"reviewed": True},
    )

    assert_round_trips(outcome)


@pytest.mark.parametrize(
    ("model_type", "payload", "missing_field"),
    [
        (Source, {"source_id": "s", "cell_id": "c", "kind": "note", "sha256": "h", "captured_at": "t"}, "source_id"),
        (Source, {"source_id": "s", "cell_id": "c", "kind": "note", "sha256": "h", "captured_at": "t"}, "cell_id"),
        (Source, {"source_id": "s", "cell_id": "c", "kind": "note", "sha256": "h", "captured_at": "t"}, "kind"),
        (Source, {"source_id": "s", "cell_id": "c", "kind": "note", "sha256": "h", "captured_at": "t"}, "sha256"),
        (Source, {"source_id": "s", "cell_id": "c", "kind": "note", "sha256": "h", "captured_at": "t"}, "captured_at"),
        (Fragment, {"fragment_id": "f", "source_id": "s", "cell_id": "c", "kind": "lesson", "text": "text"}, "fragment_id"),
        (Fragment, {"fragment_id": "f", "source_id": "s", "cell_id": "c", "kind": "lesson", "text": "text"}, "source_id"),
        (Fragment, {"fragment_id": "f", "source_id": "s", "cell_id": "c", "kind": "lesson", "text": "text"}, "cell_id"),
        (Fragment, {"fragment_id": "f", "source_id": "s", "cell_id": "c", "kind": "lesson", "text": "text"}, "text"),
        (Trace, {"trace_id": "t", "cell_id": "c", "statement": "statement", "source_fragment_ids": ["f"]}, "trace_id"),
        (Trace, {"trace_id": "t", "cell_id": "c", "statement": "statement", "source_fragment_ids": ["f"]}, "cell_id"),
        (Trace, {"trace_id": "t", "cell_id": "c", "statement": "statement", "source_fragment_ids": ["f"]}, "statement"),
        (Trace, {"trace_id": "t", "cell_id": "c", "statement": "statement", "source_fragment_ids": ["f"]}, "source_fragment_ids"),
        (Alloy, {"alloy_id": "a", "cell_id": "c", "theme": "theme", "summary": "summary", "source_trace_ids": ["t"]}, "alloy_id"),
        (Alloy, {"alloy_id": "a", "cell_id": "c", "theme": "theme", "summary": "summary", "source_trace_ids": ["t"]}, "cell_id"),
        (Alloy, {"alloy_id": "a", "cell_id": "c", "theme": "theme", "summary": "summary", "source_trace_ids": ["t"]}, "source_trace_ids"),
        (DoctrineProposal, {"doctrine_id": "d", "source_alloy_ids": ["a"], "scope": "cell", "statement": "rule", "review_status": "pending"}, "doctrine_id"),
        (DoctrineProposal, {"doctrine_id": "d", "source_alloy_ids": ["a"], "scope": "cell", "statement": "rule", "review_status": "pending"}, "source_alloy_ids"),
    ],
)
def test_required_provenance_fields_cannot_be_omitted(model_type, payload, missing_field):
    del payload[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        model_type.from_dict(payload)


@pytest.mark.parametrize(
    ("model_type", "payload", "field_name"),
    [
        (Trace, {"trace_id": "t", "cell_id": "c", "statement": "statement", "source_fragment_ids": []}, "source_fragment_ids"),
        (Alloy, {"alloy_id": "a", "cell_id": "c", "theme": "theme", "summary": "summary", "source_trace_ids": []}, "source_trace_ids"),
        (DoctrineProposal, {"doctrine_id": "d", "source_alloy_ids": [], "scope": "cell", "statement": "rule", "review_status": "pending"}, "source_alloy_ids"),
    ],
)
def test_required_provenance_lists_must_not_be_empty(model_type, payload, field_name):
    with pytest.raises(ValueError, match=field_name):
        model_type.from_dict(payload)


@pytest.mark.parametrize(
    ("model_type", "payload", "field_name"),
    [
        (Fragment, {"fragment_id": "f", "source_id": "s", "cell_id": "c", "kind": "lesson", "text": "text", "confidence": -0.01}, "confidence"),
        (Fragment, {"fragment_id": "f", "source_id": "s", "cell_id": "c", "kind": "lesson", "text": "text", "confidence": 1.01}, "confidence"),
        (Trace, {"trace_id": "t", "cell_id": "c", "statement": "statement", "source_fragment_ids": ["f"], "confidence": -0.01}, "confidence"),
        (Trace, {"trace_id": "t", "cell_id": "c", "statement": "statement", "source_fragment_ids": ["f"], "confidence": 1.01}, "confidence"),
        (Alloy, {"alloy_id": "a", "cell_id": "c", "theme": "theme", "summary": "summary", "source_trace_ids": ["t"], "confidence": -0.01}, "confidence"),
        (Alloy, {"alloy_id": "a", "cell_id": "c", "theme": "theme", "summary": "summary", "source_trace_ids": ["t"], "confidence": 1.01}, "confidence"),
        (Outcome, {"outcome_id": "o", "cell_id": "c", "loadout_id": "l", "task_id": "task", "verdict": "success", "score": -0.01}, "score"),
        (Outcome, {"outcome_id": "o", "cell_id": "c", "loadout_id": "l", "task_id": "task", "verdict": "success", "score": 1.01}, "score"),
    ],
)
def test_confidence_like_values_must_be_between_zero_and_one(model_type, payload, field_name):
    with pytest.raises(ValueError, match=field_name):
        model_type.from_dict(payload)


def test_unknown_fields_are_rejected():
    payload = {"source_id": "s", "cell_id": "c", "kind": "note", "sha256": "h", "captured_at": "t", "extra": True}

    with pytest.raises(ValueError, match="extra"):
        Source.from_dict(payload)


def test_trace_schema_accepts_active_learning_kind_and_status():
    trace = Trace.from_dict(
        {
            "trace_id": "trace-active",
            "cell_id": "cell-alpha",
            "statement": "Record when a Charge acts as a caution.",
            "source_fragment_ids": ["frag-001"],
            "kind": "failure_signature",
            "status": "isolation_candidate",
        }
    )

    assert trace.kind == "failure_signature"
    assert trace.status == "isolation_candidate"


def test_outcome_schema_records_misses_and_non_application():
    outcome = Outcome.from_dict(
        {
            "outcome_id": "outcome-active",
            "cell_id": "cell-alpha",
            "loadout_id": "loadout-active",
            "task_id": "task-active",
            "verdict": "partial",
            "trace_ids": ["trace-used"],
            "ignored_charge_ids": ["trace-ignored"],
            "ignored_caution_ids": ["trace-caution"],
            "contradicted_charge_ids": ["trace-contradicted"],
            "over_retrieved_charge_ids": ["trace-over"],
            "pack_misses": ["missing boundary condition"],
        }
    )

    assert outcome.ignored_charge_ids == ["trace-ignored"]
    assert outcome.ignored_caution_ids == ["trace-caution"]
    assert outcome.contradicted_charge_ids == ["trace-contradicted"]
    assert outcome.over_retrieved_charge_ids == ["trace-over"]
    assert outcome.pack_misses == ["missing boundary condition"]


def test_canonical_models_serialize_canonical_fields_and_read_legacy_aliases():
    evidence = Evidence.from_dict({"source_id": "src-1", "cell_id": "c", "kind": "note", "sha256": "h", "captured_at": "t"})
    assert evidence.evidence_id == "src-1"
    assert "source_id" not in evidence.to_dict()
    assert evidence.to_dict()["evidence_id"] == "src-1"

    candidate = Candidate.from_dict({
        "fragment_id": "frag-1",
        "source_id": "src-1",
        "cell_id": "c",
        "kind": "lesson",
        "text": "Use evidence.",
        "source_excerpt": "excerpt",
        "boundary_status": "pending",
    })
    assert candidate.candidate_id == "frag-1"
    assert candidate.evidence_id == "src-1"
    assert candidate.evidence_excerpt == "excerpt"
    assert candidate.regulator_status == "pending"
    assert "fragment_id" not in candidate.to_dict()

    memory = Memory.from_dict({"trace_id": "trace-1", "cell_id": "c", "statement": "statement", "source_fragment_ids": ["frag-1"]})
    assert memory.memory_id == "trace-1"
    assert memory.candidate_ids == ["frag-1"]
    assert "trace_id" not in memory.to_dict()

    pattern = Pattern.from_dict({"alloy_id": "alloy-1", "cell_id": "c", "theme": "theme", "summary": "summary", "source_trace_ids": ["trace-1"]})
    assert pattern.pattern_id == "alloy-1"
    assert pattern.memory_ids == ["trace-1"]

    rule = RuleProposal.from_dict({"doctrine_id": "rule-1", "source_alloy_ids": ["alloy-1"], "scope": "cell", "statement": "rule", "review_status": "pending"})
    assert rule.rule_id == "rule-1"
    assert rule.pattern_ids == ["alloy-1"]

    pack = Pack.from_dict({"loadout_id": "loadout-1", "cell_id": "c", "trace_ids": ["trace-1"], "alloy_ids": ["alloy-1"], "doctrine_ids": ["rule-1"], "trust_label": "reviewed", "generated_at": "t"})
    assert pack.pack_id == "loadout-1"
    assert pack.memory_ids == ["trace-1"]

    feedback = Feedback.from_dict({"outcome_id": "outcome-1", "cell_id": "c", "loadout_id": "loadout-1", "task_id": "task", "verdict": "success", "trace_ids": ["trace-1"], "ignored_charge_ids": ["old"]})
    assert feedback.feedback_id == "outcome-1"
    assert feedback.pack_id == "loadout-1"
    assert feedback.memory_ids == ["trace-1"]
    assert feedback.ignored_memory_ids == ["old"]


def test_legacy_models_remain_importable_and_round_trip_old_fields():
    legacy_source = Source(source_id="src", cell_id="c", kind="note", sha256="h", captured_at="t")
    legacy_fragment = Fragment(fragment_id="frag", source_id="src", cell_id="c", kind="lesson", text="text")
    legacy_trace = Trace(trace_id="trace", cell_id="c", statement="statement", source_fragment_ids=["frag"])
    legacy_alloy = Alloy(alloy_id="alloy", cell_id="c", theme="theme", summary="summary", source_trace_ids=["trace"])
    legacy_rule = DoctrineProposal(doctrine_id="rule", source_alloy_ids=["alloy"], scope="cell", statement="rule")
    legacy_pack = Loadout(loadout_id="pack", cell_id="c", trace_ids=["trace"], alloy_ids=["alloy"], doctrine_ids=["rule"], trust_label="reviewed", generated_at="t")
    legacy_feedback = Outcome(outcome_id="feedback", cell_id="c", loadout_id="pack", task_id="task", verdict="success")
    for item in [legacy_source, legacy_fragment, legacy_trace, legacy_alloy, legacy_rule, legacy_pack, legacy_feedback]:
        assert_round_trips(item)


def test_trace_accepts_memory_type_round_trip():
    trace = Trace.from_dict({
        "trace_id": "trace-memory-type",
        "cell_id": "cell-alpha",
        "statement": "Keep reviewed workflow memory typed.",
        "source_fragment_ids": ["frag-1"],
        "kind": "workflow",
        "memory_type": "procedural",
    })

    assert trace.memory_type == "procedural"
    assert Trace.from_dict(trace.to_dict()) == trace


def test_trace_infers_legacy_memory_type_when_absent():
    trace = Trace.from_dict({
        "trace_id": "trace-legacy-type",
        "cell_id": "cell-alpha",
        "statement": "Legacy preference record.",
        "source_fragment_ids": ["frag-1"],
        "kind": "preference",
    })

    assert trace.memory_type == "semantic"
