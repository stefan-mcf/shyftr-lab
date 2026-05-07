"""Runtime-neutral continuity support for context compaction.

Continuity is separate from durable memory. A runtime keeps ownership of the
mechanical context compression step; ShyftR supplies a bounded, trust-labeled
continuity pack and records feedback about what helped, hurt, or was missing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import uuid

from .ledger import append_jsonl, read_jsonl
from .memory_classes import resolve_memory_type
from .live_context import latest_carry_state_checkpoint
from .pack import LoadoutTaskInput, assemble_loadout, estimate_tokens, is_operational_state

PathLike = Union[str, Path]

CONTINUITY_MODES = ("off", "shadow", "advisory")
RESERVED_MODES = ("authority",)
DEFAULT_MAX_ITEMS = 8
DEFAULT_MAX_TOKENS = 1200
MAX_ITEMS_LIMIT = 50
MAX_TOKENS_LIMIT = 12000


@dataclass(frozen=True)
class ContinuityPackRequest:
    """Request schema for an opt-in runtime continuity pack."""

    memory_cell_path: str
    continuity_cell_path: str
    runtime_id: str
    session_id: str
    compaction_id: str
    query: str
    trigger: str = "context_pressure"
    mode: str = "shadow"
    max_items: int = DEFAULT_MAX_ITEMS
    max_tokens: int = DEFAULT_MAX_TOKENS
    include_candidates: bool = False
    retrieval_mode: str = "balanced"
    live_cell_path: Optional[str] = None
    write: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_path_text(self.memory_cell_path, "memory_cell_path")
        _require_path_text(self.continuity_cell_path, "continuity_cell_path")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _require_text(self.compaction_id, "compaction_id")
        _require_text(self.query, "query")
        if self.mode in RESERVED_MODES:
            raise ValueError(f"mode {self.mode!r} is reserved for a future operator-gated work slice")
        if self.mode not in CONTINUITY_MODES:
            raise ValueError(f"mode must be one of: {', '.join(CONTINUITY_MODES)}")
        if not isinstance(self.max_items, int) or isinstance(self.max_items, bool) or self.max_items < 0 or self.max_items > MAX_ITEMS_LIMIT:
            raise ValueError(f"max_items must be between 0 and {MAX_ITEMS_LIMIT}")
        if not isinstance(self.max_tokens, int) or isinstance(self.max_tokens, bool) or self.max_tokens < 1 or self.max_tokens > MAX_TOKENS_LIMIT:
            raise ValueError(f"max_tokens must be between 1 and {MAX_TOKENS_LIMIT}")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_cell_path": self.memory_cell_path,
            "continuity_cell_path": self.continuity_cell_path,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "compaction_id": self.compaction_id,
            "query": self.query,
            "trigger": self.trigger,
            "mode": self.mode,
            "max_items": self.max_items,
            "max_tokens": self.max_tokens,
            "include_candidates": self.include_candidates,
            "retrieval_mode": self.retrieval_mode,
            "live_cell_path": self.live_cell_path,
            "write": self.write,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ContinuityPackRequest":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"Unknown field(s): {', '.join(unknown)}")
        return cls(**payload)


@dataclass(frozen=True)
class ContinuityItem:
    memory_id: str
    statement: str
    trust_tier: str
    kind: Optional[str]
    memory_type: Optional[str]
    confidence: Optional[float]
    score: float
    continuity_role: str
    rationale: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "statement": self.statement,
            "trust_tier": self.trust_tier,
            "kind": self.kind,
            "memory_type": self.memory_type,
            "confidence": self.confidence,
            "score": self.score,
            "continuity_role": self.continuity_role,
            "rationale": self.rationale,
            "tags": list(self.tags),
            "provenance": dict(self.provenance),
            "token_estimate": self.token_estimate,
        }


@dataclass(frozen=True)
class ContinuityPack:
    continuity_pack_id: str
    source_pack_id: Optional[str]
    source_memory_cell_id: str
    continuity_cell_id: str
    runtime_id: str
    session_id: str
    compaction_id: str
    mode: str
    status: str
    query: str
    trigger: str
    items: List[ContinuityItem]
    total_items: int
    total_tokens: int
    generated_at: str
    safety: Dict[str, Any]
    retrieval: Dict[str, Any]
    diagnostics: Dict[str, Any]
    carry_state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "continuity_pack_id": self.continuity_pack_id,
            "source_pack_id": self.source_pack_id,
            "source_memory_cell_id": self.source_memory_cell_id,
            "continuity_cell_id": self.continuity_cell_id,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "compaction_id": self.compaction_id,
            "mode": self.mode,
            "status": self.status,
            "query": self.query,
            "trigger": self.trigger,
            "items": [item.to_dict() for item in self.items],
            "total_items": self.total_items,
            "total_tokens": self.total_tokens,
            "generated_at": self.generated_at,
            "safety": dict(self.safety),
            "retrieval": dict(self.retrieval),
            "diagnostics": dict(self.diagnostics),
            "carry_state": dict(self.carry_state or {}),
        }


@dataclass(frozen=True)
class ContinuityFeedback:
    continuity_cell_path: str
    continuity_pack_id: str
    runtime_id: str
    session_id: str
    compaction_id: str
    result: str
    useful_memory_ids: List[str] = field(default_factory=list)
    harmful_memory_ids: List[str] = field(default_factory=list)
    ignored_memory_ids: List[str] = field(default_factory=list)
    missing_notes: List[str] = field(default_factory=list)
    promote_notes: List[str] = field(default_factory=list)
    write: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_path_text(self.continuity_cell_path, "continuity_cell_path")
        _require_text(self.continuity_pack_id, "continuity_pack_id")
        _require_text(self.runtime_id, "runtime_id")
        _require_text(self.session_id, "session_id")
        _require_text(self.compaction_id, "compaction_id")
        _require_text(self.result, "result")
        for field_name in ("useful_memory_ids", "harmful_memory_ids", "ignored_memory_ids", "missing_notes", "promote_notes"):
            _validate_string_list(getattr(self, field_name), field_name)
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "continuity_cell_path": self.continuity_cell_path,
            "continuity_pack_id": self.continuity_pack_id,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "compaction_id": self.compaction_id,
            "result": self.result,
            "useful_memory_ids": list(self.useful_memory_ids),
            "harmful_memory_ids": list(self.harmful_memory_ids),
            "ignored_memory_ids": list(self.ignored_memory_ids),
            "missing_notes": list(self.missing_notes),
            "promote_notes": list(self.promote_notes),
            "write": self.write,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ContinuityFeedback":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"Unknown field(s): {', '.join(unknown)}")
        return cls(**payload)


class ContinuityProvider:
    """Small facade for runtimes embedding ShyftR continuity support."""

    def __init__(self, memory_cell_path: PathLike, continuity_cell_path: PathLike):
        self.memory_cell_path = str(memory_cell_path)
        self.continuity_cell_path = str(continuity_cell_path)

    def pack(self, *, runtime_id: str, session_id: str, compaction_id: str, query: str, **kwargs: Any) -> ContinuityPack:
        return assemble_continuity_pack(
            ContinuityPackRequest(
                memory_cell_path=self.memory_cell_path,
                continuity_cell_path=self.continuity_cell_path,
                runtime_id=runtime_id,
                session_id=session_id,
                compaction_id=compaction_id,
                query=query,
                **kwargs,
            )
        )

    def feedback(self, *, continuity_pack_id: str, runtime_id: str, session_id: str, compaction_id: str, result: str, **kwargs: Any) -> Dict[str, Any]:
        return record_continuity_feedback(
            ContinuityFeedback(
                continuity_cell_path=self.continuity_cell_path,
                continuity_pack_id=continuity_pack_id,
                runtime_id=runtime_id,
                session_id=session_id,
                compaction_id=compaction_id,
                result=result,
                **kwargs,
            )
        )


def assemble_continuity_pack(request: ContinuityPackRequest) -> ContinuityPack:
    """Build a bounded continuity pack and optionally append continuity ledgers."""
    memory_cell = _require_cell(request.memory_cell_path, "memory_cell_path")
    continuity_cell = _require_cell(request.continuity_cell_path, "continuity_cell_path")
    source_memory_cell_id = _read_cell_id(memory_cell)
    continuity_cell_id = _read_cell_id(continuity_cell)
    generated_at = _now()
    continuity_pack_id = f"continuity-pack-{uuid.uuid4().hex}"

    if request.mode == "off":
        pack = ContinuityPack(
            continuity_pack_id=continuity_pack_id,
            source_pack_id=None,
            source_memory_cell_id=source_memory_cell_id,
            continuity_cell_id=continuity_cell_id,
            runtime_id=request.runtime_id,
            session_id=request.session_id,
            compaction_id=request.compaction_id,
            mode=request.mode,
            status="disabled",
            query=request.query,
            trigger=request.trigger,
            items=[],
            total_items=0,
            total_tokens=0,
            generated_at=generated_at,
            safety=_safety(mode=request.mode, exported=False),
            retrieval={"selected_memory_ids": []},
            diagnostics={"reason": "continuity mode off"},
        )
        if request.write:
            _write_pack_ledgers(continuity_cell, request, pack, raw_candidate_count=0)
        return pack

    loadout = assemble_loadout(
        LoadoutTaskInput(
            cell_path=str(memory_cell),
            query=request.query,
            task_id=request.compaction_id,
            max_items=request.max_items,
            max_tokens=request.max_tokens,
            include_fragments=request.include_candidates,
            retrieval_mode=request.retrieval_mode,
            runtime_id=request.runtime_id,
            dry_run=not request.write,
        )
    )
    memory_items = [_continuity_item_from_loadout(item.to_dict()) for item in loadout.items]
    memory_items = [item for item in memory_items if not is_operational_state(item.statement)]
    carry_checkpoint = None
    carry_items: List[ContinuityItem] = []
    if request.live_cell_path:
        carry_checkpoint = latest_carry_state_checkpoint(
            request.continuity_cell_path,
            runtime_id=request.runtime_id,
            session_id=request.session_id,
        )
        if carry_checkpoint is None:
            from .live_context import build_carry_state_checkpoint, CarryStateCheckpointRequest
            carry_checkpoint = build_carry_state_checkpoint(
                CarryStateCheckpointRequest(
                    live_cell_path=request.live_cell_path,
                    continuity_cell_path=request.continuity_cell_path,
                    runtime_id=request.runtime_id,
                    session_id=request.session_id,
                    max_items=request.max_items,
                    max_tokens=request.max_tokens,
                    write=request.write,
                    metadata={"trigger": request.trigger, **dict(request.metadata)},
                )
            )
        carry_items = [_continuity_item_from_carry(item) for item in carry_checkpoint.continuity_items()]
    raw_items = _merge_continuity_sources(carry_items, memory_items)

    if request.mode == "shadow":
        exported_items = []
        total_tokens = 0
        exported = False
    else:
        exported_items = _enforce_bounds(raw_items, max_items=request.max_items, max_tokens=request.max_tokens)
        total_tokens = sum(item.token_estimate for item in exported_items)
        exported = True

    pack = ContinuityPack(
        continuity_pack_id=continuity_pack_id,
        source_pack_id=loadout.loadout_id,
        source_memory_cell_id=source_memory_cell_id,
        continuity_cell_id=continuity_cell_id,
        runtime_id=request.runtime_id,
        session_id=request.session_id,
        compaction_id=request.compaction_id,
        mode=request.mode,
        status="ok",
        query=request.query,
        trigger=request.trigger,
        items=exported_items,
        total_items=len(exported_items),
        total_tokens=total_tokens,
        generated_at=generated_at,
        safety=_safety(mode=request.mode, exported=exported),
        retrieval={
            "source_retrieval_id": loadout.retrieval_log.retrieval_id,
            "source_pack_id": loadout.loadout_id,
            "selected_memory_ids": [item.memory_id for item in exported_items],
            "shadow_candidate_ids": [item.memory_id for item in raw_items],
        },
        diagnostics={
            "shadow_candidate_count": len(raw_items),
            "suppressed_for_bounds": max(0, len(raw_items) - len(exported_items)),
            "mode": request.mode,
            "memory_candidate_count": len(memory_items),
            "carry_candidate_count": len(carry_items),
        },
        carry_state=carry_checkpoint.to_dict() if carry_checkpoint is not None else None,
    )
    if request.write:
        _write_pack_ledgers(continuity_cell, request, pack, raw_candidate_count=len(raw_items))
    return pack


def record_continuity_feedback(feedback: ContinuityFeedback) -> Dict[str, Any]:
    """Preview or append feedback about a continuity pack."""
    continuity_cell = _require_cell(feedback.continuity_cell_path, "continuity_cell_path")
    now = _now()
    event_id = f"continuity-feedback-{uuid.uuid4().hex}"
    preview = {
        "status": "dry_run" if not feedback.write else "ok",
        "write": bool(feedback.write),
        "event_id": event_id,
        "continuity_pack_id": feedback.continuity_pack_id,
        "runtime_id": feedback.runtime_id,
        "result": feedback.result,
        "useful_memory_ids": list(feedback.useful_memory_ids),
        "harmful_memory_ids": list(feedback.harmful_memory_ids),
        "ignored_memory_ids": list(feedback.ignored_memory_ids),
        "missing_notes": list(feedback.missing_notes),
        "promotion_proposals": len(feedback.promote_notes),
        "review_gated": True,
    }
    if not feedback.write:
        return preview

    record = {
        "event_id": event_id,
        "event_type": "continuity_feedback_recorded",
        "continuity_pack_id": feedback.continuity_pack_id,
        "runtime_id": feedback.runtime_id,
        "session_id": feedback.session_id,
        "compaction_id": feedback.compaction_id,
        "result": feedback.result,
        "useful_memory_ids": list(feedback.useful_memory_ids),
        "harmful_memory_ids": list(feedback.harmful_memory_ids),
        "ignored_memory_ids": list(feedback.ignored_memory_ids),
        "missing_notes": list(feedback.missing_notes),
        "metadata": dict(feedback.metadata),
        "recorded_at": now,
    }
    append_jsonl(continuity_cell / "ledger" / "continuity_feedback.jsonl", record)
    append_jsonl(continuity_cell / "ledger" / "continuity_events.jsonl", record)

    for note in feedback.promote_notes:
        proposal = {
            "proposal_id": f"continuity-promotion-{uuid.uuid4().hex}",
            "continuity_pack_id": feedback.continuity_pack_id,
            "runtime_id": feedback.runtime_id,
            "session_id": feedback.session_id,
            "compaction_id": feedback.compaction_id,
            "statement": note,
            "status": "proposed",
            "review_gated": True,
            "created_at": now,
        }
        append_jsonl(continuity_cell / "ledger" / "continuity_promotion_proposals.jsonl", proposal)
    return preview


def evaluate_synthetic_continuity(
    *,
    memory_cell_path: PathLike,
    continuity_cell_path: PathLike,
    runtime_id: str,
    task_id: str,
    query: str,
    expected_terms: Sequence[str],
    max_items: int = DEFAULT_MAX_ITEMS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    write: bool = False,
) -> Dict[str, Any]:
    """Run a deterministic synthetic continuity fixture.

    The fixture validates whether an advisory continuity pack contains the
    expected terms, stays within bounds, and avoids operational-state pollution.
    """
    expected = [term.strip().lower() for term in expected_terms if str(term).strip()]
    if not expected:
        raise ValueError("expected_terms must contain at least one term")
    pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell_path),
            continuity_cell_path=str(continuity_cell_path),
            runtime_id=runtime_id,
            session_id=f"synthetic-{task_id}",
            compaction_id=f"synthetic-{task_id}",
            query=query,
            trigger="synthetic_eval",
            mode="advisory",
            max_items=max_items,
            max_tokens=max_tokens,
            write=write,
            metadata={"synthetic_eval": True, "task_id": task_id},
        )
    )
    joined = "\n".join(item.statement.lower() for item in pack.items)
    matched = [term for term in expected if term in joined]
    noise = [item.memory_id for item in pack.items if is_operational_state(item.statement)]
    coverage = len(matched) / len(expected)
    status = "pass" if coverage >= 1.0 and not noise and pack.total_tokens <= max_tokens and pack.total_items <= max_items else "fail"
    report = {
        "status": status,
        "task_id": task_id,
        "runtime_id": runtime_id,
        "coverage": coverage,
        "matched_terms": matched,
        "missing_terms": [term for term in expected if term not in matched],
        "noise_count": len(noise),
        "noise_memory_ids": noise,
        "token_limit": max_tokens,
        "item_limit": max_items,
        "pack": pack.to_dict(),
        "generated_at": _now(),
    }
    if write:
        continuity_cell = _require_cell(continuity_cell_path, "continuity_cell_path")
        append_jsonl(continuity_cell / "ledger" / "continuity_eval_reports.jsonl", report)
    return report


def continuity_status(continuity_cell_path: PathLike) -> Dict[str, Any]:
    """Summarize continuity ledgers for diagnostics and hardening checks."""
    cell = _require_cell(continuity_cell_path, "continuity_cell_path")
    ledgers = {
        "packs": cell / "ledger" / "continuity_packs.jsonl",
        "feedback": cell / "ledger" / "continuity_feedback.jsonl",
        "checkpoints": cell / "ledger" / "continuity_checkpoints.jsonl",
        "promotion_proposals": cell / "ledger" / "continuity_promotion_proposals.jsonl",
        "eval_reports": cell / "ledger" / "continuity_eval_reports.jsonl",
    }
    counts = {name: _count_jsonl(path) for name, path in ledgers.items()}
    return {
        "status": "ok",
        "continuity_cell_id": _read_cell_id(cell),
        "cell_path": str(cell),
        "counts": counts,
        "review_gated_promotions": True,
        "supported_modes": list(CONTINUITY_MODES),
        "reserved_modes": list(RESERVED_MODES),
    }


def _continuity_item_from_loadout(item: Dict[str, Any]) -> ContinuityItem:
    role = str(item.get("loadout_role") or "background")
    continuity_role = {
        "guidance": "preserve",
        "caution": "caution",
        "background": "background",
        "conflict": "conflict",
    }.get(role, "background")
    statement = str(item.get("statement") or "")
    return ContinuityItem(
        memory_id=str(item.get("item_id") or ""),
        statement=statement,
        trust_tier=str(item.get("trust_tier") or "trace"),
        kind=item.get("kind"),
        memory_type=resolve_memory_type(item.get("memory_type"), kind=item.get("kind"), trust_tier=item.get("trust_tier")),
        confidence=item.get("confidence"),
        score=float(item.get("score") or 0.0),
        continuity_role=continuity_role,
        rationale=item.get("rationale"),
        tags=list(item.get("tags") or []),
        provenance={"score_trace": item.get("score_trace") or {}, "graph_context": item.get("graph_context") or []},
        token_estimate=estimate_tokens(statement),
    )



def _continuity_item_from_carry(item: Dict[str, Any]) -> ContinuityItem:
    provenance = dict(item.get("provenance") or {})
    entry_id = provenance.get("entry_id") or item.get("entry_id") or "carry-item"
    statement = str(item.get("statement") or "")
    tags = [f"section:{item.get('section')}" if item.get("section") else "section:unknown", "source:carry_state"]
    return ContinuityItem(
        memory_id=str(entry_id),
        statement=statement,
        trust_tier="session",
        kind=item.get("entry_kind"),
        memory_type=resolve_memory_type(item.get("memory_type"), entry_kind=item.get("entry_kind"), retention_hint=item.get("retention_hint")),
        confidence=item.get("confidence"),
        score=float(item.get("score") or 0.0) + 5.0,
        continuity_role=str(item.get("continuity_role") or "background"),
        rationale=f"carry_state:{item.get('section')}",
        tags=tags,
        provenance={"carry_state": True, **provenance},
        token_estimate=int(item.get("token_estimate") or estimate_tokens(statement)),
    )


def _merge_continuity_sources(carry_items: Sequence[ContinuityItem], memory_items: Sequence[ContinuityItem]) -> List[ContinuityItem]:
    merged: List[ContinuityItem] = []
    seen: set[str] = set()
    for item in list(carry_items) + list(memory_items):
        key = " ".join(item.statement.lower().split())
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    merged.sort(key=lambda current: (0 if current.provenance.get("carry_state") else 1, -current.score, current.memory_id))
    return merged


def _enforce_bounds(items: Sequence[ContinuityItem], *, max_items: int, max_tokens: int) -> List[ContinuityItem]:
    selected: List[ContinuityItem] = []
    running_tokens = 0
    for item in items:
        if len(selected) >= max_items:
            break
        next_tokens = running_tokens + item.token_estimate
        if next_tokens > max_tokens:
            continue
        selected.append(item)
        running_tokens = next_tokens
    return selected


def _write_pack_ledgers(continuity_cell: Path, request: ContinuityPackRequest, pack: ContinuityPack, *, raw_candidate_count: int) -> None:
    event = {
        "event_id": f"continuity-event-{uuid.uuid4().hex}",
        "event_type": "continuity_pack_requested",
        "continuity_pack_id": pack.continuity_pack_id,
        "source_pack_id": pack.source_pack_id,
        "runtime_id": request.runtime_id,
        "session_id": request.session_id,
        "compaction_id": request.compaction_id,
        "mode": request.mode,
        "trigger": request.trigger,
        "query": request.query,
        "raw_candidate_count": raw_candidate_count,
        "exported_item_count": pack.total_items,
        "metadata": dict(request.metadata),
        "recorded_at": pack.generated_at,
    }
    append_jsonl(continuity_cell / "ledger" / "continuity_events.jsonl", event)
    append_jsonl(continuity_cell / "ledger" / "continuity_packs.jsonl", pack.to_dict())


def _safety(*, mode: str, exported: bool) -> Dict[str, Any]:
    return {
        "authority": mode,
        "exported_to_runtime": exported,
        "mechanical_compression_owner": "runtime",
        "durable_memory_mutation": False,
        "promotion_requires_review": True,
        "reserved_authority_mode_enabled": False,
    }


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


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _line, _record in read_jsonl(path))


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


def _validate_string_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} entries must be non-empty strings")
