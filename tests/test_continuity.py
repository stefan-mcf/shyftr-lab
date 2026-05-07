from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from shyftr.continuity import (
    ContinuityFeedback,
    ContinuityPackRequest,
    assemble_continuity_pack,
    evaluate_synthetic_continuity,
    record_continuity_feedback,
)
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.provider.memory import remember


def _seed_memory(cell: Path) -> list[str]:
    first = remember(
        cell,
        "Projects using runtime context compression should keep operator decisions in a continuity pack.",
        "workflow",
        metadata={"actor": "test", "tags": ["continuity", "compression"]},
    )
    second = remember(
        cell,
        "Runtime continuity packs must not promote transient task queues into durable memory.",
        "constraint",
        metadata={"actor": "test", "tags": ["continuity", "safety"]},
    )
    return [first.memory_id, second.memory_id]


def test_continuity_pack_is_bounded_trust_labeled_and_writes_ledgers(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    memory_ids = _seed_memory(memory_cell)

    request = ContinuityPackRequest(
        memory_cell_path=str(memory_cell),
        continuity_cell_path=str(continuity_cell),
        runtime_id="synthetic-runtime",
        session_id="session-1",
        compaction_id="cmp-1",
        query="runtime context compression continuity pack",
        trigger="token_pressure",
        mode="advisory",
        max_items=2,
        max_tokens=40,
        write=True,
    )
    pack = assemble_continuity_pack(request)

    assert pack.status == "ok"
    assert pack.mode == "advisory"
    assert pack.total_items <= 2
    assert pack.total_tokens <= 40
    assert pack.source_memory_cell_id == "memory-cell"
    assert pack.continuity_cell_id == "continuity-cell"
    assert all(item.memory_id in memory_ids for item in pack.items)
    assert all(item.trust_tier in {"trace", "doctrine", "alloy", "fragment"} for item in pack.items)
    assert all(item.continuity_role in {"preserve", "caution", "background", "conflict"} for item in pack.items)
    assert pack.safety["authority"] == "advisory"
    assert pack.safety["mechanical_compression_owner"] == "runtime"

    event_rows = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_events.jsonl")]
    pack_rows = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_packs.jsonl")]
    assert event_rows[-1]["event_type"] == "continuity_pack_requested"
    assert pack_rows[-1]["continuity_pack_id"] == pack.continuity_pack_id


def test_continuity_pack_shadow_mode_does_not_export_items(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    _seed_memory(memory_cell)

    pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="synthetic-runtime",
            session_id="session-2",
            compaction_id="cmp-2",
            query="runtime context compression",
            mode="shadow",
            max_items=5,
            max_tokens=200,
            write=True,
        )
    )

    assert pack.mode == "shadow"
    assert pack.items == []
    assert pack.diagnostics["shadow_candidate_count"] > 0
    assert pack.safety["exported_to_runtime"] is False


def test_continuity_feedback_records_helpful_harmful_missing_and_promotion_proposals(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    memory_ids = _seed_memory(memory_cell)
    pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="synthetic-runtime",
            session_id="session-3",
            compaction_id="cmp-3",
            query="runtime context compression continuity pack",
            mode="advisory",
            max_items=2,
            max_tokens=80,
            write=True,
        )
    )

    feedback = record_continuity_feedback(
        ContinuityFeedback(
            continuity_cell_path=str(continuity_cell),
            continuity_pack_id=pack.continuity_pack_id,
            runtime_id="synthetic-runtime",
            session_id="session-3",
            compaction_id="cmp-3",
            result="resumed_successfully",
            useful_memory_ids=[memory_ids[0]],
            harmful_memory_ids=[memory_ids[1]],
            missing_notes=["Need adapter-specific resume hook documentation."],
            promote_notes=["Runtime continuity cells should stay separate from durable memory cells."],
            write=True,
        )
    )

    assert feedback["status"] == "ok"
    assert feedback["write"] is True
    assert feedback["promotion_proposals"] == 1
    rows = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_feedback.jsonl")]
    assert rows[-1]["continuity_pack_id"] == pack.continuity_pack_id
    proposal_rows = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_promotion_proposals.jsonl")]
    assert proposal_rows[-1]["statement"] == "Runtime continuity cells should stay separate from durable memory cells."
    assert proposal_rows[-1]["status"] == "proposed"


def test_continuity_feedback_dry_run_does_not_write(tmp_path: Path) -> None:
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    result = record_continuity_feedback(
        ContinuityFeedback(
            continuity_cell_path=str(continuity_cell),
            continuity_pack_id="cp-test",
            runtime_id="runtime",
            session_id="session",
            compaction_id="cmp",
            result="preview",
            missing_notes=["missing"],
            write=False,
        )
    )
    assert result["status"] == "dry_run"
    assert [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_feedback.jsonl")] == []


def test_continuity_pack_uses_query_text_to_select_relevant_memory(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    remember(
        memory_cell,
        "Generic autonomous execution preference should not outrank a specific compactor memory for a compactor query.",
        "preference",
        metadata={"actor": "test"},
    )
    specific = remember(
        memory_cell,
        "Hermes ShyftR compactor uses on_pre_compress to inject an advisory continuity pack.",
        "tool_quirk",
        metadata={"actor": "test"},
    )

    pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="synthetic-runtime",
            session_id="query-sensitive-session",
            compaction_id="query-sensitive-cmp",
            query="Hermes ShyftR compactor on_pre_compress advisory continuity",
            mode="advisory",
            max_items=1,
            max_tokens=80,
            write=False,
        )
    )

    assert [item.memory_id for item in pack.items] == [specific.memory_id]
    assert "on_pre_compress" in pack.items[0].statement
    assert pack.items[0].provenance["score_trace"]["sparse"] > 0



def test_synthetic_continuity_evaluation_reports_thresholds(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    _seed_memory(memory_cell)

    result = evaluate_synthetic_continuity(
        memory_cell_path=str(memory_cell),
        continuity_cell_path=str(continuity_cell),
        runtime_id="synthetic-runtime",
        task_id="eval-1",
        query="runtime context compression continuity pack",
        expected_terms=["runtime", "continuity"],
        max_items=3,
        max_tokens=120,
        write=True,
    )

    assert result["status"] in {"pass", "fail"}
    assert result["coverage"] >= 1.0
    assert result["noise_count"] == 0
    assert result["pack"]["total_items"] > 0
    rows = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_eval_reports.jsonl")]
    assert rows[-1]["task_id"] == "eval-1"


def test_continuity_cli_pack_feedback_and_eval(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    memory_ids = _seed_memory(memory_cell)

    pack_cmd = [
        sys.executable,
        "-m",
        "shyftr.cli",
        "continuity",
        "pack",
        str(memory_cell),
        str(continuity_cell),
        "runtime context compression continuity pack",
        "--runtime-id",
        "cli-runtime",
        "--session-id",
        "cli-session",
        "--compaction-id",
        "cli-cmp",
        "--mode",
        "advisory",
        "--max-items",
        "2",
        "--max-tokens",
        "80",
        "--write",
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    pack_result = subprocess.run(pack_cmd, cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True, env=env)
    pack_payload = json.loads(pack_result.stdout)
    assert pack_payload["status"] == "ok"
    assert pack_payload["mode"] == "advisory"

    feedback_cmd = [
        sys.executable,
        "-m",
        "shyftr.cli",
        "continuity",
        "feedback",
        str(continuity_cell),
        pack_payload["continuity_pack_id"],
        "resumed_successfully",
        "--runtime-id",
        "cli-runtime",
        "--session-id",
        "cli-session",
        "--compaction-id",
        "cli-cmp",
        "--useful",
        memory_ids[0],
        "--promote-note",
        "Continuity pack feedback should remain review-gated.",
        "--write",
    ]
    feedback_result = subprocess.run(feedback_cmd, cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True, env=env)
    assert json.loads(feedback_result.stdout)["status"] == "ok"

    eval_cmd = [
        sys.executable,
        "-m",
        "shyftr.cli",
        "continuity",
        "eval",
        str(memory_cell),
        str(continuity_cell),
        "runtime context compression continuity pack",
        "--expected-term",
        "runtime",
        "--expected-term",
        "continuity",
        "--runtime-id",
        "cli-runtime",
        "--task-id",
        "eval-cli",
        "--write",
    ]
    eval_result = subprocess.run(eval_cmd, cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True, env=env)
    assert json.loads(eval_result.stdout)["status"] == "pass"


def test_invalid_continuity_mode_and_authority_are_rejected(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory-cell", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity-cell", cell_type="continuity")
    with pytest.raises(ValueError, match="mode"):
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="runtime",
            session_id="session",
            compaction_id="cmp",
            query="query",
            mode="authority",
        )
    with pytest.raises(ValueError, match="max_items"):
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id="runtime",
            session_id="session",
            compaction_id="cmp",
            query="query",
            max_items=1000,
        )
