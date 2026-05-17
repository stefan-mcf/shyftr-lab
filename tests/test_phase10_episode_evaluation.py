from __future__ import annotations

from pathlib import Path

from shyftr.episodes import append_episode, approve_episode, make_episode, propose_episode
from shyftr.evaluation_bundle import build_bundle
from shyftr.layout import init_cell
from shyftr.models import Episode


def test_episode_evaluation_reports_empty_contract_coverage(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    bundle = build_bundle(cell, output_dir=tmp_path / "bundle", manifest_commands=[])
    coverage = bundle["episode_contract_coverage"]

    assert coverage["schema_version"] == "shyftr-episode-contract-coverage/v1"
    assert coverage["ledger_event_count"] == 0
    assert coverage["latest_episode_count"] == 0
    assert coverage["ledger_status_counts"] == {}
    assert coverage["latest_status_counts"] == {}
    assert coverage["anchor_completeness"] == {
        "latest_with_anchor": 0,
        "latest_missing_anchor": 0,
        "approved_with_anchor": 0,
        "approved_missing_anchor": 0,
    }
    assert coverage["task_success_lift"]["status"] == "unmeasured"


def test_episode_evaluation_counts_lifecycle_anchors_and_sensitivity(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    proposed = make_episode(
        cell,
        episode_id="episode-proposed",
        episode_kind="session",
        title="Proposed",
        summary="A proposed episode exists.",
        actor="test",
        action="observe",
        status="proposed",
        sensitivity="internal",
    )
    propose_episode(cell, proposed)

    approved = make_episode(
        cell,
        episode_id="episode-approved",
        episode_kind="incident",
        title="Approved",
        summary="An approved private episode exists.",
        actor="test",
        action="observe",
        outcome="success",
        status="approved",
        started_at="2026-05-16T00:00:00+00:00",
        ended_at="2026-05-16T00:10:00+00:00",
        sensitivity="private",
        live_context_entry_ids=["live-approved"],
    )
    approve_episode(cell, approved)

    archived = make_episode(
        cell,
        episode_id="episode-archived",
        episode_kind="tool_outcome",
        title="Archived",
        summary="An archived episode exists.",
        actor="test",
        action="observe",
        outcome="success",
        status="approved",
        started_at="2026-05-16T00:00:00+00:00",
        ended_at="2026-05-16T00:10:00+00:00",
        sensitivity="public",
        artifact_refs=["artifact://archived"],
    )
    approve_episode(cell, archived)
    append_episode(cell, Episode.from_dict({**archived.to_dict(), "status": "archived", "created_at": "2026-05-16T00:20:00+00:00"}))

    redacted = make_episode(
        cell,
        episode_id="episode-redacted",
        episode_kind="task",
        title="Redacted",
        summary="A secret redacted episode exists.",
        actor="test",
        action="observe",
        outcome="success",
        status="approved",
        started_at="2026-05-16T00:00:00+00:00",
        ended_at="2026-05-16T00:10:00+00:00",
        sensitivity="secret",
        grounding_refs=["grounding://redacted"],
    )
    approve_episode(cell, redacted)
    append_episode(cell, Episode.from_dict({**redacted.to_dict(), "status": "redacted", "created_at": "2026-05-16T00:21:00+00:00"}))

    bundle = build_bundle(cell, output_dir=tmp_path / "bundle", manifest_commands=[])
    coverage = bundle["episode_contract_coverage"]

    assert coverage["ledger_event_count"] == 6
    assert coverage["latest_episode_count"] == 4
    assert coverage["ledger_status_counts"] == {
        "approved": 3,
        "archived": 1,
        "proposed": 1,
        "redacted": 1,
    }
    assert coverage["latest_status_counts"] == {
        "approved": 1,
        "archived": 1,
        "proposed": 1,
        "redacted": 1,
    }
    assert coverage["latest_episode_kind_counts"] == {
        "incident": 1,
        "session": 1,
        "task": 1,
        "tool_outcome": 1,
    }
    assert coverage["latest_sensitivity_counts"] == {
        "internal": 1,
        "private": 1,
        "public": 1,
        "secret": 1,
    }
    assert coverage["anchor_completeness"] == {
        "latest_with_anchor": 3,
        "latest_missing_anchor": 1,
        "approved_with_anchor": 1,
        "approved_missing_anchor": 0,
    }
    assert coverage["privacy_posture"] == {
        "private_or_sensitive_latest": 2,
        "public_capsule_redaction_required": True,
    }
    assert coverage["task_success_lift"]["status"] == "unmeasured"
    assert any("task-success lift" in claim for claim in coverage["claims_not_allowed"])


def test_episode_evaluation_uses_latest_row_lifecycle_state(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    first = make_episode(
        cell,
        episode_id="episode-latest",
        episode_kind="session",
        title="Latest",
        summary="First proposed row.",
        actor="test",
        action="observe",
        status="proposed",
    )
    propose_episode(cell, first)
    second = Episode.from_dict({**first.to_dict(), "status": "approved", "started_at": "2026-05-16T00:00:00+00:00", "ended_at": "2026-05-16T00:10:00+00:00", "outcome": "success", "confidence": 0.8, "sensitivity": "internal", "live_context_entry_ids": ["live-latest"]})
    approve_episode(cell, second)

    coverage = build_bundle(cell, output_dir=tmp_path / "bundle", manifest_commands=[])["episode_contract_coverage"]

    assert coverage["ledger_event_count"] == 2
    assert coverage["latest_episode_count"] == 1
    assert coverage["ledger_status_counts"] == {"approved": 1, "proposed": 1}
    assert coverage["latest_status_counts"] == {"approved": 1}
    assert coverage["anchor_completeness"]["approved_missing_anchor"] == 0
