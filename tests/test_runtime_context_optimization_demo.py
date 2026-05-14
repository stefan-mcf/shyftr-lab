from __future__ import annotations

import json
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.live_context import (
    LiveContextCaptureRequest,
    LiveContextPackRequest,
    SessionHarvestRequest,
    build_live_context_pack,
    capture_live_context,
    harvest_session,
    live_context_metrics,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "integrations" / "runtime-context-optimization"


def test_synthetic_runtime_context_optimization_demo_flow(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "demo-live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "demo-continuity", cell_type="continuity")
    memory_cell = init_cell(tmp_path, "demo-memory", cell_type="memory")

    for kind, content, retention in [
        ("active_goal", "Complete a runtime-neutral context optimization demo.", "session"),
        ("constraint", "Do not use real transcript fixtures or runtime profile data.", "candidate"),
        ("failure", "A pack that repeats current prompt text wastes prompt budget.", "session"),
        ("verification", "Synthetic pytest coverage proves capture, pack, and harvest behavior.", "durable"),
    ]:
        capture_live_context(
            LiveContextCaptureRequest(
                cell_path=str(live_cell),
                runtime_id="synthetic-runtime",
                session_id="demo-session",
                task_id="demo-task",
                entry_kind=kind,
                content=content,
                source_ref="synthetic:runtime-context-optimization-demo",
                retention_hint=retention,
                sensitivity_hint="public",
                write=True,
            )
        )

    pack = build_live_context_pack(
        LiveContextPackRequest(
            cell_path=str(live_cell),
            runtime_id="synthetic-runtime",
            session_id="demo-session",
            query="context optimization prompt budget verification",
            max_items=3,
            max_tokens=80,
            current_prompt_excerpts=["Complete a runtime-neutral context optimization demo."],
            write=True,
        )
    )
    assert pack.advisory_only is True
    assert pack.duplicate_suppression_count == 1
    assert 1 <= pack.total_items <= 3

    harvest = harvest_session(
        SessionHarvestRequest(
            live_cell_path=str(live_cell),
            continuity_cell_path=str(continuity_cell),
            memory_cell_path=str(memory_cell),
            runtime_id="synthetic-runtime",
            session_id="demo-session",
            write=True,
        )
    )
    assert harvest.review_gated is True
    assert harvest.memory_proposal_count >= 1
    assert harvest.continuity_improvement_proposal_count >= 1

    metrics = live_context_metrics(live_cell, runtime_id="synthetic-runtime", session_id="demo-session")
    assert metrics["pack_item_count"] == pack.total_items
    assert metrics["duplicate_suppression_count"] == 1
    assert metrics["harvest_bucket_counts"]["memory_candidate"] >= 1


def test_runtime_context_optimization_examples_are_synthetic_and_contract_shaped() -> None:
    live_rows = [json.loads(line) for line in (EXAMPLES_DIR / "live_context.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    closeout = json.loads((EXAMPLES_DIR / "session_closeout.json").read_text(encoding="utf-8"))

    assert live_rows
    assert all(row["source_ref"].startswith("synthetic:") for row in live_rows)
    assert {row["sensitivity_hint"] for row in live_rows} == {"public"}
    assert closeout["contract"] == "shyftr.runtime_context_optimization.session_closeout.v1"
    assert closeout["real_runtime_profile_touched"] is False
    assert closeout["review_gated"] is True
