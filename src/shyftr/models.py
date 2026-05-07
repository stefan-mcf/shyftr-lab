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
