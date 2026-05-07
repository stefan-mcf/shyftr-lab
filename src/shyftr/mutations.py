from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.ledger_state import latest_by_key
from shyftr.models import Trace

PathLike = Union[str, Path]
JsonRecord = Dict[str, Any]

STATUS_EVENTS = "ledger/status_events.jsonl"
SUPERSESSION_EVENTS = "ledger/supersession_events.jsonl"
DEPRECATION_EVENTS = "ledger/deprecation_events.jsonl"
ISOLATION_EVENTS = "ledger/isolation_events.jsonl"
CONFLICT_EVENTS = "ledger/conflict_events.jsonl"
REDACTION_EVENTS = "ledger/redaction_events.jsonl"

LIFECYCLE_LEDGER_FILES = (
    STATUS_EVENTS,
    SUPERSESSION_EVENTS,
    DEPRECATION_EVENTS,
    ISOLATION_EVENTS,
    CONFLICT_EVENTS,
    REDACTION_EVENTS,
)

EXCLUDED_EFFECTIVE_STATUSES = {
    "forgotten",
    "replaced",
    "superseded",
    "deprecated",
    "isolation_candidate",
    "isolated",
    "redacted",
}
RISKY_INCLUDED_STATUSES = {"challenged"}


@dataclass(frozen=True)
class MutationEventResult:
    event_id: str
    action: str
    charge_id: str
    reason: str
    actor: str
    replacement_charge_id: Optional[str] = None


@dataclass(frozen=True)
class EffectiveChargeState:
    charge_id: str
    lifecycle_status: str = "active"
    include_in_retrieval: bool = True
    include_in_profile: bool = True
    include_in_pack: bool = True
    replacement_charge_id: Optional[str] = None
    sensitive_excluded: bool = False
    conflict_charge_ids: List[str] = field(default_factory=list)
    latest_event_id: Optional[str] = None
    latest_event_at: Optional[str] = None
    event_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> JsonRecord:
        return {
            "charge_id": self.charge_id,
            "lifecycle_status": self.lifecycle_status,
            "include_in_retrieval": self.include_in_retrieval,
            "include_in_profile": self.include_in_profile,
            "include_in_pack": self.include_in_pack,
            "replacement_charge_id": self.replacement_charge_id,
            "sensitive_excluded": self.sensitive_excluded,
            "conflict_charge_ids": list(self.conflict_charge_ids),
            "latest_event_id": self.latest_event_id,
            "latest_event_at": self.latest_event_at,
            "event_ids": list(self.event_ids),
        }


def forget_charge(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> MutationEventResult:
    _require_trace(Path(cell_path), charge_id)
    event = _status_event(charge_id, "forgotten", reason, actor, action="forget")
    append_jsonl(Path(cell_path) / STATUS_EVENTS, event)
    return _result(event)


def replace_charge(
    cell_path: PathLike,
    charge_id: str,
    new_statement: str,
    *,
    reason: str,
    actor: str,
) -> MutationEventResult:
    cell = Path(cell_path)
    old = _require_trace(cell, charge_id)
    from shyftr.provider.memory import remember

    replacement = remember(
        cell,
        new_statement,
        old.kind or "preference",
        pulse_context={"actor": actor, "replacement_for": charge_id},
        metadata={"actor": actor, "reason": reason, "provider_api": "replace"},
    )
    supersession = _base_event("sup", "replace", charge_id, reason, actor)
    supersession.update(
        {
            "old_charge_id": charge_id,
            "new_charge_id": replacement.charge_id,
            "replacement_charge_id": replacement.charge_id,
            "supersession_status": "superseded",
        }
    )
    append_jsonl(cell / SUPERSESSION_EVENTS, supersession)
    status = _status_event(
        charge_id,
        "superseded",
        reason,
        actor,
        action="replace",
        replacement_charge_id=replacement.charge_id,
        event_id=supersession["event_id"],
        created_at=supersession["created_at"],
    )
    append_jsonl(cell / STATUS_EVENTS, status)
    return _result(status)


def deprecate_charge(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> MutationEventResult:
    _require_trace(Path(cell_path), charge_id)
    event = _status_event(charge_id, "deprecated", reason, actor, action="deprecate")
    append_jsonl(Path(cell_path) / DEPRECATION_EVENTS, dict(event, deprecation_status="deprecated"))
    append_jsonl(Path(cell_path) / STATUS_EVENTS, event)
    return _result(event)


def isolation_charge(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> MutationEventResult:
    _require_trace(Path(cell_path), charge_id)
    event = _status_event(charge_id, "isolated", reason, actor, action="isolate")
    append_jsonl(Path(cell_path) / ISOLATION_EVENTS, dict(event, isolation_status="isolated"))
    append_jsonl(Path(cell_path) / STATUS_EVENTS, event)
    return _result(event)


def challenge_charge(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> MutationEventResult:
    _require_trace(Path(cell_path), charge_id)
    event = _status_event(charge_id, "challenged", reason, actor, action="challenge")
    append_jsonl(Path(cell_path) / ISOLATION_EVENTS, dict(event, isolation_status="challenged"))
    append_jsonl(Path(cell_path) / STATUS_EVENTS, event)
    return _result(event)


def mark_isolation_candidate(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> MutationEventResult:
    _require_trace(Path(cell_path), charge_id)
    event = _status_event(charge_id, "isolation_candidate", reason, actor, action="isolation_candidate")
    append_jsonl(Path(cell_path) / ISOLATION_EVENTS, dict(event, isolation_status="isolation_candidate"))
    append_jsonl(Path(cell_path) / STATUS_EVENTS, event)
    return _result(event)


def restore_charge(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> MutationEventResult:
    _require_trace(Path(cell_path), charge_id)
    event = _status_event(charge_id, "active", reason, actor, action="restore")
    append_jsonl(Path(cell_path) / ISOLATION_EVENTS, dict(event, isolation_status="restored"))
    append_jsonl(Path(cell_path) / STATUS_EVENTS, event)
    return _result(event)


def record_conflict(
    cell_path: PathLike,
    left_charge_id: str,
    right_charge_id: str,
    *,
    reason: str,
    actor: str,
) -> MutationEventResult:
    cell = Path(cell_path)
    _require_trace(cell, left_charge_id)
    _require_trace(cell, right_charge_id)
    event = _base_event("conf", "conflict", left_charge_id, reason, actor)
    event.update(
        {
            "left_charge_id": left_charge_id,
            "right_charge_id": right_charge_id,
            "charge_ids": [left_charge_id, right_charge_id],
            "conflict_status": "recorded",
            "winner_charge_id": None,
        }
    )
    append_jsonl(cell / CONFLICT_EVENTS, event)
    return _result(event)


def redact_charge(cell_path: PathLike, charge_id: str, *, reason: str, actor: str) -> MutationEventResult:
    _require_trace(Path(cell_path), charge_id)
    event = _base_event("red", "redact", charge_id, reason, actor)
    event.update(
        {
            "redaction_status": "projection_excluded",
            "sensitive_excluded": True,
            "include_in_profile": False,
            "include_in_retrieval": False,
            "include_in_pack": False,
        }
    )
    append_jsonl(Path(cell_path) / REDACTION_EVENTS, event)
    return _result(event)


def get_effective_charge_states(cell_path: PathLike) -> Dict[str, EffectiveChargeState]:
    cell = Path(cell_path)
    states: Dict[str, Dict[str, Any]] = {
        trace.trace_id: {
            "charge_id": trace.trace_id,
            "lifecycle_status": "active",
            "include_in_retrieval": True,
            "include_in_profile": True,
            "include_in_pack": True,
            "replacement_charge_id": None,
            "sensitive_excluded": False,
            "conflict_charge_ids": [],
            "latest_event_id": None,
            "latest_event_at": None,
            "event_ids": [],
        }
        for trace in approved_traces(cell)
    }

    def ensure(charge_id: str) -> Dict[str, Any]:
        return states.setdefault(
            charge_id,
            {
                "charge_id": charge_id,
                "lifecycle_status": "active",
                "include_in_retrieval": True,
                "include_in_profile": True,
                "include_in_pack": True,
                "replacement_charge_id": None,
                "sensitive_excluded": False,
                "conflict_charge_ids": [],
                "latest_event_id": None,
                "latest_event_at": None,
                "event_ids": [],
            },
        )

    events = _read_lifecycle_events(cell)
    for _, event in sorted(events, key=lambda item: _event_sort_key(item[0], item[1])):
        action = event.get("action")
        charge_id = event.get("charge_id") or event.get("old_charge_id")
        if not isinstance(charge_id, str):
            continue
        state = ensure(charge_id)
        event_id = str(event.get("event_id") or "")
        if event_id:
            state["event_ids"].append(event_id)
        state["latest_event_id"] = event_id or state.get("latest_event_id")
        state["latest_event_at"] = event.get("created_at") or state.get("latest_event_at")

        if action in {"forget", "replace", "deprecate", "isolate", "challenge", "isolation_candidate", "restore"} or event.get("status"):
            status = str(event.get("status") or "").strip()
            if action == "forget":
                status = "forgotten"
            elif action == "replace":
                status = status or "superseded"
            elif action == "deprecate":
                status = "deprecated"
            elif action == "isolate":
                status = "isolated"
            elif action == "challenge":
                status = "challenged"
            elif action == "isolation_candidate":
                status = "isolation_candidate"
            elif action == "restore":
                status = "active"
            if status:
                state["lifecycle_status"] = "superseded" if status == "replaced" else status
                if state["lifecycle_status"] in EXCLUDED_EFFECTIVE_STATUSES:
                    state["include_in_retrieval"] = False
                    state["include_in_profile"] = False
                    state["include_in_pack"] = False
                elif state["lifecycle_status"] == "active" or state["lifecycle_status"] in RISKY_INCLUDED_STATUSES:
                    state["include_in_retrieval"] = True
                    state["include_in_profile"] = True
                    state["include_in_pack"] = True
            replacement = event.get("replacement_charge_id") or event.get("new_charge_id")
            if isinstance(replacement, str) and replacement:
                state["replacement_charge_id"] = replacement
        elif action == "redact":
            state["lifecycle_status"] = "redacted"
            state["sensitive_excluded"] = True
            state["include_in_retrieval"] = False
            state["include_in_profile"] = False
            state["include_in_pack"] = False
        elif action == "conflict":
            ids = event.get("charge_ids") or [event.get("left_charge_id"), event.get("right_charge_id")]
            ids = [item for item in ids if isinstance(item, str)] if isinstance(ids, list) else []
            for cid in ids:
                other_state = ensure(cid)
                others = [other for other in ids if other != cid]
                for other in others:
                    if other not in other_state["conflict_charge_ids"]:
                        other_state["conflict_charge_ids"].append(other)
                if event_id:
                    other_state["event_ids"].append(event_id)
                other_state["latest_event_id"] = event_id or other_state.get("latest_event_id")
                other_state["latest_event_at"] = event.get("created_at") or other_state.get("latest_event_at")

    return {charge_id: EffectiveChargeState(**state) for charge_id, state in states.items()}


def effective_state_for_charge(cell_path: PathLike, charge_id: str) -> EffectiveChargeState:
    return get_effective_charge_states(cell_path).get(charge_id, EffectiveChargeState(charge_id=charge_id))


def active_charge_ids(cell_path: PathLike, *, projection: str = "retrieval") -> set[str]:
    states = get_effective_charge_states(cell_path)
    include_field = {
        "retrieval": "include_in_retrieval",
        "profile": "include_in_profile",
        "pack": "include_in_pack",
    }.get(projection, "include_in_retrieval")
    return {charge_id for charge_id, state in states.items() if getattr(state, include_field)}


def is_charge_included_by_default(cell_path: PathLike, charge_id: str, *, projection: str = "retrieval") -> bool:
    return charge_id in active_charge_ids(cell_path, projection=projection)


def approved_traces(cell_path: PathLike) -> List[Trace]:
    cell = Path(cell_path)
    ledger = cell / "traces" / "approved.jsonl"
    if not ledger.exists():
        return []
    allowed = {field.name for field in fields(Trace)}
    records = [record for _, record in read_jsonl(ledger)]
    latest_records = latest_by_key(records, "trace_id")
    traces = [
        Trace.from_dict({key: value for key, value in record.items() if key in allowed})
        for record in latest_records
    ]
    return [trace for trace in traces if trace.status == "approved"]


def _read_lifecycle_events(cell: Path) -> List[tuple[int, JsonRecord]]:
    events: List[tuple[int, JsonRecord]] = []
    for relpath in LIFECYCLE_LEDGER_FILES:
        path = cell / relpath
        if not path.exists():
            continue
        for line, record in read_jsonl(path):
            events.append((line, record))
    legacy = cell / "ledger" / "memory_provider_events.jsonl"
    if legacy.exists():
        for line, record in read_jsonl(legacy):
            action = record.get("action")
            mapped = dict(record)
            if action == "forget":
                mapped["status"] = "forgotten"
            elif action == "replace":
                mapped["status"] = "superseded"
            elif action == "deprecate":
                mapped["status"] = "deprecated"
            events.append((line, mapped))
    return events


def _event_sort_key(line_number: int, event: JsonRecord) -> tuple[str, str, int]:
    return (str(event.get("created_at") or ""), str(event.get("event_id") or ""), line_number)


def _base_event(prefix: str, action: str, charge_id: str, reason: str, actor: str) -> JsonRecord:
    return {
        "event_id": f"{prefix}-{uuid4().hex}",
        "action": action,
        "charge_id": _require_text(charge_id, "charge_id"),
        "reason": _require_text(reason, "reason"),
        "actor": _require_text(actor, "actor"),
        "created_at": _now(),
        "canonical_truth": "cell_ledgers",
        "append_only": True,
    }


def _status_event(
    charge_id: str,
    status: str,
    reason: str,
    actor: str,
    *,
    action: str,
    replacement_charge_id: Optional[str] = None,
    event_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> JsonRecord:
    event = _base_event("stat", action, charge_id, reason, actor)
    if event_id is not None:
        event["event_id"] = event_id
    if created_at is not None:
        event["created_at"] = created_at
    event.update(
        {
            "status": status,
            "include_in_retrieval": status not in EXCLUDED_EFFECTIVE_STATUSES,
            "include_in_profile": status not in EXCLUDED_EFFECTIVE_STATUSES,
            "include_in_pack": status not in EXCLUDED_EFFECTIVE_STATUSES,
        }
    )
    if replacement_charge_id is not None:
        event["replacement_charge_id"] = replacement_charge_id
    return event


def _result(event: JsonRecord) -> MutationEventResult:
    return MutationEventResult(
        event_id=str(event["event_id"]),
        action=str(event.get("action") or ""),
        charge_id=str(event.get("charge_id") or event.get("old_charge_id") or ""),
        reason=str(event.get("reason") or ""),
        actor=str(event.get("actor") or ""),
        replacement_charge_id=event.get("replacement_charge_id") if isinstance(event.get("replacement_charge_id"), str) else None,
    )


def _require_trace(cell: Path, charge_id: str) -> Trace:
    clean_id = _require_text(charge_id, "charge_id")
    for trace in approved_traces(cell):
        if trace.trace_id == clean_id:
            return trace
    raise ValueError(f"Unknown charge_id: {charge_id}")


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return " ".join(value.split())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
