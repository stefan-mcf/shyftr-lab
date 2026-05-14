from __future__ import annotations

import pytest

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.policy import BoundaryPolicyError
from shyftr.provider.memory import MemoryProvider, search
from shyftr.provider.trusted import TrustedMemoryProvider, remember_trusted


def _records(path):
    return [record for _, record in read_jsonl(path)]


def _metadata(**overrides):
    data = {
        "actor": "reviewer-1",
        "trust_reason": "explicit user instruction",
        "pulse_channel": "cli",
        "created_at": "2026-04-30T03:00:00Z",
    }
    data.update(overrides)
    return data


def test_remember_trusted_promotes_preference_with_required_metadata_and_search(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    result = remember_trusted(
        cell,
        "User prefers concise terminal updates.",
        "preference",
        **_metadata(),
    )

    assert result.status == "approved"
    assert result.charge_id is not None
    assert result.charge_id.startswith("trace-")
    assert result.pulse_id.startswith("src-")
    assert result.spark_id.startswith("frag-")
    assert result.trusted_direct_promotion is True
    assert search(cell, "concise terminal", kinds=["preference"])[0].charge_id == result.charge_id

    sources = _records(cell / "ledger" / "sources.jsonl")
    fragments = _records(cell / "ledger" / "fragments.jsonl")
    reviews = _records(cell / "ledger" / "reviews.jsonl")
    promotions = _records(cell / "ledger" / "promotions.jsonl")
    traces = _records(cell / "traces" / "approved.jsonl")

    assert sources[0]["metadata"]["provider_api"] == "remember"
    assert sources[0]["metadata"]["operation_origin"] == "remember_trusted"
    assert sources[0]["metadata"]["actor"] == "reviewer-1"
    assert sources[0]["metadata"]["trust_reason"] == "explicit user instruction"
    assert sources[0]["metadata"]["pulse_channel"] == "cli"
    assert sources[0]["metadata"]["created_at"] == "2026-04-30T03:00:00Z"
    assert fragments[0]["source_id"] == result.pulse_id
    assert reviews[0]["candidate_id"] == result.spark_id
    assert reviews[0]["review_status"] == "approved"
    assert reviews[0]["metadata"]["regulator_decision"]["trusted_direct_promotion"] is True
    assert promotions[0]["source_id"] == result.pulse_id
    assert promotions[0]["source_fragment_ids"] == [result.spark_id]
    assert traces[0]["trace_id"] == result.charge_id
    assert traces[0]["source_fragment_ids"] == [result.spark_id]
    assert traces[0]["kind"] == "preference"


@pytest.mark.parametrize("kind", ["preference", "constraint", "workflow", "tool_quirk"])
def test_remember_trusted_supports_required_trusted_kinds(tmp_path, kind):
    cell = init_cell(tmp_path, "core", cell_type="user")

    result = remember_trusted(cell, f"Trusted {kind} memory for ShyftR tests.", kind, **_metadata())

    assert result.status == "approved"
    assert _records(cell / "traces" / "approved.jsonl")[-1]["kind"] == kind


@pytest.mark.parametrize("missing_field", ["actor", "trust_reason", "pulse_channel", "created_at"])
def test_remember_trusted_requires_metadata_before_ledger_write(tmp_path, missing_field):
    cell = init_cell(tmp_path, "core", cell_type="user")
    metadata = _metadata(**{missing_field: ""})

    with pytest.raises(ValueError, match=missing_field):
        remember_trusted(cell, "User prefers precise memory updates.", "preference", **metadata)

    assert _records(cell / "ledger" / "sources.jsonl") == []
    assert _records(cell / "ledger" / "fragments.jsonl") == []
    assert _records(cell / "traces" / "approved.jsonl") == []


def test_remember_trusted_rejects_unsupported_kind_before_ledger_write(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    with pytest.raises(ValueError, match="unsupported trusted memory kind"):
        remember_trusted(cell, "User likes unsupported memories.", "random_note", **_metadata())

    assert _records(cell / "ledger" / "sources.jsonl") == []


def test_remember_trusted_still_blocks_operational_state_pollution(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    with pytest.raises(BoundaryPolicyError):
        remember_trusted(
            cell,
            "Queue item dmq-1 is in_progress on branch task/dmq-1-fix.",
            "workflow",
            **_metadata(),
        )

    assert _records(cell / "ledger" / "sources.jsonl") == []
    assert _records(cell / "traces" / "approved.jsonl") == []


def test_remember_trusted_can_disable_direct_promotion_and_leave_pending_evidence(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    result = remember_trusted(
        cell,
        "User prefers explicit review for shared Rails.",
        "constraint",
        trusted_direct_promotion=False,
        **_metadata(trust_reason="operator wants review gate"),
    )

    assert result.status == "pending_review"
    assert result.charge_id is None
    assert result.trusted_direct_promotion is False
    sources = _records(cell / "ledger" / "sources.jsonl")
    fragments = _records(cell / "ledger" / "fragments.jsonl")
    assert sources[0]["metadata"]["trusted_direct_promotion"] is False
    assert fragments[0]["review_status"] == "pending"
    assert _records(cell / "ledger" / "reviews.jsonl") == []
    assert _records(cell / "ledger" / "promotions.jsonl") == []
    assert _records(cell / "traces" / "approved.jsonl") == []


def test_trusted_memory_provider_and_memory_provider_wrappers(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")

    trusted = TrustedMemoryProvider(cell, actor="reviewer-1", pulse_channel="cli")
    result = trusted.remember_trusted(
        "User prefers local-first Cells.",
        "preference",
        trust_reason="explicit profile preference",
        created_at="2026-04-30T03:00:00Z",
    )
    assert trusted.search("local-first")[0].charge_id == result.charge_id

    provider = MemoryProvider(cell)
    wrapped = provider.remember_trusted(
        "Use focused pytest before full pytest.",
        "workflow",
        actor="reviewer-1",
        trust_reason="explicit workflow preference",
        pulse_channel="cli",
        created_at="2026-04-30T03:01:00Z",
    )
    assert provider.search("focused pytest")[0].charge_id == wrapped.charge_id
