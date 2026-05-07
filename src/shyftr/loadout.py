"""Bounded memory Loadout assembly for ShyftR agents.

Builds trust-labeled, token-bounded memory packages from Cell ledgers
before agent execution.  Each Loadout item carries explicit trust tier
and provenance; raw operational state is rejected; Fragments are
background-only unless explicitly requested.

ShyftR doctrine: JSONL ledgers are canonical truth; retrieval/index
layers are rebuildable acceleration; Loadout is application.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from .decay import score_memory_decay
from .ledger import append_jsonl, read_jsonl
from .mutations import active_charge_ids
from .frontier import project_confidence_state
from .policy import check_source_boundary  # noqa: F401 (re-exported for downstream)
from .privacy import AccessPolicy, is_charge_export_allowed
from .retrieval.hybrid import (
    NEGATIVE_SPACE_KINDS,
    CandidateItem,
)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Operational state detection (reuses boundary-policy patterns)
# ---------------------------------------------------------------------------

_POLLUTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "transient task or queue status",
        re.compile(
            r"\b(queue item|queue status|worker_summary|pending_manager_pickup|in_progress|awaiting_manager_review|dependency_blocked)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "branch or worktree state",
        re.compile(r"\b(branch|worktree|git status|HEAD|task/[A-Za-z0-9_.-]+|SANDBOX/active)\b", re.IGNORECASE),
    ),
    (
        "artifact path as memory",
        re.compile(
            r"\b(artifact path|worker_runs|worker_manager_returns|CHASSIS/runtime|/Users/[^\s]+|/tmp/[^\s]+|\.log\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "completion or closeout log",
        re.compile(r"\b(completion log|closeout|completed successfully|saving session|exit code)\b", re.IGNORECASE),
    ),
    (
        "unsupported verification claim",
        re.compile(r"\b(tests passed|verification (is )?complete|verified complete|all checks passed)\b", re.IGNORECASE),
    ),
)


def is_operational_state(text: str) -> bool:
    """Return True if *text* matches any operational-state pollution pattern."""
    if not isinstance(text, str) or not text.strip():
        return False
    for _reason, pattern in _POLLUTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Token estimation (deterministic whitespace-based)
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Deterministic whitespace-based token count approximation."""
    if not text:
        return 0
    return len(text.split())


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", str(value or "").lower()))


def _query_sparse_score(query: str, candidate: CandidateItem) -> float:
    """Return a simple lexical score for loadout query relevance.

    Loadout candidates are assembled directly from ledgers, so they may not
    arrive with sparse/vector scores already populated. This deterministic
    score keeps pack assembly query-sensitive without depending on rebuildable
    indexes.
    """
    query_terms = _terms(query)
    if not query_terms:
        return 0.0
    haystack = " ".join(
        [
            candidate.statement,
            candidate.rationale or "",
            candidate.kind or "",
            " ".join(candidate.tags),
        ]
    )
    overlap = query_terms & _terms(haystack)
    if not overlap:
        return 0.0
    return min(1.0, len(overlap) / max(len(query_terms), 1))


def _apply_query_sparse_scores(query: str, candidates: Sequence[CandidateItem]) -> List[CandidateItem]:
    if not query or not query.strip():
        return list(candidates)
    scored: List[CandidateItem] = []
    for candidate in candidates:
        score = _query_sparse_score(query, candidate)
        if score <= candidate.sparse_score:
            scored.append(candidate)
        else:
            scored.append(replace(candidate, sparse_score=score))
    return scored


# ---------------------------------------------------------------------------
# Task input schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LoadoutTaskInput:
    """Task input schema for Loadout assembly."""

    cell_path: str
    query: str
    task_id: str
    max_items: int = 20
    max_tokens: int = 4000
    include_fragments: bool = False
    requested_trust_tiers: Optional[List[str]] = None
    query_kind: Optional[str] = None
    query_tags: Optional[List[str]] = None
    caution_max_items: int = 3
    audit_mode: bool = False
    retrieval_mode: str = "balanced"
    dry_run: bool = False
    runtime_id: str = "default"
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    allowed_sensitivity: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_path": self.cell_path,
            "query": self.query,
            "task_id": self.task_id,
            "max_items": self.max_items,
            "max_tokens": self.max_tokens,
            "include_fragments": self.include_fragments,
            "requested_trust_tiers": self.requested_trust_tiers,
            "query_kind": self.query_kind,
            "query_tags": self.query_tags,
            "caution_max_items": self.caution_max_items,
            "audit_mode": self.audit_mode,
            "retrieval_mode": self.retrieval_mode,
            "dry_run": self.dry_run,
            "runtime_id": self.runtime_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "allowed_sensitivity": self.allowed_sensitivity,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "LoadoutTaskInput":
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Loadout item
# ---------------------------------------------------------------------------

LOADOUT_ROLES = (
    "guidance",
    "caution",
    "background",
    "conflict",
)

_GUIDANCE_KINDS = {"guidance", "success_pattern", "recovery_pattern", "verification_heuristic", "workflow", "error"}
_CAUTION_KINDS = {"caution", "warning", "failure_signature", "anti_pattern", "anti-pattern", "supersession", "risk", "pitfall", "trap"}
_BACKGROUND_KINDS = {"alloy", "doctrine", "observation", "fragment", "context"}
_CONFLICT_KINDS = {"conflict", "contradiction", "disagreement"}


def _compute_loadout_role(kind: Optional[str], selection_reason: Optional[str] = None, trust_tier: Optional[str] = None) -> str:
    """Map retrieval semantics onto Pack/Loadout roles."""
    reason = str(selection_reason or "").strip().lower()
    normalized_kind = str(kind or "").strip().lower().replace("_", "-")

    if reason == "conflict" or normalized_kind in _CONFLICT_KINDS:
        return "conflict"
    if reason == "caution" or normalized_kind in _CAUTION_KINDS:
        return "caution"
    if reason == "positive_guidance" or normalized_kind in _GUIDANCE_KINDS:
        return "guidance"
    if normalized_kind in _BACKGROUND_KINDS or trust_tier in {"alloy", "fragment"}:
        return "background"
    if trust_tier == "doctrine":
        return "guidance"
    return "background"


@dataclass(frozen=True)
class LoadoutItem:
    """A single item in a Loadout with trust tier and provenance."""

    item_id: str
    trust_tier: str
    statement: str
    rationale: Optional[str]
    tags: List[str]
    kind: Optional[str]
    confidence: Optional[float]
    score: float
    score_trace: Dict[str, Any]
    loadout_role: Optional[str] = None
    graph_context: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "trust_tier": self.trust_tier,
            "statement": self.statement,
            "rationale": self.rationale,
            "tags": self.tags,
            "kind": self.kind,
            "confidence": self.confidence,
            "score": self.score,
            "score_trace": self.score_trace,
            "loadout_role": self.loadout_role,
            "graph_context": list(self.graph_context),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "LoadoutItem":
        data = dict(payload)
        if "pack_role" in data and "loadout_role" not in data:
            data["loadout_role"] = data["pack_role"]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Retrieval log
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetrievalLog:
    """Retrieval log with selected IDs, score traces, and retrieval_id."""

    retrieval_id: str = ""
    loadout_id: Optional[str] = None
    selected_ids: List[str] = field(default_factory=list)
    score_traces: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    query: str = ""
    generated_at: str = ""
    candidate_ids: List[str] = field(default_factory=list)
    caution_ids: List[str] = field(default_factory=list)
    suppressed_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retrieval_id": self.retrieval_id,
            "loadout_id": self.loadout_id,
            "selected_ids": self.selected_ids,
            "score_traces": self.score_traces,
            "query": self.query,
            "generated_at": self.generated_at,
            "candidate_ids": list(self.candidate_ids),
            "caution_ids": list(self.caution_ids),
            "suppressed_ids": list(self.suppressed_ids),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RetrievalLog":
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Assembled loadout
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssembledLoadout:
    """A fully assembled Loadout with items, limits, and retrieval log."""

    loadout_id: str
    cell_id: str
    task_id: str
    items: List[LoadoutItem]
    total_tokens: int
    total_items: int
    retrieval_log: RetrievalLog
    generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loadout_id": self.loadout_id,
            "cell_id": self.cell_id,
            "task_id": self.task_id,
            "items": [i.to_dict() for i in self.items],
            "total_tokens": self.total_tokens,
            "total_items": self.total_items,
            "retrieval_log": self.retrieval_log.to_dict(),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AssembledLoadout":
        items = [LoadoutItem.from_dict(i) for i in payload.get("items", [])]
        log = RetrievalLog.from_dict(payload.get("retrieval_log", {}))
        return cls(
            loadout_id=payload["loadout_id"],
            cell_id=payload["cell_id"],
            task_id=payload["task_id"],
            items=items,
            total_tokens=payload["total_tokens"],
            total_items=payload["total_items"],
            retrieval_log=log,
            generated_at=payload["generated_at"],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def guidance_items(self) -> List[LoadoutItem]:
        """Actionable guidance items in deterministic Loadout order."""
        return [item for item in self.items if item.loadout_role == "guidance"]

    @property
    def caution_items(self) -> List[LoadoutItem]:
        """Warnings and negative-space items in deterministic Loadout order."""
        return [item for item in self.items if item.loadout_role == "caution"]

    @property
    def background_items(self) -> List[LoadoutItem]:
        """Supporting context items in deterministic Loadout order."""
        return [item for item in self.items if item.loadout_role == "background"]

    @property
    def conflict_items(self) -> List[LoadoutItem]:
        """Conflict-labeled items in deterministic Loadout order."""
        return [item for item in self.items if item.loadout_role == "conflict"]

    @classmethod
    def from_json(cls, payload: str) -> "AssembledLoadout":
        return cls.from_dict(json.loads(payload))


# ---------------------------------------------------------------------------
# Cell data readers
# ---------------------------------------------------------------------------

def _read_cell_id(cell_path: Path) -> str:
    """Read cell_id from the Cell manifest."""
    manifest_path = cell_path / "config" / "cell_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Cell manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cell_id = manifest.get("cell_id")
    if not cell_id:
        raise ValueError("Cell manifest is missing cell_id")
    return str(cell_id)


def _read_traces(cell_path: Path) -> List[Dict[str, Any]]:
    """Read approved traces from traces/approved.jsonl."""
    ledger = cell_path / "traces" / "approved.jsonl"
    if not ledger.exists():
        return []
    return [record for _, record in read_jsonl(ledger) if record.get("status", "approved") == "approved"]


def _read_alloys(cell_path: Path) -> List[Dict[str, Any]]:
    """Read approved alloys from alloys/approved.jsonl."""
    ledger = cell_path / "alloys" / "approved.jsonl"
    if not ledger.exists():
        return []
    return [record for _, record in read_jsonl(ledger) if record.get("proposal_status", "approved") == "approved"]


def _read_doctrine(cell_path: Path) -> List[Dict[str, Any]]:
    """Read approved public rules and compatibility doctrine."""
    records: List[Dict[str, Any]] = []
    for ledger in (cell_path / "ledger" / "rules" / "approved.jsonl", cell_path / "doctrine" / "approved.jsonl"):
        if not ledger.exists():
            continue
        for _, record in read_jsonl(ledger):
            if record.get("review_status", "approved") == "approved":
                records.append(record)
    return records


def _read_fragments(cell_path: Path) -> List[Dict[str, Any]]:
    """Read fragments from ledger/fragments.jsonl."""
    ledger = cell_path / "ledger" / "fragments.jsonl"
    if not ledger.exists():
        return []
    return [record for _, record in read_jsonl(ledger)]


# ---------------------------------------------------------------------------
# Candidate building
# ---------------------------------------------------------------------------

def _build_candidate_from_trace(record: Dict[str, Any]) -> CandidateItem:
    """Convert a trace record to a CandidateItem.

    AL-2: if the trace ``kind`` is a negative-space kind
    (failure_signature, anti_pattern, supersession), ``negative_space_kind``
    is set on the candidate.
    """
    kind = record.get("kind")
    negative_space_kind = kind if (kind and str(kind).lower() in NEGATIVE_SPACE_KINDS) else None
    decay_score = score_memory_decay(record).combined
    return CandidateItem(
        item_id=record.get("trace_id", ""),
        cell_id=record.get("cell_id", ""),
        trust_tier="trace",
        statement=record.get("statement", ""),
        rationale=record.get("rationale"),
        tags=record.get("tags", []),
        kind=kind,
        status=record.get("status", "approved"),
        confidence=record.get("confidence"),
        success_count=record.get("success_count", 0),
        failure_count=record.get("failure_count", 0),
        decay=decay_score,
        negative_space_kind=negative_space_kind,
        related_positive_ids=record.get("related_positive_ids", []),
    )


def _build_candidate_from_alloy(record: Dict[str, Any]) -> CandidateItem:
    """Convert an alloy record to a CandidateItem."""
    return CandidateItem(
        item_id=record.get("alloy_id", ""),
        cell_id=record.get("cell_id", ""),
        trust_tier="alloy",
        statement=record.get("summary", ""),
        rationale=record.get("theme"),
        tags=[],
        kind="alloy",
        status=record.get("proposal_status", "approved"),
        confidence=record.get("confidence"),
    )


def _build_candidate_from_doctrine(record: Dict[str, Any]) -> CandidateItem:
    """Convert an approved rule/doctrine record to a CandidateItem."""
    source_cells = record.get("source_cell_ids") or []
    return CandidateItem(
        item_id=record.get("rule_id") or record.get("doctrine_id", ""),
        cell_id=record.get("cell_id") or (source_cells[0] if source_cells else ""),
        trust_tier="doctrine",
        statement=record.get("statement", ""),
        rationale=record.get("scope") or record.get("proposed_scope"),
        tags=record.get("tags", []),
        kind="doctrine",
        status=record.get("review_status", "approved"),
        confidence=(record.get("confidence_summary") or {}).get("max_score") if isinstance(record.get("confidence_summary"), dict) else None,
    )


def _build_candidate_from_fragment(record: Dict[str, Any]) -> CandidateItem:
    """Convert a fragment record to a CandidateItem.

    AL-2: if the fragment ``kind`` is a negative-space kind,
    ``negative_space_kind`` is set on the candidate.
    """
    kind = record.get("kind")
    negative_space_kind = kind if (kind and str(kind).lower() in NEGATIVE_SPACE_KINDS) else None
    return CandidateItem(
        item_id=record.get("fragment_id", ""),
        cell_id=record.get("cell_id", ""),
        trust_tier="fragment",
        statement=record.get("text", ""),
        rationale=None,
        tags=record.get("tags", []),
        kind=kind,
        status=record.get("review_status", "pending"),
        confidence=record.get("confidence"),
        negative_space_kind=negative_space_kind,
    )


# ---------------------------------------------------------------------------
# Core assembly
# ---------------------------------------------------------------------------

def assemble_loadout(task: LoadoutTaskInput) -> AssembledLoadout:
    """Assemble a bounded, trust-labeled memory Loadout from a Cell.

    1. Reads Doctrine, Traces, Alloys, and optionally Fragments from the Cell.
    2. Builds candidates and scores them via hybrid search.
    3. Filters out operational state.
    4. Enforces item and token limits deterministically.
    5. Appends a retrieval log to ledger/retrieval_logs.jsonl.
    """
    from .retrieval.hybrid import hybrid_search
    from .graph import graph_context_for
    from .retrieval_modes import apply_retrieval_mode_to_task, filter_items_for_retrieval_mode, retrieval_mode_config

    task = apply_retrieval_mode_to_task(task)
    mode_config = retrieval_mode_config(task.retrieval_mode)

    cell_path = Path(task.cell_path)
    now = datetime.now(timezone.utc).isoformat()
    loadout_id = f"lo-{uuid.uuid4().hex[:12]}"

    # Read cell_id
    cell_id = _read_cell_id(cell_path)

    # Empty query yields an empty loadout
    if not task.query or not task.query.strip():
        retrieval_log = RetrievalLog(
            retrieval_id=f"rl-{uuid.uuid4().hex[:12]}",
            loadout_id=loadout_id,
            selected_ids=[],
            score_traces={},
            query=task.query,
            generated_at=now,
        )
        if not task.dry_run:
            log_ledger = cell_path / "ledger" / "retrieval_logs.jsonl"
            append_jsonl(log_ledger, retrieval_log.to_dict())
        return AssembledLoadout(
            loadout_id=loadout_id,
            cell_id=cell_id,
            task_id=task.task_id,
            items=[],
            total_tokens=0,
            total_items=0,
            retrieval_log=retrieval_log,
            generated_at=now,
        )

    # Gather candidates from all sources
    candidates: List[CandidateItem] = []

    # Doctrine (always included, highest trust)
    for record in _read_doctrine(cell_path):
        candidates.append(_build_candidate_from_doctrine(record))

    allowed_pack_charge_ids = active_charge_ids(cell_path, projection="pack")
    sensitivity_policy = AccessPolicy(
        runtime_id=task.runtime_id or "default",
        user_id=task.user_id,
        project_id=task.project_id,
        allowed_sensitivity=tuple(task.allowed_sensitivity) if task.allowed_sensitivity else ("public", "internal"),
        allow_audit_sensitive=task.audit_mode,
    )

    # Traces (always included, subject to lifecycle and sensitivity/export policy)
    privacy_suppressed_ids: List[str] = []
    for record in _read_traces(cell_path):
        trace_id = record.get("trace_id")
        if trace_id not in allowed_pack_charge_ids and not task.audit_mode:
            privacy_suppressed_ids.append(str(trace_id))
            continue
        privacy_allowed, _privacy_warnings = is_charge_export_allowed(
            record,
            sensitivity_policy,
            cell_path=cell_path,
            audit_mode=task.audit_mode,
        )
        if not privacy_allowed:
            privacy_suppressed_ids.append(str(trace_id))
            continue
        candidates.append(_build_candidate_from_trace(project_confidence_state(record)))

    # Alloys (always included)
    for record in _read_alloys(cell_path):
        candidates.append(_build_candidate_from_alloy(record))

    # Fragments (background-only unless explicitly requested)
    if task.include_fragments:
        for record in _read_fragments(cell_path):
            candidates.append(_build_candidate_from_fragment(record))

    # Filter by requested trust tiers if specified
    if task.requested_trust_tiers:
        candidates = [c for c in candidates if c.trust_tier in task.requested_trust_tiers]

    # Ledger-built candidates do not necessarily carry sparse/vector scores.
    # Apply a deterministic query-text score before hybrid fusion so loadouts
    # and continuity packs are actually sensitive to the runtime request.
    candidates = _apply_query_sparse_scores(task.query, candidates)

    # Score via hybrid search
    results = hybrid_search(
        candidates,
        query_kind=task.query_kind,
        query_tags=task.query_tags,
        include_fragments=task.include_fragments,
        include_all_statuses=task.audit_mode,
        top_k=max(task.max_items, task.max_items + max(task.caution_max_items, 0)),
    )

    # Build LoadoutItems, filtering operational state and preserving a bounded
    # caution budget so warnings cannot crowd out all guidance.
    items: List[LoadoutItem] = []
    total_tokens = 0
    candidate_ids = [c.item_id for c in candidates]
    caution_ids: List[str] = []
    suppressed_ids: List[str] = list(dict.fromkeys(privacy_suppressed_ids))
    max_item_count = max(task.max_items, 0)
    requested_caution_budget = min(max(task.caution_max_items, 0), max_item_count)
    has_non_caution_result = any(
        not is_operational_state(result.statement)
        and _compute_loadout_role(result.kind, result.selection_reason, result.trust_tier) != "caution"
        for result in results
    )
    caution_budget = requested_caution_budget
    if has_non_caution_result and max_item_count > 0:
        caution_budget = min(caution_budget, max_item_count - 1)

    for result in results:
        # Reject operational state for every role.
        if is_operational_state(result.statement):
            suppressed_ids.append(result.item_id)
            continue

        selection_reason = result.selection_reason
        loadout_role = _compute_loadout_role(result.kind, selection_reason, result.trust_tier)

        if loadout_role == "caution" and len(caution_ids) >= caution_budget:
            suppressed_ids.append(result.item_id)
            continue

        # Check item limit
        if len(items) >= task.max_items:
            suppressed_ids.append(result.item_id)
            continue

        # Check token limit
        item_tokens = estimate_tokens(result.statement)
        if result.rationale:
            item_tokens += estimate_tokens(result.rationale)
        if total_tokens + item_tokens > task.max_tokens:
            suppressed_ids.append(result.item_id)
            continue

        if selection_reason in {"suppressed", "filtered"}:
            suppressed_ids.append(result.item_id)

        score_trace = {
            **result.components.to_dict(),
            "selection_reason": selection_reason,
            "loadout_role": loadout_role,
            "retrieval_mode": task.retrieval_mode,
            "retrieval_mode_description": mode_config["description"],
        }
        items.append(
            LoadoutItem(
                item_id=result.item_id,
                trust_tier=result.trust_tier,
                statement=result.statement,
                rationale=result.rationale,
                tags=result.tags,
                kind=result.kind,
                confidence=result.confidence,
                score=result.final_score,
                score_trace=score_trace,
                loadout_role=loadout_role,
                graph_context=[],
            )
        )
        if loadout_role == "caution":
            caution_ids.append(result.item_id)
        total_tokens += item_tokens

    # Apply final retrieval-mode filters after scoring so default balanced mode
    # remains compatible and non-default modes are explicit/dry-run friendly.
    items, mode_suppressed_ids = filter_items_for_retrieval_mode(items, task.retrieval_mode)
    suppressed_ids.extend(mode_suppressed_ids)

    graph_map = graph_context_for(cell_path, [item.item_id for item in items])
    if graph_map:
        items = [
            LoadoutItem(
                item_id=item.item_id,
                trust_tier=item.trust_tier,
                statement=item.statement,
                rationale=item.rationale,
                tags=item.tags,
                kind=item.kind,
                confidence=item.confidence,
                score=item.score,
                score_trace=item.score_trace,
                loadout_role=item.loadout_role,
                graph_context=graph_map.get(item.item_id, []),
            )
            for item in items
        ]

    total_tokens = sum(estimate_tokens(item.statement) + (estimate_tokens(item.rationale) if item.rationale else 0) for item in items)
    caution_ids = [item.item_id for item in items if item.loadout_role == "caution"]

    # Build retrieval log
    selected_ids = [i.item_id for i in items]
    score_traces = {i.item_id: i.score_trace for i in items}

    retrieval_log = RetrievalLog(
        retrieval_id=f"rl-{uuid.uuid4().hex[:12]}",
        loadout_id=loadout_id,
        selected_ids=selected_ids,
        score_traces=score_traces,
        query=task.query,
        generated_at=now,
        candidate_ids=candidate_ids,
        caution_ids=caution_ids,
        suppressed_ids=suppressed_ids,
    )

    # Append retrieval log to ledger unless this is an explicit read-only
    # simulation/dry-run request.
    if not task.dry_run:
        log_ledger = cell_path / "ledger" / "retrieval_logs.jsonl"
        append_jsonl(log_ledger, retrieval_log.to_dict())

    return AssembledLoadout(
        loadout_id=loadout_id,
        cell_id=cell_id,
        task_id=task.task_id,
        items=items,
        total_tokens=total_tokens,
        total_items=len(items),
        retrieval_log=retrieval_log,
        generated_at=now,
    )
