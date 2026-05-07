"""MCP bridge for ShyftR.

The bridge keeps ShyftR's ledger-first safety model intact. Read/pack tools
prefer dry-run behavior, while memory and feedback writes require an explicit
``write=True`` flag.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

from shyftr.pack import LoadoutTaskInput, assemble_loadout
from shyftr.provider.memory import profile, record_signal, remember, search

TOOL_NAMES = (
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
)

JsonArgs = str | bytes | bytearray | Mapping[str, Any]


def shyftr_search_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    cell_path = _require_cell_path(payload)
    query = _require_text(payload.get("query"), "query")
    items = search(
        cell_path,
        query,
        top_k=_bounded_int(payload.get("limit", 10), "limit", minimum=1, maximum=50),
        trust_tiers=_optional_str_list(payload.get("trust_tiers")),
        kinds=_optional_str_list(payload.get("kinds")),
        memory_types=_optional_str_list(payload.get("memory_types")),
    )
    return {
        "tool": "shyftr_search",
        "status": "ok",
        "cell_path": str(cell_path),
        "query": query,
        "results": [_search_result_to_public(item) for item in items],
    }


def shyftr_pack_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    cell_path = _require_cell_path(payload)
    query = _require_text(payload.get("query"), "query")
    task_id = _require_text(payload.get("task_id"), "task_id")
    write = bool(payload.get("write", False))
    runtime_id = str(payload.get("runtime_id") or "mcp")
    task = LoadoutTaskInput(
        cell_path=str(cell_path),
        query=query,
        task_id=task_id,
        runtime_id=runtime_id,
        max_items=_bounded_int(payload.get("max_items", 10), "max_items", minimum=0, maximum=50),
        max_tokens=_bounded_int(payload.get("max_tokens", 2000), "max_tokens", minimum=1, maximum=12000),
        dry_run=not write,
        include_fragments=bool(payload.get("include_candidates", False)),
        requested_trust_tiers=_optional_str_list(payload.get("trust_tiers")),
        query_kind=_optional_text(payload.get("kind")),
        query_tags=_optional_str_list(payload.get("tags")),
        retrieval_mode=str(payload.get("retrieval_mode") or "balanced"),
    )
    assembled = assemble_loadout(task)
    result = assembled.to_dict()
    return {
        "tool": "shyftr_pack",
        "status": "ok",
        "write": write,
        "cell_path": str(cell_path),
        "pack_id": result.get("loadout_id"),
        "task_id": result.get("task_id"),
        "total_items": result.get("total_items"),
        "total_tokens": result.get("total_tokens"),
        "selected_memory_ids": list(result.get("retrieval_log", {}).get("selected_ids", [])),
        "items": [_memory_item_to_public(item) for item in result.get("items", [])],
        "retrieval": _retrieval_to_public(result.get("retrieval_log", {})),
    }


def shyftr_profile_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    cell_path = _require_cell_path(payload)
    projected = profile(
        cell_path,
        max_tokens=_bounded_int(payload.get("max_tokens", 2000), "max_tokens", minimum=1, maximum=12000),
    )
    return {
        "tool": "shyftr_profile",
        "status": "ok",
        "cell_path": str(cell_path),
        "projection_id": projected.projection_id,
        "source_memory_ids": list(projected.source_charge_ids),
        "entry_count": len(projected.source_charge_ids),
        "markdown": projected.markdown,
        "compact_markdown": projected.compact_markdown,
    }


def shyftr_remember_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    cell_path = _require_cell_path(payload)
    statement = _require_text(payload.get("statement"), "statement")
    kind = _require_text(payload.get("kind"), "kind")
    write = bool(payload.get("write", False))
    metadata = _optional_mapping(payload.get("metadata"))
    actor = _optional_text(payload.get("actor"))
    if actor:
        metadata = dict(metadata or {})
        metadata.setdefault("actor", actor)
    if not write:
        return {
            "tool": "shyftr_remember",
            "status": "dry_run",
            "write": False,
            "cell_path": str(cell_path),
            "kind": kind,
            "statement_preview": statement[:240],
            "message": "No memory was written. Re-run with write=true to commit after reviewing the statement.",
        }
    result = remember(cell_path, statement, kind, metadata=metadata, memory_type=_optional_text(payload.get("memory_type")))
    return {
        "tool": "shyftr_remember",
        "status": result.status,
        "write": True,
        "cell_path": str(cell_path),
        "memory_id": result.charge_id,
        "source_id": result.pulse_id,
        "candidate_id": result.spark_id,
        "trust_tier": result.trust_tier,
        "memory_type": result.memory_type,
    }


def shyftr_record_feedback_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    cell_path = _require_cell_path(payload)
    pack_id = _require_text(payload.get("pack_id"), "pack_id")
    result = _require_text(payload.get("result"), "result")
    write = bool(payload.get("write", False))
    if not write:
        return {
            "tool": "shyftr_record_feedback",
            "status": "dry_run",
            "write": False,
            "cell_path": str(cell_path),
            "pack_id": pack_id,
            "result": result,
            "message": "No feedback was written. Re-run with write=true to commit after reviewing the payload.",
        }
    payload_result = record_signal(
        cell_path,
        pack_id,
        result=result,
        applied_charge_ids=_optional_str_list(payload.get("applied_memory_ids")),
        useful_charge_ids=_optional_str_list(payload.get("useful_memory_ids")),
        harmful_charge_ids=_optional_str_list(payload.get("harmful_memory_ids")),
        ignored_charge_ids=_optional_str_list(payload.get("ignored_memory_ids")),
        missing_memory_notes=_optional_str_list(payload.get("missing_memory_notes")),
        runtime_id=str(payload.get("runtime_id") or "mcp"),
        task_id=_optional_text(payload.get("task_id")),
    )
    return {
        "tool": "shyftr_record_feedback",
        "status": payload_result.get("status", "ok"),
        "write": True,
        "cell_path": str(cell_path),
        "feedback": _json_safe(payload_result),
    }




def _with_continuity_aliases(payload: Mapping[str, Any]) -> dict[str, Any]:
    mapped = dict(payload)
    if "continuity_cell_path" not in mapped and "carry_cell_path" in mapped:
        mapped["continuity_cell_path"] = mapped["carry_cell_path"]
    if "continuity_pack_id" not in mapped and "carry_pack_id" in mapped:
        mapped["continuity_pack_id"] = mapped["carry_pack_id"]
    return mapped

def shyftr_continuity_pack_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _with_continuity_aliases(_load_payload(args))
    from shyftr.continuity import ContinuityPackRequest, assemble_continuity_pack

    request = ContinuityPackRequest(
        memory_cell_path=str(_require_cell_path_named(payload, "memory_cell_path")),
        continuity_cell_path=str(_require_cell_path_named(payload, "continuity_cell_path")),
        runtime_id=str(payload.get("runtime_id") or "mcp"),
        session_id=_require_text(payload.get("session_id"), "session_id"),
        compaction_id=_require_text(payload.get("compaction_id"), "compaction_id"),
        query=_require_text(payload.get("query"), "query"),
        trigger=str(payload.get("trigger") or "context_pressure"),
        mode=str(payload.get("mode") or "shadow"),
        max_items=_bounded_int(payload.get("max_items", 8), "max_items", minimum=0, maximum=50),
        max_tokens=_bounded_int(payload.get("max_tokens", 1200), "max_tokens", minimum=1, maximum=12000),
        include_candidates=bool(payload.get("include_candidates", False)),
        retrieval_mode=str(payload.get("retrieval_mode") or "balanced"),
        live_cell_path=(str(_require_cell_path_named(payload, "live_cell_path")) if payload.get("live_cell_path") else None),
        write=bool(payload.get("write", False)),
        metadata=_optional_mapping(payload.get("metadata")) or {},
    )
    result = assemble_continuity_pack(request).to_dict()
    return {"tool": "shyftr_continuity_pack", "status": result.get("status"), "write": bool(payload.get("write", False)), **result}


def shyftr_continuity_feedback_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _with_continuity_aliases(_load_payload(args))
    from shyftr.continuity import ContinuityFeedback, record_continuity_feedback

    feedback = ContinuityFeedback(
        continuity_cell_path=str(_require_cell_path_named(payload, "continuity_cell_path")),
        continuity_pack_id=_require_text(payload.get("continuity_pack_id"), "continuity_pack_id"),
        runtime_id=str(payload.get("runtime_id") or "mcp"),
        session_id=_require_text(payload.get("session_id"), "session_id"),
        compaction_id=_require_text(payload.get("compaction_id"), "compaction_id"),
        result=_require_text(payload.get("result"), "result"),
        useful_memory_ids=_optional_str_list(payload.get("useful_memory_ids")) or [],
        harmful_memory_ids=_optional_str_list(payload.get("harmful_memory_ids")) or [],
        ignored_memory_ids=_optional_str_list(payload.get("ignored_memory_ids")) or [],
        missing_notes=_optional_str_list(payload.get("missing_notes")) or [],
        promote_notes=_optional_str_list(payload.get("promote_notes")) or [],
        write=bool(payload.get("write", False)),
        metadata=_optional_mapping(payload.get("metadata")) or {},
    )
    return {"tool": "shyftr_continuity_feedback", **record_continuity_feedback(feedback)}


def shyftr_continuity_status_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _with_continuity_aliases(_load_payload(args))
    from shyftr.continuity import continuity_status

    return {"tool": "shyftr_continuity_status", **continuity_status(_require_cell_path_named(payload, "continuity_cell_path"))}






def shyftr_carry_pack_bridge(args: JsonArgs) -> dict[str, Any]:
    result = shyftr_continuity_pack_bridge(args)
    return {**result, "tool": "shyftr_carry_pack"}


def shyftr_carry_feedback_bridge(args: JsonArgs) -> dict[str, Any]:
    result = shyftr_continuity_feedback_bridge(args)
    return {**result, "tool": "shyftr_carry_feedback"}


def shyftr_carry_status_bridge(args: JsonArgs) -> dict[str, Any]:
    result = shyftr_continuity_status_bridge(args)
    return {**result, "tool": "shyftr_carry_status"}

def shyftr_live_context_capture_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    from shyftr.live_context import LiveContextCaptureRequest, capture_live_context

    request = LiveContextCaptureRequest(
        cell_path=str(_require_cell_path_named(payload, "cell_path")),
        runtime_id=str(payload.get("runtime_id") or "mcp"),
        session_id=_require_text(payload.get("session_id"), "session_id"),
        task_id=str(payload.get("task_id") or "default-task"),
        entry_kind=_require_text(payload.get("entry_kind") or payload.get("kind"), "entry_kind"),
        content=_require_text(payload.get("content"), "content"),
        source_ref=str(payload.get("source_ref") or "mcp"),
        retention_hint=str(payload.get("retention_hint") or "session"),
        sensitivity_hint=str(payload.get("sensitivity_hint") or "internal"),
        status=_optional_text(payload.get("status")),
        scope=str(payload.get("scope") or "session"),
        parent_entry_id=_optional_text(payload.get("parent_entry_id")),
        related_entry_ids=_optional_str_list(payload.get("related_entry_ids")) or [],
        confidence=(float(payload["confidence"]) if payload.get("confidence") is not None else None),
        evidence_refs=_optional_str_list(payload.get("evidence_refs")) or [],
        grounding_refs=_optional_str_list(payload.get("grounding_refs")) or [],
        valid_until=_optional_text(payload.get("valid_until")),
        metadata=_optional_mapping(payload.get("metadata")) or {},
        write=bool(payload.get("write", False)),
    )
    return {"tool": "shyftr_live_context_capture", **capture_live_context(request)}


def shyftr_live_context_pack_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    from shyftr.live_context import LiveContextPackRequest, build_live_context_pack

    request = LiveContextPackRequest(
        cell_path=str(_require_cell_path_named(payload, "cell_path")),
        query=_require_text(payload.get("query"), "query"),
        runtime_id=str(payload.get("runtime_id") or "mcp"),
        session_id=_require_text(payload.get("session_id"), "session_id"),
        max_items=_bounded_int(payload.get("max_items", 8), "max_items", minimum=0, maximum=100),
        max_tokens=_bounded_int(payload.get("max_tokens", 1200), "max_tokens", minimum=1, maximum=12000),
        suppress_entry_ids=_optional_str_list(payload.get("suppress_entry_ids")) or [],
        current_prompt_excerpts=_optional_str_list(payload.get("current_prompt_excerpts")) or [],
        metadata=_optional_mapping(payload.get("metadata")) or {},
        write=bool(payload.get("write", False)),
    )
    return {"tool": "shyftr_live_context_pack", "status": "ok", "write": bool(payload.get("write", False)), **build_live_context_pack(request).to_dict()}


def shyftr_live_context_checkpoint_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    from shyftr.live_context import CarryStateCheckpointRequest, build_carry_state_checkpoint

    request = CarryStateCheckpointRequest(
        live_cell_path=str(_require_cell_path_named(payload, "live_cell_path")),
        continuity_cell_path=str(_require_cell_path_named(payload, "continuity_cell_path")),
        runtime_id=str(payload.get("runtime_id") or "mcp"),
        session_id=_require_text(payload.get("session_id"), "session_id"),
        max_items=_bounded_int(payload.get("max_items", 8), "max_items", minimum=0, maximum=100),
        max_tokens=_bounded_int(payload.get("max_tokens", 1200), "max_tokens", minimum=1, maximum=12000),
        write=bool(payload.get("write", False)),
        metadata=_optional_mapping(payload.get("metadata")) or {},
    )
    return {"tool": "shyftr_live_context_checkpoint", "status": "ok", "write": bool(payload.get("write", False)), **build_carry_state_checkpoint(request).to_dict()}


def shyftr_live_context_resume_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    from shyftr.live_context import reconstruct_resume_state

    return {
        "tool": "shyftr_live_context_resume",
        "status": "ok",
        **reconstruct_resume_state(
            _require_cell_path_named(payload, "continuity_cell_path"),
            runtime_id=str(payload.get("runtime_id") or "mcp"),
            session_id=_require_text(payload.get("session_id"), "session_id"),
            max_items=_bounded_int(payload.get("max_items", 8), "max_items", minimum=0, maximum=100),
            max_tokens=_bounded_int(payload.get("max_tokens", 1200), "max_tokens", minimum=1, maximum=12000),
        ).to_dict(),
    }


def shyftr_session_harvest_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    from shyftr.live_context import SessionHarvestRequest, harvest_session

    request = SessionHarvestRequest(
        live_cell_path=str(_require_cell_path_named(payload, "live_cell_path")),
        continuity_cell_path=str(_require_cell_path_named(payload, "continuity_cell_path")),
        memory_cell_path=str(_require_cell_path_named(payload, "memory_cell_path")),
        runtime_id=str(payload.get("runtime_id") or "mcp"),
        session_id=_require_text(payload.get("session_id"), "session_id"),
        write=bool(payload.get("write", False)),
        allow_direct_durable_memory=bool(payload.get("allow_direct_durable_memory", False)),
        metadata=_optional_mapping(payload.get("metadata")) or {},
    )
    return {"tool": "shyftr_session_harvest", **harvest_session(request).to_dict()}


def shyftr_live_context_status_bridge(args: JsonArgs) -> dict[str, Any]:
    payload = _load_payload(args)
    from shyftr.live_context import live_context_status

    return {"tool": "shyftr_live_context_status", **live_context_status(_require_cell_path_named(payload, "cell_path"))}


def create_mcp_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError("ShyftR MCP bridge requires optional package 'mcp'.") from exc

    server = FastMCP("shyftr")

    @server.tool(name="shyftr_search")
    def shyftr_search_tool(
        cell_path: str,
        query: str,
        limit: int = 10,
        trust_tiers: list[str] | None = None,
        kinds: list[str] | None = None,
        memory_types: list[str] | None = None,
    ) -> dict[str, Any]:
        return shyftr_search_bridge(
            {"cell_path": cell_path, "query": query, "limit": limit, "trust_tiers": trust_tiers, "kinds": kinds, "memory_types": memory_types}
        )

    @server.tool(name="shyftr_pack")
    def shyftr_pack_tool(
        cell_path: str,
        query: str,
        task_id: str,
        runtime_id: str = "mcp",
        max_items: int = 10,
        max_tokens: int = 2000,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_pack_bridge(
            {
                "cell_path": cell_path,
                "query": query,
                "task_id": task_id,
                "runtime_id": runtime_id,
                "max_items": max_items,
                "max_tokens": max_tokens,
                "write": write,
            }
        )

    @server.tool(name="shyftr_profile")
    def shyftr_profile_tool(cell_path: str, max_tokens: int = 2000) -> dict[str, Any]:
        return shyftr_profile_bridge({"cell_path": cell_path, "max_tokens": max_tokens})

    @server.tool(name="shyftr_remember")
    def shyftr_remember_tool(
        cell_path: str,
        statement: str,
        kind: str,
        actor: str | None = None,
        memory_type: str | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_remember_bridge(
            {"cell_path": cell_path, "statement": statement, "kind": kind, "actor": actor, "memory_type": memory_type, "write": write}
        )

    @server.tool(name="shyftr_record_feedback")
    def shyftr_record_feedback_tool(
        cell_path: str,
        pack_id: str,
        result: str,
        runtime_id: str = "mcp",
        task_id: str | None = None,
        applied_memory_ids: list[str] | None = None,
        useful_memory_ids: list[str] | None = None,
        harmful_memory_ids: list[str] | None = None,
        ignored_memory_ids: list[str] | None = None,
        missing_memory_notes: list[str] | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_record_feedback_bridge(
            {
                "cell_path": cell_path,
                "pack_id": pack_id,
                "result": result,
                "runtime_id": runtime_id,
                "task_id": task_id,
                "applied_memory_ids": applied_memory_ids,
                "useful_memory_ids": useful_memory_ids,
                "harmful_memory_ids": harmful_memory_ids,
                "ignored_memory_ids": ignored_memory_ids,
                "missing_memory_notes": missing_memory_notes,
                "write": write,
            }
        )

    @server.tool(name="shyftr_continuity_pack")
    def shyftr_continuity_pack_tool(
        memory_cell_path: str,
        continuity_cell_path: str,
        query: str,
        session_id: str,
        compaction_id: str,
        runtime_id: str = "mcp",
        trigger: str = "context_pressure",
        mode: str = "shadow",
        max_items: int = 8,
        max_tokens: int = 1200,
        live_cell_path: str | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_continuity_pack_bridge(
            {
                "memory_cell_path": memory_cell_path,
                "continuity_cell_path": continuity_cell_path,
                "query": query,
                "session_id": session_id,
                "compaction_id": compaction_id,
                "runtime_id": runtime_id,
                "trigger": trigger,
                "mode": mode,
                "max_items": max_items,
                "max_tokens": max_tokens,
                "live_cell_path": live_cell_path,
                "write": write,
            }
        )

    @server.tool(name="shyftr_continuity_feedback")
    def shyftr_continuity_feedback_tool(
        continuity_cell_path: str,
        continuity_pack_id: str,
        result: str,
        session_id: str,
        compaction_id: str,
        runtime_id: str = "mcp",
        useful_memory_ids: list[str] | None = None,
        harmful_memory_ids: list[str] | None = None,
        ignored_memory_ids: list[str] | None = None,
        missing_notes: list[str] | None = None,
        promote_notes: list[str] | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_continuity_feedback_bridge(
            {
                "continuity_cell_path": continuity_cell_path,
                "continuity_pack_id": continuity_pack_id,
                "result": result,
                "session_id": session_id,
                "compaction_id": compaction_id,
                "runtime_id": runtime_id,
                "useful_memory_ids": useful_memory_ids,
                "harmful_memory_ids": harmful_memory_ids,
                "ignored_memory_ids": ignored_memory_ids,
                "missing_notes": missing_notes,
                "promote_notes": promote_notes,
                "write": write,
            }
        )

    @server.tool(name="shyftr_continuity_status")
    def shyftr_continuity_status_tool(continuity_cell_path: str) -> dict[str, Any]:
        return shyftr_continuity_status_bridge({"continuity_cell_path": continuity_cell_path})





    @server.tool(name="shyftr_carry_pack")
    def shyftr_carry_pack_tool(
        memory_cell_path: str,
        carry_cell_path: str,
        query: str,
        session_id: str,
        compaction_id: str,
        runtime_id: str = "mcp",
        trigger: str = "context_pressure",
        mode: str = "shadow",
        max_items: int = 8,
        max_tokens: int = 1200,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_carry_pack_bridge(
            {
                "memory_cell_path": memory_cell_path,
                "carry_cell_path": carry_cell_path,
                "query": query,
                "session_id": session_id,
                "compaction_id": compaction_id,
                "runtime_id": runtime_id,
                "trigger": trigger,
                "mode": mode,
                "max_items": max_items,
                "max_tokens": max_tokens,
                "write": write,
            }
        )

    @server.tool(name="shyftr_carry_feedback")
    def shyftr_carry_feedback_tool(
        carry_cell_path: str,
        carry_pack_id: str,
        result: str,
        session_id: str,
        compaction_id: str,
        runtime_id: str = "mcp",
        useful_memory_ids: list[str] | None = None,
        harmful_memory_ids: list[str] | None = None,
        ignored_memory_ids: list[str] | None = None,
        missing_notes: list[str] | None = None,
        promote_notes: list[str] | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_carry_feedback_bridge(
            {
                "carry_cell_path": carry_cell_path,
                "carry_pack_id": carry_pack_id,
                "result": result,
                "session_id": session_id,
                "compaction_id": compaction_id,
                "runtime_id": runtime_id,
                "useful_memory_ids": useful_memory_ids,
                "harmful_memory_ids": harmful_memory_ids,
                "ignored_memory_ids": ignored_memory_ids,
                "missing_notes": missing_notes,
                "promote_notes": promote_notes,
                "write": write,
            }
        )

    @server.tool(name="shyftr_carry_status")
    def shyftr_carry_status_tool(carry_cell_path: str) -> dict[str, Any]:
        return shyftr_carry_status_bridge({"carry_cell_path": carry_cell_path})

    @server.tool(name="shyftr_live_context_capture")
    def shyftr_live_context_capture_tool(
        cell_path: str,
        content: str,
        session_id: str,
        entry_kind: str,
        runtime_id: str = "mcp",
        task_id: str = "default-task",
        source_ref: str = "mcp",
        retention_hint: str = "session",
        sensitivity_hint: str = "internal",
        status: str | None = None,
        scope: str = "session",
        parent_entry_id: str | None = None,
        related_entry_ids: list[str] | None = None,
        confidence: float | None = None,
        evidence_refs: list[str] | None = None,
        grounding_refs: list[str] | None = None,
        valid_until: str | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_live_context_capture_bridge({
            "cell_path": cell_path,
            "content": content,
            "session_id": session_id,
            "entry_kind": entry_kind,
            "runtime_id": runtime_id,
            "task_id": task_id,
            "source_ref": source_ref,
            "retention_hint": retention_hint,
            "sensitivity_hint": sensitivity_hint,
            "status": status,
            "scope": scope,
            "parent_entry_id": parent_entry_id,
            "related_entry_ids": related_entry_ids,
            "confidence": confidence,
            "evidence_refs": evidence_refs,
            "grounding_refs": grounding_refs,
            "valid_until": valid_until,
            "write": write,
        })

    @server.tool(name="shyftr_live_context_pack")
    def shyftr_live_context_pack_tool(
        cell_path: str,
        query: str,
        session_id: str,
        runtime_id: str = "mcp",
        max_items: int = 8,
        max_tokens: int = 1200,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_live_context_pack_bridge({
            "cell_path": cell_path,
            "query": query,
            "session_id": session_id,
            "runtime_id": runtime_id,
            "max_items": max_items,
            "max_tokens": max_tokens,
            "write": write,
        })

    @server.tool(name="shyftr_live_context_checkpoint")
    def shyftr_live_context_checkpoint_tool(
        live_cell_path: str,
        continuity_cell_path: str,
        session_id: str,
        runtime_id: str = "mcp",
        max_items: int = 8,
        max_tokens: int = 1200,
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_live_context_checkpoint_bridge({
            "live_cell_path": live_cell_path,
            "continuity_cell_path": continuity_cell_path,
            "session_id": session_id,
            "runtime_id": runtime_id,
            "max_items": max_items,
            "max_tokens": max_tokens,
            "write": write,
        })

    @server.tool(name="shyftr_live_context_resume")
    def shyftr_live_context_resume_tool(
        continuity_cell_path: str,
        session_id: str,
        runtime_id: str = "mcp",
        max_items: int = 8,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        return shyftr_live_context_resume_bridge({
            "continuity_cell_path": continuity_cell_path,
            "session_id": session_id,
            "runtime_id": runtime_id,
            "max_items": max_items,
            "max_tokens": max_tokens,
        })

    @server.tool(name="shyftr_session_harvest")
    def shyftr_session_harvest_tool(
        live_cell_path: str,
        continuity_cell_path: str,
        memory_cell_path: str,
        session_id: str,
        runtime_id: str = "mcp",
        write: bool = False,
    ) -> dict[str, Any]:
        return shyftr_session_harvest_bridge({
            "live_cell_path": live_cell_path,
            "continuity_cell_path": continuity_cell_path,
            "memory_cell_path": memory_cell_path,
            "session_id": session_id,
            "runtime_id": runtime_id,
            "write": write,
        })

    @server.tool(name="shyftr_live_context_status")
    def shyftr_live_context_status_tool(cell_path: str) -> dict[str, Any]:
        return shyftr_live_context_status_bridge({"cell_path": cell_path})

    return server


def tool_names() -> tuple[str, ...]:
    return TOOL_NAMES


def main() -> None:
    if os.getenv("SHYFTR_FORCE_STDIO_FALLBACK") == "1":
        _run_json_rpc_stdio(sys.stdin, sys.stdout)
        return
    try:
        server = create_mcp_server()
    except RuntimeError:
        _run_json_rpc_stdio(sys.stdin, sys.stdout)
        return
    server.run()


def _load_payload(args: JsonArgs) -> dict[str, Any]:
    if isinstance(args, Mapping):
        return dict(args)
    if isinstance(args, str | bytes | bytearray):
        decoded = json.loads(args)
        if not isinstance(decoded, dict):
            raise ValueError("args must decode to a JSON object")
        return decoded
    raise TypeError("args must be a JSON object string or mapping")


def _require_cell_path(payload: Mapping[str, Any]) -> Path:
    raw = _require_text(payload.get("cell_path"), "cell_path")
    path = Path(raw).expanduser()
    manifest = path / "config" / "cell_manifest.json"
    if not manifest.exists():
        raise ValueError(f"cell_path is not a ShyftR cell: {path}")
    return path


def _require_cell_path_named(payload: Mapping[str, Any], field_name: str) -> Path:
    raw = _require_text(payload.get(field_name), field_name)
    path = Path(raw).expanduser()
    manifest = path / "config" / "cell_manifest.json"
    if not manifest.exists():
        raise ValueError(f"{field_name} is not a ShyftR cell: {path}")
    return path


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return " ".join(value.split())


def _optional_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return _require_text(value, "value")


def _optional_str_list(value: Any) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return [str(item) for item in value if str(item).strip()]
    raise ValueError("expected a list of strings")


def _optional_mapping(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be an object")
    return dict(value)


def _bounded_int(value: Any, field_name: str, *, minimum: int, maximum: int) -> int:
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return parsed


def _search_result_to_public(item: Any) -> dict[str, Any]:
    return {
        "memory_id": item.charge_id,
        "statement": item.statement,
        "trust_tier": item.trust_tier,
        "kind": item.kind,
        "memory_type": getattr(item, "memory_type", None),
        "confidence": item.confidence,
        "score": item.score,
        "lifecycle_status": item.lifecycle_status,
        "selection_rationale": item.selection_rationale,
        "provenance": _json_safe(item.provenance),
    }


def _memory_item_to_public(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "memory_id": item.get("item_id"),
        "trust_tier": item.get("trust_tier"),
        "statement": item.get("statement"),
        "rationale": item.get("rationale"),
        "tags": item.get("tags", []),
        "kind": item.get("kind"),
        "memory_type": item.get("memory_type"),
        "confidence": item.get("confidence"),
        "score": item.get("score"),
        "pack_role": item.get("loadout_role"),
        "graph_context": item.get("graph_context", []),
    }


def _retrieval_to_public(log: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "retrieval_id": log.get("retrieval_id"),
        "pack_id": log.get("pack_id") or log.get("loadout_id"),
        "selected_memory_ids": log.get("selected_ids", []),
        "candidate_memory_ids": log.get("candidate_ids", []),
        "caution_memory_ids": log.get("caution_ids", []),
        "suppressed_memory_ids": log.get("suppressed_ids", []),
        "query": log.get("query"),
        "logged_at": log.get("logged_at") or log.get("generated_at"),
        "generated_at": log.get("generated_at") or log.get("logged_at"),
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _run_json_rpc_stdio(stdin: TextIO, stdout: TextIO) -> None:
    for line in stdin:
        if not line.strip():
            continue
        response = _handle_json_rpc_message(json.loads(line))
        if response is not None:
            stdout.write(json.dumps(response, sort_keys=True) + "\n")
            stdout.flush()


def _handle_json_rpc_message(message: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    try:
        if method == "initialize":
            return _json_rpc_result(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "shyftr", "version": "0.0.0"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _json_rpc_result(request_id, {"tools": _tool_descriptors()})
        if method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            call_map = {
                "shyftr_search": shyftr_search_bridge,
                "shyftr_pack": shyftr_pack_bridge,
                "shyftr_profile": shyftr_profile_bridge,
                "shyftr_remember": shyftr_remember_bridge,
                "shyftr_record_feedback": shyftr_record_feedback_bridge,
                "shyftr_carry_pack": shyftr_carry_pack_bridge,
                "shyftr_carry_feedback": shyftr_carry_feedback_bridge,
                "shyftr_carry_status": shyftr_carry_status_bridge,
                "shyftr_continuity_pack": shyftr_continuity_pack_bridge,
                "shyftr_continuity_feedback": shyftr_continuity_feedback_bridge,
                "shyftr_continuity_status": shyftr_continuity_status_bridge,
                "shyftr_live_context_capture": shyftr_live_context_capture_bridge,
                "shyftr_live_context_pack": shyftr_live_context_pack_bridge,
                "shyftr_live_context_checkpoint": shyftr_live_context_checkpoint_bridge,
                "shyftr_live_context_resume": shyftr_live_context_resume_bridge,
                "shyftr_session_harvest": shyftr_session_harvest_bridge,
                "shyftr_live_context_status": shyftr_live_context_status_bridge,
            }
            if name not in call_map:
                raise ValueError(f"unknown tool: {name}")
            payload = call_map[name](arguments)
            return _json_rpc_result(
                request_id,
                {"content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}], "isError": False},
            )
        raise ValueError(f"unsupported method: {method}")
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def _json_rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _tool_descriptors() -> list[dict[str, Any]]:
    return [
        _tool_descriptor("shyftr_search", "Search reviewed ShyftR memory.", ["cell_path", "query"]),
        _tool_descriptor("shyftr_pack", "Build a bounded ShyftR pack; dry-run unless write=true.", ["cell_path", "query", "task_id"]),
        _tool_descriptor("shyftr_profile", "Build a compact profile projection from reviewed memory.", ["cell_path"]),
        _tool_descriptor("shyftr_remember", "Preview or write explicit memory through ShyftR policy.", ["cell_path", "statement", "kind"]),
        _tool_descriptor("shyftr_record_feedback", "Preview or record ShyftR pack feedback.", ["cell_path", "pack_id", "result"]),
        _tool_descriptor("shyftr_carry_pack", "Build an opt-in runtime carry pack; dry-run unless write=true.", ["memory_cell_path", "carry_cell_path", "query", "session_id", "compaction_id"]),
        _tool_descriptor("shyftr_carry_feedback", "Preview or record runtime carry feedback.", ["carry_cell_path", "carry_pack_id", "result", "session_id", "compaction_id"]),
        _tool_descriptor("shyftr_carry_status", "Summarize carry ledgers for a cell.", ["carry_cell_path"]),
        _tool_descriptor("shyftr_continuity_pack", "Compatibility alias: build an opt-in runtime carry pack; dry-run unless write=true.", ["memory_cell_path", "continuity_cell_path", "query", "session_id", "compaction_id"]),
        _tool_descriptor("shyftr_continuity_feedback", "Compatibility alias: preview or record runtime carry feedback.", ["continuity_cell_path", "continuity_pack_id", "result", "session_id", "compaction_id"]),
        _tool_descriptor("shyftr_continuity_status", "Compatibility alias: summarize carry ledgers for a cell.", ["continuity_cell_path"]),
        _tool_descriptor("shyftr_live_context_capture", "Capture live working context; dry-run unless write=true.", ["cell_path", "content", "session_id", "entry_kind"]),
        _tool_descriptor("shyftr_live_context_pack", "Build a bounded advisory live context pack.", ["cell_path", "query", "session_id"]),
        _tool_descriptor("shyftr_live_context_checkpoint", "Build a compact advisory carry-state checkpoint; dry-run unless write=true.", ["live_cell_path", "continuity_cell_path", "session_id"]),
        _tool_descriptor("shyftr_live_context_resume", "Reconstruct deterministic advisory resume state from continuity/carry records.", ["continuity_cell_path", "session_id"]),
        _tool_descriptor("shyftr_session_harvest", "Classify session live context into review-gated harvest outputs.", ["live_cell_path", "continuity_cell_path", "memory_cell_path", "session_id"]),
        _tool_descriptor("shyftr_live_context_status", "Summarize live context ledgers for a cell.", ["cell_path"]),
    ]


def _tool_descriptor(name: str, description: str, required: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "properties": {}, "required": required},
    }


if __name__ == "__main__":  # pragma: no cover
    main()
