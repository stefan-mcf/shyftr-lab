"""Replacement-readiness harness for bounded managed-memory pilots."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import json
from typing import Any, Dict, Iterable, List, Optional, Union
from uuid import uuid4

from .ledger import append_jsonl, read_jsonl
from .layout import init_cell
from .pack import is_operational_state
from .observability import append_diagnostic_log, read_diagnostic_logs, summarize_diagnostics
from .provider.memory import MemoryProvider

PathLike = Union[str, Path]


def _records(path: Path) -> List[Dict[str, Any]]:
    return [record for _, record in read_jsonl(path)] if path.exists() else []


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    details: str = ""
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ReadinessReport:
    status: str
    ready: bool
    cell_id: str
    checks: List[ReadinessCheck]
    blockers: List[str] = field(default_factory=list)
    replay_report: Optional[Dict[str, Any]] = None
    diagnostic_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "ready": self.ready,
            "cell_id": self.cell_id,
            "checks": [check.to_dict() for check in self.checks],
            "blockers": list(self.blockers),
            "replay_report": self.replay_report,
            "diagnostic_summary": dict(self.diagnostic_summary),
            "authority_boundary": "bounded-domain primary memory only after operator approval; existing backend remains fallback/archive",
            "schema_version": "replacement-readiness/v1",
        }


def read_manifest_cell_id(cell_path: PathLike) -> str:
    manifest = Path(cell_path) / "config" / "cell_manifest.json"
    return str(json.loads(manifest.read_text(encoding="utf-8")).get("cell_id"))


def export_replacement_snapshot(cell_path: PathLike) -> Dict[str, Any]:
    """Export a rollback/archive snapshot from canonical Cell ledgers."""
    cell = Path(cell_path)
    payload = {
        "schema_version": "shyftr-snapshot/v1",
        "cell_id": read_manifest_cell_id(cell),
        "ledgers": {},
        "fallback_archive_preserved": True,
    }
    for ledger in sorted((cell / "ledger").glob("*.jsonl")):
        payload["ledgers"][f"ledger/{ledger.name}"] = _records(ledger)
    for rel in ("traces/approved.jsonl", "traces/deprecated.jsonl", "charges/approved.jsonl"):
        payload["ledgers"][rel] = _records(cell / rel)
    append_diagnostic_log(cell, operation="export_snapshot", runtime_id="readiness", metadata={"ledger_count": len(payload["ledgers"])})
    return payload


def import_replacement_snapshot(target_cell_path: PathLike, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Import a snapshot into an empty Cell while preserving append-only files."""
    cell = Path(target_cell_path)
    imported = 0
    for rel, records in sorted(dict(snapshot.get("ledgers", {})).items()):
        path = cell / rel
        if path.exists() and _records(path):
            append_diagnostic_log(
                cell,
                operation="import_snapshot",
                runtime_id="readiness",
                status="rejected",
                warnings=[f"target ledger is not empty: {rel}"],
            )
            raise ValueError(f"Refusing to import snapshot into non-empty append-only ledger: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        for record in records:
            append_jsonl(path, dict(record))
            imported += 1
    append_diagnostic_log(cell, operation="import_snapshot", runtime_id="readiness", metadata={"record_count": imported})
    return {"status": "ok", "record_count": imported, "cell_id": read_manifest_cell_id(cell)}


def import_managed_memory_records(cell_path: PathLike, records: Iterable[Dict[str, Any]], *, runtime_id: str = "managed-memory-import") -> Dict[str, Any]:
    """Import exported managed-memory records through Regulator-governed provider writes.

    Noisy operational state and secrets are rejected before promotion.
    """
    provider = MemoryProvider(cell_path)
    imported: List[str] = []
    rejected: List[Dict[str, Any]] = []
    for record in records:
        text = str(record.get("statement") or record.get("memory") or record.get("text") or "").strip()
        kind = str(record.get("kind") or "memory")
        if not text or is_operational_state(text):
            rejected.append({"external_id": record.get("id"), "reason": "operational_state_or_empty"})
            continue
        try:
            result = provider.remember(
                text,
                kind,
                pulse_context={"external_id": record.get("id"), "runtime_id": runtime_id},
                metadata={"actor": runtime_id, "tags": list(record.get("tags", [])) if isinstance(record.get("tags"), list) else []},
            )
            imported.append(result.charge_id)
        except Exception as exc:
            rejected.append({"external_id": record.get("id"), "reason": exc.__class__.__name__})
    append_diagnostic_log(
        cell_path,
        operation="managed_memory_import",
        runtime_id=runtime_id,
        selected_charge_ids=imported,
        warnings=[f"rejected:{len(rejected)}"] if rejected else [],
        regulator_decisions=[{"status": "rejected", **item} for item in rejected],
    )
    return {"status": "ok", "imported_charge_ids": imported, "rejected": rejected}


def run_replacement_replay(cell_path: PathLike, fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Run a deterministic replacement replay against a Cell."""
    provider = MemoryProvider(cell_path)
    migration = import_managed_memory_records(cell_path, fixture.get("exported_memories", []))
    query = str(fixture.get("query") or "preferences workflow guidance")
    pack_one = provider.pack(query, task_id="replacement-replay", runtime_id="replacement-replay")
    pack_two = provider.pack(query, task_id="replacement-replay", runtime_id="replacement-replay")
    deterministic = [i["statement"] for i in pack_one["items"]] == [i["statement"] for i in pack_two["items"]]
    selected_ids = list(pack_one.get("selected_ids", []))
    signal = provider.record_signal(
        pack_one["loadout_id"],
        result=str(fixture.get("result") or "success"),
        applied_charge_ids=selected_ids[:1],
        useful_charge_ids=selected_ids[:1],
        harmful_charge_ids=list(fixture.get("harmful_charge_ids", [])),
        missing_memory_notes=list(fixture.get("missing_memory_notes", ["Need bounded-domain rollback runbook."])),
        runtime_id="replacement-replay",
        task_id="replacement-replay-task",
    )
    snapshot = provider.export_snapshot()
    report = {
        "status": "passed" if deterministic and selected_ids and signal.get("accepted") else "failed",
        "imported_count": len(migration["imported_charge_ids"]),
        "rejected_count": len(migration["rejected"]),
        "selected_charge_ids": selected_ids,
        "deterministic_pack": deterministic,
        "signal_id": signal.get("outcome_id"),
        "fallback_archive_preserved": bool(snapshot.get("fallback_archive_preserved")),
        "diagnostic_count": len(read_diagnostic_logs(cell_path)),
    }
    append_jsonl(Path(cell_path) / "reports" / "replacement_replay_reports.jsonl", report)
    append_diagnostic_log(cell_path, operation="replacement_replay", runtime_id="replacement-replay", status=report["status"], selected_charge_ids=selected_ids, signal_id=signal.get("outcome_id"))
    return report


def replacement_pilot_readiness(cell_path: PathLike, *, run_replay: bool = False, fixture_path: Optional[PathLike] = None) -> ReadinessReport:
    cell = Path(cell_path)
    cell_id = read_manifest_cell_id(cell)
    replay_report: Optional[Dict[str, Any]] = None
    evidence_cell = cell
    tempdir: Optional[tempfile.TemporaryDirectory[str]] = None
    if run_replay:
        fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8")) if fixture_path else default_replacement_fixture()
        tempdir = tempfile.TemporaryDirectory(prefix="shyftr-replacement-readiness-")
        evidence_cell = init_cell(Path(tempdir.name), f"{cell_id}-readiness-shadow", cell_type="user")
        replay_report = run_replacement_replay(evidence_cell, fixture)

    diagnostics = summarize_diagnostics(evidence_cell)
    ledgers = {
        "sources": _records(evidence_cell / "ledger" / "sources.jsonl"),
        "fragments": _records(evidence_cell / "ledger" / "fragments.jsonl"),
        "reviews": _records(evidence_cell / "ledger" / "reviews.jsonl"),
        "promotions": _records(evidence_cell / "ledger" / "promotions.jsonl"),
        "retrieval_logs": _records(evidence_cell / "ledger" / "retrieval_logs.jsonl"),
        "outcomes": _records(evidence_cell / "ledger" / "outcomes.jsonl"),
        "traces": _records(evidence_cell / "traces" / "approved.jsonl"),
    }
    checks = [
        ReadinessCheck("review_gated_promotions", bool(ledgers["reviews"] and ledgers["promotions"]), "Provider writes produced review and promotion ledgers."),
        ReadinessCheck("pack_retrieval_logs", bool(ledgers["retrieval_logs"]), "Pack generation appended retrieval logs."),
        ReadinessCheck("signal_linkage", bool(ledgers["outcomes"]), "Signal/Outcome records are present."),
        ReadinessCheck("diagnostic_logs", diagnostics.get("diagnostic_count", 0) > 0, "Diagnostic logs explain operations."),
        ReadinessCheck("fallback_export", bool(export_replacement_snapshot(evidence_cell).get("fallback_archive_preserved")), "Export snapshot preserves fallback/archive path."),
    ]
    if replay_report is not None:
        checks.append(ReadinessCheck("replacement_replay", replay_report.get("status") == "passed", "Controlled replay report completed.", [] if replay_report.get("status") == "passed" else ["replacement replay failed"]))
    blockers: List[str] = []
    for check in checks:
        if not check.passed:
            blockers.extend(check.blockers or [check.name])
    ready = not blockers and (replay_report is None or replay_report.get("status") == "passed")
    report = ReadinessReport(
        status="passed" if ready else "blocked",
        ready=ready,
        cell_id=cell_id,
        checks=checks,
        blockers=blockers,
        replay_report=replay_report,
        diagnostic_summary=summarize_diagnostics(evidence_cell),
    )
    append_jsonl(cell / "reports" / "replacement_readiness_reports.jsonl", report.to_dict())
    metadata = {"replay_mode": "shadow" if run_replay else "in_place_checks"}
    if run_replay:
        metadata["evidence_cell_id"] = read_manifest_cell_id(evidence_cell)
    append_diagnostic_log(cell, operation="replacement_readiness", runtime_id="readiness", status=report.status, warnings=blockers, metadata=metadata)
    if tempdir is not None:
        tempdir.cleanup()
    return report


def default_replacement_fixture() -> Dict[str, Any]:
    return {
        "exported_memories": [
            {"id": "pref-1", "kind": "preference", "memory": "User prefers concise terminal-readable updates."},
            {"id": "workflow-1", "kind": "workflow", "memory": "Run tests before claiming ShyftR replacement readiness."},
            {"id": "noise-1", "kind": "workflow", "memory": "Queue item task-123 is in_progress on branch tmp/demo."},
        ],
        "query": "concise updates tests replacement readiness",
        "result": "success",
        "missing_memory_notes": ["Need rollback/archive proof before bounded-domain primary mode."],
    }
