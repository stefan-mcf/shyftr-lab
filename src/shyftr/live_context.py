"""Live context optimization, typed working-state capture, carry-state checkpoints,
and session-close harvest support.

The live context cell is separate from the continuity cell and durable memory
cell. It captures high-churn working context during a runtime session, returns a
bounded advisory pack when asked, produces compact carry-state checkpoints for
resume support, and classifies session-close entries into reviewable harvest
outputs. Mechanical prompt construction and compaction remain owned by the
runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union
import uuid

from .episodes import get_latest_episode, propose_episode
from .ledger import append_jsonl, read_jsonl
from .memory_classes import resolve_memory_type
from .models import Episode
from .pack import estimate_tokens

PathLike = Union[str, Path]

CANONICAL_LIVE_CONTEXT_ENTRY_KINDS = (
    "goal",
    "subgoal",
    "plan_step",
    "constraint",
    "decision",
    "assumption",
    "artifact_ref",
    "tool_state",
    "error",
    "recovery",
    "open_question",
    "verification_result",
)
LIVE_CONTEXT_ENTRY_KIND_ALIASES = {
    "active_goal": "goal",
    "active_plan": "plan_step",
    "active_artifact": "artifact_ref",
    "failure": "error",
    "verification": "verification_result",
}
LIVE_CONTEXT_ENTRY_KINDS = CANONICAL_LIVE_CONTEXT_ENTRY_KINDS + tuple(LIVE_CONTEXT_ENTRY_KIND_ALIASES.keys())
ENTRY_STATUSES = (
    "active",
    "pending",
    "blocked",
    "open",
    "resolved",
    "completed",
    "failed",
    "superseded",
    "archived",
)
RETENTION_HINTS = ("ephemeral", "session", "archive", "candidate", "durable", "skill")
SENSITIVITY_HINTS = ("public", "internal", "private", "sensitive")
HARVEST_BUCKETS = (
    "discard",
    "archive",
    "continuity_feedback",
    "memory_candidate",
    "direct_durable_memory",
    "skill_proposal",
)
DEFAULT_MAX_ITEMS = 8
DEFAULT_MAX_TOKENS = 1200
MAX_ITEMS_LIMIT = 100
MAX_TOKENS_LIMIT = 12000
NOTE_CHAR_LIMIT = 600
CHECKPOINT_SECTION_ORDER = (
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
)
ENTRY_KIND_ROLE_MAP = {
    "goal": "current_state",
    "subgoal": "current_state",
    "plan_step": "current_state",
    "constraint": "guidance",
    "decision": "guidance",
    "assumption": "current_state",
    "artifact_ref": "current_state",
    "tool_state": "current_state",
    "error": "caution",
    "recovery": "current_state",
    "open_question": "open_question",
    "verification_result": "guidance",
}


@dataclass(frozen=True)
class LiveContextEntry:
    runtime_id: str
    session_id: str
    task_id: str
    entry_id: str
    entry_kind: str
    content: str
    created_at: str
    source_ref: str
    retention_hint: str = "session"
    sensitivity_hint: str = "internal"
    status: str = "active"
    scope: str = "session"
    parent_entry_id: Optional[str] = None
    related_entry_ids: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    evidence_refs: List[str] = field(default_factory=list)
    grounding_refs: List[str] = field(default_factory=list)
    valid_until: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    original_entry_kind: Optional[str] = None

    def __post_init__(self) -> None:
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _require_text(self.task_id, "task_id")
        _require_text(self.entry_id, "entry_id")
        canonical_kind = _canonical_entry_kind(self.entry_kind)
        _require_choice(canonical_kind, CANONICAL_LIVE_CONTEXT_ENTRY_KINDS, "entry_kind")
        object.__setattr__(self, "entry_kind", canonical_kind)
        _require_text(self.content, "content")
        _require_text(self.created_at, "created_at")
        _require_text(self.source_ref, "source_ref")
        _require_choice(self.retention_hint, RETENTION_HINTS, "retention_hint")
        _require_choice(self.sensitivity_hint, SENSITIVITY_HINTS, "sensitivity_hint")
        _require_choice(self.status, ENTRY_STATUSES, "status")
        _require_text(self.scope, "scope")
        _validate_optional_text(self.parent_entry_id, "parent_entry_id")
        _validate_string_list(self.related_entry_ids, "related_entry_ids")
        _validate_string_list(self.evidence_refs, "evidence_refs")
        _validate_string_list(self.grounding_refs, "grounding_refs")
        _validate_optional_iso(self.valid_until, "valid_until")
        if self.confidence is not None:
            object.__setattr__(self, "confidence", _bounded_float(self.confidence, "confidence"))
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")
        if self.parent_entry_id and self.parent_entry_id == self.entry_id:
            raise ValueError("parent_entry_id cannot equal entry_id")
        if self.entry_id in self.related_entry_ids:
            raise ValueError("related_entry_ids cannot include entry_id")
        if self.parent_entry_id and self.parent_entry_id in self.related_entry_ids:
            raise ValueError("parent_entry_id must not be duplicated in related_entry_ids")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "entry_id": self.entry_id,
            "entry_kind": self.entry_kind,
            "content": self.content,
            "created_at": self.created_at,
            "source_ref": self.source_ref,
            "retention_hint": self.retention_hint,
            "sensitivity_hint": self.sensitivity_hint,
            "status": self.status,
            "scope": self.scope,
            "parent_entry_id": self.parent_entry_id,
            "related_entry_ids": list(self.related_entry_ids),
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "grounding_refs": list(self.grounding_refs),
            "valid_until": self.valid_until,
            "metadata": dict(self.metadata),
            "content_hash": self.content_hash or _content_hash(
                self.runtime_id,
                self.session_id,
                self.entry_kind,
                self.content,
                self.status,
                self.parent_entry_id,
            ),
            "original_entry_kind": self.original_entry_kind,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiveContextEntry":
        normalized = _normalize_entry_payload(payload)
        return cls(**_known_fields(cls, normalized))


@dataclass(frozen=True)
class LiveContextCaptureRequest:
    cell_path: str
    runtime_id: str
    session_id: str
    task_id: str
    entry_kind: str
    content: str
    source_ref: str
    retention_hint: str = "session"
    sensitivity_hint: str = "internal"
    status: Optional[str] = None
    scope: str = "session"
    parent_entry_id: Optional[str] = None
    related_entry_ids: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    evidence_refs: List[str] = field(default_factory=list)
    grounding_refs: List[str] = field(default_factory=list)
    valid_until: Optional[str] = None
    entry_id: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    write: bool = False

    def __post_init__(self) -> None:
        _require_path_text(self.cell_path, "cell_path")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _require_text(self.task_id, "task_id")
        canonical_kind = _canonical_entry_kind(self.entry_kind)
        _require_choice(canonical_kind, CANONICAL_LIVE_CONTEXT_ENTRY_KINDS, "entry_kind")
        object.__setattr__(self, "entry_kind", canonical_kind)
        _require_text(self.content, "content")
        _reject_sensitive_content(self.content, self.sensitivity_hint)
        _require_text(self.source_ref, "source_ref")
        _require_choice(self.retention_hint, RETENTION_HINTS, "retention_hint")
        _require_choice(self.sensitivity_hint, SENSITIVITY_HINTS, "sensitivity_hint")
        status = self.status or _default_status_for_kind(self.entry_kind)
        _require_choice(status, ENTRY_STATUSES, "status")
        object.__setattr__(self, "status", status)
        _require_text(self.scope, "scope")
        _validate_optional_text(self.parent_entry_id, "parent_entry_id")
        _validate_string_list(self.related_entry_ids, "related_entry_ids")
        _validate_string_list(self.evidence_refs, "evidence_refs")
        _validate_string_list(self.grounding_refs, "grounding_refs")
        _validate_optional_iso(self.valid_until, "valid_until")
        if self.confidence is not None:
            object.__setattr__(self, "confidence", _bounded_float(self.confidence, "confidence"))
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")
        if self.parent_entry_id and self.parent_entry_id in self.related_entry_ids:
            raise ValueError("parent_entry_id must not be duplicated in related_entry_ids")

    def to_entry(self) -> LiveContextEntry:
        content_hash = _content_hash(
            self.runtime_id,
            self.session_id,
            self.entry_kind,
            self.content,
            self.status or _default_status_for_kind(self.entry_kind),
            self.parent_entry_id,
        )
        return LiveContextEntry(
            runtime_id=self.runtime_id,
            session_id=self.session_id,
            task_id=self.task_id,
            entry_id=self.entry_id or f"live-entry-{content_hash[:20]}",
            entry_kind=self.entry_kind,
            content=self.content,
            created_at=self.created_at or _now(),
            source_ref=self.source_ref,
            retention_hint=self.retention_hint,
            sensitivity_hint=self.sensitivity_hint,
            status=self.status or _default_status_for_kind(self.entry_kind),
            scope=self.scope,
            parent_entry_id=self.parent_entry_id,
            related_entry_ids=list(self.related_entry_ids),
            confidence=self.confidence,
            evidence_refs=list(self.evidence_refs),
            grounding_refs=list(self.grounding_refs),
            valid_until=self.valid_until,
            metadata=dict(self.metadata),
            content_hash=content_hash,
            original_entry_kind=self.metadata.get("original_entry_kind") if isinstance(self.metadata.get("original_entry_kind"), str) else None,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiveContextCaptureRequest":
        normalized = _normalize_capture_payload(payload)
        return cls(**_known_fields(cls, normalized))


@dataclass(frozen=True)
class LiveContextPackRequest:
    cell_path: str
    query: str
    runtime_id: str
    session_id: str
    max_items: int = DEFAULT_MAX_ITEMS
    max_tokens: int = DEFAULT_MAX_TOKENS
    suppress_entry_ids: List[str] = field(default_factory=list)
    current_prompt_excerpts: List[str] = field(default_factory=list)
    write: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_path_text(self.cell_path, "cell_path")
        _require_text(self.query, "query")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _bounded_int(self.max_items, "max_items", minimum=0, maximum=MAX_ITEMS_LIMIT)
        _bounded_int(self.max_tokens, "max_tokens", minimum=1, maximum=MAX_TOKENS_LIMIT)
        _validate_string_list(self.suppress_entry_ids, "suppress_entry_ids")
        _validate_string_list(self.current_prompt_excerpts, "current_prompt_excerpts")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiveContextPackRequest":
        return cls(**_known_fields(cls, payload))


@dataclass(frozen=True)
class LiveContextPack:
    pack_id: str
    runtime_id: str
    session_id: str
    query: str
    items: List[Dict[str, Any]]
    excluded_items: List[Dict[str, Any]]
    suppressed_items: List[Dict[str, Any]]
    total_items: int
    total_tokens: int
    max_items: int
    max_tokens: int
    duplicate_suppression_count: int
    stale_suppression_count: int
    created_at: str
    advisory_only: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "query": self.query,
            "items": [dict(item) for item in self.items],
            "excluded_items": [dict(item) for item in self.excluded_items],
            "suppressed_items": [dict(item) for item in self.suppressed_items],
            "total_items": self.total_items,
            "total_tokens": self.total_tokens,
            "max_items": self.max_items,
            "max_tokens": self.max_tokens,
            "duplicate_suppression_count": self.duplicate_suppression_count,
            "stale_suppression_count": self.stale_suppression_count,
            "created_at": self.created_at,
            "advisory_only": self.advisory_only,
            "runtime_compactor_owner": "runtime",
        }


@dataclass(frozen=True)
class CarryStateCheckpointRequest:
    live_cell_path: str
    continuity_cell_path: str
    runtime_id: str
    session_id: str
    max_items: int = DEFAULT_MAX_ITEMS
    max_tokens: int = DEFAULT_MAX_TOKENS
    write: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_path_text(self.live_cell_path, "live_cell_path")
        _require_path_text(self.continuity_cell_path, "continuity_cell_path")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _bounded_int(self.max_items, "max_items", minimum=0, maximum=MAX_ITEMS_LIMIT)
        _bounded_int(self.max_tokens, "max_tokens", minimum=1, maximum=MAX_TOKENS_LIMIT)
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")


@dataclass(frozen=True)
class CarryStateCheckpoint:
    checkpoint_id: str
    runtime_id: str
    session_id: str
    live_cell_id: str
    continuity_cell_id: str
    sections: Dict[str, List[Dict[str, Any]]]
    total_items: int
    total_tokens: int
    max_items: int
    max_tokens: int
    generated_at: str
    advisory_only: bool = True
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "live_cell_id": self.live_cell_id,
            "continuity_cell_id": self.continuity_cell_id,
            "sections": {key: [dict(item) for item in value] for key, value in self.sections.items()},
            "total_items": self.total_items,
            "total_tokens": self.total_tokens,
            "max_items": self.max_items,
            "max_tokens": self.max_tokens,
            "generated_at": self.generated_at,
            "advisory_only": self.advisory_only,
            "diagnostics": dict(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CarryStateCheckpoint":
        normalized = dict(payload)
        sections = {
            key: [dict(item) for item in list((normalized.get("sections") or {}).get(key, []))]
            for key in CHECKPOINT_SECTION_ORDER
        }
        normalized["sections"] = sections
        return cls(**_known_fields(cls, normalized))

    def continuity_items(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for section in CHECKPOINT_SECTION_ORDER:
            for item in self.sections.get(section, []):
                role = _continuity_role_for_section(section)
                items.append(
                    {
                        "entry_id": item.get("entry_id"),
                        "entry_kind": item.get("entry_kind"),
                        "statement": item.get("content", ""),
                        "continuity_role": role,
                        "source_kind": "carry_state",
                        "token_estimate": int(item.get("token_estimate") or estimate_tokens(str(item.get("content") or ""))),
                        "score": float(item.get("score", 0.0) or 0.0),
                        "status": item.get("status"),
                        "scope": item.get("scope"),
                        "parent_entry_id": item.get("parent_entry_id"),
                        "related_entry_ids": list(item.get("related_entry_ids") or []),
                        "confidence": item.get("confidence"),
                        "evidence_refs": list(item.get("evidence_refs") or []),
                        "grounding_refs": list(item.get("grounding_refs") or []),
                        "valid_until": item.get("valid_until"),
                        "section": section,
                        "provenance": {
                            "checkpoint_id": self.checkpoint_id,
                            "section": section,
                            "entry_id": item.get("entry_id"),
                        },
                    }
                )
        return items


@dataclass(frozen=True)
class ResumeState:
    resume_id: str
    checkpoint_id: Optional[str]
    runtime_id: str
    session_id: str
    sections: Dict[str, List[Dict[str, Any]]]
    total_items: int
    total_tokens: int
    validation: Dict[str, Any]
    generated_at: str
    advisory_only: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resume_id": self.resume_id,
            "checkpoint_id": self.checkpoint_id,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "sections": {key: [dict(item) for item in value] for key, value in self.sections.items()},
            "total_items": self.total_items,
            "total_tokens": self.total_tokens,
            "validation": dict(self.validation),
            "generated_at": self.generated_at,
            "advisory_only": self.advisory_only,
        }


@dataclass(frozen=True)
class HarvestDecision:
    entry_id: str
    bucket: str
    rationale: str
    confidence: float
    memory_type: Optional[str] = None
    proposal: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        _require_text(self.entry_id, "entry_id")
        _require_choice(self.bucket, HARVEST_BUCKETS, "bucket")
        _require_text(self.rationale, "rationale")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "bucket": self.bucket,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "memory_type": self.memory_type,
            "proposal": dict(self.proposal or {}),
        }


@dataclass(frozen=True)
class SessionHarvestRequest:
    live_cell_path: str
    continuity_cell_path: str
    memory_cell_path: str
    runtime_id: str
    session_id: str
    write: bool = False
    allow_direct_durable_memory: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_path_text(self.live_cell_path, "live_cell_path")
        _require_path_text(self.continuity_cell_path, "continuity_cell_path")
        _require_path_text(self.memory_cell_path, "memory_cell_path")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SessionHarvestRequest":
        return cls(**_known_fields(cls, payload))


@dataclass(frozen=True)
class SessionHarvestReport:
    harvest_id: str
    runtime_id: str
    session_id: str
    status: str
    write: bool
    decisions: List[HarvestDecision]
    bucket_counts: Dict[str, int]
    memory_proposal_count: int
    continuity_improvement_proposal_count: int
    skill_proposal_count: int
    direct_durable_memory_writes: int
    generated_at: str
    episode_proposal_count: int = 0
    review_gated: bool = True
    carry_state_checkpoint: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "harvest_id": self.harvest_id,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "status": self.status,
            "write": self.write,
            "decisions": [decision.to_dict() for decision in self.decisions],
            "bucket_counts": dict(self.bucket_counts),
            "memory_proposal_count": self.memory_proposal_count,
            "continuity_improvement_proposal_count": self.continuity_improvement_proposal_count,
            "skill_proposal_count": self.skill_proposal_count,
            "direct_durable_memory_writes": self.direct_durable_memory_writes,
            "episode_proposal_count": self.episode_proposal_count,
            "generated_at": self.generated_at,
            "review_gated": self.review_gated,
            "carry_state_checkpoint": dict(self.carry_state_checkpoint or {}),
            "real_runtime_profile_touched": False,
        }


def capture_live_context(request: LiveContextCaptureRequest) -> Dict[str, Any]:
    cell = _require_cell(request.cell_path, "cell_path")
    entry = request.to_entry()
    existing = _find_entry_by_hash(cell, entry.content_hash, runtime_id=request.runtime_id, session_id=request.session_id)
    status = "dry_run" if not request.write else "ok"
    if existing is not None:
        return {"status": status, "write": bool(request.write), "deduped": True, "entry": _normalize_entry_record(existing)}
    if request.write:
        append_jsonl(cell / "ledger" / "live_context_entries.jsonl", entry.to_dict())
        append_jsonl(cell / "ledger" / "live_context_events.jsonl", {
            "event_id": f"live-context-event-{uuid.uuid4().hex}",
            "event_type": "live_context_captured",
            "runtime_id": request.runtime_id,
            "session_id": request.session_id,
            "entry_id": entry.entry_id,
            "entry_kind": entry.entry_kind,
            "recorded_at": entry.created_at,
        })
    return {"status": status, "write": bool(request.write), "deduped": False, "entry": entry.to_dict()}


def build_live_context_pack(request: LiveContextPackRequest) -> LiveContextPack:
    cell = _require_cell(request.cell_path, "cell_path")
    entries = _entries_for_session(cell, request.runtime_id, request.session_id)
    query_terms = set(_terms(request.query))
    suppress_ids = set(request.suppress_entry_ids)
    prompt_excerpts = [excerpt.lower() for excerpt in request.current_prompt_excerpts if excerpt.strip()]
    candidates: List[Dict[str, Any]] = []
    suppressed: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    stale_count = 0
    duplicate_count = 0

    active_entry_ids = {entry["entry_id"] for entry in entries if entry.get("status") in {"active", "pending", "blocked", "open"}}

    for entry in entries:
        if entry["entry_id"] in suppress_ids or _already_in_prompt(entry["content"], prompt_excerpts):
            duplicate_count += 1
            suppressed.append(_pack_stub(entry, "duplicate_or_current_prompt"))
            continue
        if _is_stale(entry):
            stale_count += 1
            excluded.append(_pack_stub(entry, "stale"))
            continue
        score_trace = _entry_score(entry, query_terms, active_entry_ids)
        role = _pack_role(entry)
        candidate = {
            "entry_id": entry["entry_id"],
            "entry_kind": entry["entry_kind"],
            "role": role,
            "content": entry["content"],
            "source_ref": entry["source_ref"],
            "retention_hint": entry["retention_hint"],
            "sensitivity_hint": entry["sensitivity_hint"],
            "status": entry["status"],
            "scope": entry["scope"],
            "parent_entry_id": entry.get("parent_entry_id"),
            "related_entry_ids": list(entry.get("related_entry_ids") or []),
            "confidence": entry.get("confidence"),
            "evidence_refs": list(entry.get("evidence_refs") or []),
            "grounding_refs": list(entry.get("grounding_refs") or []),
            "valid_until": entry.get("valid_until"),
            "provenance": {
                "runtime_id": entry["runtime_id"],
                "session_id": entry["session_id"],
                "task_id": entry["task_id"],
                "entry_id": entry["entry_id"],
            },
            "token_estimate": estimate_tokens(entry["content"]),
            "score": score_trace["score"],
            "score_trace": score_trace,
            "advisory_only": True,
        }
        candidates.append(candidate)

    candidates.sort(key=lambda item: (-_role_priority(item["role"]), -float(item["score"]), item["entry_id"]))
    selected: List[Dict[str, Any]] = []
    running_tokens = 0
    for item in candidates:
        if len(selected) >= request.max_items:
            excluded.append(_pack_stub(item, "item_limit"))
            continue
        next_tokens = running_tokens + int(item["token_estimate"])
        if next_tokens > request.max_tokens:
            excluded.append(_pack_stub(item, "token_limit"))
            continue
        selected.append(item)
        running_tokens = next_tokens

    pack = LiveContextPack(
        pack_id=f"live-context-pack-{uuid.uuid4().hex}",
        runtime_id=request.runtime_id,
        session_id=request.session_id,
        query=request.query,
        items=selected,
        excluded_items=excluded,
        suppressed_items=suppressed,
        total_items=len(selected),
        total_tokens=running_tokens,
        max_items=request.max_items,
        max_tokens=request.max_tokens,
        duplicate_suppression_count=duplicate_count,
        stale_suppression_count=stale_count,
        created_at=_now(),
    )
    if request.write:
        append_jsonl(cell / "ledger" / "live_context_packs.jsonl", pack.to_dict())
        append_jsonl(cell / "ledger" / "live_context_events.jsonl", {
            "event_id": f"live-context-event-{uuid.uuid4().hex}",
            "event_type": "live_context_pack_built",
            "runtime_id": request.runtime_id,
            "session_id": request.session_id,
            "pack_id": pack.pack_id,
            "selected_count": pack.total_items,
            "recorded_at": pack.created_at,
        })
    return pack


def build_carry_state_checkpoint(request: CarryStateCheckpointRequest) -> CarryStateCheckpoint:
    live_cell = _require_cell(request.live_cell_path, "live_cell_path")
    continuity_cell = _require_cell(request.continuity_cell_path, "continuity_cell_path")
    entries = _entries_for_session(live_cell, request.runtime_id, request.session_id)
    selected, diagnostics = _select_checkpoint_items(entries, max_items=request.max_items, max_tokens=request.max_tokens)
    sections: Dict[str, List[Dict[str, Any]]] = {key: [] for key in CHECKPOINT_SECTION_ORDER}
    total_tokens = 0
    for item in selected:
        sections[item["section"]].append(item["record"])
        total_tokens += int(item["record"]["token_estimate"])
    checkpoint = CarryStateCheckpoint(
        checkpoint_id=f"carry-state-checkpoint-{uuid.uuid4().hex}",
        runtime_id=request.runtime_id,
        session_id=request.session_id,
        live_cell_id=_read_cell_id(live_cell),
        continuity_cell_id=_read_cell_id(continuity_cell),
        sections=sections,
        total_items=sum(len(value) for value in sections.values()),
        total_tokens=total_tokens,
        max_items=request.max_items,
        max_tokens=request.max_tokens,
        generated_at=_now(),
        diagnostics=diagnostics,
    )
    if request.write:
        append_jsonl(continuity_cell / "ledger" / "continuity_checkpoints.jsonl", checkpoint.to_dict())
        append_jsonl(continuity_cell / "ledger" / "continuity_events.jsonl", {
            "event_id": f"continuity-event-{uuid.uuid4().hex}",
            "event_type": "carry_state_checkpoint_built",
            "checkpoint_id": checkpoint.checkpoint_id,
            "runtime_id": request.runtime_id,
            "session_id": request.session_id,
            "recorded_at": checkpoint.generated_at,
            "metadata": dict(request.metadata),
        })
    return checkpoint


def latest_carry_state_checkpoint(continuity_cell_path: PathLike, *, runtime_id: str, session_id: str) -> Optional[CarryStateCheckpoint]:
    continuity_cell = _require_cell(continuity_cell_path, "continuity_cell_path")
    matches: List[CarryStateCheckpoint] = []
    for record in _read_jsonl_if_exists(continuity_cell / "ledger" / "continuity_checkpoints.jsonl"):
        if record.get("runtime_id") == runtime_id and record.get("session_id") == session_id:
            matches.append(CarryStateCheckpoint.from_dict(record))
    if not matches:
        return None
    matches.sort(key=lambda item: (item.generated_at, item.checkpoint_id))
    return matches[-1]


def reconstruct_resume_state(
    continuity_cell_path: PathLike,
    *,
    runtime_id: str,
    session_id: str,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> ResumeState:
    checkpoint = latest_carry_state_checkpoint(continuity_cell_path, runtime_id=runtime_id, session_id=session_id)
    if checkpoint is None:
        return ResumeState(
            resume_id=f"resume-state-{uuid.uuid4().hex}",
            checkpoint_id=None,
            runtime_id=runtime_id,
            session_id=session_id,
            sections={key: [] for key in CHECKPOINT_SECTION_ORDER},
            total_items=0,
            total_tokens=0,
            validation={"status": "missing_checkpoint", "broken_reference_count": 0, "expired_count": 0, "wrong_state_count": 0, "missing_state_count": 0},
            generated_at=_now(),
        )
    selected: Dict[str, List[Dict[str, Any]]] = {key: [] for key in CHECKPOINT_SECTION_ORDER}
    running_tokens = 0
    total_items = 0
    entry_ids = set()
    for section in CHECKPOINT_SECTION_ORDER:
        for item in checkpoint.sections.get(section, []):
            token_estimate = int(item.get("token_estimate") or estimate_tokens(str(item.get("content") or "")))
            if total_items >= max_items or running_tokens + token_estimate > max_tokens:
                continue
            selected[section].append(dict(item))
            running_tokens += token_estimate
            total_items += 1
            if item.get("entry_id"):
                entry_ids.add(str(item["entry_id"]))
    broken_references = []
    expired = []
    for section_items in selected.values():
        for item in section_items:
            parent = item.get("parent_entry_id")
            if parent and parent not in entry_ids:
                broken_references.append({"entry_id": item.get("entry_id"), "missing_parent_entry_id": parent})
            if _is_expired(item):
                expired.append(item.get("entry_id"))
    validation = {
        "status": "ok" if not broken_references else "invalid",
        "broken_reference_count": len(broken_references),
        "broken_references": broken_references,
        "expired_count": len(expired),
        "expired_entry_ids": expired,
        "wrong_state_count": len(expired),
        "missing_state_count": len(broken_references),
    }
    return ResumeState(
        resume_id=f"resume-state-{uuid.uuid4().hex}",
        checkpoint_id=checkpoint.checkpoint_id,
        runtime_id=runtime_id,
        session_id=session_id,
        sections=selected,
        total_items=total_items,
        total_tokens=running_tokens,
        validation=validation,
        generated_at=_now(),
    )


def harvest_session(request: SessionHarvestRequest) -> SessionHarvestReport:
    live_cell = _require_cell(request.live_cell_path, "live_cell_path")
    continuity_cell = _require_cell(request.continuity_cell_path, "continuity_cell_path")
    memory_cell = _require_cell(request.memory_cell_path, "memory_cell_path")
    _ = memory_cell
    entries = _entries_for_session(live_cell, request.runtime_id, request.session_id)
    checkpoint = build_carry_state_checkpoint(
        CarryStateCheckpointRequest(
            live_cell_path=str(live_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id=request.runtime_id,
            session_id=request.session_id,
            write=request.write,
            metadata={"trigger": "session_harvest", **dict(request.metadata)},
        )
    )
    decisions = [_classify_entry(entry, allow_direct=request.allow_direct_durable_memory) for entry in entries]
    episode_proposals = _episode_proposals_from_entries(request, entries)
    bucket_counts = {bucket: 0 for bucket in HARVEST_BUCKETS}
    for decision in decisions:
        bucket_counts[decision.bucket] += 1
    harvest_fingerprint = hashlib.sha256("\n".join(str(entry.get("entry_id") or "") for entry in entries).encode("utf-8")).hexdigest()[:12]
    report = SessionHarvestReport(
        harvest_id=f"session-harvest-{request.runtime_id}-{request.session_id}-{harvest_fingerprint}",
        runtime_id=request.runtime_id,
        session_id=request.session_id,
        status="dry_run" if not request.write else "ok",
        write=bool(request.write),
        decisions=decisions,
        bucket_counts=bucket_counts,
        memory_proposal_count=bucket_counts["memory_candidate"] + (bucket_counts["direct_durable_memory"] if not request.allow_direct_durable_memory else 0),
        continuity_improvement_proposal_count=bucket_counts["continuity_feedback"],
        skill_proposal_count=bucket_counts["skill_proposal"],
        direct_durable_memory_writes=0,
        generated_at=_now(),
        episode_proposal_count=len(episode_proposals),
        carry_state_checkpoint=checkpoint.to_dict(),
    )
    if not request.write:
        return report
    if _harvest_already_written(live_cell, report.harvest_id):
        return report
    append_jsonl(live_cell / "ledger" / "session_harvests.jsonl", report.to_dict())
    for episode in episode_proposals:
        latest = get_latest_episode(memory_cell, episode.episode_id)
        if latest is not None and latest.status != "proposed":
            continue
        propose_episode(memory_cell, episode)
    for decision in decisions:
        if decision.bucket in {"memory_candidate", "direct_durable_memory", "skill_proposal", "continuity_feedback"}:
            proposal = _proposal_from_decision(report, decision, entries)
            append_jsonl(live_cell / "ledger" / "session_harvest_proposals.jsonl", proposal)
            if decision.bucket == "continuity_feedback":
                append_jsonl(continuity_cell / "ledger" / "continuity_feedback.jsonl", {
                    "event_id": f"continuity-feedback-{uuid.uuid4().hex}",
                    "event_type": "session_harvest_continuity_feedback",
                    "runtime_id": request.runtime_id,
                    "session_id": request.session_id,
                    "compaction_id": f"session-close-{request.session_id}",
                    "result": "harvest_observation",
                    "missing_notes": [proposal["statement"][:NOTE_CHAR_LIMIT]],
                    "metadata": {"harvest_id": report.harvest_id, "source_entry_id": decision.entry_id},
                    "recorded_at": report.generated_at,
                })
        if decision.bucket == "archive":
            append_jsonl(live_cell / "ledger" / "session_archive.jsonl", {"harvest_id": report.harvest_id, "entry_id": decision.entry_id, "archived_at": report.generated_at})
    append_jsonl(live_cell / "ledger" / "live_context_events.jsonl", {
        "event_id": f"live-context-event-{uuid.uuid4().hex}",
        "event_type": "session_harvest_completed",
        "runtime_id": request.runtime_id,
        "session_id": request.session_id,
        "harvest_id": report.harvest_id,
        "checkpoint_id": checkpoint.checkpoint_id,
        "recorded_at": report.generated_at,
    })
    return report


def live_context_status(cell_path: PathLike) -> Dict[str, Any]:
    cell = _require_cell(cell_path, "cell_path")
    counts = {
        "entries": _count_jsonl(cell / "ledger" / "live_context_entries.jsonl"),
        "packs": _count_jsonl(cell / "ledger" / "live_context_packs.jsonl"),
        "harvests": _count_jsonl(cell / "ledger" / "session_harvests.jsonl"),
        "harvest_proposals": _count_jsonl(cell / "ledger" / "session_harvest_proposals.jsonl"),
    }
    return {"status": "ok", "cell_path": str(cell), "cell_id": _read_cell_id(cell), "counts": counts, "advisory_only": True}


def live_context_metrics(cell_path: PathLike, *, runtime_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    cell = _require_cell(cell_path, "cell_path")
    packs = _read_jsonl_if_exists(cell / "ledger" / "live_context_packs.jsonl")
    harvests = _read_jsonl_if_exists(cell / "ledger" / "session_harvests.jsonl")
    if runtime_id:
        packs = [p for p in packs if p.get("runtime_id") == runtime_id]
        harvests = [h for h in harvests if h.get("runtime_id") == runtime_id]
    if session_id:
        packs = [p for p in packs if p.get("session_id") == session_id]
        harvests = [h for h in harvests if h.get("session_id") == session_id]
    bucket_counts = {bucket: 0 for bucket in HARVEST_BUCKETS}
    checkpoint_count = 0
    checkpoint_tokens = 0
    for report in harvests:
        for bucket, count in dict(report.get("bucket_counts") or {}).items():
            if bucket in bucket_counts:
                bucket_counts[bucket] += int(count)
        checkpoint_payload = dict(report.get("carry_state_checkpoint") or {})
        if checkpoint_payload:
            checkpoint_count += 1
            checkpoint_tokens += int(checkpoint_payload.get("total_tokens") or 0)
    return {
        "status": "ok",
        "pack_item_count": sum(int(p.get("total_items") or 0) for p in packs),
        "estimated_pack_tokens": sum(int(p.get("total_tokens") or 0) for p in packs),
        "duplicate_suppression_count": sum(int(p.get("duplicate_suppression_count") or 0) for p in packs),
        "stale_item_suppression_count": sum(int(p.get("stale_suppression_count") or 0) for p in packs),
        "harvest_bucket_counts": bucket_counts,
        "memory_proposal_count": sum(int(h.get("memory_proposal_count") or 0) for h in harvests),
        "continuity_improvement_proposal_count": sum(int(h.get("continuity_improvement_proposal_count") or 0) for h in harvests),
        "carry_state_checkpoint_count": checkpoint_count,
        "carry_state_checkpoint_tokens": checkpoint_tokens,
        "useful_feedback_rate": _synthetic_rate(cell, "useful"),
        "ignored_feedback_rate": _synthetic_rate(cell, "ignored"),
        "harmful_feedback_rate": _synthetic_rate(cell, "harmful"),
    }


def _synthetic_rate(cell: Path, key: str) -> float:
    rows = _read_jsonl_if_exists(cell / "ledger" / "continuity_feedback.jsonl")
    if not rows:
        return 0.0
    count = 0
    for row in rows:
        if key == "useful" and row.get("useful_memory_ids"):
            count += 1
        elif key == "ignored" and row.get("ignored_memory_ids"):
            count += 1
        elif key == "harmful" and row.get("harmful_memory_ids"):
            count += 1
    return count / len(rows)


def _classify_entry(entry: Mapping[str, Any], *, allow_direct: bool) -> HarvestDecision:
    kind = str(entry.get("entry_kind") or "")
    retention = str(entry.get("retention_hint") or "session")
    sensitivity = str(entry.get("sensitivity_hint") or "internal")
    status = str(entry.get("status") or _default_status_for_kind(kind))
    metadata = dict(entry.get("metadata") or {})
    confidence = float(entry.get("confidence") if entry.get("confidence") is not None else metadata.get("confidence", 0.72) or 0.72)
    valid_until = entry.get("valid_until")
    if _is_expired(entry):
        return HarvestDecision(entry["entry_id"], "archive", "expired working-state entry is archived for reconstruction only", min(confidence, 0.6))
    if sensitivity in {"private", "sensitive"} and retention not in {"durable", "skill"}:
        return HarvestDecision(entry["entry_id"], "archive", "private/sensitive working context is archived for review instead of promoted", min(confidence, 0.65))
    if retention == "ephemeral":
        return HarvestDecision(entry["entry_id"], "discard", "entry retention hint is ephemeral", 0.95)
    if retention == "archive":
        return HarvestDecision(entry["entry_id"], "archive", "entry retention hint requests archive", 0.9, memory_type=resolve_memory_type("episodic", entry_kind=kind, retention_hint=retention))
    if retention == "skill" or kind == "recovery":
        return HarvestDecision(entry["entry_id"], "skill_proposal", "reusable recovery or skill-oriented context", max(confidence, 0.78), memory_type=resolve_memory_type("procedural", entry_kind=kind, retention_hint=retention))
    if kind in {"error", "open_question", "tool_state", "assumption", "goal", "subgoal", "plan_step"} and status in {"active", "pending", "blocked", "open", "failed"}:
        return HarvestDecision(entry["entry_id"], "continuity_feedback", "active or unresolved typed working state should improve future continuity and resume support", max(confidence, 0.76), memory_type=resolve_memory_type("continuity", entry_kind=kind, retention_hint=retention))
    if retention == "durable" and sensitivity == "public" and allow_direct and confidence >= 0.92 and kind in {"decision", "constraint", "verification_result"}:
        return HarvestDecision(entry["entry_id"], "direct_durable_memory", "high-confidence public durable fact permitted by local policy", confidence, memory_type=resolve_memory_type(None, entry_kind=kind, retention_hint=retention))
    if retention in {"candidate", "durable"} or kind in {"decision", "constraint", "verification_result", "artifact_ref"}:
        return HarvestDecision(entry["entry_id"], "memory_candidate", "typed decision, constraint, verification, artifact, or durable hint becomes review-gated memory candidate", max(confidence, 0.8), memory_type=resolve_memory_type(None, entry_kind=kind, retention_hint=retention))
    if valid_until and status in {"completed", "resolved", "superseded", "archived"}:
        return HarvestDecision(entry["entry_id"], "archive", "completed typed state is retained for reconstruction only", confidence, memory_type=resolve_memory_type("episodic", entry_kind=kind, retention_hint=retention))
    return HarvestDecision(entry["entry_id"], "archive", "session context retained for reconstruction only", confidence, memory_type=resolve_memory_type("episodic", entry_kind=kind, retention_hint=retention))


def _proposal_from_decision(report: SessionHarvestReport, decision: HarvestDecision, entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    entry = next((e for e in entries if e.get("entry_id") == decision.entry_id), {})
    return {
        "proposal_id": f"session-harvest-proposal-{uuid.uuid4().hex}",
        "harvest_id": report.harvest_id,
        "runtime_id": report.runtime_id,
        "session_id": report.session_id,
        "entry_id": decision.entry_id,
        "entry_kind": entry.get("entry_kind"),
        "memory_type": decision.memory_type,
        "bucket": decision.bucket,
        "statement": str(entry.get("content") or "")[:NOTE_CHAR_LIMIT],
        "rationale": decision.rationale,
        "confidence": decision.confidence,
        "review_gated": True,
        "created_at": report.generated_at,
    }


def _episode_proposals_from_entries(request: SessionHarvestRequest, entries: Sequence[Mapping[str, Any]]) -> List[Episode]:
    material = [entry for entry in entries if str(entry.get("retention_hint") or "") in {"archive", "session", "durable"} and str(entry.get("status") or "") in {"completed", "resolved", "failed", "blocked", "archived", "superseded"}]
    incident_entries = [entry for entry in material if str(entry.get("entry_kind") or "") in {"error", "recovery"}]
    proposals: List[Episode] = []
    if material:
        proposals.append(_session_episode_from_entries(request, material))
    if any(str(entry.get("entry_kind") or "") == "error" for entry in incident_entries) and any(str(entry.get("entry_kind") or "") == "recovery" for entry in incident_entries):
        proposals.append(_incident_episode_from_entries(request, incident_entries))
    return proposals


def _session_episode_from_entries(request: SessionHarvestRequest, entries: Sequence[Mapping[str, Any]]) -> Episode:
    entry_ids = [str(entry["entry_id"]) for entry in entries if entry.get("entry_id")]
    sensitivity = _max_sensitivity(entries)
    return Episode(
        episode_id=f"episode-session-{request.runtime_id}-{request.session_id}",
        cell_id=_read_cell_id(_require_cell(request.memory_cell_path, "memory_cell_path")),
        episode_kind="session",
        title=f"Session {request.session_id} harvested",
        summary=_episode_summary(entries),
        started_at=str(entries[0].get("created_at") or _now()),
        ended_at=str(entries[-1].get("created_at") or _now()),
        actor=request.runtime_id,
        action="session_harvest",
        outcome=_episode_outcome(entries),
        status="proposed",
        memory_type="episodic",
        confidence=min(0.82, max(float(entry.get("confidence") or 0.72) for entry in entries)),
        sensitivity=sensitivity,
        created_at=_now(),
        runtime_id=request.runtime_id,
        session_id=request.session_id,
        task_id=str(entries[-1].get("task_id") or "session"),
        key_points=[str(entry.get("content") or "")[:160] for entry in entries[:5] if entry.get("content")],
        live_context_entry_ids=entry_ids,
        grounding_refs=_combined_refs(entries, "grounding_refs"),
        artifact_refs=_artifact_refs(entries),
        metadata={"harvest_bridge": "session", "entry_count": len(entries)},
    )


def _incident_episode_from_entries(request: SessionHarvestRequest, entries: Sequence[Mapping[str, Any]]) -> Episode:
    entry_ids = [str(entry["entry_id"]) for entry in entries if entry.get("entry_id")]
    return Episode(
        episode_id=f"episode-incident-{request.runtime_id}-{request.session_id}",
        cell_id=_read_cell_id(_require_cell(request.memory_cell_path, "memory_cell_path")),
        episode_kind="incident",
        title=f"Incident/recovery cluster for {request.session_id}",
        summary=_episode_summary(entries),
        started_at=str(entries[0].get("created_at") or _now()),
        ended_at=str(entries[-1].get("created_at") or _now()),
        actor=request.runtime_id,
        action="session_harvest_incident_cluster",
        outcome=_incident_outcome(entries),
        status="proposed",
        memory_type="episodic",
        confidence=0.78,
        sensitivity=_max_sensitivity(entries),
        created_at=_now(),
        runtime_id=request.runtime_id,
        session_id=request.session_id,
        task_id=str(entries[-1].get("task_id") or "session"),
        key_points=[str(entry.get("content") or "")[:160] for entry in entries[:5] if entry.get("content")],
        live_context_entry_ids=entry_ids,
        grounding_refs=_combined_refs(entries, "grounding_refs"),
        artifact_refs=_artifact_refs(entries),
        metadata={"harvest_bridge": "incident", "entry_count": len(entries)},
    )


def _episode_summary(entries: Sequence[Mapping[str, Any]]) -> str:
    excerpts = [str(entry.get("content") or "").strip() for entry in entries if str(entry.get("content") or "").strip()]
    return " | ".join(excerpt[:180] for excerpt in excerpts[:3])[:600] or "Session harvest episode proposal."


def _episode_outcome(entries: Sequence[Mapping[str, Any]]) -> str:
    terminal = [str(entry.get("status") or "") for entry in entries if str(entry.get("status") or "") in {"completed", "resolved", "failed", "blocked", "superseded"}]
    if not terminal:
        return "informational"
    latest_status = terminal[-1]
    if latest_status in {"completed", "resolved"}:
        return "success"
    if latest_status == "failed":
        return "failure"
    if latest_status == "blocked":
        return "blocked"
    if latest_status == "superseded":
        return "superseded"
    return "informational"


def _incident_outcome(entries: Sequence[Mapping[str, Any]]) -> str:
    recovery_statuses = [str(entry.get("status") or "") for entry in entries if str(entry.get("entry_kind") or "") == "recovery"]
    if any(status in {"completed", "resolved"} for status in recovery_statuses):
        return "partial"
    if any(status == "blocked" for status in recovery_statuses):
        return "blocked"
    return "failure"


def _max_sensitivity(entries: Sequence[Mapping[str, Any]]) -> str:
    order = {"public": 0, "internal": 1, "private": 2, "secret": 3, "restricted": 4, "sensitive": 3}
    canonical = {"sensitive": "secret"}
    value = "internal"
    for entry in entries:
        candidate = str(entry.get("sensitivity_hint") or "internal")
        candidate = canonical.get(candidate, candidate)
        if order.get(candidate, 1) > order.get(value, 1):
            value = candidate
    return value


def _combined_refs(entries: Sequence[Mapping[str, Any]], key: str) -> List[str]:
    refs: List[str] = []
    for entry in entries:
        for value in entry.get(key) or []:
            text = str(value)
            if text and text not in refs:
                refs.append(text)
    return refs


def _artifact_refs(entries: Sequence[Mapping[str, Any]]) -> List[str]:
    refs = _combined_refs(entries, "evidence_refs")
    for entry in entries:
        if str(entry.get("entry_kind") or "") == "artifact_ref" and entry.get("source_ref"):
            source_ref = str(entry["source_ref"])
            if source_ref not in refs:
                refs.append(source_ref)
    return refs


def _entries_for_session(cell: Path, runtime_id: str, session_id: str) -> List[Dict[str, Any]]:
    rows = _read_jsonl_if_exists(cell / "ledger" / "live_context_entries.jsonl")
    entries = [_normalize_entry_record(row) for row in rows if row.get("runtime_id") == runtime_id and row.get("session_id") == session_id]
    entries.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("entry_id") or "")))
    return entries


def _find_entry_by_hash(cell: Path, content_hash: str, *, runtime_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    for record in _read_jsonl_if_exists(cell / "ledger" / "live_context_entries.jsonl"):
        if record.get("content_hash") == content_hash and record.get("runtime_id") == runtime_id and record.get("session_id") == session_id:
            return _normalize_entry_record(record)
    return None


def _pack_role(entry: Mapping[str, Any]) -> str:
    return ENTRY_KIND_ROLE_MAP.get(str(entry.get("entry_kind") or ""), "current_state")


def _role_priority(role: str) -> int:
    return {"guidance": 4, "current_state": 3, "caution": 2, "open_question": 1}.get(role, 0)


def _entry_score(entry: Mapping[str, Any], query_terms: set[str], active_entry_ids: set[str]) -> Dict[str, float]:
    content_terms = set(_terms(str(entry.get("content") or "")))
    overlap = len(query_terms & content_terms) / max(1, len(query_terms)) if query_terms else 0.0
    kind_bonus = {
        "goal": 0.22,
        "subgoal": 0.18,
        "plan_step": 0.18,
        "constraint": 0.2,
        "decision": 0.19,
        "assumption": 0.14,
        "artifact_ref": 0.14,
        "tool_state": 0.12,
        "error": 0.16,
        "recovery": 0.16,
        "open_question": 0.11,
        "verification_result": 0.18,
    }.get(str(entry.get("entry_kind") or ""), 0.0)
    status_bonus = {
        "active": 0.18,
        "pending": 0.16,
        "blocked": 0.16,
        "open": 0.14,
        "resolved": 0.06,
        "completed": 0.05,
        "failed": 0.12,
        "superseded": -0.1,
        "archived": -0.12,
    }.get(str(entry.get("status") or "active"), 0.0)
    confidence = float(entry.get("confidence") or 0.0)
    confidence_bonus = min(max(confidence, 0.0), 1.0) * 0.08
    relationship_bonus = 0.03 if entry.get("parent_entry_id") or list(entry.get("related_entry_ids") or []) else 0.0
    locality_bonus = 0.04 if str(entry.get("entry_id") or "") in active_entry_ids else 0.0
    freshness_bonus = 0.0 if _is_expired(entry) else 0.04
    lexical_fallback = 0.02 if not query_terms and content_terms else 0.0
    score = round(overlap + kind_bonus + status_bonus + confidence_bonus + relationship_bonus + locality_bonus + freshness_bonus + lexical_fallback, 4)
    return {
        "lexical_overlap": round(overlap, 4),
        "kind_bonus": round(kind_bonus, 4),
        "status_bonus": round(status_bonus, 4),
        "confidence_bonus": round(confidence_bonus, 4),
        "relationship_locality_bonus": round(relationship_bonus + locality_bonus, 4),
        "freshness_bonus": round(freshness_bonus, 4),
        "lexical_fallback": round(lexical_fallback, 4),
        "score": score,
    }


def _terms(text: str) -> List[str]:
    return [part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(part) > 2]


def _already_in_prompt(content: str, excerpts: Sequence[str]) -> bool:
    lowered = content.lower()
    return any(lowered in excerpt or excerpt in lowered for excerpt in excerpts if excerpt)


def _is_stale(entry: Mapping[str, Any]) -> bool:
    metadata = dict(entry.get("metadata") or {})
    status = str(entry.get("status") or "")
    return bool(metadata.get("stale") or metadata.get("superseded") or status in {"superseded", "archived"} or _is_expired(entry))


def _is_checkpoint_suppressed(entry: Mapping[str, Any]) -> bool:
    metadata = dict(entry.get("metadata") or {})
    status = str(entry.get("status") or "")
    return bool(metadata.get("stale") or metadata.get("superseded") or status in {"superseded", "archived"})


def _is_expired(entry: Mapping[str, Any]) -> bool:
    valid_until = entry.get("valid_until")
    if not isinstance(valid_until, str) or not valid_until.strip():
        return False
    try:
        return _parse_iso(valid_until) <= datetime.now(timezone.utc)
    except ValueError:
        return False


def _pack_stub(item: Mapping[str, Any], reason: str) -> Dict[str, Any]:
    return {"entry_id": item.get("entry_id"), "reason": reason, "entry_kind": item.get("entry_kind")}


def _harvest_already_written(cell: Path, harvest_id: str) -> bool:
    return any(record.get("harvest_id") == harvest_id for record in _read_jsonl_if_exists(cell / "ledger" / "session_harvests.jsonl"))


def _select_checkpoint_items(entries: Sequence[Mapping[str, Any]], *, max_items: int, max_tokens: int) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    section_totals = {key: 0 for key in CHECKPOINT_SECTION_ORDER}
    for entry in entries:
        if _is_checkpoint_suppressed(entry):
            continue
        section = _checkpoint_section(entry)
        if section is None:
            continue
        section_totals[section] += 1
        record = _checkpoint_record(entry)
        priority = _checkpoint_priority(section, entry)
        candidates.append({"section": section, "record": record, "priority": priority})
    candidates.sort(key=lambda item: (-item["priority"], str(item["record"].get("created_at") or ""), str(item["record"].get("entry_id") or "")))
    selected: List[Dict[str, Any]] = []
    running_tokens = 0
    section_counts = {key: 0 for key in CHECKPOINT_SECTION_ORDER}
    for item in candidates:
        if len(selected) >= max_items:
            break
        token_estimate = int(item["record"]["token_estimate"])
        if running_tokens + token_estimate > max_tokens:
            continue
        selected.append(item)
        running_tokens += token_estimate
        section_counts[item["section"]] += 1
    diagnostics = {
        "section_totals": section_totals,
        "selected_section_counts": section_counts,
        "suppressed_for_bounds": max(0, len(candidates) - len(selected)),
    }
    return selected, diagnostics


def _checkpoint_record(entry: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "entry_id": entry.get("entry_id"),
        "entry_kind": entry.get("entry_kind"),
        "memory_type": resolve_memory_type(None, entry_kind=entry.get("entry_kind"), retention_hint=entry.get("retention_hint")),
        "content": entry.get("content"),
        "status": entry.get("status"),
        "scope": entry.get("scope"),
        "created_at": entry.get("created_at"),
        "source_ref": entry.get("source_ref"),
        "parent_entry_id": entry.get("parent_entry_id"),
        "related_entry_ids": list(entry.get("related_entry_ids") or []),
        "confidence": entry.get("confidence"),
        "evidence_refs": list(entry.get("evidence_refs") or []),
        "grounding_refs": list(entry.get("grounding_refs") or []),
        "valid_until": entry.get("valid_until"),
        "token_estimate": estimate_tokens(str(entry.get("content") or "")),
        "score": _checkpoint_priority(_checkpoint_section(entry) or "artifact_refs", entry),
    }


def _checkpoint_section(entry: Mapping[str, Any]) -> Optional[str]:
    kind = str(entry.get("entry_kind") or "")
    status = str(entry.get("status") or _default_status_for_kind(kind))
    if kind in {"goal", "subgoal"} and status in {"active", "pending", "blocked", "open"}:
        return "unresolved_goals"
    if kind == "plan_step" and status in {"active", "pending", "blocked"}:
        return "current_plan_steps"
    if kind == "open_question" and status in {"active", "pending", "blocked", "open"}:
        return "open_loops"
    if kind == "decision" and status in {"active", "pending", "blocked", "resolved", "completed"}:
        return "commitments"
    if kind == "constraint":
        return "constraints"
    if kind == "assumption" and status in {"active", "pending", "blocked", "open"}:
        return "active_assumptions"
    if kind == "error":
        return "recent_errors"
    if kind == "recovery":
        return "recent_recoveries"
    if kind == "artifact_ref":
        return "artifact_refs"
    if kind in {"tool_state", "error"}:
        return "cautions"
    if kind == "verification_result":
        return "verification_results"
    return None


def _checkpoint_priority(section: str, entry: Mapping[str, Any]) -> float:
    status = str(entry.get("status") or "active")
    base = {
        "unresolved_goals": 10.0,
        "current_plan_steps": 9.5,
        "open_loops": 9.0,
        "commitments": 8.7,
        "constraints": 8.5,
        "active_assumptions": 8.2,
        "recent_errors": 8.0,
        "recent_recoveries": 7.8,
        "artifact_refs": 7.4,
        "cautions": 7.2,
        "verification_results": 7.0,
    }.get(section, 5.0)
    status_bonus = {
        "active": 0.6,
        "pending": 0.55,
        "blocked": 0.5,
        "open": 0.45,
        "resolved": 0.15,
        "completed": 0.1,
        "failed": 0.4,
        "superseded": -1.0,
        "archived": -1.2,
    }.get(status, 0.0)
    confidence = float(entry.get("confidence") or 0.0)
    return round(base + status_bonus + (confidence * 0.2), 4)


def _continuity_role_for_section(section: str) -> str:
    return {
        "unresolved_goals": "preserve",
        "current_plan_steps": "preserve",
        "open_loops": "preserve",
        "commitments": "preserve",
        "constraints": "preserve",
        "active_assumptions": "background",
        "recent_errors": "caution",
        "recent_recoveries": "background",
        "artifact_refs": "background",
        "cautions": "caution",
        "verification_results": "preserve",
    }.get(section, "background")


def _normalize_entry_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    raw_kind = str(normalized.get("entry_kind") or normalized.get("kind") or "")
    canonical_kind = _canonical_entry_kind(raw_kind)
    normalized["entry_kind"] = canonical_kind
    if raw_kind and raw_kind != canonical_kind:
        normalized.setdefault("original_entry_kind", raw_kind)
    normalized.setdefault("status", _default_status_for_kind(canonical_kind if canonical_kind else raw_kind))
    normalized.setdefault("scope", "session")
    metadata = dict(normalized.get("metadata") or {})
    if normalized.get("confidence") is None and metadata.get("confidence") is not None:
        normalized["confidence"] = metadata.get("confidence")
    normalized.setdefault("related_entry_ids", list(metadata.get("related_entry_ids") or []))
    normalized.setdefault("evidence_refs", list(metadata.get("evidence_refs") or []))
    normalized.setdefault("grounding_refs", list(metadata.get("grounding_refs") or metadata.get("resource_refs") or []))
    normalized.setdefault("parent_entry_id", metadata.get("parent_entry_id"))
    normalized.setdefault("scope", metadata.get("scope") or normalized.get("scope") or "session")
    normalized.setdefault("valid_until", metadata.get("valid_until"))
    return normalized


def _normalize_capture_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    if "kind" in normalized and "entry_kind" not in normalized:
        normalized["entry_kind"] = normalized["kind"]
    raw_kind = str(normalized.get("entry_kind") or "")
    canonical_kind = _canonical_entry_kind(raw_kind)
    normalized["entry_kind"] = canonical_kind
    metadata = dict(normalized.get("metadata") or {})
    if raw_kind and raw_kind != canonical_kind:
        metadata.setdefault("original_entry_kind", raw_kind)
    normalized["metadata"] = metadata
    if normalized.get("status") is None:
        normalized["status"] = _default_status_for_kind(canonical_kind)
    if normalized.get("confidence") is None and metadata.get("confidence") is not None:
        normalized["confidence"] = metadata.get("confidence")
    normalized.setdefault("related_entry_ids", list(metadata.get("related_entry_ids") or []))
    normalized.setdefault("evidence_refs", list(metadata.get("evidence_refs") or []))
    normalized.setdefault("grounding_refs", list(metadata.get("grounding_refs") or metadata.get("resource_refs") or []))
    normalized.setdefault("parent_entry_id", metadata.get("parent_entry_id"))
    normalized.setdefault("scope", metadata.get("scope") or normalized.get("scope") or "session")
    normalized.setdefault("valid_until", metadata.get("valid_until") or normalized.get("valid_until"))
    return normalized


def _normalize_entry_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    return LiveContextEntry.from_dict(record).to_dict()


def _canonical_entry_kind(value: str) -> str:
    if value in CANONICAL_LIVE_CONTEXT_ENTRY_KINDS:
        return value
    return LIVE_CONTEXT_ENTRY_KIND_ALIASES.get(value, value)


def _default_status_for_kind(kind: str) -> str:
    canonical = _canonical_entry_kind(kind)
    return {
        "goal": "active",
        "subgoal": "active",
        "plan_step": "active",
        "constraint": "active",
        "decision": "active",
        "assumption": "active",
        "artifact_ref": "active",
        "tool_state": "active",
        "error": "open",
        "recovery": "resolved",
        "open_question": "open",
        "verification_result": "resolved",
    }.get(canonical, "active")


def _reject_sensitive_content(content: str, sensitivity_hint: str) -> None:
    lowered = content.lower()
    if sensitivity_hint == "public" and any(marker in lowered for marker in ("secret=", "api_key=", "password=", "private transcript")):
        raise ValueError("public live context content appears to contain sensitive fixture text")


def _require_cell(value: PathLike, field_name: str) -> Path:
    path = Path(value).expanduser()
    if not (path / "config" / "cell_manifest.json").exists():
        raise ValueError(f"{field_name} is not a ShyftR cell: {path}")
    return path


def _read_cell_id(cell_path: Path) -> str:
    manifest = json.loads((cell_path / "config" / "cell_manifest.json").read_text(encoding="utf-8"))
    cell_id = manifest.get("cell_id")
    if not cell_id:
        raise ValueError("cell manifest is missing cell_id")
    return str(cell_id)


def _read_jsonl_if_exists(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [record for _, record in read_jsonl(path)]


def _count_jsonl(path: Path) -> int:
    return len(_read_jsonl_if_exists(path))


def _content_hash(runtime_id: str, session_id: str, entry_kind: str, content: str, status: str, parent_entry_id: Optional[str]) -> str:
    h = hashlib.sha256()
    h.update(runtime_id.encode())
    h.update(b"\0")
    h.update(session_id.encode())
    h.update(b"\0")
    h.update(entry_kind.encode())
    h.update(b"\0")
    h.update(status.encode())
    h.update(b"\0")
    h.update((parent_entry_id or "").encode())
    h.update(b"\0")
    h.update(" ".join(content.split()).encode())
    return h.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value


def _require_path_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value


def _require_choice(value: Any, choices: Sequence[str], field_name: str) -> None:
    if value not in choices:
        raise ValueError(f"{field_name} must be one of: {', '.join(choices)}")


def _bounded_int(value: Any, field_name: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum or value > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return value


def _bounded_float(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    numeric = float(value)
    if numeric < 0 or numeric > 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return numeric


def _validate_string_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} entries must be strings")


def _validate_optional_text(value: Any, field_name: str) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValueError(f"{field_name} must be a non-empty string when provided")


def _validate_optional_iso(value: Any, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an ISO timestamp when provided")
    _parse_iso(value)


def _known_fields(cls: Any, payload: Mapping[str, Any]) -> Dict[str, Any]:
    allowed = {field.name for field in cls.__dataclass_fields__.values()}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"Unknown field(s): {', '.join(unknown)}")
    return dict(payload)
