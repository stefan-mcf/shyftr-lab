from __future__ import annotations

from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.live_context import (
    LiveContextCaptureRequest,
    SessionHarvestRequest,
    capture_live_context,
    harvest_session,
    live_context_metrics,
)


def _capture(cell: Path, *, kind: str, content: str, retention: str = "session", sensitivity: str = "public", confidence: float = 0.8) -> str:
    result = capture_live_context(
        LiveContextCaptureRequest(
            cell_path=str(cell),
            runtime_id="synthetic-runtime",
            session_id="synthetic-session",
            task_id="synthetic-task",
            entry_kind=kind,
            content=content,
            source_ref="synthetic:session-closeout",
            retention_hint=retention,
            sensitivity_hint=sensitivity,
            metadata={"confidence": confidence},
            write=True,
        )
    )
    return result["entry"]["entry_id"]


def test_session_harvest_classifies_each_bucket_and_writes_review_gated_outputs(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")

    _capture(live_cell, kind="active_plan", content="Discard scratch plan after the session.", retention="ephemeral")
    _capture(live_cell, kind="active_artifact", content="Archive internal scratch artifact only.", retention="session", sensitivity="private")
    _capture(live_cell, kind="failure", content="Context pack missed the current verification output.")
    _capture(live_cell, kind="decision", content="Runtime compaction remains runtime-owned.", retention="candidate")
    _capture(live_cell, kind="verification", content="Public durable verification can be written when local policy allows it.", retention="durable", confidence=0.95)
    _capture(live_cell, kind="recovery", content="Reusable recovery steps should become a skill proposal.", retention="skill")

    report = harvest_session(
        SessionHarvestRequest(
            live_cell_path=str(live_cell),
            continuity_cell_path=str(continuity_cell),
            memory_cell_path=str(memory_cell),
            runtime_id="synthetic-runtime",
            session_id="synthetic-session",
            write=True,
            allow_direct_durable_memory=True,
        )
    )

    assert report.status == "ok"
    assert report.review_gated is True
    assert report.bucket_counts["discard"] == 1
    assert report.bucket_counts["archive"] == 1
    assert report.bucket_counts["continuity_feedback"] == 1
    assert report.bucket_counts["memory_candidate"] == 1
    assert report.bucket_counts["direct_durable_memory"] == 1
    assert report.bucket_counts["skill_proposal"] == 1
    assert report.direct_durable_memory_writes == 0

    proposals = [record for _, record in read_jsonl(live_cell / "ledger" / "session_harvest_proposals.jsonl")]
    assert {proposal["bucket"] for proposal in proposals} == {
        "continuity_feedback",
        "memory_candidate",
        "direct_durable_memory",
        "skill_proposal",
    }
    assert all(proposal["review_gated"] is True for proposal in proposals)
    assert (memory_cell / "ledger" / "memories" / "approved.jsonl").read_text(encoding="utf-8") == ""

    continuity_feedback = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_feedback.jsonl")]
    assert len(continuity_feedback) == 1
    assert continuity_feedback[0]["event_type"] == "session_harvest_continuity_feedback"

    metrics = live_context_metrics(live_cell, runtime_id="synthetic-runtime", session_id="synthetic-session")
    assert metrics["harvest_bucket_counts"]["skill_proposal"] == 1
    assert metrics["memory_proposal_count"] == 1
    assert metrics["continuity_improvement_proposal_count"] == 1


def test_session_harvest_is_idempotent_and_direct_durable_defaults_to_proposal(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    _capture(live_cell, kind="verification", content="Review high-confidence durable facts unless local policy permits direct write.", retention="durable", confidence=0.99)

    request = SessionHarvestRequest(
        live_cell_path=str(live_cell),
        continuity_cell_path=str(continuity_cell),
        memory_cell_path=str(memory_cell),
        runtime_id="synthetic-runtime",
        session_id="synthetic-session",
        write=True,
    )
    first = harvest_session(request)
    second = harvest_session(request)

    assert first.bucket_counts["memory_candidate"] == 1
    assert first.bucket_counts["direct_durable_memory"] == 0
    assert second.harvest_id == first.harvest_id
    assert len([record for _, record in read_jsonl(live_cell / "ledger" / "session_harvests.jsonl")]) == 1
    assert len([record for _, record in read_jsonl(live_cell / "ledger" / "session_harvest_proposals.jsonl")]) == 1


def test_session_harvest_dry_run_does_not_write_ledgers(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    _capture(live_cell, kind="open_question", content="Should missing continuity feedback become a proposal?")

    report = harvest_session(
        SessionHarvestRequest(
            live_cell_path=str(live_cell),
            continuity_cell_path=str(continuity_cell),
            memory_cell_path=str(memory_cell),
            runtime_id="synthetic-runtime",
            session_id="synthetic-session",
            write=False,
        )
    )

    assert report.status == "dry_run"
    assert report.continuity_improvement_proposal_count == 1
    assert (live_cell / "ledger" / "session_harvests.jsonl").read_text(encoding="utf-8") == ""
    assert (live_cell / "ledger" / "session_harvest_proposals.jsonl").read_text(encoding="utf-8") == ""
