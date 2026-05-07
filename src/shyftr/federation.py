from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import uuid4

from .ledger import append_jsonl, read_jsonl
from .privacy import AccessPolicy, is_charge_export_allowed, redact_charge_projection

PathLike = Union[str, Path]
TRUST_LABELS = {"local", "imported", "federated", "verified"}
SCHEMA_VERSION = "federation.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _records(path: Path) -> List[Dict[str, Any]]:
    return [record for _, record in read_jsonl(path)] if path.exists() else []


def _manifest(cell: Path) -> Dict[str, Any]:
    path = cell / "config" / "cell_manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"cell_id": cell.name, "cell_type": "domain"}


def _record_id(record: Dict[str, Any]) -> str:
    return str(record.get("memory_id") or record.get("trace_id") or record.get("pattern_id") or record.get("alloy_id") or record.get("rule_id") or record.get("doctrine_id") or "")


def _approved_records(cell: Path, policy: AccessPolicy) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    redacted = 0
    sources = [
        ("memory", cell / "ledger" / "memories" / "approved.jsonl"),
        ("memory", cell / "traces" / "approved.jsonl"),
        ("pattern", cell / "ledger" / "patterns" / "approved.jsonl"),
        ("pattern", cell / "alloys" / "approved.jsonl"),
        ("rule", cell / "ledger" / "rules" / "approved.jsonl"),
        ("rule", cell / "doctrine" / "approved.jsonl"),
    ]
    for kind, path in sources:
        for record in _records(path):
            rid = _record_id(record)
            if kind == "memory":
                allowed, reasons = is_charge_export_allowed(record, policy, cell_path=cell)
                if not allowed:
                    excluded.append({"record_id": rid, "record_kind": kind, "reasons": reasons})
                    continue
                projected = redact_charge_projection(record)
                if projected.get("redacted"):
                    redacted += 1
            else:
                projected = dict(record)
            projected.pop("local_path", None)
            projected.pop("cell_path", None)
            records.append({
                "record_kind": kind,
                "record_id": rid,
                "source_path_kind": path.name,
                "payload": projected,
                "trust_label": "local",
            })
    return records, {"excluded": excluded, "redacted_count": redacted, "policy": policy.to_dict()}


def validate_export_package(payload: Dict[str, Any]) -> Dict[str, Any]:
    required = ["schema_version", "export_id", "source_cell_id", "source_cell_type", "created_at", "records", "redaction_summary", "provenance", "policy_summary"]
    missing = [name for name in required if name not in payload]
    if missing:
        raise ValueError(f"Missing federation package field(s): {', '.join(missing)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported federation package schema_version")
    for record in payload.get("records") or []:
        if record.get("record_kind") not in {"memory", "pattern", "rule"}:
            raise ValueError(f"Unknown federation record kind: {record.get('record_kind')}")
        label = str(record.get("trust_label") or "local")
        if label not in TRUST_LABELS:
            raise ValueError(f"Unsupported trust label: {label}")
        encoded = json.dumps(record, sort_keys=True)
        if "/Users/" in encoded or "\\Users\\" in encoded:
            raise ValueError("federation package records must not include local absolute paths")
    return payload


def export_cell(cell_path: PathLike, output_path: PathLike, policy: Optional[AccessPolicy] = None) -> Dict[str, Any]:
    cell = Path(cell_path)
    manifest = _manifest(cell)
    access_policy = policy or AccessPolicy(runtime_id="federation-export", allowed_sensitivity=("public", "internal"))
    records, summary = _approved_records(cell, access_policy)
    export_id = f"export-{hashlib.sha256((str(manifest.get('cell_id')) + _now()).encode()).hexdigest()[:12]}"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "export_id": export_id,
        "source_cell_id": str(manifest.get("cell_id") or cell.name),
        "source_cell_type": str(manifest.get("cell_type") or "domain"),
        "created_at": _now(),
        "records": records,
        "redaction_summary": summary,
        "provenance": {"activity_id": f"activity-{uuid4().hex[:12]}", "derivation_kind": "selective_federation_export", "source_cell_id": str(manifest.get("cell_id") or cell.name)},
        "policy_summary": access_policy.to_dict(),
        "package_signature": None,
    }
    validate_export_package(payload)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    append_jsonl(cell / "ledger" / "federation_events.jsonl", {"event_kind": "exported", "export_id": export_id, "record_count": len(records), "created_at": payload["created_at"], "append_only": True})
    return payload


def import_package(target_cell_path: PathLike, package_path: PathLike, review_mode: str = "required", trust_label: str = "imported", record_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    if trust_label not in TRUST_LABELS - {"local", "verified"}:
        raise ValueError("imports must start as imported or federated")
    if review_mode != "required":
        raise ValueError("federation import review_mode must be required")
    target = Path(target_cell_path)
    package = validate_export_package(json.loads(Path(package_path).read_text(encoding="utf-8")))
    wanted = set(record_ids or [])
    import_id = f"import-{uuid4().hex[:12]}"
    imported: List[Dict[str, Any]] = []
    for record in package["records"]:
        if wanted and record.get("record_id") not in wanted:
            continue
        candidate = {
            "import_id": f"{import_id}-{len(imported)+1}",
            "package_import_id": import_id,
            "source_export_id": package["export_id"],
            "source_cell_id": package["source_cell_id"],
            "source_record_id": record["record_id"],
            "record_kind": record["record_kind"],
            "payload": record["payload"],
            "trust_label": trust_label,
            "review_status": "pending",
            "provenance": {"source_cell_id": package["source_cell_id"], "source_record_id": record["record_id"], "source_export_id": package["export_id"], "activity_id": package["provenance"].get("activity_id")},
            "imported_at": _now(),
        }
        append_jsonl(target / "ledger" / "import_candidates.jsonl", candidate)
        imported.append(candidate)
    event = {"event_kind": "imported", "package_import_id": import_id, "source_export_id": package["export_id"], "source_cell_id": package["source_cell_id"], "record_count": len(imported), "created_at": _now(), "append_only": True}
    append_jsonl(target / "ledger" / "federation_events.jsonl", event)
    return {"status": "ok", "package_import_id": import_id, "imported_count": len(imported), "imports": imported}


def list_imports(cell_path: PathLike, status: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _records(Path(cell_path) / "ledger" / "import_candidates.jsonl")
    reviews = {r.get("import_id"): r for r in _records(Path(cell_path) / "ledger" / "import_reviews.jsonl")}
    out = []
    for row in rows:
        merged = dict(row)
        if row.get("import_id") in reviews:
            merged["latest_review"] = reviews[row.get("import_id")]
            merged["review_status"] = reviews[row.get("import_id")].get("review_status", merged.get("review_status"))
            merged["trust_label"] = reviews[row.get("import_id")].get("trust_label", merged.get("trust_label"))
        if status and merged.get("review_status") != status:
            continue
        out.append(merged)
    return out


def review_import(cell_path: PathLike, import_id: str, decision: str, reviewer: str = "operator", rationale: str = "reviewed") -> Dict[str, Any]:
    if decision not in {"approve", "reject"}:
        raise ValueError("decision must be approve or reject")
    candidates = {row.get("import_id"): row for row in list_imports(cell_path)}
    if import_id not in candidates:
        raise ValueError(f"Unknown import_id: {import_id}")
    candidate = candidates[import_id]
    status = "approved" if decision == "approve" else "rejected"
    label = "verified" if decision == "approve" else candidate.get("trust_label", "imported")
    event = {"review_id": f"import-review-{uuid4().hex[:12]}", "import_id": import_id, "review_status": status, "trust_label": label, "reviewer": reviewer, "rationale": rationale, "reviewed_at": _now(), "append_only": True}
    cell = Path(cell_path)
    append_jsonl(cell / "ledger" / "import_reviews.jsonl", event)
    if decision == "approve" and candidate.get("record_kind") == "memory":
        payload = dict(candidate.get("payload") or {})
        source_id = str(candidate.get("source_record_id"))
        payload.setdefault("trace_id", f"verified-import-{source_id}")
        payload["trust_label"] = "verified"
        payload["source_cell_id"] = candidate.get("source_cell_id")
        payload["source_record_id"] = source_id
        payload["status"] = "approved"
        append_jsonl(cell / "traces" / "approved.jsonl", payload)
    return event


def approve_import(cell_path: PathLike, import_id: str, reviewer: str = "operator", rationale: str = "approved") -> Dict[str, Any]:
    return review_import(cell_path, import_id, "approve", reviewer=reviewer, rationale=rationale)


def reject_import(cell_path: PathLike, import_id: str, reviewer: str = "operator", rationale: str = "rejected") -> Dict[str, Any]:
    return review_import(cell_path, import_id, "reject", reviewer=reviewer, rationale=rationale)
