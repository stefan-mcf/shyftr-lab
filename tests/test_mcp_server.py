from __future__ import annotations

import json
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.mcp_server import (
    _handle_json_rpc_message,
    shyftr_carry_feedback_bridge,
    shyftr_carry_pack_bridge,
    shyftr_carry_status_bridge,
    shyftr_continuity_feedback_bridge,
    shyftr_continuity_pack_bridge,
    shyftr_continuity_status_bridge,
    shyftr_live_context_capture_bridge,
    shyftr_live_context_pack_bridge,
    shyftr_live_context_checkpoint_bridge,
    shyftr_live_context_resume_bridge,
    shyftr_live_context_status_bridge,
    shyftr_session_harvest_bridge,
    shyftr_pack_bridge,
    shyftr_profile_bridge,
    shyftr_record_feedback_bridge,
    shyftr_remember_bridge,
    shyftr_search_bridge,
    tool_names,
)
from shyftr.live_context import reconstruct_resume_state
from shyftr.provider.memory import remember


def test_tool_names_are_stable() -> None:
    assert tool_names() == (
        "shyftr_search",
        "shyftr_pack",
        "shyftr_profile",
        "shyftr_remember",
        "shyftr_record_feedback",
        "shyftr_carry_pack",
        "shyftr_carry_feedback",
        "shyftr_carry_status",
        "shyftr_continuity_pack",
        "shyftr_continuity_feedback",
        "shyftr_continuity_status",
        "shyftr_live_context_capture",
        "shyftr_live_context_pack",
        "shyftr_live_context_checkpoint",
        "shyftr_live_context_resume",
        "shyftr_session_harvest",
        "shyftr_live_context_status",
        "shyftr_episode_capture",
        "shyftr_episode_search",
    )


def test_search_and_profile_return_public_memory_ids(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "User prefers concise terminal updates.", "preference")

    search_result = shyftr_search_bridge({"cell_path": str(cell), "query": "concise updates"})
    assert search_result["status"] == "ok"
    assert search_result["results"][0]["memory_id"] == remembered.charge_id
    assert "charge_id" not in search_result["results"][0]

    profile_result = shyftr_profile_bridge({"cell_path": str(cell), "max_tokens": 100})
    assert profile_result["status"] == "ok"
    assert profile_result["source_memory_ids"] == [remembered.charge_id]


def test_pack_defaults_to_dry_run_without_retrieval_log(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "Use pytest before publishing Python changes.", "workflow")

    result = shyftr_pack_bridge(
        {"cell_path": str(cell), "query": "pytest publishing", "task_id": "task-1"}
    )

    assert result["status"] == "ok"
    assert result["write"] is False
    assert result["selected_memory_ids"] == [remembered.charge_id]
    assert result["items"][0]["memory_id"] == remembered.charge_id
    assert (cell / "ledger" / "retrieval_logs.jsonl").read_text(encoding="utf-8") == ""


def test_remember_requires_explicit_write(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "core", cell_type="user")

    preview = shyftr_remember_bridge(
        {"cell_path": str(cell), "statement": "User prefers local-first memory.", "kind": "preference"}
    )
    assert preview["status"] == "dry_run"
    assert not (cell / "traces" / "approved.jsonl").read_text(encoding="utf-8")

    committed = shyftr_remember_bridge(
        {
            "cell_path": str(cell),
            "statement": "User prefers local-first memory.",
            "kind": "preference",
            "write": True,
        }
    )
    assert committed["status"] == "approved"
    assert committed["memory_id"].startswith("trace-")


def test_feedback_requires_explicit_write(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "core", cell_type="user")
    preview = shyftr_record_feedback_bridge(
        {"cell_path": str(cell), "pack_id": "pack-1", "result": "success"}
    )
    assert preview["status"] == "dry_run"
    assert preview["write"] is False


def test_json_rpc_fallback_lists_and_calls_tools(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "core", cell_type="user")
    remember(cell, "User prefers concise terminal updates.", "preference")

    listed = _handle_json_rpc_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    assert {tool["name"] for tool in listed["result"]["tools"]} == set(tool_names())
    episode_capture_tool = [tool for tool in listed["result"]["tools"] if tool["name"] == "shyftr_episode_capture"][0]
    assert episode_capture_tool["inputSchema"]["required"] == ["cell_path", "episode_id"]

    called = _handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "shyftr_search",
                "arguments": {"cell_path": str(cell), "query": "concise"},
            },
        }
    )
    assert called is not None
    payload = json.loads(called["result"]["content"][0]["text"])
    assert payload["results"][0]["memory_id"].startswith("trace-")


def test_continuity_mcp_bridges_are_dry_run_by_default_and_write_when_requested(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    remembered = remember(memory_cell, "Runtime context compression should request a continuity pack before trimming.", "workflow")

    preview = shyftr_continuity_pack_bridge(
        {
            "memory_cell_path": str(memory_cell),
            "continuity_cell_path": str(continuity_cell),
            "query": "context compression continuity",
            "session_id": "session",
            "compaction_id": "cmp",
            "mode": "advisory",
            "max_items": 2,
            "max_tokens": 80,
        }
    )
    assert preview["status"] == "ok"
    assert preview["write"] is False
    assert preview["items"][0]["memory_id"] == remembered.memory_id
    assert (continuity_cell / "ledger" / "continuity_packs.jsonl").read_text(encoding="utf-8") == ""

    committed = shyftr_continuity_pack_bridge(
        {
            "memory_cell_path": str(memory_cell),
            "continuity_cell_path": str(continuity_cell),
            "query": "context compression continuity",
            "session_id": "session",
            "compaction_id": "cmp",
            "mode": "advisory",
            "max_items": 2,
            "max_tokens": 80,
            "write": True,
        }
    )
    assert committed["write"] is True
    assert committed["continuity_pack_id"].startswith("continuity-pack-")

    feedback_preview = shyftr_continuity_feedback_bridge(
        {
            "continuity_cell_path": str(continuity_cell),
            "continuity_pack_id": committed["continuity_pack_id"],
            "result": "resumed_successfully",
            "session_id": "session",
            "compaction_id": "cmp",
            "useful_memory_ids": [remembered.memory_id],
        }
    )
    assert feedback_preview["status"] == "dry_run"
    feedback_written = shyftr_continuity_feedback_bridge(
        {
            "continuity_cell_path": str(continuity_cell),
            "continuity_pack_id": committed["continuity_pack_id"],
            "result": "resumed_successfully",
            "session_id": "session",
            "compaction_id": "cmp",
            "useful_memory_ids": [remembered.memory_id],
            "promote_notes": ["Continuity feedback promotions remain review-gated."],
            "write": True,
        }
    )
    assert feedback_written["status"] == "ok"
    status = shyftr_continuity_status_bridge({"continuity_cell_path": str(continuity_cell)})
    assert status["counts"]["packs"] == 1
    assert status["counts"]["feedback"] == 1
    assert status["counts"]["promotion_proposals"] == 1


def test_carry_mcp_bridges_are_operator_aliases_for_continuity(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    carry_cell = init_cell(tmp_path, "carry", cell_type="continuity")
    remembered = remember(memory_cell, "Carry packs preserve context compression decisions.", "workflow")

    pack = shyftr_carry_pack_bridge(
        {
            "memory_cell_path": str(memory_cell),
            "carry_cell_path": str(carry_cell),
            "query": "carry context compression decisions",
            "session_id": "session",
            "compaction_id": "cmp",
            "mode": "advisory",
            "max_items": 2,
            "max_tokens": 80,
            "write": True,
        }
    )
    assert pack["tool"] == "shyftr_carry_pack"
    assert pack["status"] == "ok"
    assert pack["items"][0]["memory_id"] == remembered.memory_id

    feedback = shyftr_carry_feedback_bridge(
        {
            "carry_cell_path": str(carry_cell),
            "carry_pack_id": pack["continuity_pack_id"],
            "result": "resumed_successfully",
            "session_id": "session",
            "compaction_id": "cmp",
            "useful_memory_ids": [remembered.memory_id],
            "write": True,
        }
    )
    assert feedback["tool"] == "shyftr_carry_feedback"
    assert feedback["status"] == "ok"

    status = shyftr_carry_status_bridge({"carry_cell_path": str(carry_cell)})
    assert status["tool"] == "shyftr_carry_status"
    assert status["counts"]["packs"] == 1
    assert status["counts"]["feedback"] == 1


def test_json_rpc_fallback_can_call_continuity_pack(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    remember(memory_cell, "Use continuity packs for context compression boundaries.", "workflow")

    called = _handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "shyftr_continuity_pack",
                "arguments": {
                    "memory_cell_path": str(memory_cell),
                    "continuity_cell_path": str(continuity_cell),
                    "query": "context compression continuity",
                    "session_id": "session",
                    "compaction_id": "cmp",
                    "mode": "advisory",
                },
            },
        }
    )
    assert called is not None
    payload = json.loads(called["result"]["content"][0]["text"])
    assert payload["tool"] == "shyftr_continuity_pack"
    assert payload["status"] == "ok"



def test_json_rpc_fallback_can_call_carry_pack(tmp_path: Path) -> None:
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    carry_cell = init_cell(tmp_path, "carry", cell_type="continuity")
    remember(memory_cell, "Use carry packs for context compression events.", "workflow")

    called = _handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": 33,
            "method": "tools/call",
            "params": {
                "name": "shyftr_carry_pack",
                "arguments": {
                    "memory_cell_path": str(memory_cell),
                    "carry_cell_path": str(carry_cell),
                    "query": "context compression carry",
                    "session_id": "session",
                    "compaction_id": "cmp",
                    "mode": "advisory",
                },
            },
        }
    )
    assert called is not None
    payload = json.loads(called["result"]["content"][0]["text"])
    assert payload["tool"] == "shyftr_carry_pack"
    assert payload["status"] == "ok"


def test_live_context_mcp_bridges_are_dry_run_by_default_and_write_when_requested(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")

    preview = shyftr_live_context_capture_bridge(
        {
            "cell_path": str(live_cell),
            "session_id": "session",
            "entry_kind": "decision",
            "content": "Prefer bounded live context packs before prompt trimming.",
        }
    )
    assert preview["status"] == "dry_run"
    assert (live_cell / "ledger" / "live_context_entries.jsonl").read_text(encoding="utf-8") == ""

    committed = shyftr_live_context_capture_bridge(
        {
            "cell_path": str(live_cell),
            "session_id": "session",
            "entry_kind": "goal",
            "content": "Prefer bounded live context packs before prompt trimming.",
            "status": "active",
            "related_entry_ids": ["external-ref"],
            "confidence": 0.9,
            "evidence_refs": ["docs/plan.md"],
            "grounding_refs": ["tests/test_mcp_server.py"],
            "write": True,
        }
    )
    assert committed["status"] == "ok"
    assert committed["entry"]["entry_id"].startswith("live-entry-")
    assert committed["entry"]["entry_kind"] == "goal"
    assert committed["entry"]["status"] == "active"
    assert committed["entry"]["related_entry_ids"] == ["external-ref"]

    pack = shyftr_live_context_pack_bridge(
        {"cell_path": str(live_cell), "session_id": "session", "query": "bounded context", "write": True}
    )
    assert pack["status"] == "ok"
    assert pack["items"][0]["entry_id"] == committed["entry"]["entry_id"]

    checkpoint = shyftr_live_context_checkpoint_bridge(
        {"live_cell_path": str(live_cell), "continuity_cell_path": str(continuity_cell), "session_id": "session", "write": True}
    )
    assert checkpoint["status"] == "ok"
    assert checkpoint["checkpoint_id"].startswith("carry-state-checkpoint-")

    harvest = shyftr_session_harvest_bridge(
        {
            "live_cell_path": str(live_cell),
            "continuity_cell_path": str(continuity_cell),
            "memory_cell_path": str(memory_cell),
            "session_id": "session",
            "write": True,
        }
    )
    assert harvest["status"] == "ok"
    assert harvest["review_gated"] is True
    assert harvest["carry_state_checkpoint"]["checkpoint_id"].startswith("carry-state-checkpoint-")
    assert (
        harvest["memory_proposal_count"]
        + harvest["continuity_improvement_proposal_count"]
        + harvest["skill_proposal_count"]
    ) >= 1

    resume = shyftr_live_context_resume_bridge({"continuity_cell_path": str(continuity_cell), "session_id": "session"})
    assert resume["status"] == "ok"
    assert resume["validation"]["status"] == "ok"
    assert resume["sections"]["unresolved_goals"][0]["entry_id"] == committed["entry"]["entry_id"]

    status = shyftr_live_context_status_bridge({"cell_path": str(live_cell)})
    assert status["counts"]["entries"] == 1
    assert status["counts"]["packs"] == 1
    assert status["counts"]["harvests"] == 1


def test_json_rpc_fallback_can_call_live_context_pack(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    shyftr_live_context_capture_bridge(
        {
            "cell_path": str(live_cell),
            "session_id": "session",
            "entry_kind": "verification",
            "content": "Live context packs should be advisory not authoritative.",
            "write": True,
        }
    )

    called = _handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "shyftr_live_context_pack",
                "arguments": {"cell_path": str(live_cell), "query": "advisory", "session_id": "session"},
            },
        }
    )
    assert called is not None
    payload = json.loads(called["result"]["content"][0]["text"])
    assert payload["tool"] == "shyftr_live_context_pack"
    assert payload["status"] == "ok"
