"""Live context optimization and session-close harvest support.

The live context cell is separate from the continuity cell and durable memory
cell. It captures high-churn working context during a runtime session, returns a
bounded advisory pack when asked, and classifies session-close entries into
reviewable harvest outputs. Mechanical prompt construction and compaction remain
owned by the runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union
import uuid

from .ledger import append_jsonl, read_jsonl
from .loadout import estimate_tokens

PathLike = Union[str, Path]

LIVE_CONTEXT_ENTRY_KINDS = (
    "active_goal",
    "active_plan",
    "active_artifact",
    "decision",
    "constraint",
    "failure",
    "recovery",
    "verification",
    "open_question",
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
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self) -> None:
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _require_text(self.task_id, "task_id")
        _require_text(self.entry_id, "entry_id")
        _require_choice(self.entry_kind, LIVE_CONTEXT_ENTRY_KINDS, "entry_kind")
        _require_text(self.content, "content")
        _require_text(self.created_at, "created_at")
        _require_text(self.source_ref, "source_ref")
        _require_choice(self.retention_hint, RETENTION_HINTS, "retention_hint")
        _require_choice(self.sensitivity_hint, SENSITIVITY_HINTS, "sensitivity_hint")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")

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
            "metadata": dict(self.metadata),
            "content_hash": self.content_hash or _content_hash(self.runtime_id, self.session_id, self.entry_kind, self.content),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiveContextEntry":
        return cls(**_known_fields(cls, payload))


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
    entry_id: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    write: bool = False

    def __post_init__(self) -> None:
        _require_path_text(self.cell_path, "cell_path")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _require_text(self.task_id, "task_id")
        _require_choice(self.entry_kind, LIVE_CONTEXT_ENTRY_KINDS, "entry_kind")
        _require_text(self.content, "content")
        _reject_sensitive_content(self.content, self.sensitivity_hint)
        _require_text(self.source_ref, "source_ref")
        _require_choice(self.retention_hint, RETENTION_HINTS, "retention_hint")
        _require_choice(self.sensitivity_hint, SENSITIVITY_HINTS, "sensitivity_hint")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")

    def to_entry(self) -> LiveContextEntry:
        content_hash = _content_hash(self.runtime_id, self.session_id, self.entry_kind, self.content)
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
            metadata=dict(self.metadata),
            content_hash=content_hash,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiveContextCaptureRequest":
        return cls(**_known_fields(cls, payload))


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
class HarvestDecision:
    entry_id: str
    bucket: str
    rationale: str
    confidence: float
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
    review_gated: bool = True

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
            "generated_at": self.generated_at,
            "review_gated": self.review_gated,
            "real_runtime_profile_touched": False,
        }


def capture_live_context(request: LiveContextCaptureRequest) -> Dict[str, Any]:
    cell = _require_cell(request.cell_path, "cell_path")
    entry = request.to_entry()
    existing = _find_entry_by_hash(cell, entry.content_hash, runtime_id=request.runtime_id, session_id=request.session_id)
    status = "dry_run" if not request.write else "ok"
    if existing is not None:
        return {"status": status, "write": bool(request.write), "deduped": True, "entry": existing}
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

    for entry in entries:
        if entry["entry_id"] in suppress_ids or _already_in_prompt(entry["content"], prompt_excerpts):
            duplicate_count += 1
            suppressed.append(_pack_stub(entry, "duplicate_or_current_prompt"))
            continue
        if _is_stale(entry):
            stale_count += 1
            excluded.append(_pack_stub(entry, "stale"))
            continue
        score = _entry_score(entry, query_terms)
        role = _pack_role(entry)
        candidate = {
            "entry_id": entry["entry_id"],
            "entry_kind": entry["entry_kind"],
            "role": role,
            "content": entry["content"],
            "source_ref": entry["source_ref"],
            "retention_hint": entry["retention_hint"],
            "sensitivity_hint": entry["sensitivity_hint"],
            "provenance": {"runtime_id": entry["runtime_id"], "session_id": entry["session_id"], "task_id": entry["task_id"], "entry_id": entry["entry_id"]},
            "token_estimate": estimate_tokens(entry["content"]),
            "score": score,
            "advisory_only": True,
        }
        candidates.append(candidate)

    candidates.sort(key=lambda item: (-_role_priority(item["role"]), -item["score"], item["entry_id"]))
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


def harvest_session(request: SessionHarvestRequest) -> SessionHarvestReport:
    live_cell = _require_cell(request.live_cell_path, "live_cell_path")
    continuity_cell = _require_cell(request.continuity_cell_path, "continuity_cell_path")
    memory_cell = _require_cell(request.memory_cell_path, "memory_cell_path")
    _ = memory_cell
    entries = _entries_for_session(live_cell, request.runtime_id, request.session_id)
    decisions = [_classify_entry(entry, allow_direct=request.allow_direct_durable_memory) for entry in entries]
    bucket_counts = {bucket: 0 for bucket in HARVEST_BUCKETS}
    for decision in decisions:
        bucket_counts[decision.bucket] += 1
    report = SessionHarvestReport(
        harvest_id=f"session-harvest-{request.runtime_id}-{request.session_id}",
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
    )
    if not request.write:
        return report
    if _harvest_already_written(live_cell, report.harvest_id):
        return report
    append_jsonl(live_cell / "ledger" / "session_harvests.jsonl", report.to_dict())
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
    for report in harvests:
        for bucket, count in dict(report.get("bucket_counts") or {}).items():
            if bucket in bucket_counts:
                bucket_counts[bucket] += int(count)
    return {
        "status": "ok",
        "pack_item_count": sum(int(p.get("total_items") or 0) for p in packs),
        "estimated_pack_tokens": sum(int(p.get("total_tokens") or 0) for p in packs),
        "duplicate_suppression_count": sum(int(p.get("duplicate_suppression_count") or 0) for p in packs),
        "stale_item_suppression_count": sum(int(p.get("stale_suppression_count") or 0) for p in packs),
        "harvest_bucket_counts": bucket_counts,
        "memory_proposal_count": sum(int(h.get("memory_proposal_count") or 0) for h in harvests),
        "continuity_improvement_proposal_count": sum(int(h.get("continuity_improvement_proposal_count") or 0) for h in harvests),
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
    metadata = dict(entry.get("metadata") or {})
    confidence = float(metadata.get("confidence", 0.72) or 0.72)
    if sensitivity in {"private", "sensitive"} and retention not in {"durable", "skill"}:
        return HarvestDecision(entry["entry_id"], "archive", "private/sensitive working context is archived for review instead of promoted", min(confidence, 0.65))
    if retention == "ephemeral":
        return HarvestDecision(entry["entry_id"], "discard", "entry retention hint is ephemeral", 0.95)
    if retention == "archive":
        return HarvestDecision(entry["entry_id"], "archive", "entry retention hint requests archive", 0.9)
    if retention == "skill" or kind == "recovery":
        return HarvestDecision(entry["entry_id"], "skill_proposal", "reusable recovery or skill-oriented context", max(confidence, 0.78))
    if kind in {"failure", "open_question"}:
        return HarvestDecision(entry["entry_id"], "continuity_feedback", "failure or open question can improve future continuity packs", max(confidence, 0.74))
    if retention == "durable" and sensitivity == "public" and allow_direct and confidence >= 0.92:
        return HarvestDecision(entry["entry_id"], "direct_durable_memory", "high-confidence public durable fact permitted by local policy", confidence)
    if retention in {"candidate", "durable"} or kind in {"decision", "constraint", "verification"}:
        return HarvestDecision(entry["entry_id"], "memory_candidate", "decision, constraint, verification, or durable hint becomes review-gated memory candidate", max(confidence, 0.8))
    return HarvestDecision(entry["entry_id"], "archive", "session context retained for reconstruction only", confidence)


def _proposal_from_decision(report: SessionHarvestReport, decision: HarvestDecision, entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    entry = next((e for e in entries if e.get("entry_id") == decision.entry_id), {})
    return {
        "proposal_id": f"session-harvest-proposal-{uuid.uuid4().hex}",
        "harvest_id": report.harvest_id,
        "runtime_id": report.runtime_id,
        "session_id": report.session_id,
        "entry_id": decision.entry_id,
        "bucket": decision.bucket,
        "statement": str(entry.get("content") or "")[:NOTE_CHAR_LIMIT],
        "rationale": decision.rationale,
        "confidence": decision.confidence,
        "review_gated": True,
        "created_at": report.generated_at,
    }


def _entries_for_session(cell: Path, runtime_id: str, session_id: str) -> List[Dict[str, Any]]:
    rows = _read_jsonl_if_exists(cell / "ledger" / "live_context_entries.jsonl")
    return [row for row in rows if row.get("runtime_id") == runtime_id and row.get("session_id") == session_id]


def _find_entry_by_hash(cell: Path, content_hash: str, *, runtime_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    for record in _read_jsonl_if_exists(cell / "ledger" / "live_context_entries.jsonl"):
        if record.get("content_hash") == content_hash and record.get("runtime_id") == runtime_id and record.get("session_id") == session_id:
            return record
    return None


def _pack_role(entry: Mapping[str, Any]) -> str:
    kind = entry.get("entry_kind")
    if kind in {"constraint", "verification", "decision"}:
        return "guidance"
    if kind in {"active_goal", "active_plan", "active_artifact", "recovery"}:
        return "current_state"
    if kind == "failure":
        return "caution"
    if kind == "open_question":
        return "open_question"
    return "current_state"


def _role_priority(role: str) -> int:
    return {"guidance": 4, "current_state": 3, "caution": 2, "open_question": 1}.get(role, 0)


def _entry_score(entry: Mapping[str, Any], query_terms: set[str]) -> float:
    content_terms = set(_terms(str(entry.get("content") or "")))
    if not query_terms:
        return 0.0
    overlap = len(query_terms & content_terms) / max(1, len(query_terms))
    recency = 0.05 if str(entry.get("retention_hint")) in {"session", "candidate", "durable"} else 0.0
    return round(overlap + recency, 4)


def _terms(text: str) -> List[str]:
    return [part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(part) > 2]


def _already_in_prompt(content: str, excerpts: Sequence[str]) -> bool:
    lowered = content.lower()
    return any(lowered in excerpt or excerpt in lowered for excerpt in excerpts if excerpt)


def _is_stale(entry: Mapping[str, Any]) -> bool:
    metadata = dict(entry.get("metadata") or {})
    return bool(metadata.get("stale") or metadata.get("superseded"))


def _pack_stub(item: Mapping[str, Any], reason: str) -> Dict[str, Any]:
    return {"entry_id": item.get("entry_id"), "reason": reason, "entry_kind": item.get("entry_kind")}


def _harvest_already_written(cell: Path, harvest_id: str) -> bool:
    return any(record.get("harvest_id") == harvest_id for record in _read_jsonl_if_exists(cell / "ledger" / "session_harvests.jsonl"))


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


def _content_hash(runtime_id: str, session_id: str, entry_kind: str, content: str) -> str:
    h = hashlib.sha256()
    h.update(runtime_id.encode())
    h.update(b"\0")
    h.update(session_id.encode())
    h.update(b"\0")
    h.update(entry_kind.encode())
    h.update(b"\0")
    h.update(" ".join(content.split()).encode())
    return h.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _validate_string_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} entries must be strings")


def _known_fields(cls: Any, payload: Mapping[str, Any]) -> Dict[str, Any]:
    allowed = {field.name for field in cls.__dataclass_fields__.values()}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"Unknown field(s): {', '.join(unknown)}")
    return dict(payload)
