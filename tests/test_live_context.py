from __future__ import annotations

from pathlib import Path

import pytest

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.live_context import (
    LiveContextCaptureRequest,
    LiveContextPackRequest,
    capture_live_context,
    build_live_context_pack,
    live_context_metrics,
    live_context_status,
)


def test_live_context_layout_ledgers_are_seeded_and_idempotent(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "live", cell_type="live_context")
    expected = [
        "ledger/live_context_events.jsonl",
        "ledger/live_context_entries.jsonl",
        "ledger/live_context_packs.jsonl",
        "ledger/session_harvests.jsonl",
        "ledger/session_harvest_proposals.jsonl",
    ]
    for relative in expected:
        assert (cell / relative).is_file()

    (cell / "ledger" / "live_context_entries.jsonl").write_text('{"entry_id":"existing"}\n', encoding="utf-8")
    init_cell(tmp_path, "live", cell_type="live_context")
    assert "existing" in (cell / "ledger" / "live_context_entries.jsonl").read_text(encoding="utf-8")


def test_capture_is_append_only_deduped_and_does_not_touch_memory_ledgers(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "live", cell_type="live_context")
    request = LiveContextCaptureRequest(
        cell_path=str(cell),
        runtime_id="runtime",
        session_id="session",
        task_id="task",
        entry_kind="decision",
        content="Keep the runtime compactor owned by the runtime.",
        source_ref="synthetic:test",
        retention_hint="candidate",
        sensitivity_hint="public",
        write=True,
    )

    first = capture_live_context(request)
    second = capture_live_context(request)

    assert first["status"] == "ok"
    assert first["deduped"] is False
    assert second["deduped"] is True
    rows = [record for _, record in read_jsonl(cell / "ledger" / "live_context_entries.jsonl")]
    assert len(rows) == 1
    assert rows[0]["entry_kind"] == "decision"
    assert (cell / "ledger" / "memories" / "approved.jsonl").read_text(encoding="utf-8") == ""


def test_capture_dry_run_does_not_write(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "live", cell_type="live_context")
    result = capture_live_context(
        LiveContextCaptureRequest(
            cell_path=str(cell),
            runtime_id="runtime",
            session_id="session",
            task_id="task",
            entry_kind="active_goal",
            content="Finish the public-safe synthetic work slice.",
            source_ref="synthetic:test",
            write=False,
        )
    )
    assert result["status"] == "dry_run"
    assert (cell / "ledger" / "live_context_entries.jsonl").read_text(encoding="utf-8") == ""


def test_live_context_pack_is_bounded_advisory_and_suppresses_duplicates(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "live", cell_type="live_context")
    entries = [
        ("constraint", "Do not claim numeric context-window expansion.", "candidate", {}),
        ("active_plan", "Implement context optimization with bounded packs.", "session", {}),
        ("failure", "Previous pack included stale runtime configuration.", "session", {"stale": True}),
        ("open_question", "Should the session harvest propose a skill update?", "session", {}),
    ]
    for kind, content, retention, metadata in entries:
        capture_live_context(
            LiveContextCaptureRequest(
                cell_path=str(cell),
                runtime_id="runtime",
                session_id="session",
                task_id="task",
                entry_kind=kind,
                content=content,
                source_ref="synthetic:test",
                retention_hint=retention,
                sensitivity_hint="public",
                metadata=metadata,
                write=True,
            )
        )

    pack = build_live_context_pack(
        LiveContextPackRequest(
            cell_path=str(cell),
            runtime_id="runtime",
            session_id="session",
            query="context optimization bounded pack runtime",
            max_items=2,
            max_tokens=30,
            current_prompt_excerpts=["Implement context optimization with bounded packs."],
            write=True,
        )
    )

    assert pack.advisory_only is True
    assert pack.total_items <= 2
    assert pack.total_tokens <= 30
    assert pack.duplicate_suppression_count == 1
    assert pack.stale_suppression_count == 1
    assert all(item["provenance"]["entry_id"] for item in pack.items)
    assert {item["role"] for item in pack.items} <= {"guidance", "current_state", "caution", "open_question"}
    metrics = live_context_metrics(cell)
    assert metrics["pack_item_count"] == pack.total_items
    assert metrics["duplicate_suppression_count"] == 1
    assert live_context_status(cell)["counts"]["packs"] == 1


def test_public_sensitive_content_guard(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "live", cell_type="live_context")
    with pytest.raises(ValueError, match="sensitive"):
        LiveContextCaptureRequest(
            cell_path=str(cell),
            runtime_id="runtime",
            session_id="session",
            task_id="task",
            entry_kind="active_artifact",
            content="password=abc123",
            source_ref="synthetic:test",
            sensitivity_hint="public",
        )



def test_live_context_readers_tolerate_missing_alpha_ledgers(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "legacy", cell_type="memory")

    assert live_context_status(cell)["counts"] == {
        "entries": 0,
        "packs": 0,
        "harvests": 0,
        "harvest_proposals": 0,
    }
    metrics = live_context_metrics(cell)
    assert metrics["pack_item_count"] == 0
    assert metrics["harvest_bucket_counts"]["memory_candidate"] == 0
