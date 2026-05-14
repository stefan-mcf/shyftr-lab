from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

MEMORY_TYPES = (
    "working",
    "continuity",
    "episodic",
    "semantic",
    "procedural",
    "resource",
    "rule",
)

DURABLE_MEMORY_TYPES = (
    "semantic",
    "procedural",
    "resource",
    "rule",
    "episodic",
)

MEMORY_TYPE_BY_KIND = {
    "preference": "semantic",
    "constraint": "semantic",
    "workflow": "procedural",
    "recovery_pattern": "procedural",
    "verification_heuristic": "procedural",
    "routing_heuristic": "procedural",
    "tool_quirk": "procedural",
    "success_pattern": "procedural",
    "failure_signature": "procedural",
    "anti_pattern": "procedural",
    "audit_finding": "procedural",
    "scope_exception": "procedural",
    "rail_candidate": "rule",
    "escalation_rule": "rule",
    "supersession": "rule",
}

ENTRY_KIND_TO_MEMORY_TYPE = {
    "goal": "working",
    "subgoal": "working",
    "plan_step": "working",
    "assumption": "working",
    "tool_state": "working",
    "open_question": "working",
    "decision": "semantic",
    "constraint": "semantic",
    "verification_result": "procedural",
    "recovery": "procedural",
    "error": "episodic",
    "artifact_ref": "resource",
}

DEFAULT_AUTHORITY_BY_MEMORY_TYPE = {
    "working": "runtime_only",
    "continuity": "advisory_runtime",
    "episodic": "review_gated",
    "semantic": "review_gated",
    "procedural": "review_gated",
    "resource": "grounded_reference",
    "rule": "reviewed_precedence",
}

DEFAULT_RETENTION_BY_MEMORY_TYPE = {
    "working": "session",
    "continuity": "session_resume",
    "episodic": "event_history",
    "semantic": "durable",
    "procedural": "durable",
    "resource": "durable_reference",
    "rule": "durable_policy",
}

DEFAULT_ROLE_BY_MEMORY_TYPE = {
    "working": "current_state",
    "continuity": "preserve",
    "episodic": "background",
    "semantic": "guidance",
    "procedural": "guidance",
    "resource": "background",
    "rule": "guidance",
}

DEFAULT_PRECEDENCE_BY_MEMORY_TYPE = {
    "rule": 70,
    "semantic": 60,
    "procedural": 55,
    "resource": 40,
    "episodic": 35,
    "continuity": 20,
    "working": 10,
}


@dataclass(frozen=True)
class MemoryClassSpec:
    memory_type: str
    authority: str
    retention: str
    default_role: str
    precedence: int
    legacy_compatible: bool = True
    reviewed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_type": self.memory_type,
            "authority": self.authority,
            "retention": self.retention,
            "default_role": self.default_role,
            "precedence": self.precedence,
            "legacy_compatible": self.legacy_compatible,
            "reviewed": self.reviewed,
        }


def normalize_memory_type(memory_type: Optional[str]) -> Optional[str]:
    if memory_type is None:
        return None
    value = str(memory_type).strip().lower().replace('-', '_')
    if not value:
        return None
    if value not in MEMORY_TYPES:
        raise ValueError(f'invalid memory_type: {memory_type}')
    return value


def infer_memory_type(*, kind: Optional[str] = None, trust_tier: Optional[str] = None, entry_kind: Optional[str] = None, retention_hint: Optional[str] = None) -> Optional[str]:
    if entry_kind:
        ek = str(entry_kind).strip().lower()
        if ek in ENTRY_KIND_TO_MEMORY_TYPE:
            inferred = ENTRY_KIND_TO_MEMORY_TYPE[ek]
            if retention_hint == 'archive' and inferred == 'working':
                return 'episodic'
            return inferred
    if kind:
        kk = str(kind).strip().lower()
        if kk in MEMORY_TYPE_BY_KIND:
            return MEMORY_TYPE_BY_KIND[kk]
    if trust_tier:
        tier = str(trust_tier).strip().lower()
        if tier == 'doctrine':
            return 'rule'
        if tier == 'alloy':
            return 'procedural'
        if tier == 'fragment':
            return 'episodic'
    return None


def resolve_memory_type(memory_type: Optional[str], *, kind: Optional[str] = None, trust_tier: Optional[str] = None, entry_kind: Optional[str] = None, retention_hint: Optional[str] = None) -> Optional[str]:
    normalized = normalize_memory_type(memory_type)
    if normalized is not None:
        return normalized
    return infer_memory_type(kind=kind, trust_tier=trust_tier, entry_kind=entry_kind, retention_hint=retention_hint)


def class_spec(memory_type: Optional[str], *, kind: Optional[str] = None, trust_tier: Optional[str] = None, entry_kind: Optional[str] = None, retention_hint: Optional[str] = None) -> Optional[MemoryClassSpec]:
    resolved = resolve_memory_type(memory_type, kind=kind, trust_tier=trust_tier, entry_kind=entry_kind, retention_hint=retention_hint)
    if resolved is None:
        return None
    return MemoryClassSpec(
        memory_type=resolved,
        authority=DEFAULT_AUTHORITY_BY_MEMORY_TYPE[resolved],
        retention=DEFAULT_RETENTION_BY_MEMORY_TYPE[resolved],
        default_role=DEFAULT_ROLE_BY_MEMORY_TYPE[resolved],
        precedence=DEFAULT_PRECEDENCE_BY_MEMORY_TYPE[resolved],
    )


def compatibility_memory_type(record: Mapping[str, Any], *, kind_key: str = 'kind', memory_type_key: str = 'memory_type', trust_tier_key: str = 'trust_tier') -> Optional[str]:
    return resolve_memory_type(
        record.get(memory_type_key),
        kind=record.get(kind_key),
        trust_tier=record.get(trust_tier_key),
    )


def classify_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        inferred = compatibility_memory_type(record)
        rows.append({
            'memory_id': record.get('memory_id') or record.get('trace_id') or record.get('charge_id'),
            'kind': record.get('kind'),
            'memory_type': inferred,
            'ambiguous': inferred is None,
        })
    return rows


def validate_resource_memory(statement: str, metadata: Optional[Mapping[str, Any]] = None) -> None:
    refs = dict(metadata or {})
    resource_ref = refs.get('resource_ref')
    if isinstance(resource_ref, dict):
        locator = str(resource_ref.get('locator') or '').strip()
        ref_type = str(resource_ref.get('ref_type') or '').strip()
        if not locator:
            raise ValueError('resource_ref locator is required for resource memory')
        if not ref_type:
            raise ValueError('resource_ref ref_type is required for resource memory')
    has_ref = any(refs.get(key) for key in ('resource_ref', 'resource_refs', 'file_path', 'url', 'code_span', 'log_span', 'artifact_handle', 'artifact_handles', 'evidence_refs', 'grounding_refs'))
    text = str(statement or '')
    lexical_ref = any(token in text for token in ('/', 'http://', 'https://', '.png', '.jpg', '.log', '.py:', '.md:', 'file:', 'url:'))
    if not has_ref and not lexical_ref:
        raise ValueError('resource memory requires a reference/handle, not blob-only content')
