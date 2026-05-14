from __future__ import annotations

from shyftr.evolution import propose_candidate_split


def test_long_multi_topic_candidate_emits_split_proposal() -> None:
    text = """# Runtime adapters
Adapters should be validated with synthetic files before pilots. The operator records evidence and keeps ledgers append-only.

# Garden irrigation
Irrigation schedules depend on soil moisture, weather, and pump flow. This subject is unrelated to runtime adapter verification.
"""
    proposal = propose_candidate_split({"candidate_id": "cand-1", "evidence_id": "ev-1", "text": text}, max_chars=120)
    assert proposal is not None
    assert proposal["proposal_type"] == "split_candidate"
    assert proposal["candidate_ids"] == ["cand-1"]
    assert proposal["evidence_refs"] == ["ev-1"]
    assert proposal["auto_apply"] is False
    assert len(proposal["proposed_children"]) >= 2


def test_short_single_topic_candidate_emits_no_split_proposal() -> None:
    proposal = propose_candidate_split({"candidate_id": "cand-2", "evidence_id": "ev-2", "text": "Always run the alpha gate before tester outreach."})
    assert proposal is None
