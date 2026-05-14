from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from shyftr.continuity import ContinuityPackRequest, assemble_continuity_pack
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.live_context import (
    CarryStateCheckpointRequest,
    LiveContextCaptureRequest,
    build_carry_state_checkpoint,
    capture_live_context,
    reconstruct_resume_state,
)
from shyftr.provider.memory import remember


def _capture(
    cell: Path,
    *,
    kind: str,
    content: str,
    status: str | None = None,
    parent_entry_id: str | None = None,
    related_entry_ids: list[str] | None = None,
    valid_until: str | None = None,
    write: bool = True,
) -> str:
    result = capture_live_context(
        LiveContextCaptureRequest(
            cell_path=str(cell),
            runtime_id="runtime",
            session_id="session",
            task_id="task",
            entry_kind=kind,
            content=content,
            source_ref="synthetic:test",
            retention_hint="session",
            sensitivity_hint="public",
            status=status,
            parent_entry_id=parent_entry_id,
            related_entry_ids=related_entry_ids or [],
            valid_until=valid_until,
            confidence=0.9,
            write=write,
        )
    )
    return result["entry"]["entry_id"]


def test_checkpoint_shape_is_deterministic_bounded_and_written_when_requested(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")

    goal_id = _capture(live_cell, kind="goal", content="Land Phase 2 typed working context.")
    _capture(live_cell, kind="plan_step", content="Update tests before more implementation.", parent_entry_id=goal_id)
    _capture(live_cell, kind="open_question", content="Do carry checkpoints stay compact under token pressure?", related_entry_ids=[goal_id])
    _capture(live_cell, kind="constraint", content="Keep continuity advisory only.")
    _capture(live_cell, kind="artifact_ref", content="docs/status/phase-2-typed-working-context-preflight-inventory.md")

    checkpoint = build_carry_state_checkpoint(
        CarryStateCheckpointRequest(
            live_cell_path=str(live_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="runtime",
            session_id="session",
            max_items=4,
            max_tokens=60,
            write=True,
        )
    )

    payload = checkpoint.to_dict()
    assert list(payload["sections"].keys()) == [
        "unresolved_goals",
        "current_plan_steps",
        "open_loops",
        "commitments",
        "constraints",
        "active_assumptions",
        "recent_errors",
        "recent_recoveries",
        "artifact_refs",
        "cautions",
        "verification_results",
    ]
    assert checkpoint.total_items <= 4
    assert checkpoint.total_tokens <= 60
    assert checkpoint.advisory_only is True
    rows = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_checkpoints.jsonl")]
    assert rows[-1]["checkpoint_id"] == checkpoint.checkpoint_id
    assert rows[-1]["sections"] == payload["sections"]


def test_continuity_pack_merges_carry_state_and_memory_without_losing_memory_only_behavior(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    remembered = remember(memory_cell, "Durable memory still contributes to advisory continuity packs.", "workflow")

    no_carry = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="runtime",
            session_id="session-a",
            compaction_id="cmp-a",
            query="advisory continuity packs",
            mode="advisory",
            max_items=3,
            max_tokens=80,
            write=False,
        )
    )
    assert [item.memory_id for item in no_carry.items] == [remembered.memory_id]
    assert no_carry.diagnostics["carry_candidate_count"] == 0

    _capture(live_cell, kind="goal", content="Resume active implementation context for Phase 2.")
    _capture(live_cell, kind="error", content="Prior context was compacted before the active goal was recorded.", status="open")

    mixed = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            live_cell_path=str(live_cell),
            runtime_id="runtime",
            session_id="session",
            compaction_id="cmp",
            query="resume active implementation context",
            mode="advisory",
            max_items=5,
            max_tokens=140,
            write=True,
        )
    )

    assert mixed.status == "ok"
    assert mixed.safety["mechanical_compression_owner"] == "runtime"
    assert mixed.carry_state is not None
    assert mixed.diagnostics["carry_candidate_count"] > 0
    assert mixed.diagnostics["memory_candidate_count"] >= 1
    assert any(item.provenance.get("carry_state") for item in mixed.items)
    assert any(item.memory_id == remembered.memory_id for item in mixed.items)


def test_resume_state_reconstruction_flags_broken_and_expired_references(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")

    expired = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    goal_id = _capture(live_cell, kind="goal", content="Complete the final verification tranche.")
    _capture(
        live_cell,
        kind="plan_step",
        content="Run full tests and baseline comparison.",
        parent_entry_id=goal_id,
        valid_until=expired,
    )
    _capture(
        live_cell,
        kind="open_question",
        content="Does any resume item point at a missing parent?",
        parent_entry_id="missing-goal",
    )
    _capture(live_cell, kind="constraint", content="Do not widen public claims beyond tested behavior.")

    build_carry_state_checkpoint(
        CarryStateCheckpointRequest(
            live_cell_path=str(live_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="runtime",
            session_id="session",
            max_items=8,
            max_tokens=140,
            write=True,
        )
    )

    resume = reconstruct_resume_state(
        continuity_cell,
        runtime_id="runtime",
        session_id="session",
        max_items=8,
        max_tokens=140,
    )

    assert resume.total_items > 0
    assert resume.validation["broken_reference_count"] == 1
    assert resume.validation["expired_count"] == 1
    assert resume.validation["missing_state_count"] == 1
    assert resume.validation["wrong_state_count"] == 1
    assert resume.sections["unresolved_goals"][0]["entry_id"] == goal_id
    assert resume.advisory_only is True
