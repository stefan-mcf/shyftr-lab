"""Tests for RI-9 runtime proposal export contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from shyftr.integrations.proposals import (
    EXPORTABLE_REVIEW_STATUSES,
    RUNTIME_PROPOSAL_TYPES,
    RuntimeProposal,
    append_runtime_proposal,
    export_runtime_proposals,
    proposal_from_evidence,
    read_runtime_proposals,
    runtime_proposals_ledger_path,
)
from shyftr.layout import init_cell


def _cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "proposal-cell")


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "shyftr.cli", *args],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_runtime_proposal_contract_fields_are_serialized() -> None:
    proposal = RuntimeProposal(
        proposal_id="prop-runtime-001",
        proposal_type="routing_hint",
        target_external_system="runtime-alpha",
        target_external_scope="team-a",
        target_external_refs=[{"kind": "task", "id": "task-1"}],
        recommendation="Prefer a verification-heavy lane for similar jobs.",
        evidence_charge_ids=["charge-1"],
        evidence_pulse_ids=["pulse-1"],
        confidence=0.72,
        review_status="pending",
        created_timestamp="2026-04-25T00:00:00+00:00",
        metadata={"source": "signal-pattern"},
    )

    payload = proposal.to_dict()
    assert payload == RuntimeProposal.from_dict(payload).to_dict()
    assert payload["proposal_id"] == "prop-runtime-001"
    assert payload["proposal_type"] == "routing_hint"
    assert payload["target_external_system"] == "runtime-alpha"
    assert payload["target_external_scope"] == "team-a"
    assert payload["target_external_refs"] == [{"kind": "task", "id": "task-1"}]
    assert payload["recommendation"].startswith("Prefer")
    assert payload["evidence_charge_ids"] == ["charge-1"]
    assert payload["evidence_pulse_ids"] == ["pulse-1"]
    assert payload["confidence"] == 0.72
    assert payload["review_status"] == "pending"
    assert payload["created_timestamp"] == "2026-04-25T00:00:00+00:00"


@pytest.mark.parametrize("proposal_type", RUNTIME_PROPOSAL_TYPES)
def test_required_proposal_types_are_supported(proposal_type: str) -> None:
    proposal = RuntimeProposal(
        proposal_id=f"prop-{proposal_type}",
        proposal_type=proposal_type,
        target_external_system="runtime-alpha",
        target_external_scope="team-a",
        recommendation=f"Advisory recommendation for {proposal_type}.",
    )
    assert proposal.proposal_type == proposal_type


def test_invalid_proposals_fail_fast() -> None:
    with pytest.raises(ValueError, match="proposal_type"):
        RuntimeProposal(
            proposal_id="prop-bad",
            proposal_type="direct_policy_mutation",
            target_external_system="runtime-alpha",
            target_external_scope="team-a",
            recommendation="Mutate policy directly.",
        )
    with pytest.raises(ValueError, match="confidence"):
        RuntimeProposal(
            proposal_id="prop-confidence",
            proposal_type="verification_hint",
            target_external_system="runtime-alpha",
            target_external_scope="team-a",
            recommendation="Check evidence first.",
            confidence=1.5,
        )
    with pytest.raises(ValueError, match="review_status"):
        RuntimeProposal(
            proposal_id="prop-status",
            proposal_type="verification_hint",
            target_external_system="runtime-alpha",
            target_external_scope="team-a",
            recommendation="Check evidence first.",
            review_status="auto_applied",
        )


def test_append_and_read_runtime_proposals_filters_by_system_and_review_status(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    pending = proposal_from_evidence(
        proposal_id="prop-pending",
        proposal_type="memory_application_hint",
        target_external_system="runtime-alpha",
        target_external_scope="project-a",
        recommendation="Apply Charge charge-1 before similar work.",
        evidence_charge_ids=["charge-1"],
        evidence_pulse_ids=["pulse-1"],
        confidence=0.81,
    )
    accepted = RuntimeProposal(
        proposal_id="prop-accepted",
        proposal_type="retry_caution",
        target_external_system="runtime-alpha",
        target_external_scope="project-a",
        recommendation="Retry only after reviewing failure evidence.",
        review_status="accepted",
    )
    other_system = RuntimeProposal(
        proposal_id="prop-other-system",
        proposal_type="verification_hint",
        target_external_system="runtime-beta",
        target_external_scope="project-b",
        recommendation="Verify independent evidence.",
    )

    append_runtime_proposal(cell, pending)
    append_runtime_proposal(cell, accepted)
    append_runtime_proposal(cell, other_system)

    assert runtime_proposals_ledger_path(cell).exists()
    proposals = read_runtime_proposals(cell, external_system="runtime-alpha")
    assert [proposal.proposal_id for proposal in proposals] == ["prop-pending"]
    assert EXPORTABLE_REVIEW_STATUSES == ("pending", "deferred")


def test_export_runtime_proposals_is_advisory_and_does_not_mutate_external_policy(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    policy_file = tmp_path / "runtime-policy.json"
    policy_file.write_text('{"worker":"stable"}\n', encoding="utf-8")
    append_runtime_proposal(
        cell,
        RuntimeProposal(
            proposal_id="prop-policy-candidate",
            proposal_type="policy_change_candidate",
            target_external_system="runtime-alpha",
            target_external_scope="project-a",
            target_external_refs=[{"kind": "policy_file", "path": str(policy_file)}],
            recommendation="Consider lowering automatic retry concurrency.",
            evidence_pulse_ids=["pulse-policy-1"],
            confidence=0.64,
        ),
    )

    payload = export_runtime_proposals(cell, external_system="runtime-alpha")

    assert payload["contract"] == "shyftr.runtime_proposals.v1"
    assert payload["advisory_only"] is True
    assert payload["requires_external_review"] is True
    assert payload["mutates_external_runtime"] is False
    assert payload["proposal_count"] == 1
    assert payload["proposals"][0]["proposal_id"] == "prop-policy-candidate"
    assert json.loads(policy_file.read_text(encoding="utf-8")) == {"worker": "stable"}


def test_export_runtime_proposals_can_write_relative_export_under_cell(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_runtime_proposal(
        cell,
        RuntimeProposal(
            proposal_id="prop-file-export",
            proposal_type="missing_memory_candidate",
            target_external_system="runtime-alpha",
            target_external_scope="project-a",
            recommendation="Capture missing verification guidance as a reviewed Charge.",
            evidence_pulse_ids=["pulse-gap-1"],
        ),
    )

    payload = export_runtime_proposals(
        cell,
        external_system="runtime-alpha",
        output_path="runtime-alpha-proposals.json",
    )

    export_path = Path(payload["export_path"])
    assert export_path == cell / "exports" / "proposals" / "runtime-alpha-proposals.json"
    written = json.loads(export_path.read_text(encoding="utf-8"))
    assert written["proposal_count"] == 1


def test_cli_proposals_export_outputs_json(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_runtime_proposal(
        cell,
        RuntimeProposal(
            proposal_id="prop-cli-export",
            proposal_type="verification_hint",
            target_external_system="runtime-alpha",
            target_external_scope="project-a",
            recommendation="Verify the build result before applying memory updates.",
            evidence_charge_ids=["charge-cli"],
            evidence_pulse_ids=["pulse-cli"],
        ),
    )

    result = _cli(
        "proposals",
        "export",
        "--cell",
        str(cell),
        "--external-system",
        "runtime-alpha",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["contract"] == "shyftr.runtime_proposals.v1"
    assert payload["proposal_count"] == 1
    assert payload["proposals"][0]["proposal_id"] == "prop-cli-export"


def test_cli_proposals_export_requires_existing_cell(tmp_path: Path) -> None:
    result = _cli(
        "proposals",
        "export",
        "--cell",
        str(tmp_path / "missing-cell"),
        "--external-system",
        "runtime-alpha",
        "--json",
    )
    assert result.returncode != 0
    assert "not a directory" in result.stderr
