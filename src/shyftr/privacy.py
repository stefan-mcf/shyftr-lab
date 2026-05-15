from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

SENSITIVE_NESTED_FIELDS = {"locator", "path", "uri", "sha256", "content_digest", "token", "secret"}
SAFE_NESTED_FIELDS = {"label", "ref_type", "kind", "origin", "span", "safe_display", "source_fragment_ids", "grounding_refs", "trace_id", "cell_id"}

from shyftr.ledger import append_jsonl
from shyftr.mutations import effective_state_for_charge

PathLike = Union[str, Path]

SENSITIVITY_LEVELS = ("public", "internal", "private", "secret", "restricted")
DEFAULT_ALLOWED_LEVELS = ("public", "internal")


@dataclass(frozen=True)
class AccessPolicy:
    runtime_id: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    allowed_sensitivity: Sequence[str] = DEFAULT_ALLOWED_LEVELS
    export_allowed: bool = True
    allow_audit_sensitive: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "allowed_sensitivity": list(self.allowed_sensitivity),
            "export_allowed": self.export_allowed,
            "allow_audit_sensitive": self.allow_audit_sensitive,
            "warnings": list(self.warnings),
        }


def sensitivity_for_charge(record: Dict[str, Any]) -> str:
    raw = record.get("sensitivity") or (record.get("metadata") or {}).get("sensitivity") or "internal"
    sensitivity = str(raw).lower().strip()
    return sensitivity if sensitivity in SENSITIVITY_LEVELS else "internal"


def charge_scope(record: Dict[str, Any]) -> Dict[str, Optional[str]]:
    meta = record.get("metadata") or {}
    return {
        "user_id": record.get("user_id") or meta.get("user_id"),
        "project_id": record.get("project_id") or meta.get("project_id"),
        "runtime_id": record.get("runtime_id") or meta.get("runtime_id"),
    }


def is_charge_export_allowed(
    record: Dict[str, Any],
    policy: AccessPolicy,
    *,
    cell_path: Optional[PathLike] = None,
    audit_mode: bool = False,
) -> tuple[bool, List[str]]:
    warnings: List[str] = []
    charge_id = str(record.get("trace_id") or record.get("charge_id") or "")
    if cell_path is not None and charge_id:
        state = effective_state_for_charge(cell_path, charge_id)
        if not state.include_in_pack and not audit_mode:
            return False, [f"excluded lifecycle state: {state.lifecycle_status}"]
        if state.lifecycle_status in {"challenged", "isolated", "isolation_candidate"}:
            warnings.append(f"risky lifecycle state: {state.lifecycle_status}")
    sensitivity = sensitivity_for_charge(record)
    if sensitivity not in policy.allowed_sensitivity:
        if audit_mode and policy.allow_audit_sensitive:
            warnings.append(f"sensitive guidance included for audit only: {sensitivity}")
        else:
            return False, [f"sensitivity not allowed: {sensitivity}"]
    scope = charge_scope(record)
    for key in ("user_id", "project_id", "runtime_id"):
        value = scope.get(key)
        policy_value = getattr(policy, key)
        if value and policy_value and value != policy_value:
            return False, [f"scope mismatch: {key}"]
    if not policy.export_allowed:
        return False, ["policy forbids export"]
    return True, warnings


def redact_charge_projection(record: Dict[str, Any], *, reason: str = "sensitive") -> Dict[str, Any]:
    redacted = dict(record)
    if sensitivity_for_charge(record) in {"private", "secret", "restricted"}:
        redacted["statement"] = "[REDACTED]"
        for key, value in list(redacted.items()):
            if isinstance(value, dict):
                redacted[key] = _redact_nested_mapping(value)
        redacted["redacted"] = True
        redacted["redaction_reason"] = reason
    return redacted


def _redact_nested_mapping(value: Dict[str, Any]) -> Dict[str, Any]:
    projected: Dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            projected[key] = _redact_nested_mapping(item)
            continue
        if key in SENSITIVE_NESTED_FIELDS:
            projected[key] = "[REDACTED]"
            continue
        projected[key] = item
    return projected


def filter_charge_records(
    cell_path: PathLike,
    records: Iterable[Dict[str, Any]],
    policy: AccessPolicy,
    *,
    audit_mode: bool = False,
) -> Dict[str, Any]:
    included: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    for record in records:
        allowed, row_warnings = is_charge_export_allowed(record, policy, cell_path=cell_path, audit_mode=audit_mode)
        charge_id = str(record.get("trace_id") or record.get("charge_id") or "")
        if allowed:
            projected = record if audit_mode else redact_charge_projection(record)
            included.append(projected)
            if row_warnings:
                warnings.append({"charge_id": charge_id, "warnings": row_warnings})
        else:
            excluded.append({"charge_id": charge_id, "reasons": row_warnings})
    return {"included": included, "excluded": excluded, "warnings": warnings, "policy": policy.to_dict()}


def append_access_policy(cell_path: PathLike, policy: AccessPolicy, *, actor: str = "system") -> None:
    append_jsonl(Path(cell_path) / "ledger" / "access_policy_events.jsonl", {
        "event_type": "access_policy",
        "actor": actor,
        "policy": policy.to_dict(),
        "append_only": True,
        "canonical_truth": "cell_ledgers",
    })
