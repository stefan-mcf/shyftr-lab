from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import uuid4

from shyftr.ledger import append_jsonl
from shyftr.ledger_state import latest_by_key
from shyftr.memory_classes import class_spec, infer_memory_type, resolve_memory_type, validate_resource_memory
from shyftr.models import Fragment, Source, Trace
from shyftr.mutations import (
    active_charge_ids,
    approved_traces,
    deprecate_charge,
    forget_charge,
    replace_charge,
)
from shyftr.policy import check_provider_memory_policy, evaluate_direct_write_policy
from shyftr.profile import ProfileProjection, build_profile
from shyftr.promote import promote_fragment
from shyftr.review import approve_fragment

PathLike = Union[str, Path]


@dataclass(frozen=True)
class RememberResult:
    memory_id: Optional[str]
    evidence_id: str
    candidate_id: str
    status: str
    trust_tier: str = "memory"
    memory_type: Optional[str] = None

    @property
    def charge_id(self) -> Optional[str]:
        return self.memory_id

    @property
    def pulse_id(self) -> str:
        return self.evidence_id

    @property
    def spark_id(self) -> str:
        return self.candidate_id


@dataclass(frozen=True)
class SearchResult:
    memory_id: str
    statement: str
    trust_tier: str
    kind: Optional[str]
    memory_type: Optional[str] = None
    confidence: Optional[float] = None
    score: float = 0.0
    lifecycle_status: str = "approved"
    selection_rationale: str = "lexical_overlap"
    provenance: Dict[str, Any] = field(default_factory=dict)

    @property
    def charge_id(self) -> str:
        return self.memory_id


@dataclass(frozen=True)
class LifecycleEventResult:
    event_id: str
    action: str
    memory_id: str
    reason: str
    actor: str
    replacement_memory_id: Optional[str] = None

    @property
    def charge_id(self) -> str:
        return self.memory_id

    @property
    def replacement_charge_id(self) -> Optional[str]:
        return self.replacement_memory_id


class MemoryProvider:
    """ShyftR-native memory-provider facade for one Cell."""

    def __init__(self, cell_path: PathLike):
        self.cell_path = Path(cell_path)

    def remember(
        self,
        statement: str,
        kind: str,
        pulse_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        memory_type: Optional[str] = None,
        allow_direct_durable_memory: bool = False,
    ) -> RememberResult:
        return remember(
            self.cell_path,
            statement,
            kind,
            pulse_context=pulse_context,
            metadata=metadata,
            memory_type=memory_type,
            allow_direct_durable_memory=allow_direct_durable_memory,
        )

    def remember_trusted(
        self,
        statement: str,
        kind: str,
        *,
        actor: str,
        trust_reason: str,
        pulse_channel: str,
        created_at: str,
        trusted_direct_promotion: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        from shyftr.provider.trusted import remember_trusted

        return remember_trusted(
            self.cell_path,
            statement,
            kind,
            actor=actor,
            trust_reason=trust_reason,
            pulse_channel=pulse_channel,
            created_at=created_at,
            trusted_direct_promotion=trusted_direct_promotion,
            metadata=metadata,
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        trust_tiers: Optional[Sequence[str]] = None,
        kinds: Optional[Sequence[str]] = None,
        memory_types: Optional[Sequence[str]] = None,
    ) -> List[SearchResult]:
        return search(self.cell_path, query, top_k=top_k, trust_tiers=trust_tiers, kinds=kinds, memory_types=memory_types)

    def profile(self, max_tokens: int = 2000) -> ProfileProjection:
        return profile(self.cell_path, max_tokens=max_tokens)

    def forget(self, charge_id: str, reason: str, actor: str) -> LifecycleEventResult:
        return forget(self.cell_path, charge_id, reason=reason, actor=actor)

    def replace(self, charge_id: str, new_statement: str, reason: str, actor: str) -> LifecycleEventResult:
        return replace(self.cell_path, charge_id, new_statement, reason=reason, actor=actor)

    def deprecate(self, charge_id: str, reason: str, actor: str) -> LifecycleEventResult:
        return deprecate(self.cell_path, charge_id, reason=reason, actor=actor)

    def pack(self, query: str, *, task_id: str, runtime_id: str = "memory-provider", max_items: int = 10, max_tokens: int = 2000) -> Dict[str, Any]:
        return pack(self.cell_path, query, task_id=task_id, runtime_id=runtime_id, max_items=max_items, max_tokens=max_tokens)

    def record_signal(
        self,
        pack_id: str,
        *,
        result: str,
        applied_charge_ids: Optional[Sequence[str]] = None,
        useful_charge_ids: Optional[Sequence[str]] = None,
        harmful_charge_ids: Optional[Sequence[str]] = None,
        ignored_charge_ids: Optional[Sequence[str]] = None,
        missing_memory_notes: Optional[Sequence[str]] = None,
        runtime_id: str = "memory-provider",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return record_signal(
            self.cell_path,
            pack_id,
            result=result,
            applied_charge_ids=applied_charge_ids,
            useful_charge_ids=useful_charge_ids,
            harmful_charge_ids=harmful_charge_ids,
            ignored_charge_ids=ignored_charge_ids,
            missing_memory_notes=missing_memory_notes,
            runtime_id=runtime_id,
            task_id=task_id,
        )

    def export_snapshot(self) -> Dict[str, Any]:
        return export_snapshot(self.cell_path)

    def import_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        return import_snapshot(self.cell_path, snapshot)


def remember(
    cell_path: PathLike,
    statement: str,
    kind: str,
    pulse_context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    memory_type: Optional[str] = None,
    *,
    allow_direct_durable_memory: bool = False,
) -> RememberResult:
    """Store explicit memory through ShyftR's Regulator and ledger chain."""
    cell = Path(cell_path)
    if not kind:
        raise ValueError("kind is required")
    clean_statement = _require_text(statement, "statement")
    event_metadata = dict(metadata or {})
    if pulse_context is not None:
        event_metadata["pulse_context"] = dict(pulse_context)
    requested_provider_api = event_metadata.get("provider_api")
    event_metadata["provider_api"] = "remember"
    if requested_provider_api and requested_provider_api != "remember":
        event_metadata["operation_origin"] = requested_provider_api
    resolved_memory_type = resolve_memory_type(memory_type or event_metadata.get("memory_type"), kind=kind, trust_tier="trace")
    if resolved_memory_type is not None:
        event_metadata["memory_type"] = resolved_memory_type
    event_metadata["allow_direct_durable_memory"] = bool(allow_direct_durable_memory or event_metadata.get("allow_direct_durable_memory", False))
    if resolved_memory_type == "resource":
        validate_resource_memory(clean_statement, event_metadata)
    provider_policy = check_provider_memory_policy(clean_statement, kind, metadata=event_metadata, raise_on_reject=True)
    direct_write = evaluate_direct_write_policy(
        kind=kind,
        memory_type=resolved_memory_type,
        metadata=event_metadata,
    )

    cell_id = _read_cell_id(cell)
    now = _now()
    digest = hashlib.sha256(clean_statement.encode("utf-8")).hexdigest()

    source = Source(
        source_id=f"src-{uuid4().hex}",
        cell_id=cell_id,
        kind=kind,
        sha256=digest,
        captured_at=now,
        uri=None,
        metadata=event_metadata,
    )
    append_jsonl(cell / "ledger" / "sources.jsonl", source.to_dict())

    fragment = Fragment(
        fragment_id=f"frag-{uuid4().hex}",
        source_id=source.source_id,
        cell_id=cell_id,
        kind=kind,
        text=clean_statement,
        source_excerpt=_excerpt(clean_statement),
        boundary_status="accepted",
        review_status="approved" if direct_write.trusted_direct_promotion else "pending",
        confidence=0.8,
        tags=list(event_metadata.get("tags", [])) if isinstance(event_metadata.get("tags"), list) else [],
    )
    append_jsonl(cell / "ledger" / "fragments.jsonl", fragment.to_dict())

    regulator_decision = {
        "status": direct_write.status,
        "reasons": provider_policy.reasons + direct_write.reasons,
        "review_required": provider_policy.review_required or direct_write.review_required,
        "trusted_direct_promotion": provider_policy.trusted_direct_promotion and direct_write.trusted_direct_promotion,
        "authority": direct_write.authority,
    }

    if not direct_write.trusted_direct_promotion:
        return RememberResult(
            memory_id=None,
            evidence_id=source.source_id,
            candidate_id=fragment.fragment_id,
            status="pending_review",
            memory_type=resolved_memory_type,
        )

    review = approve_fragment(
        cell,
        fragment.fragment_id,
        reviewer=str(event_metadata.get("actor") or event_metadata.get("reviewer") or "memory-provider"),
        rationale="trusted explicit memory provider write accepted by Regulator policy",
        metadata={
            "provider_api": "remember",
            "regulator_decision": regulator_decision,
        },
    )

    trace = promote_fragment(
        cell,
        fragment.fragment_id,
        promoter="memory-provider",
        statement=clean_statement,
        rationale="Explicit memory provider write approved by Regulator policy.",
        memory_type=resolved_memory_type,
    )

    return RememberResult(
        memory_id=trace.trace_id,
        evidence_id=source.source_id,
        candidate_id=fragment.fragment_id,
        status=trace.status,
        memory_type=trace.memory_type,
    )


def search(
    cell_path: PathLike,
    query: str,
    top_k: int = 10,
    trust_tiers: Optional[Sequence[str]] = None,
    kinds: Optional[Sequence[str]] = None,
    memory_types: Optional[Sequence[str]] = None,
) -> List[SearchResult]:
    """Search reviewed memory using a lightweight ShyftR-native provider surface."""
    cell = Path(cell_path)
    requested_tiers = set(trust_tiers or ["trace"])
    requested_kinds = set(kinds or [])
    requested_memory_types = {resolve_memory_type(item) for item in (memory_types or []) if item is not None}
    active_ids = active_charge_ids(cell, projection="retrieval")
    query_terms = _terms(query)
    results: List[SearchResult] = []

    if "trace" not in requested_tiers:
        return []

    for trace in approved_traces(cell):
        if trace.trace_id not in active_ids:
            continue
        if requested_kinds and trace.kind not in requested_kinds:
            continue
        resolved_memory_type = resolve_memory_type(getattr(trace, "memory_type", None), kind=trace.kind, trust_tier="trace")
        if requested_memory_types and resolved_memory_type not in requested_memory_types:
            continue
        score = _score(query_terms, trace)
        if query_terms and score <= 0:
            continue
        provenance = {"source_fragment_ids": list(trace.source_fragment_ids), "memory_type": resolved_memory_type}
        if getattr(trace, "resource_ref", None) is not None:
            provenance["resource_ref"] = trace.resource_ref.to_dict()
        if getattr(trace, "grounding_refs", None):
            provenance["grounding_refs"] = list(trace.grounding_refs)
        results.append(
            SearchResult(
                memory_id=trace.trace_id,
                statement=trace.statement,
                trust_tier="memory",
                kind=trace.kind,
                memory_type=resolved_memory_type,
                confidence=trace.confidence,
                score=score,
                lifecycle_status="approved",
                selection_rationale="lexical_overlap",
                provenance=provenance,
            )
        )

    results.sort(key=lambda item: (-item.score, item.memory_id))
    return results[: max(top_k, 0)]


def profile(cell_path: PathLike, max_tokens: int = 2000) -> ProfileProjection:
    return build_profile(cell_path, max_tokens=max_tokens)


def forget(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> LifecycleEventResult:
    event = forget_charge(cell_path, charge_id, reason=reason, actor=actor)
    return LifecycleEventResult(event_id=event.event_id, action=event.action, memory_id=event.charge_id, reason=reason, actor=actor)


def replace(cell_path: PathLike, charge_id: str, new_statement: str, *, reason: str, actor: str) -> LifecycleEventResult:
    event = replace_charge(cell_path, charge_id, new_statement, reason=reason, actor=actor)
    return LifecycleEventResult(
        event_id=event.event_id,
        action=event.action,
        memory_id=event.charge_id,
        reason=reason,
        actor=actor,
        replacement_memory_id=event.replacement_charge_id,
    )


def deprecate(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> LifecycleEventResult:
    event = deprecate_charge(cell_path, charge_id, reason=reason, actor=actor)
    return LifecycleEventResult(event_id=event.event_id, action=event.action, memory_id=event.charge_id, reason=reason, actor=actor)


def pack(
    cell_path: PathLike,
    query: str,
    *,
    task_id: str,
    runtime_id: str = "memory-provider",
    max_items: int = 10,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    from shyftr.loadout import LoadoutTaskInput, assemble_loadout
    from shyftr.observability import append_diagnostic_log, operation_timer

    with operation_timer() as timer:
        assembled = assemble_loadout(
            LoadoutTaskInput(
                cell_path=str(cell_path),
                query=query,
                task_id=task_id,
                max_items=max_items,
                max_tokens=max_tokens,
                query_tags=[runtime_id] if runtime_id else None,
            )
        )
    payload = assembled.to_dict()
    payload["pack_id"] = payload["loadout_id"]
    payload["selected_ids"] = list(assembled.retrieval_log.selected_ids)
    append_diagnostic_log(
        cell_path,
        operation="pack",
        runtime_id=runtime_id,
        loadout_id=assembled.loadout_id,
        selected_charge_ids=list(assembled.retrieval_log.selected_ids),
        excluded_charge_ids=list(assembled.retrieval_log.suppressed_ids),
        scoring_components=dict(assembled.retrieval_log.score_traces),
        token_estimate=assembled.total_tokens,
        latency_ms=timer.elapsed_ms,
    )
    return payload


def record_signal(
    cell_path: PathLike,
    pack_id: str,
    *,
    result: str,
    applied_charge_ids: Optional[Sequence[str]] = None,
    useful_charge_ids: Optional[Sequence[str]] = None,
    harmful_charge_ids: Optional[Sequence[str]] = None,
    ignored_charge_ids: Optional[Sequence[str]] = None,
    missing_memory_notes: Optional[Sequence[str]] = None,
    runtime_id: str = "memory-provider",
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    from shyftr.integrations.outcome_api import RuntimeOutcomeReport, process_runtime_outcome_report
    from shyftr.observability import append_diagnostic_log, operation_timer

    report = RuntimeOutcomeReport(
        cell_path_or_id=str(cell_path),
        loadout_id=pack_id,
        result=result,
        external_system=runtime_id,
        external_scope="provider-api",
        external_task_id=task_id,
        applied_trace_ids=list(applied_charge_ids or []),
        useful_trace_ids=list(useful_charge_ids or []),
        harmful_trace_ids=list(harmful_charge_ids or []),
        ignored_trace_ids=list(ignored_charge_ids or []),
        missing_memory_notes=list(missing_memory_notes or []),
        runtime_metadata={"provider_api": "record_signal"},
    )
    with operation_timer() as timer:
        response = process_runtime_outcome_report(report)
    payload = response.to_dict()
    append_diagnostic_log(
        cell_path,
        operation="signal",
        runtime_id=runtime_id,
        loadout_id=pack_id,
        signal_id=payload.get("outcome_id"),
        selected_charge_ids=list(applied_charge_ids or []),
        warnings=list(payload.get("warnings", [])),
        latency_ms=timer.elapsed_ms,
        status=payload.get("status", "unknown"),
    )
    return payload


def export_snapshot(cell_path: PathLike) -> Dict[str, Any]:
    from shyftr.readiness import export_replacement_snapshot

    return export_replacement_snapshot(cell_path)


def import_snapshot(cell_path: PathLike, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    from shyftr.readiness import import_replacement_snapshot

    return import_replacement_snapshot(cell_path, snapshot)


def _read_cell_id(cell: Path) -> str:
    manifest_path = cell / "manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return str(payload.get("cell_id") or cell.name)
    return cell.name


def _require_text(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _excerpt(text: str, limit: int = 120) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", str(text or "").lower()))


def _score(query_terms: set[str], trace: Trace) -> float:
    if not query_terms:
        return 0.0
    haystack = " ".join(
        [
            trace.statement,
            trace.rationale or "",
            trace.kind or "",
            " ".join(trace.tags),
            trace.resource_ref.label if trace.resource_ref and trace.resource_ref.label else "",
        ]
    )
    overlap = query_terms & _terms(haystack)
    if not overlap:
        return 0.0
    return min(1.0, len(overlap) / max(len(query_terms), 1))


def approved_traces(cell_path: PathLike) -> List[Trace]:
    cell = Path(cell_path)
    rows = [record for _, record in _read_jsonl_safe(cell / "traces" / "approved.jsonl")]
    latest_rows = latest_by_key(rows, "trace_id")
    traces: List[Trace] = []
    for record in latest_rows:
        traces.append(Trace.from_dict(record))
    return traces


def _read_jsonl_safe(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            rows.append((idx, json.loads(line)))
    return rows


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
