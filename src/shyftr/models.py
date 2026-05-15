from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
import json
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Type, TypeVar

from .memory_classes import MEMORY_TYPES, resolve_memory_type


T = TypeVar("T", bound="SerializableModel")


_COMPAT_MEMORY_ID_KEYS = (
    "memory_id",
    "charge_id",
    "trace_id",
    "id",
)


def canonical_memory_id(record: Dict[str, Any]) -> Optional[str]:
    """Return the current memory id from a record with compatibility fallback."""
    if not isinstance(record, dict):
        return None
    for key in _COMPAT_MEMORY_ID_KEYS:
        value = record.get(key)
        if value:
            return str(value)
    return None


def with_canonical_memory_id(record: Dict[str, Any], *, include_compat: bool = False) -> Dict[str, Any]:
    """Return a copy that exposes memory_id as the primary user-facing id."""
    payload = dict(record)
    memory_id = canonical_memory_id(payload)
    if memory_id is not None:
        payload["memory_id"] = memory_id
    if not include_compat:
        for key in _COMPAT_MEMORY_ID_KEYS:
            if key != "memory_id":
                payload.pop(key, None)
    return payload


class SerializableModel:
    """Small deterministic serialization base for ShyftR lifecycle records."""

    _required_fields: ClassVar[Sequence[str]] = ()
    _non_empty_fields: ClassVar[Sequence[str]] = ()
    _bounded_fields: ClassVar[Sequence[str]] = ()
    _field_aliases: ClassVar[Dict[str, str]] = {}

    def __post_init__(self) -> None:
        _validate_required(self, self._required_fields)
        for field_name in self._non_empty_fields:
            _validate_non_empty_string_list(field_name, getattr(self, field_name))
        for field_name in self._bounded_fields:
            value = getattr(self, field_name)
            if value is not None:
                _validate_zero_to_one(field_name, value)
        _validate_non_negative_counters(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            field.name: getattr(self, field.name)
            for field in sorted(fields(self), key=lambda item: item.name)
        }

    @classmethod
    def from_dict(cls: Type[T], payload: Dict[str, Any]) -> T:
        if not isinstance(payload, dict):
            raise ValueError(f"{cls.__name__}.from_dict requires a mapping payload")

        canonical_payload = dict(payload)
        for old_name, new_name in cls._field_aliases.items():
            if old_name in canonical_payload and new_name not in canonical_payload:
                canonical_payload[new_name] = canonical_payload.pop(old_name)

        missing = [field_name for field_name in cls._required_fields if field_name not in canonical_payload]
        if missing:
            raise ValueError(f"Missing required field(s): {', '.join(missing)}")

        allowed = {field.name for field in fields(cls)}
        allowed.update(cls._field_aliases)
        unknown = sorted(set(canonical_payload) - allowed)
        if unknown:
            compatibility_ignored = {"row_hash", "previous_row_hash"}
            unknown = [field_name for field_name in unknown if field_name not in compatibility_ignored]
        if unknown:
            raise ValueError(f"Unknown field(s): {', '.join(unknown)}")

        values = {}
        for field in fields(cls):
            if field.name in canonical_payload:
                values[field.name] = canonical_payload[field.name]
            elif field.default is not MISSING or field.default_factory is not MISSING:  # type: ignore[attr-defined]
                continue
            else:
                raise ValueError(f"Missing required field(s): {field.name}")
        return cls(**values)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls: Type[T], payload: str) -> T:
        return cls.from_dict(json.loads(payload))


def _normalize_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _normalize_string_list(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    normalized: List[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            raise ValueError(f"{field_name} entries must be non-empty strings")
        normalized.append(text)
    return normalized


def _validate_required(instance: Any, field_names: Sequence[str]) -> None:
    for field_name in field_names:
        value = getattr(instance, field_name)
        if value is None:
            raise ValueError(f"{field_name} is required")
        if isinstance(value, str) and value == "":
            raise ValueError(f"{field_name} is required")


def _validate_non_empty_string_list(field_name: str, value: Any) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if not value:
        raise ValueError(f"{field_name} must contain at least one entry")
    if any(not isinstance(item, str) or item == "" for item in value):
        raise ValueError(f"{field_name} entries must be non-empty strings")


def _validate_zero_to_one(field_name: str, value: Any) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number between 0.0 and 1.0")
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")


def _validate_non_negative_counters(instance: Any) -> None:
    for field_name in ("use_count", "success_count", "failure_count"):
        if not hasattr(instance, field_name):
            continue
        value = getattr(instance, field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer")


@dataclass(frozen=True)
class Evidence(SerializableModel):
    evidence_id: str
    cell_id: str
    kind: str
    sha256: str
    captured_at: str
    uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "evidence_id",
        "cell_id",
        "kind",
        "sha256",
        "captured_at",
    )
    _field_aliases: ClassVar[Dict[str, str]] = {"source_id": "evidence_id"}


@dataclass(frozen=True)
class Candidate(SerializableModel):
    candidate_id: str
    evidence_id: str
    cell_id: str
    kind: str
    text: str
    evidence_excerpt: Optional[str] = None
    regulator_status: str = "pending"
    review_status: str = "pending"
    confidence: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    _required_fields: ClassVar[Sequence[str]] = (
        "candidate_id",
        "evidence_id",
        "cell_id",
        "text",
    )
    _bounded_fields: ClassVar[Sequence[str]] = ("confidence",)
    _field_aliases: ClassVar[Dict[str, str]] = {
        "fragment_id": "candidate_id",
        "source_id": "evidence_id",
        "source_excerpt": "evidence_excerpt",
        "boundary_status": "regulator_status",
    }


@dataclass(frozen=True)
class ResourceSpan(SerializableModel):
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None

    def __post_init__(self) -> None:
        for field_name in ("start_line", "end_line", "start_char", "end_char"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.start_line is not None and self.end_line is not None and self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        if self.start_char is not None and self.end_char is not None and self.end_char < self.start_char:
            raise ValueError("end_char must be greater than or equal to start_char")


@dataclass(frozen=True)
class ResourceRef(SerializableModel):
    ref_type: str
    locator: str
    label: Optional[str] = None
    span: Optional[ResourceSpan] = None
    content_digest: Optional[str] = None
    captured_at: Optional[str] = None
    origin: Optional[str] = None
    tool_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None

    _required_fields: ClassVar[Sequence[str]] = ("ref_type", "locator")

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.size_bytes is not None and (not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool) or self.size_bytes < 0):
            raise ValueError("size_bytes must be a non-negative integer")
        if self.span is not None and not isinstance(self.span, ResourceSpan):
            raise ValueError("span must be a ResourceSpan")

    def to_dict(self) -> Dict[str, Any]:
        payload = super().to_dict()
        if self.span is not None:
            payload["span"] = self.span.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ResourceRef":
        data = dict(payload)
        span = data.get("span")
        if isinstance(span, dict):
            data["span"] = ResourceSpan.from_dict(span)
        return super().from_dict(data)


MEMORY_KINDS = (
    "success_pattern",
    "failure_signature",
    "anti_pattern",
    "recovery_pattern",
    "verification_heuristic",
    "routing_heuristic",
    "tool_quirk",
    "escalation_rule",
    "preference",
    "constraint",
    "workflow",
    # Runtime value kept for compatibility until rule-candidate lifecycle
    # handling is migrated end-to-end.
    "rail_candidate",
    "supersession",
    "scope_exception",
    "audit_finding",
)

MEMORY_STATUSES = (
    "proposed",
    "approved",
    "challenged",
    # Runtime values kept for compatibility until quarantine lifecycle
    # handling is migrated end-to-end.
    "isolation_candidate",
    "isolated",
    "superseded",
    "deprecated",
)


@dataclass(frozen=True)
class Memory(SerializableModel):
    memory_id: str
    cell_id: str
    statement: str
    candidate_ids: List[str]
    kind: Optional[str] = None
    memory_type: Optional[str] = None
    rationale: Optional[str] = None
    status: str = "proposed"
    confidence: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    use_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "memory_type", resolve_memory_type(self.memory_type, kind=self.kind, trust_tier="trace"))

    _required_fields: ClassVar[Sequence[str]] = (
        "memory_id",
        "cell_id",
        "statement",
        "candidate_ids",
    )
    _non_empty_fields: ClassVar[Sequence[str]] = ("candidate_ids",)
    _bounded_fields: ClassVar[Sequence[str]] = ("confidence",)
    _field_aliases: ClassVar[Dict[str, str]] = {
        "trace_id": "memory_id",
        "source_fragment_ids": "candidate_ids",
    }


@dataclass(frozen=True)
class Pattern(SerializableModel):
    pattern_id: str
    cell_id: str
    theme: str
    summary: str
    memory_ids: List[str]
    proposal_status: str = "proposed"
    confidence: Optional[float] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "pattern_id",
        "cell_id",
        "theme",
        "summary",
        "memory_ids",
    )
    _non_empty_fields: ClassVar[Sequence[str]] = ("memory_ids",)
    _bounded_fields: ClassVar[Sequence[str]] = ("confidence",)
    _field_aliases: ClassVar[Dict[str, str]] = {
        "alloy_id": "pattern_id",
        "source_trace_ids": "memory_ids",
    }


@dataclass(frozen=True)
class RuleProposal(SerializableModel):
    rule_id: str
    pattern_ids: List[str]
    scope: str
    statement: str
    review_status: str = "pending"

    _required_fields: ClassVar[Sequence[str]] = (
        "rule_id",
        "pattern_ids",
        "scope",
        "statement",
        "review_status",
    )
    _non_empty_fields: ClassVar[Sequence[str]] = ("pattern_ids",)
    _field_aliases: ClassVar[Dict[str, str]] = {
        "doctrine_id": "rule_id",
        "source_alloy_ids": "pattern_ids",
    }


@dataclass(frozen=True)
class Pack(SerializableModel):
    pack_id: str
    cell_id: str
    memory_ids: List[str]
    pattern_ids: List[str]
    rule_ids: List[str]
    trust_label: str
    generated_at: str
    metadata: Optional[Dict[str, Any]] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "pack_id",
        "cell_id",
        "memory_ids",
        "pattern_ids",
        "rule_ids",
        "trust_label",
        "generated_at",
    )
    _field_aliases: ClassVar[Dict[str, str]] = {
        "loadout_id": "pack_id",
        "trace_ids": "memory_ids",
        "alloy_ids": "pattern_ids",
        "doctrine_ids": "rule_ids",
    }


@dataclass(frozen=True)
class Feedback(SerializableModel):
    feedback_id: str
    cell_id: str
    pack_id: str
    task_id: str
    verdict: str
    memory_ids: List[str] = field(default_factory=list)
    ignored_memory_ids: List[str] = field(default_factory=list)
    ignored_caution_ids: List[str] = field(default_factory=list)
    contradicted_memory_ids: List[str] = field(default_factory=list)
    over_retrieved_memory_ids: List[str] = field(default_factory=list)
    pack_misses: List[str] = field(default_factory=list)
    pack_miss_details: List[Dict[str, Any]] = field(default_factory=list)
    score: Optional[float] = None
    observed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "feedback_id",
        "cell_id",
        "pack_id",
        "task_id",
        "verdict",
    )
    _bounded_fields: ClassVar[Sequence[str]] = ("score",)
    _field_aliases: ClassVar[Dict[str, str]] = {
        "outcome_id": "feedback_id",
        "loadout_id": "pack_id",
        "trace_ids": "memory_ids",
        "ignored_charge_ids": "ignored_memory_ids",
        "contradicted_charge_ids": "contradicted_memory_ids",
        "over_retrieved_charge_ids": "over_retrieved_memory_ids",
    }


# Legacy compatibility models keep old constructor fields for existing imports and ledgers.
@dataclass(frozen=True)
class Source(SerializableModel):
    source_id: str
    cell_id: str
    kind: str
    sha256: str
    captured_at: str
    uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "source_id",
        "cell_id",
        "kind",
        "sha256",
        "captured_at",
    )


@dataclass(frozen=True)
class Fragment(SerializableModel):
    fragment_id: str
    source_id: str
    cell_id: str
    kind: str
    text: str
    source_excerpt: Optional[str] = None
    boundary_status: str = "pending"
    review_status: str = "pending"
    confidence: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    _required_fields: ClassVar[Sequence[str]] = (
        "fragment_id",
        "source_id",
        "cell_id",
        "text",
    )
    _bounded_fields: ClassVar[Sequence[str]] = ("confidence",)


@dataclass(frozen=True)
class Trace(SerializableModel):
    trace_id: str
    cell_id: str
    statement: str
    source_fragment_ids: List[str]
    kind: Optional[str] = None
    memory_type: Optional[str] = None
    resource_ref: Optional[ResourceRef] = None
    grounding_refs: List[str] = field(default_factory=list)
    sensitivity: Optional[str] = None
    retention_hint: Optional[str] = None
    rationale: Optional[str] = None
    status: str = "proposed"
    confidence: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    use_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "memory_type", resolve_memory_type(self.memory_type, kind=self.kind, trust_tier="trace"))
        object.__setattr__(self, "grounding_refs", _normalize_string_list(self.grounding_refs, "grounding_refs"))
        object.__setattr__(self, "sensitivity", _normalize_optional_text(self.sensitivity))
        object.__setattr__(self, "retention_hint", _normalize_optional_text(self.retention_hint))
        if self.resource_ref is not None and not isinstance(self.resource_ref, ResourceRef):
            raise ValueError("resource_ref must be a ResourceRef")
        if self.memory_type == "resource" and self.resource_ref is None:
            raise ValueError("resource_ref is required for resource memory")

    def to_dict(self) -> Dict[str, Any]:
        payload = super().to_dict()
        if self.resource_ref is not None:
            payload["resource_ref"] = self.resource_ref.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Trace":
        data = dict(payload)
        resource_ref = data.get("resource_ref")
        if isinstance(resource_ref, str):
            resource_ref = {"ref_type": "artifact", "locator": resource_ref, "label": resource_ref}
        if isinstance(resource_ref, dict):
            data["resource_ref"] = ResourceRef.from_dict(resource_ref)
        grounding_refs = data.get("grounding_refs")
        if grounding_refs is None and isinstance(data.get("metadata"), dict):
            grounding_refs = data["metadata"].get("grounding_refs")
        if grounding_refs is not None:
            data["grounding_refs"] = grounding_refs
        if data.get("sensitivity") is None and isinstance(data.get("metadata"), dict):
            data["sensitivity"] = data["metadata"].get("sensitivity")
        if data.get("retention_hint") is None and isinstance(data.get("metadata"), dict):
            data["retention_hint"] = data["metadata"].get("retention_hint")
        return super().from_dict(data)

    _required_fields: ClassVar[Sequence[str]] = (
        "trace_id",
        "cell_id",
        "statement",
        "source_fragment_ids",
    )
    _non_empty_fields: ClassVar[Sequence[str]] = ("source_fragment_ids",)
    _bounded_fields: ClassVar[Sequence[str]] = ("confidence",)


@dataclass(frozen=True)
class Alloy(SerializableModel):
    alloy_id: str
    cell_id: str
    theme: str
    summary: str
    source_trace_ids: List[str]
    proposal_status: str = "proposed"
    confidence: Optional[float] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "alloy_id",
        "cell_id",
        "theme",
        "summary",
        "source_trace_ids",
    )
    _non_empty_fields: ClassVar[Sequence[str]] = ("source_trace_ids",)
    _bounded_fields: ClassVar[Sequence[str]] = ("confidence",)


@dataclass(frozen=True)
class DoctrineProposal(SerializableModel):
    doctrine_id: str
    source_alloy_ids: List[str]
    scope: str
    statement: str
    review_status: str = "pending"

    _required_fields: ClassVar[Sequence[str]] = (
        "doctrine_id",
        "source_alloy_ids",
        "scope",
        "statement",
        "review_status",
    )
    _non_empty_fields: ClassVar[Sequence[str]] = ("source_alloy_ids",)


@dataclass(frozen=True)
class Loadout(SerializableModel):
    loadout_id: str
    cell_id: str
    trace_ids: List[str]
    alloy_ids: List[str]
    doctrine_ids: List[str]
    trust_label: str
    generated_at: str
    metadata: Optional[Dict[str, Any]] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "loadout_id",
        "cell_id",
        "trace_ids",
        "alloy_ids",
        "doctrine_ids",
        "trust_label",
        "generated_at",
    )


@dataclass(frozen=True)
class Outcome(SerializableModel):
    outcome_id: str
    cell_id: str
    loadout_id: str
    task_id: str
    verdict: str
    trace_ids: List[str] = field(default_factory=list)
    ignored_charge_ids: List[str] = field(default_factory=list)
    ignored_caution_ids: List[str] = field(default_factory=list)
    contradicted_charge_ids: List[str] = field(default_factory=list)
    over_retrieved_charge_ids: List[str] = field(default_factory=list)
    pack_misses: List[str] = field(default_factory=list)
    pack_miss_details: List[Dict[str, Any]] = field(default_factory=list)
    score: Optional[float] = None
    observed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    _required_fields: ClassVar[Sequence[str]] = (
        "outcome_id",
        "cell_id",
        "loadout_id",
        "task_id",
        "verdict",
    )
    _bounded_fields: ClassVar[Sequence[str]] = ("score",)


# Deprecated public aliases retained for compatibility with the former power theme.
Pulse = Evidence
Spark = Candidate
Charge = Memory
Coil = Pattern
RailProposal = RuleProposal
Signal = Feedback

# Deprecated implementation aliases retained for existing imports and cells.
TRACE_KINDS = MEMORY_KINDS
TRACE_STATUSES = MEMORY_STATUSES
