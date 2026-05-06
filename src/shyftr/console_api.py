"""Console-facing read models and pilot metrics for the local ShyftR UI.

These helpers are projections over append-only Cell ledgers. They intentionally
avoid becoming a second write path: every mutating console endpoint delegates to
existing Regulator/ledger functions.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from .ledger import read_jsonl
from .mutations import get_effective_charge_states
from .models import with_canonical_memory_id
from .observability import summarize_diagnostics

PathLike = Union[str, Path]


def _records(path: Path) -> List[Dict[str, Any]]:
    return [record for _, record in read_jsonl(path)] if path.exists() else []


def _manifest(cell: Path) -> Dict[str, Any]:
    path = cell / "config" / "cell_manifest.json"
    if not path.exists():
        return {"cell_id": cell.name, "cell_type": "unknown"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"cell_id": cell.name, "cell_type": "invalid"}


def _latest_by(records: Iterable[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for record in records:
        value = record.get(key)
        if value:
            latest[str(value)] = record
    return latest


def cell_summary(cell_path: PathLike) -> Dict[str, Any]:
    """Return the dashboard projection for a Cell."""

    cell = Path(cell_path)
    manifest = _manifest(cell)
    sources = _records(cell / "ledger" / "sources.jsonl")
    pulses = _records(cell / "ledger" / "pulses.jsonl")
    sparks = _records(cell / "ledger" / "fragments.jsonl") + _records(cell / "ledger" / "sparks.jsonl")
    reviews = _records(cell / "ledger" / "reviews.jsonl")
    review_by_spark = _latest_by(reviews, "fragment_id")
    charges = _records(cell / "traces" / "approved.jsonl") + _records(cell / "charges" / "approved.jsonl")
    signals = _records(cell / "ledger" / "outcomes.jsonl") + _records(cell / "ledger" / "signals.jsonl")
    proposals = proposal_inbox(cell)["proposals"]
    diagnostics = summarize_diagnostics(cell)

    pending_sparks = [
        spark for spark in sparks
        if review_by_spark.get(str(spark.get("fragment_id") or spark.get("spark_id")), {}).get("review_status", spark.get("review_status", "pending")) == "pending"
    ]
    hygiene_warnings = len(diagnostics.get("warnings", [])) + len(diagnostics.get("errors", []))
    grid_files = list((cell / "grid").glob("*")) + list((cell / "indexes").glob("*"))

    return {
        "status": "ok",
        "cell_id": manifest.get("cell_id") or cell.name,
        "cell_type": manifest.get("cell_type"),
        "cell_path": str(cell),
        "counts": {
            "pulses": len(pulses) + len(sources),
            "sparks": len(sparks),
            "pending_review": len(pending_sparks),
            "approved_charges": len(charges),
            "approved_memories": len(charges),
            "signals": len(signals),
            "feedback": len(signals),
            "graph_edges": len(_records(cell / "ledger" / "graph_edges.jsonl")),
            "reputation_events": len(_records(cell / "ledger" / "reputation" / "events.jsonl")),
            "regulator_proposals": len(_records(cell / "ledger" / "regulator_proposals.jsonl")),
            "evolution_proposals": len(_records(cell / "ledger" / "evolution" / "proposals.jsonl")),
            "open_proposals": len([p for p in proposals if p.get("status") not in {"accepted", "rejected"}]),
            "hygiene_warnings": hygiene_warnings,
            "grid_artifacts": len([p for p in grid_files if p.is_file()]),
        },
        "grid_status": "present" if any(p.is_file() for p in grid_files) else "empty",
        "diagnostics": diagnostics,
    }


def spark_review_queue(cell_path: PathLike, *, status: Optional[str] = None, kind: Optional[str] = None, tag: Optional[str] = None) -> Dict[str, Any]:
    cell = Path(cell_path)
    sparks = _records(cell / "ledger" / "fragments.jsonl") + _records(cell / "ledger" / "sparks.jsonl")
    latest = _latest_by(_records(cell / "ledger" / "reviews.jsonl"), "fragment_id")
    rows: List[Dict[str, Any]] = []
    for spark in sparks:
        spark_id = str(spark.get("fragment_id") or spark.get("spark_id") or "")
        review = latest.get(spark_id, {})
        effective = review.get("review_status") or spark.get("review_status") or "pending"
        row = dict(spark)
        row["effective_review_status"] = effective
        row["latest_review"] = review or None
        rows.append(row)
    if status:
        rows = [row for row in rows if row.get("effective_review_status") == status]
    if kind:
        rows = [row for row in rows if row.get("kind") == kind]
    if tag:
        rows = [row for row in rows if tag in row.get("tags", [])]
    return {"status": "ok", "sparks": rows, "total": len(rows)}


def memory_explorer(cell_path: PathLike, *, query: str = "", kind: str = "", status: str = "", tag: str = "") -> Dict[str, Any]:
    cell = Path(cell_path)
    charges = _records(cell / "traces" / "approved.jsonl") + _records(cell / "charges" / "approved.jsonl")
    states = {k: v.to_dict() for k, v in get_effective_charge_states(cell).items()}
    outcomes = _records(cell / "ledger" / "outcomes.jsonl") + _records(cell / "ledger" / "signals.jsonl")
    confidence = _records(cell / "ledger" / "confidence_events.jsonl")
    rows: List[Dict[str, Any]] = []
    q = query.lower().strip()
    for charge in charges:
        memory_id = str(charge.get("memory_id") or charge.get("trace_id") or charge.get("charge_id") or "")
        statement = str(charge.get("statement") or charge.get("text") or "")
        row = with_canonical_memory_id(charge)
        row["effective_state"] = states.get(memory_id, {"lifecycle_status": charge.get("status", "active")})
        row["feedback_history"] = [o for o in outcomes if memory_id in (o.get("useful_memory_ids", []) + o.get("harmful_memory_ids", []) + o.get("applied_memory_ids", []) + o.get("useful_trace_ids", []) + o.get("harmful_trace_ids", []) + o.get("applied_trace_ids", []))]
        row["confidence_events"] = [e for e in confidence if e.get("memory_id") == memory_id or e.get("charge_id") == memory_id or e.get("trace_id") == memory_id]
        if q and q not in statement.lower() and q not in str(row.get("rationale", "")).lower():
            continue
        if kind and row.get("kind") != kind:
            continue
        if status and row.get("effective_state", {}).get("lifecycle_status") != status and row.get("status") != status:
            continue
        if tag and tag not in row.get("tags", []):
            continue
        rows.append(row)
    return {"status": "ok", "memories": rows, "total": len(rows)}


def proposal_inbox(cell_path: PathLike) -> Dict[str, Any]:
    cell = Path(cell_path)
    proposals = _records(cell / "reports" / "runtime_proposals.jsonl")
    proposals.extend(_records(cell / "reports" / "sweep_proposals.jsonl"))
    proposals.extend(_records(cell / "ledger" / "evolution" / "proposals.jsonl"))
    decisions = _latest_by(_records(cell / "ledger" / "proposal_decisions.jsonl"), "proposal_id")
    decisions.update(_latest_by(_records(cell / "ledger" / "evolution" / "reviews.jsonl"), "proposal_id"))
    rows: List[Dict[str, Any]] = []
    status_map = {"accept": "accepted", "reject": "rejected", "defer": "deferred"}
    for proposal in proposals:
        row = dict(proposal)
        proposal_id = str(row.get("proposal_id") or row.get("id") or "")
        decision = decisions.get(proposal_id)
        if decision:
            row["latest_decision"] = decision
            row["status"] = status_map.get(str(decision.get("decision")), str(decision.get("decision")))
        rows.append(row)
    return {"status": "ok", "proposals": rows, "total": len(rows)}


def frontier_review_surfaces(cell_path: PathLike) -> Dict[str, Any]:
    """Return read-only frontier surface projections for the console."""
    from .graph import list_graph_edges
    from .reputation import reputation_summary
    from .regulator_proposals import generate_regulator_proposals
    from .evalgen import generate_eval_tasks
    from .retrieval_modes import RETRIEVAL_MODES
    from .evolution import read_evolution_proposals, scan_cell

    cell = Path(cell_path)
    return {
        "status": "ok",
        "review_gated": True,
        "auto_apply": False,
        "retrieval_modes": sorted(RETRIEVAL_MODES),
        "graph_edges": list_graph_edges(cell),
        "reputation": reputation_summary(cell),
        "regulator_proposals": _records(cell / "ledger" / "regulator_proposals.jsonl") or generate_regulator_proposals(cell),
        "evolution": {
            "proposals": read_evolution_proposals(cell),
            "dry_run_scan": scan_cell(cell, write_proposals=False),
            "simulation_required_for_retrieval_changes": True,
        },
        "eval_tasks": generate_eval_tasks(cell),
    }

def pilot_metrics(cell_path: PathLike) -> Dict[str, Any]:
    """Compute controlled-pilot usefulness and operator-burden metrics."""

    from .metrics import metrics_summary

    cell = Path(cell_path)
    retrieval_logs = _records(cell / "ledger" / "retrieval_logs.jsonl")
    diagnostics = _records(cell / "ledger" / "diagnostic_logs.jsonl")
    outcomes = _records(cell / "ledger" / "outcomes.jsonl") + _records(cell / "ledger" / "signals.jsonl")
    reviews = _records(cell / "ledger" / "reviews.jsonl")
    proposals = proposal_inbox(cell)["proposals"]
    sparks = spark_review_queue(cell)["sparks"]

    total_selected = sum(len(r.get("selected_ids", []) or r.get("trace_ids", []) or r.get("selected_charge_ids", []) or []) for r in retrieval_logs)
    if not total_selected:
        total_selected = sum(len(d.get("selected_charge_ids", [])) for d in diagnostics if d.get("operation") in {"pack", "provider_pack"})

    applied = sum(len(o.get("applied_trace_ids", []) or o.get("applied_charge_ids", []) or []) for o in outcomes)
    useful = sum(len(o.get("useful_trace_ids", []) or o.get("useful_charge_ids", []) or []) for o in outcomes)
    harmful = sum(len(o.get("harmful_trace_ids", []) or o.get("harmful_charge_ids", []) or []) for o in outcomes)
    ignored = sum(len(o.get("ignored_trace_ids", []) or o.get("ignored_charge_ids", []) or []) for o in outcomes)
    missing = sum(len(o.get("missing_memory", []) or o.get("missing_memory_notes", []) or []) for o in outcomes)
    accepted_reviews = [r for r in reviews if r.get("review_status") in {"approved", "accepted"}]
    pending_sparks = [s for s in sparks if s.get("effective_review_status") == "pending"]
    pending_proposals = [p for p in proposals if p.get("status") not in {"accepted", "rejected"}]
    rejected_reviews = [r for r in reviews if r.get("review_status") == "rejected"]
    review_pressure = min(100, len(pending_sparks) * 8 + len(pending_proposals) * 10 + len(rejected_reviews) * 2)

    def rate(n: int, d: int) -> float:
        return round(n / d, 4) if d else 0.0

    phase10 = metrics_summary(cell)
    metrics = {
        "pack_count": len(retrieval_logs) or len([d for d in diagnostics if d.get("operation") in {"pack", "provider_pack"}]),
        "feedback_count": len(outcomes),
        "pack_application_rate": rate(applied, total_selected),
        "useful_memory_rate": phase10["retrieval_quality"]["precision_proxy"],
        "harmful_memory_rate": rate(harmful, total_selected),
        "ignored_memory_rate": rate(ignored, total_selected),
        "over_retrieval_rate": rate(max(total_selected - applied - ignored, 0), total_selected),
        "missing_memory_rate": rate(missing, max(len(outcomes), 1)),
        "review_approval_rate": rate(len(accepted_reviews), len(reviews)),
        "proposal_acceptance_rate": rate(len([p for p in proposals if p.get("status") == "accepted"]), len(proposals)),
        "time_saved_per_task_minutes": 0.0,
        "task_failure_reduction_rate": 0.0,
        "pending_sparks": len(pending_sparks),
        "pending_proposals": len(pending_proposals),
        "average_review_time_minutes": 0.0,
        "stale_review_items": len(pending_sparks),
        "rejected_item_ratio": rate(len(rejected_reviews), len(reviews)),
        "review_pressure_score": review_pressure,
    }
    return {
        "status": "ok",
        "metrics": metrics,
        "phase10_metrics": phase10,
        "can_answer_improvement": bool(outcomes and total_selected),
    }


def pilot_metrics_csv(cell_path: PathLike) -> str:
    payload = pilot_metrics(cell_path)["metrics"]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["metric", "value"])
    for key in sorted(payload):
        writer.writerow([key, payload[key]])
    return out.getvalue()


def policy_tuning_report(cell_path: PathLike) -> Dict[str, Any]:
    cell = Path(cell_path)
    diagnostics = _records(cell / "ledger" / "diagnostic_logs.jsonl")
    rejected = []
    approvals = []
    operational = []
    for row in diagnostics:
        decisions = row.get("regulator_decisions", []) or []
        for decision in decisions:
            if decision.get("status") == "rejected":
                rejected.append(decision)
            if decision.get("status") == "approved":
                approvals.append(decision)
            text = json.dumps(decision, sort_keys=True).lower()
            if any(term in text for term in ("queue", "pid", "session", "token", "secret", "password")):
                operational.append(decision)
    return {
        "status": "ok",
        "false_rejection_candidates": rejected[:25],
        "false_approval_candidates": approvals[:25],
        "operational_state_decisions": operational[:25],
        "recommended_fixture_count": len(rejected) + len(operational),
    }


# ---------------------------------------------------------------------------
# Phase 6 multi-cell console projections
# ---------------------------------------------------------------------------

def registered_cells(registry_path: PathLike, *, cell_type: Optional[str] = None, tag: Optional[str] = None) -> Dict[str, Any]:
    from .registry import list_cells
    tags = [tag] if tag else None
    cells = [entry.to_dict() for entry in list_cells(registry_path, cell_type=cell_type, tags=tags)]
    return {"status": "ok", "cells": cells, "total": len(cells), "metadata_only": True}


def cell_detail(registry_path: PathLike, cell_id: str) -> Dict[str, Any]:
    from .registry import get_cell
    entry = get_cell(registry_path, cell_id)
    return {"status": "ok", "cell": entry.to_dict(), "metadata_only": True}


def resonance_results(registry_path: PathLike, cell_ids: List[str], *, threshold: float = 0.25) -> Dict[str, Any]:
    from .resonance import scan_registry_resonance
    results = scan_registry_resonance(registry_path, cell_ids, threshold=threshold)
    return {"status": "ok", "explicit_cross_cell_scope": True, "trust_label": "local", "results": results, "total": len(results)}


def rule_review_queue(cell_path: PathLike, *, status: Optional[str] = None) -> Dict[str, Any]:
    from .distill.rules import list_rule_proposals
    rules = list_rule_proposals(cell_path, status=status)
    return {"status": "ok", "rules": rules, "total": len(rules), "requires_operator_decision": True}


def import_review_queue(cell_path: PathLike, *, status: Optional[str] = "pending") -> Dict[str, Any]:
    from .federation import list_imports
    imports = list_imports(cell_path, status=status)
    return {"status": "ok", "imports": imports, "total": len(imports), "trust_labels": ["local", "imported", "federated", "verified"]}


# Compatibility alias for older server imports.
charge_explorer = memory_explorer
