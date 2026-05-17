from __future__ import annotations

from pathlib import Path

from shyftr.episodes import approve_episode, list_episode_rows
from shyftr.layout import init_cell
from shyftr.live_context import LiveContextCaptureRequest, SessionHarvestRequest, capture_live_context, harvest_session


def _capture(
    cell: Path,
    *,
    kind: str,
    content: str,
    status: str = "completed",
    retention: str = "archive",
    sensitivity: str = "internal",
    source_ref: str = "artifact://session",
) -> str:
    result = capture_live_context(
        LiveContextCaptureRequest(
            cell_path=str(cell),
            runtime_id="runtime-1",
            session_id="session-1",
            task_id="task-1",
            entry_kind=kind,
            content=content,
            source_ref=source_ref,
            retention_hint=retention,
            sensitivity_hint=sensitivity,
            status=status,
            grounding_refs=["grounding-1"],
            evidence_refs=["artifact-1"],
            write=True,
        )
    )
    return result["entry"]["entry_id"]


def _request(live_cell: Path, continuity_cell: Path, memory_cell: Path, *, write: bool = True) -> SessionHarvestRequest:
    return SessionHarvestRequest(
        live_cell_path=str(live_cell),
        continuity_cell_path=str(continuity_cell),
        memory_cell_path=str(memory_cell),
        runtime_id="runtime-1",
        session_id="session-1",
        write=write,
    )


def test_session_harvest_emits_review_gated_session_episode_proposal(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    entry_id = _capture(live_cell, kind="verification", content="Session finished with a verified artifact.")

    report = harvest_session(_request(live_cell, continuity_cell, memory_cell))

    assert report.episode_proposal_count == 1
    episodes = list_episode_rows(memory_cell)
    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.status == "proposed"
    assert episode.episode_kind == "session"
    assert episode.live_context_entry_ids == [entry_id]
    assert episode.grounding_refs == ["grounding-1"]
    assert episode.artifact_refs == ["artifact-1"]


def test_harvest_error_recovery_cluster_emits_incident_episode(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    _capture(live_cell, kind="error", content="Tool call failed with a deterministic error.", status="failed", sensitivity="private")
    _capture(live_cell, kind="recovery", content="Recovery reran the focused proof and passed.", status="completed")

    report = harvest_session(_request(live_cell, continuity_cell, memory_cell))

    assert report.episode_proposal_count == 2
    episodes = list_episode_rows(memory_cell)
    incident = [episode for episode in episodes if episode.episode_kind == "incident"][0]
    assert incident.status == "proposed"
    assert incident.outcome == "partial"
    assert incident.sensitivity == "private"
    assert len(incident.live_context_entry_ids) == 2


def test_harvest_blocked_session_emits_session_episode_proposal(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    blocked_id = _capture(live_cell, kind="goal", content="Session blocked waiting for external approval.", status="blocked", retention="session")

    report = harvest_session(_request(live_cell, continuity_cell, memory_cell))

    assert report.episode_proposal_count == 1
    episode = list_episode_rows(memory_cell)[0]
    assert episode.episode_kind == "session"
    assert episode.outcome == "blocked"
    assert episode.live_context_entry_ids == [blocked_id]


def test_harvest_recovered_session_outcome_is_success_with_separate_incident(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    _capture(live_cell, kind="error", content="Recoverable failure occurred.", status="failed")
    _capture(live_cell, kind="recovery", content="Recovery completed.", status="resolved")

    harvest_session(_request(live_cell, continuity_cell, memory_cell))

    episodes = list_episode_rows(memory_cell)
    session_episode = next(episode for episode in episodes if episode.episode_kind == "session")
    incident_episode = next(episode for episode in episodes if episode.episode_kind == "incident")
    assert session_episode.outcome == "success"
    assert incident_episode.outcome == "partial"


def test_harvest_does_not_emit_incident_episode_for_ephemeral_open_noise(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    _capture(live_cell, kind="error", content="Transient open error should not become incident history.", status="active", retention="ephemeral")
    _capture(live_cell, kind="recovery", content="Transient open recovery should not become incident history.", status="active", retention="ephemeral")

    report = harvest_session(_request(live_cell, continuity_cell, memory_cell))

    assert report.episode_proposal_count == 0
    assert list_episode_rows(memory_cell) == []


def test_harvest_dry_run_does_not_write_episode_proposals(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    _capture(live_cell, kind="verification", content="Dry-run should preview the episode proposal.")

    report = harvest_session(_request(live_cell, continuity_cell, memory_cell, write=False))

    assert report.episode_proposal_count == 1
    assert list_episode_rows(memory_cell) == []


def test_repeated_written_harvest_refreshes_episode_proposals(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    first_entry_id = _capture(live_cell, kind="verification", content="First persisted harvest entry.")

    harvest_session(_request(live_cell, continuity_cell, memory_cell))
    harvest_session(_request(live_cell, continuity_cell, memory_cell))
    assert len(list_episode_rows(memory_cell)) == 1

    second_entry_id = _capture(live_cell, kind="verification", content="Second persisted harvest entry.", source_ref="artifact://session-second")
    harvest_session(_request(live_cell, continuity_cell, memory_cell))

    episodes = list_episode_rows(memory_cell)
    assert len(episodes) == 2
    assert episodes[-1].live_context_entry_ids == [first_entry_id, second_entry_id]


def test_followup_harvest_skips_reproposal_after_episode_approval(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    _capture(live_cell, kind="verification", content="Reviewed harvest entry.")
    harvest_session(_request(live_cell, continuity_cell, memory_cell))
    proposed = list_episode_rows(memory_cell)[0]
    approved = proposed.__class__.from_dict(
        {
            **proposed.to_dict(),
            "title": proposed.title or "Reviewed session",
            "summary": proposed.summary or "Reviewed session summary.",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "actor": proposed.actor or "test",
            "action": proposed.action or "harvest",
            "outcome": proposed.outcome if proposed.outcome in {"success", "failure", "partial", "blocked", "unknown"} else "success",
            "status": "approved",
            "confidence": proposed.confidence or 0.8,
            "sensitivity": proposed.sensitivity or "internal",
        }
    )
    approve_episode(memory_cell, approved)
    _capture(live_cell, kind="open_question", content="Non-material follow-up note.", status="active", retention="ephemeral", source_ref="artifact://noise")

    harvest_session(_request(live_cell, continuity_cell, memory_cell))

    assert [episode.status for episode in list_episode_rows(memory_cell)].count("proposed") == 1
    assert [episode.status for episode in list_episode_rows(memory_cell)].count("approved") == 1
