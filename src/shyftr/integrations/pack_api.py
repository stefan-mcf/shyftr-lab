"""Runtime Loadout request/response API for external agent runtimes.

Defines the stable JSON-serializable contract that external runtimes
use to request Loadouts and receive trust-labeled, provenance-linked
memory bundles.  This is the canonical RI-5 integration surface.

ShyftR doctrine:
  - Loadout is application; the Cell Boundary controls admission.
  - Returned memory is always trust-labeled and provenance-linked.
  - Responses are deterministic and schema-stable.
  - External runtimes never see raw ShyftR internals unless explicitly
    exported through this contract.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..pack import (
    AssembledLoadout,
    LoadoutItem,
    LoadoutTaskInput,
    assemble_loadout,
    estimate_tokens,
)


# ---------------------------------------------------------------------------
# Runtime Loadout Request
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeLoadoutRequest:
    """JSON-serializable Loadout request from an external runtime.

    Fields:
        cell_path_or_id: Path or unique identifier for the target Cell.
        query: Task or search text for memory retrieval.
        task_kind: Categorization of the kind of work (e.g. "code",
            "research", "debug").
        external_system: Identity of the calling runtime or adapter.
        external_scope: Logical scope within the external system.
        external_task_id: Runtime-local task identifier for correlation.
        tags: Optional free-form tags to refine retrieval.
        max_items: Maximum number of Loadout items to return (default 20).
        max_tokens: Maximum estimated token count (default 4000).
        requested_trust_tiers: Which trust tiers to include; defaults
            to all approved tiers (doctrine, trace, alloy). If empty or
            None, all approved tiers are included.
            Valid values: "doctrine", "trace", "alloy", "fragment".
        include_fragments: If True, include fragment-tier items
            (background-only unless explicitly requested).
    """

    cell_path_or_id: str
    query: str
    task_kind: Optional[str] = None
    external_system: str = "unknown"
    external_scope: str = "default"
    external_task_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    max_items: int = 20
    max_tokens: int = 4000
    requested_trust_tiers: List[str] = field(default_factory=list)
    include_fragments: bool = False
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    allowed_sensitivity: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_path_or_id": self.cell_path_or_id,
            "query": self.query,
            "task_kind": self.task_kind,
            "external_system": self.external_system,
            "external_scope": self.external_scope,
            "external_task_id": self.external_task_id,
            "tags": list(self.tags),
            "max_items": self.max_items,
            "max_tokens": self.max_tokens,
            "requested_trust_tiers": list(self.requested_trust_tiers),
            "include_fragments": self.include_fragments,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "allowed_sensitivity": list(self.allowed_sensitivity),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RuntimeLoadoutRequest":
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, payload: str) -> "RuntimeLoadoutRequest":
        return cls.from_dict(json.loads(payload))


# ---------------------------------------------------------------------------
# Runtime Loadout Response
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeLoadoutResponse:
    """JSON-serializable Loadout response for an external runtime.

    Items are pre-categorized into guidance, caution, background, and
    conflict groups so the runtime can apply them without parsing prose.

    Fields:
        loadout_id: Compatibility identifier for this loadout assembly event.
        request: The original request that produced this response.
        guidance_items: High-trust actionable guidance (doctrine, high-
            confidence traces). These are the primary memory the runtime
            should apply.
        caution_items: Warnings, anti-patterns, and traps the runtime
            should avoid or be aware of.
        background_items: Supporting context (traces, alloys, fragments)
            that may be useful but are not critical guidance.
        conflict_items: Items that have conflicting statements with
            other items in the loadout (detected heuristically).
        risk_flags: Boolean signals for common risk categories.
        selected_ids: Flat list of all item IDs in this response.
        score_traces: Per-item scoring provenance dictionary.
        total_items: Total number of items returned.
        total_tokens: Estimated total token count.
        generated_at: ISO-8601 timestamp of assembly.
    """

    loadout_id: str
    request: RuntimeLoadoutRequest
    guidance_items: List[Dict[str, Any]] = field(default_factory=list)
    caution_items: List[Dict[str, Any]] = field(default_factory=list)
    background_items: List[Dict[str, Any]] = field(default_factory=list)
    conflict_items: List[Dict[str, Any]] = field(default_factory=list)
    risk_flags: Dict[str, bool] = field(default_factory=dict)
    selected_ids: List[str] = field(default_factory=list)
    score_traces: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    total_items: int = 0
    total_tokens: int = 0
    generated_at: str = ""

    @property
    def pack_id(self) -> str:
        return self.loadout_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "loadout_id": self.loadout_id,
            "request": self.request.to_dict(),
            "guidance_items": list(self.guidance_items),
            "caution_items": list(self.caution_items),
            "background_items": list(self.background_items),
            "conflict_items": list(self.conflict_items),
            "risk_flags": dict(self.risk_flags),
            "selected_ids": list(self.selected_ids),
            "score_traces": dict(self.score_traces),
            "total_items": self.total_items,
            "total_tokens": self.total_tokens,
            "generated_at": self.generated_at,
            "logged_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RuntimeLoadoutResponse":
        request_data = payload.get("request", {})
        req = RuntimeLoadoutRequest.from_dict(request_data) if request_data else RuntimeLoadoutRequest(cell_path_or_id="", query="")
        return cls(
            loadout_id=payload.get("loadout_id") or payload.get("pack_id", ""),
            request=req,
            guidance_items=list(payload.get("guidance_items", [])),
            caution_items=list(payload.get("caution_items", [])),
            background_items=list(payload.get("background_items", [])),
            conflict_items=list(payload.get("conflict_items", [])),
            risk_flags=dict(payload.get("risk_flags", {})),
            selected_ids=list(payload.get("selected_ids", [])),
            score_traces=dict(payload.get("score_traces", {})),
            total_items=payload.get("total_items", 0),
            total_tokens=payload.get("total_tokens", 0),
            generated_at=payload.get("generated_at") or payload.get("logged_at", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, payload: str) -> "RuntimeLoadoutResponse":
        return cls.from_dict(json.loads(payload))


# ---------------------------------------------------------------------------
# Item categorization helpers
# ---------------------------------------------------------------------------

# Kinds that map to "caution" category
_CAUTION_KINDS: set = {
    "caution",
    "warning",
    "anti-pattern",
    "anti_pattern",
    "failure_signature",
    "supersession",
    "trap",
    "pitfall",
    "danger",
    "risk",
}

# Kinds that map to "guidance" category
_GUIDANCE_KINDS: set = {
    "guidance",
    "doctrine",
    "rule",
    "policy",
    "principle",
    "standard",
    "best-practice",
}

# Kinds that map to "conflict" category
_CONFLICT_KINDS: set = {
    "conflict",
    "contradiction",
    "disagreement",
    "exception",
}


def _categorize_item(item: LoadoutItem) -> str:
    """Return the category for a LoadoutItem: guidance, caution, background, or conflict."""
    if item.loadout_role in {"guidance", "caution", "background", "conflict"}:
        return item.loadout_role

    kind = (item.kind or "").lower()

    if kind in _CAUTION_KINDS:
        return "caution"
    if kind in _GUIDANCE_KINDS:
        return "guidance"
    if kind in _CONFLICT_KINDS:
        return "conflict"

    # Trust-tier based fallback for items without explicit kind
    if item.trust_tier == "doctrine":
        return "guidance"

    return "background"


def _detect_risk_flags(items: List[Dict[str, Any]]) -> Dict[str, bool]:
    """Detect common risk conditions from a list of serialized items."""
    flags: Dict[str, bool] = {
        "has_caution": False,
        "has_conflict": False,
        "low_confidence_items": False,
        "empty_loadout": False,
    }

    if not items:
        flags["empty_loadout"] = True
        return flags

    for item in items:
        confidence = item.get("confidence")
        if confidence is not None and confidence < 0.4:
            flags["low_confidence_items"] = True

    return flags


def _item_to_dict(item: LoadoutItem) -> Dict[str, Any]:
    """Serialize a LoadoutItem to a dict with stable provenance fields."""
    return {
        "item_id": item.item_id,
        "trust_tier": item.trust_tier,
        "statement": item.statement,
        "rationale": item.rationale,
        "tags": list(item.tags),
        "kind": item.kind,
        "confidence": item.confidence,
        "score": item.score,
        "loadout_role": item.loadout_role,
        "score_trace": dict(item.score_trace),
    }


def _conflict_detection(items: List[LoadoutItem]) -> set:
    """Simple heuristic conflict detection: items with kind='conflict' or
    conflicting trust_tier assignments on the same statement.  Returns set of
    item_ids that are flagged as conflicting."""
    conflict_ids: set = set()
    for item in items:
        kind = (item.kind or "").lower()
        if kind in _CONFLICT_KINDS:
            conflict_ids.add(item.item_id)

    # Also flag items whose statements directly contradict trusted items
    # (identified by statement-level overlap)
    guidance_statements: set = set()
    conflict_candidates: list = []
    for item in items:
        if _categorize_item(item) == "guidance":
            guidance_statements.add(item.statement.strip().lower())
        elif _categorize_item(item) == "conflict":
            conflict_candidates.append(item)

    for item in conflict_candidates:
        stmt = item.statement.strip().lower()
        for gs in guidance_statements:
            # Simple negation detection: if a guidance statement exists with
            # opposite assertion markers
            if stmt.startswith("do not ") or stmt.startswith("avoid "):
                negated = stmt.replace("do not ", "", 1).replace("avoid ", "", 1)
                if negated in gs or gs.startswith(negated):
                    conflict_ids.add(item.item_id)

    return conflict_ids


# ---------------------------------------------------------------------------
# Request processing
# ---------------------------------------------------------------------------


def process_runtime_loadout_request(request: RuntimeLoadoutRequest) -> RuntimeLoadoutResponse:
    """Process a RuntimeLoadoutRequest and return a RuntimeLoadoutResponse.

    This is the core integration entry point for RI-5.  It:

    1. Maps the runtime request to the internal LoadoutTaskInput schema.
    2. Calls assemble_loadout for scoring, filtering, and limit enforcement.
    3. Categorizes items into guidance/caution/background/conflict groups.
    4. Attaches risk flags.
    5. Returns a stable, schema-versioned response.
    """
    now = datetime.now(timezone.utc).isoformat()
    loadout_id = f"lo-{uuid.uuid4().hex[:12]}"

    # Map to internal task input
    task_input = LoadoutTaskInput(
        cell_path=request.cell_path_or_id,
        query=request.query,
        task_id=request.external_task_id or request.query[:40],
        max_items=request.max_items,
        max_tokens=request.max_tokens,
        include_fragments=request.include_fragments,
        requested_trust_tiers=request.requested_trust_tiers if request.requested_trust_tiers else None,
        query_kind=request.task_kind,
        query_tags=request.tags if request.tags else None,
        runtime_id=request.external_system,
        user_id=request.user_id,
        project_id=request.project_id or request.external_scope,
        allowed_sensitivity=request.allowed_sensitivity if request.allowed_sensitivity else None,
    )

    # Assemble the Loadout
    assembled = assemble_loadout(task_input)

    # Categorize items
    guidance_items: List[Dict[str, Any]] = []
    caution_items: List[Dict[str, Any]] = []
    background_items: List[Dict[str, Any]] = []
    conflict_items: List[Dict[str, Any]] = []

    conflict_ids = _conflict_detection(assembled.items)

    for item in assembled.items:
        item_dict = _item_to_dict(item)
        if item.item_id in conflict_ids:
            conflict_items.append(item_dict)
            continue
        category = _categorize_item(item)
        if category == "guidance":
            guidance_items.append(item_dict)
        elif category == "caution":
            caution_items.append(item_dict)
        elif category == "conflict":
            conflict_items.append(item_dict)
        else:
            background_items.append(item_dict)

    # Build risk flags from ALL categorized items
    risk_flags = _detect_risk_flags(
        guidance_items + caution_items + background_items + conflict_items
    )
    if caution_items:
        risk_flags["has_caution"] = True
    if conflict_items:
        risk_flags["has_conflict"] = True

    return RuntimeLoadoutResponse(
        loadout_id=assembled.loadout_id,
        request=request,
        guidance_items=guidance_items,
        caution_items=caution_items,
        background_items=background_items,
        conflict_items=conflict_items,
        risk_flags=risk_flags,
        selected_ids=assembled.retrieval_log.selected_ids,
        score_traces=assembled.retrieval_log.score_traces,
        total_items=assembled.total_items,
        total_tokens=assembled.total_tokens,
        generated_at=assembled.generated_at,
    )
