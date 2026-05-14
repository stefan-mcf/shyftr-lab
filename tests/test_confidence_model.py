from pathlib import Path

from shyftr.confidence import ConfidenceState, confidence_from_feedback, project_confidence_state


def test_new_memory_has_high_uncertainty_and_scalar_compatibility() -> None:
    record = {"trace_id": "m1", "cell_id": "c", "statement": "Use typed APIs", "confidence": 0.5}
    projected = project_confidence_state(record)
    assert projected["confidence"] == 0.5
    assert projected["confidence_state"]["expected_confidence"] == 0.5
    assert projected["confidence_state"]["uncertainty"] > 0.3
    assert projected["confidence"] == record["confidence"]


def test_positive_feedback_increases_expected_confidence_and_reduces_uncertainty() -> None:
    before = ConfidenceState(prior=0.5).to_dict()
    after = confidence_from_feedback({"confidence": 0.5}, useful=4)
    assert after["expected_confidence"] > before["expected_confidence"]
    assert after["uncertainty"] < before["uncertainty"]
    assert after["positive_evidence_count"] == 4


def test_negative_feedback_decreases_expected_confidence_and_preserves_audit_fields() -> None:
    after = confidence_from_feedback({"confidence": 0.7, "success_count": 2}, harmful=3)
    assert after["expected_confidence"] < 0.7
    assert after["negative_evidence_count"] == 3
    assert after["public_baseline"] == "transparent_beta_binomial"
