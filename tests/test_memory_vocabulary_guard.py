from __future__ import annotations

from dataclasses import asdict

from scripts import audit_memory_vocabulary
from shyftr.models import canonical_memory_id, with_canonical_memory_id
from shyftr.provider.memory import RememberResult, SearchResult


def test_audit_has_no_user_facing_memory_vocabulary_matches():
    matches = audit_memory_vocabulary.scan()
    user_facing = [m for m in matches if m.classification == "must_fix_user_facing"]
    assert user_facing == []


def test_canonical_memory_id_prefers_memory_id_and_accepts_compatibility_input():
    assert canonical_memory_id({"memory_id": "mem-1", "trace_id": "old-1"}) == "mem-1"
    assert canonical_memory_id({"trace_id": "old-1"}) == "old-1"
    assert canonical_memory_id({"charge_id": "old-2"}) == "old-2"


def test_public_memory_id_projection_strips_compatibility_fields_by_default():
    payload = with_canonical_memory_id({"trace_id": "old-1", "charge_id": "old-2", "statement": "x"})
    assert payload == {"memory_id": "old-2", "statement": "x"}
    compat = with_canonical_memory_id({"trace_id": "old-1", "statement": "x"}, include_compat=True)
    assert compat["memory_id"] == "old-1"
    assert compat["trace_id"] == "old-1"


def test_provider_result_public_dicts_use_memory_id():
    remembered = RememberResult(memory_id="mem-1", evidence_id="ev-1", candidate_id="cand-1", status="approved")
    searched = SearchResult(memory_id="mem-1", statement="x", trust_tier="memory", kind="preference", confidence=0.8, score=1.0)
    assert asdict(remembered)["memory_id"] == "mem-1"
    assert asdict(searched)["memory_id"] == "mem-1"
    assert "charge_id" not in asdict(remembered)
    assert "charge_id" not in asdict(searched)
