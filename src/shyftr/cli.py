"""ShyftR CLI — Attachable recursive memory cells for AI agents.

Usage:
    shyftr init <cell_path> [--cell-id ID] [--cell-type TYPE]
    shyftr ingest <cell_path> <evidence_file> --kind KIND
    shyftr candidate <cell_path> <evidence_id>
    shyftr review approve <cell_path> <candidate_id> --reviewer NAME --rationale TEXT
    shyftr review reject <cell_path> <candidate_id> --reviewer NAME --rationale TEXT
    shyftr memory <cell_path> <candidate_id> --promoter NAME
    shyftr search <cell_path> <query>
    shyftr retrieve <cell_path> <query>
    shyftr pack <cell_path> <query> --task-id ID [options]
    shyftr feedback <cell_path> <pack_id> <result> [options]
    shyftr hygiene <cell_path>
    shyftr counters <cell_path>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _cell_path(value: str) -> Path:
    p = Path(value)
    if not p.is_dir():
        raise argparse.ArgumentTypeError(f"not a directory: {value}")
    if not (p / "config" / "cell_manifest.json").exists():
        raise argparse.ArgumentTypeError(f"no cell_manifest.json in {value}")
    return p


# ---------------------------------------------------------------------------
# Subcommand: init
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> None:
    from shyftr.layout import init_cell

    target = Path(args.path)
    parent = target.parent
    cell_id = args.cell_id or target.name
    cell_path = init_cell(
        root=parent,
        cell_id=cell_id,
        cell_type=args.cell_type,
    )
    _print_json({"status": "ok", "cell_path": str(cell_path), "cell_id": cell_id})


def _add_init(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("path", type=str, help="directory where the Cell will be created")
    sub.add_argument("--cell-id", type=str, default=None, help="Cell identifier (default: directory basename)")
    sub.add_argument("--cell-type", type=str, default="domain", help="Cell type (default: domain)")


# ---------------------------------------------------------------------------
# Subcommand: ingest
# ---------------------------------------------------------------------------


def cmd_ingest(args: argparse.Namespace) -> None:
    from shyftr.ingest import ingest_source

    source = ingest_source(
        cell_path=args.cell_path,
        source_path=args.evidence_file,
        kind=args.kind,
        metadata=json.loads(args.metadata) if args.metadata else None,
    )
    _print_json(_canonicalize_record(source.to_dict()))


def _add_ingest(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("evidence_file", type=str, help="path to the evidence file to ingest")
    sub.add_argument("--kind", type=str, required=True, help="kind label for the evidence")
    sub.add_argument("--metadata", type=str, default=None, help="JSON metadata dict")


# ---------------------------------------------------------------------------
# Subcommand: fragment
# ---------------------------------------------------------------------------


def cmd_candidate(args: argparse.Namespace) -> None:
    from shyftr.extract import extract_fragments
    from shyftr.ledger import read_jsonl
    from shyftr.models import Source

    # Find the source record by source_id
    cell = Path(args.cell_path)
    sources_ledger = cell / "ledger" / "sources.jsonl"
    source: Optional[Source] = None
    for _, record in read_jsonl(sources_ledger):
        if record.get("source_id") == args.evidence_id:
            source = Source.from_dict(record)
            break

    if source is None:
        _fail(f"Evidence not found: {args.evidence_id}")

    fragments = extract_fragments(cell_path=args.cell_path, source=source)
    _print_json([_canonicalize_record(f.to_dict()) for f in fragments])


def _add_candidate(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("evidence_id", type=str, help="evidence_id from ingest")


# ---------------------------------------------------------------------------
# Subcommand: review
# ---------------------------------------------------------------------------


def cmd_review_approve(args: argparse.Namespace) -> None:
    from shyftr.review import approve_fragment

    event = approve_fragment(
        cell_path=args.cell_path,
        fragment_id=args.fragment_id,
        reviewer=args.reviewer,
        rationale=args.rationale,
        metadata=json.loads(args.metadata) if args.metadata else None,
    )
    _print_json(event)


def cmd_review_reject(args: argparse.Namespace) -> None:
    from shyftr.review import reject_fragment

    event = reject_fragment(
        cell_path=args.cell_path,
        fragment_id=args.fragment_id,
        reviewer=args.reviewer,
        rationale=args.rationale,
        metadata=json.loads(args.metadata) if args.metadata else None,
    )
    _print_json(event)


def _add_review_action(
    parser: argparse.ArgumentParser,
    *,
    required_action: Optional[str] = None,
) -> None:
    parser.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    parser.add_argument("fragment_id", type=str, help="candidate_id to review")
    parser.add_argument("--reviewer", type=str, required=True, help="reviewer identifier")
    parser.add_argument("--rationale", type=str, required=True, help="review rationale")
    parser.add_argument("--metadata", type=str, default=None, help="optional JSON metadata")
    if required_action is not None:
        parser.set_defaults(review_action=required_action)


def _add_review(sub: argparse.ArgumentParser) -> None:
    review_sub = sub.add_subparsers(dest="review_action", required=True)
    _add_review_action(review_sub.add_parser("approve", help="Approve a fragment"))
    _add_review_action(review_sub.add_parser("reject", help="Reject a fragment"))


# ---------------------------------------------------------------------------
# Subcommand: promote
# ---------------------------------------------------------------------------


def cmd_memory(args: argparse.Namespace) -> None:
    from shyftr.promote import promote_fragment

    trace = promote_fragment(
        cell_path=args.cell_path,
        fragment_id=args.fragment_id,
        promoter=args.promoter,
        statement=args.statement,
        rationale=args.rationale,
    )
    _print_json(_canonicalize_record(trace.to_dict()))


def _add_memory(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("fragment_id", type=str, help="candidate_id to promote")
    sub.add_argument("--promoter", type=str, required=True, help="promoter identifier")
    sub.add_argument("--statement", type=str, default=None, help="optional trace statement override")
    sub.add_argument("--rationale", type=str, default=None, help="optional trace rationale override")


# ---------------------------------------------------------------------------
# Subcommand: search / retrieve
# ---------------------------------------------------------------------------


def _do_search(args: argparse.Namespace) -> None:
    from shyftr.ledger import read_jsonl
    from shyftr.retrieval.sparse import open_sparse_index, query_sparse, rebuild_sparse_index

    cell = Path(args.cell_path)
    cell_id = _read_cell_id(cell)
    db_path = cell / "indexes" / "sparse.db"

    conn = open_sparse_index(db_path)

    # Check if index needs rebuilding
    count = conn.execute("SELECT COUNT(*) FROM traces_fts").fetchone()[0]
    if count == 0:
        indexed = rebuild_sparse_index(conn, cell)
    else:
        indexed = count

    results = query_sparse(
        conn,
        query=args.query,
        cell_id=cell_id,
        limit=args.limit,
    )

    output = []
    for r in results:
        output.append({
            "trace_id": r.trace_id,
            "cell_id": r.cell_id,
            "statement": r.statement,
            "rationale": r.rationale,
            "tags": r.tags,
            "kind": r.kind,
            "status": r.status,
            "confidence": r.confidence,
            "bm25_score": round(r.bm25_score, 4),
        })

    _print_json({"query": args.query, "results": output, "index_size": indexed})


def _read_cell_id(cell: Path) -> str:
    import json as _json
    manifest_path = cell / "config" / "cell_manifest.json"
    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    return str(manifest.get("cell_id", ""))


def _add_search(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("query", type=str, help="search query text")
    sub.add_argument("--limit", type=int, default=10, help="max results (default: 10)")


# ---------------------------------------------------------------------------
# Subcommand: profile
# ---------------------------------------------------------------------------


def cmd_profile(args: argparse.Namespace) -> None:
    from shyftr.profile import write_profile_projections

    paths = write_profile_projections(args.cell_path, max_tokens=args.max_tokens)
    profile_payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    _print_json({
        "status": "ok",
        "cell_id": profile_payload["cell_id"],
        "projection_id": profile_payload["projection_id"],
        "source_charge_ids": profile_payload["source_charge_ids"],
        "paths": {name: str(path) for name, path in paths.items()},
    })


def _add_profile(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--max-tokens", type=int, default=2000, help="compact profile token budget (default: 2000)")


# ---------------------------------------------------------------------------
# Subcommand: loadout
# ---------------------------------------------------------------------------


def cmd_pack(args: argparse.Namespace) -> None:
    from shyftr.loadout import LoadoutTaskInput, assemble_loadout

    if args.request_json:
        import json as _json
        raw = _json.loads(Path(args.request_json).read_text(encoding="utf-8"))
        from shyftr.integrations.loadout_api import (
            RuntimeLoadoutRequest,
            process_runtime_loadout_request,
        )
        request = RuntimeLoadoutRequest.from_dict(raw)
        response = process_runtime_loadout_request(request)
        _print_json(response.to_dict())
        return

    task = LoadoutTaskInput(
        cell_path=str(args.cell_path),
        query=args.query,
        task_id=args.task_id,
        max_items=args.max_items,
        max_tokens=args.max_tokens,
        include_fragments=args.include_fragments,
        query_kind=args.query_kind,
        query_tags=args.query_tags.split(",") if args.query_tags else None,
        runtime_id=args.runtime_id,
        user_id=args.user_id,
        project_id=args.project_id,
        allowed_sensitivity=args.allowed_sensitivity.split(",") if args.allowed_sensitivity else None,
        retrieval_mode=args.retrieval_mode,
    )

    assembled = assemble_loadout(task)
    _print_json(_canonicalize_record(assembled.to_dict()))


def _add_pack(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, nargs="?", help="path to the Cell directory (optional with --request-json)")
    sub.add_argument("query", type=str, nargs="?", help="search query for memory assembly (optional with --request-json)")
    sub.add_argument("--request-json", type=str, default=None, help="path to a RuntimeLoadoutRequest JSON file")
    sub.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")
    sub.add_argument("--task-id", type=str, default=None, help="task identifier (required for positional mode)")
    sub.add_argument("--max-items", type=int, default=20, help="max items (default: 20)")
    sub.add_argument("--max-tokens", type=int, default=4000, help="max tokens (default: 4000)")
    sub.add_argument("--include-candidates", "--include-fragments", dest="include_fragments", action="store_true", default=False, help="include candidate-tier items")
    sub.add_argument("--query-kind", type=str, default=None, help="expected kind for kind-match scoring")
    sub.add_argument("--query-tags", type=str, default=None, help="comma-separated expected tags for tag-match")
    sub.add_argument("--runtime-id", type=str, default="default", help="runtime identity for sensitivity policy checks")
    sub.add_argument("--user-id", type=str, default=None, help="user identity for sensitivity policy checks")
    sub.add_argument("--project-id", type=str, default=None, help="project identity for sensitivity policy checks")
    sub.add_argument("--allowed-sensitivity", type=str, default=None, help="comma-separated sensitivity levels explicitly allowed for export")
    sub.add_argument("--retrieval-mode", type=str, default="balanced", choices=("balanced", "conservative", "exploratory", "risk_averse", "audit", "rule_only", "low_latency"), help="explicit retrieval mode (default: balanced)")


# ---------------------------------------------------------------------------
# Subcommand: outcome
# ---------------------------------------------------------------------------


def cmd_feedback(args: argparse.Namespace) -> None:
    if args.report_json:
        from shyftr.integrations.outcome_api import (
            RuntimeOutcomeReport,
            process_runtime_outcome_report,
        )

        payload = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
        report = RuntimeOutcomeReport.from_dict(payload)
        response = process_runtime_outcome_report(report)
        _print_json(response.to_dict())
        return

    if args.cell_path is None or args.loadout_id is None or args.result is None:
        raise ValueError("outcome requires cell_path, loadout_id, and result unless --report-json is provided")

    from shyftr.outcomes import record_outcome

    outcome = record_outcome(
        cell_path=args.cell_path,
        loadout_id=args.loadout_id,
        result=args.result,
        applied_trace_ids=args.applied.split(",") if args.applied else [],
        useful_trace_ids=args.useful.split(",") if args.useful else [],
        harmful_trace_ids=args.harmful.split(",") if args.harmful else [],
        missing_memory=args.missing.split(",") if args.missing else [],
        verification_evidence=json.loads(args.verification) if args.verification else None,
    )
    _print_json(_canonicalize_record(outcome.to_dict()))


def _add_feedback(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, nargs="?", help="path to the Cell directory (optional with --report-json)")
    sub.add_argument("loadout_id", type=str, nargs="?", help="loadout identifier (optional with --report-json)")
    sub.add_argument("result", type=str, nargs="?", help='verdict string (e.g. "success", "failure"; optional with --report-json)')
    sub.add_argument("--report-json", type=str, default=None, help="path to a RuntimeOutcomeReport JSON file")
    sub.add_argument("--applied", type=str, default="", help="comma-separated applied trace ids")
    sub.add_argument("--useful", type=str, default="", help="comma-separated useful trace ids")
    sub.add_argument("--harmful", type=str, default="", help="comma-separated harmful trace ids")
    sub.add_argument("--missing", type=str, default="", help="comma-separated missing memory items")
    sub.add_argument("--verification", type=str, default=None, help="optional JSON verification evidence")


# ---------------------------------------------------------------------------
# Subcommand: sweep
# ---------------------------------------------------------------------------


def cmd_sweep(args: argparse.Namespace) -> None:
    from shyftr.sweep import run_sweep

    cell_path = args.cell if args.cell is not None else args.cell_path
    if cell_path is None:
        raise SystemExit("sweep requires cell_path or --cell")
    dry_run = bool(args.dry_run or not args.propose)
    report = run_sweep(
        cell_path=cell_path,
        dry_run=dry_run,
        output_path=args.output,
        propose=args.propose,
        apply_low_risk=args.apply_low_risk,
    )
    _print_json(report.to_dict())


def cmd_challenge(args: argparse.Namespace) -> None:
    from shyftr.audit.challenger import run_challenge

    cell_path = args.cell if args.cell is not None else args.cell_path
    if cell_path is None:
        raise SystemExit("challenge requires cell_path or --cell")
    dry_run = bool(args.dry_run or not args.propose)
    report = run_challenge(
        cell_path=cell_path,
        dry_run=dry_run,
        propose=args.propose,
        top_n=args.top_impact,
        min_rank_score=args.min_rank_score,
        charge_id=args.charge_id,
        output_path=args.output,
    )
    _print_json(report.to_dict())


def _add_sweep(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", nargs="?", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--cell", type=_cell_path, default=None, help="path to the Cell directory")
    sub.add_argument("--dry-run", action="store_true", default=False, help="force read-only dry-run mode")
    sub.add_argument("--output", type=str, default=None, help="optional output path for the report JSON")
    sub.add_argument("--propose", action="store_true", default=False, help="append deterministic proposal events to active-learning ledgers")
    sub.add_argument("--apply-low-risk", action="store_true", default=False, help="mark low-risk retrieval-affinity decrease events as applied append-only proposals")


# ---------------------------------------------------------------------------
# Subcommand: challenge
# ---------------------------------------------------------------------------


def _add_challenge(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", nargs="?", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--cell", type=_cell_path, default=None, help="path to the Cell directory")
    sub.add_argument("--dry-run", action="store_true", default=False, help="force read-only dry-run mode")
    sub.add_argument("--output", type=str, default=None, help="optional output path for the report JSON")
    sub.add_argument("--propose", action="store_true", default=False, help="append audit sparks to ledger/audit_sparks.jsonl")
    sub.add_argument("--charge-id", type=str, default=None, help="challenge only this specific charge/trace")
    sub.add_argument("--top-impact", type=int, default=None, help="only challenge the top N highest-impact targets")
    sub.add_argument("--min-rank-score", type=float, default=0.0, help="minimum rank score threshold")


# ---------------------------------------------------------------------------
# Subcommand: proposals
# ---------------------------------------------------------------------------


def cmd_proposals_export(args: argparse.Namespace) -> None:
    from shyftr.integrations.proposals import export_runtime_proposals

    payload = export_runtime_proposals(
        args.cell,
        external_system=args.external_system,
        output_path=args.output,
        include_accepted=args.include_accepted,
    )
    _print_json(payload)


def _add_proposals(sub: argparse.ArgumentParser) -> None:
    proposals_sub = sub.add_subparsers(dest="proposals_action", required=True)
    export = proposals_sub.add_parser("export", help="Export advisory runtime proposals as JSON")
    export.add_argument("--cell", type=_cell_path, required=True, help="path to the Cell directory")
    export.add_argument("--external-system", required=True, help="target external runtime identifier")
    export.add_argument("--output", default=None, help="optional output path; relative paths are written under the Cell")
    export.add_argument("--include-accepted", action="store_true", default=False, help="also export accepted proposals")
    export.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")



# ---------------------------------------------------------------------------
# Subcommand: cell / resonance / rule / import (Phase 6)
# ---------------------------------------------------------------------------


def cmd_cell_register(args: argparse.Namespace) -> None:
    from shyftr.registry import CellRegistryEntry, register_cell
    entry = CellRegistryEntry(
        cell_id=args.cell_id,
        cell_type=args.cell_type,
        path=str(Path(args.path).expanduser().resolve()),
        owner=args.owner,
        tags=[tag for tag in (args.tags or "").split(",") if tag],
        domain=args.domain,
        trust_boundary=args.trust_boundary,
        registered_at=args.registered_at or __import__("datetime").datetime.datetime.now(__import__("datetime").timezone.utc).isoformat(),
        metadata=json.loads(args.metadata) if args.metadata else {},
    )
    _print_json(register_cell(args.registry, entry).to_dict())


def cmd_cell_list(args: argparse.Namespace) -> None:
    from shyftr.registry import list_cells
    tags = [tag for tag in (args.tags or "").split(",") if tag] or None
    _print_json({"status": "ok", "cells": [entry.to_dict() for entry in list_cells(args.registry, cell_type=args.cell_type, tags=tags)]})


def cmd_cell_info(args: argparse.Namespace) -> None:
    from shyftr.registry import get_cell
    _print_json(get_cell(args.registry, args.cell_id).to_dict())


def cmd_cell_unregister(args: argparse.Namespace) -> None:
    from shyftr.registry import unregister_cell
    _print_json(unregister_cell(args.registry, args.cell_id, args.reason))


def cmd_cell_export(args: argparse.Namespace) -> None:
    from shyftr.federation import export_cell
    _print_json(export_cell(args.cell_path, args.output))


def cmd_cell_import(args: argparse.Namespace) -> None:
    from shyftr.federation import import_package
    _print_json(import_package(args.cell_path, args.package))


def cmd_resonance_scan(args: argparse.Namespace) -> None:
    from shyftr.resonance import scan_registry_resonance
    if not args.cell or len(args.cell) < 2:
        raise ValueError("resonance scan requires at least two explicit --cell values")
    _print_json({"status": "ok", "dry_run": True, "results": scan_registry_resonance(args.registry, args.cell, threshold=args.threshold)})


def cmd_rule_propose_from_resonance(args: argparse.Namespace) -> None:
    from shyftr.distill.rules import propose_rule_from_resonance
    payload = json.loads(Path(args.resonance_json).read_text(encoding="utf-8"))
    results = payload.get("results", payload if isinstance(payload, list) else [])
    _print_json(propose_rule_from_resonance(args.cell_path, results, scope=args.scope, statement=args.statement))


def cmd_rule_list(args: argparse.Namespace) -> None:
    from shyftr.distill.rules import list_rule_proposals
    _print_json({"status": "ok", "rules": list_rule_proposals(args.cell_path, status=args.status)})


def cmd_rule_approve(args: argparse.Namespace) -> None:
    from shyftr.distill.rules import approve_rule_proposal
    _print_json(approve_rule_proposal(args.cell_path, args.rule_id, reviewer_id=args.reviewer, rationale=args.rationale))


def cmd_rule_reject(args: argparse.Namespace) -> None:
    from shyftr.distill.rules import reject_rule_proposal
    _print_json(reject_rule_proposal(args.cell_path, args.rule_id, reviewer_id=args.reviewer, rationale=args.rationale))


def cmd_import_list(args: argparse.Namespace) -> None:
    from shyftr.federation import list_imports
    _print_json({"status": "ok", "imports": list_imports(args.cell_path, status=args.status)})


def cmd_import_approve(args: argparse.Namespace) -> None:
    from shyftr.federation import approve_import
    _print_json(approve_import(args.cell_path, args.import_id, reviewer=args.reviewer, rationale=args.rationale))


def cmd_import_reject(args: argparse.Namespace) -> None:
    from shyftr.federation import reject_import
    _print_json(reject_import(args.cell_path, args.import_id, reviewer=args.reviewer, rationale=args.rationale))


def _add_cell(sub: argparse.ArgumentParser) -> None:
    cell_sub = sub.add_subparsers(dest="cell_action", required=True)
    reg = cell_sub.add_parser("register", help="Register a Cell in an append-only registry")
    reg.add_argument("--registry", required=True)
    reg.add_argument("--cell-id", required=True)
    reg.add_argument("--cell-type", required=True)
    reg.add_argument("--path", required=True)
    reg.add_argument("--owner", required=True)
    reg.add_argument("--tags", default="")
    reg.add_argument("--domain", required=True)
    reg.add_argument("--trust-boundary", required=True)
    reg.add_argument("--registered-at", default=None)
    reg.add_argument("--metadata", default=None)
    ls = cell_sub.add_parser("list", help="List registered Cells")
    ls.add_argument("--registry", required=True)
    ls.add_argument("--cell-type", default=None)
    ls.add_argument("--tags", default=None)
    info = cell_sub.add_parser("info", help="Show registered Cell metadata")
    info.add_argument("--registry", required=True)
    info.add_argument("cell_id")
    unreg = cell_sub.add_parser("unregister", help="Append an unregister registry event")
    unreg.add_argument("--registry", required=True)
    unreg.add_argument("cell_id")
    unreg.add_argument("--reason", required=True)
    exp = cell_sub.add_parser("export", help="Export approved Cell records as a selective federation package")
    exp.add_argument("--cell-path", type=_cell_path, required=True)
    exp.add_argument("--output", required=True)
    imp = cell_sub.add_parser("import", help="Import a federation package into a review queue")
    imp.add_argument("--cell-path", type=_cell_path, required=True)
    imp.add_argument("--package", required=True)


def _add_resonance(sub: argparse.ArgumentParser) -> None:
    resonance_sub = sub.add_subparsers(dest="resonance_action", required=True)
    scan = resonance_sub.add_parser("scan", help="Dry-run registry-scoped cross-cell resonance")
    scan.add_argument("--registry", required=True)
    scan.add_argument("--cell", action="append", required=True)
    scan.add_argument("--threshold", type=float, default=0.25)
    scan.add_argument("--dry-run", action="store_true", default=True)


def _add_rule(sub: argparse.ArgumentParser) -> None:
    rule_sub = sub.add_subparsers(dest="rule_action", required=True)
    propose = rule_sub.add_parser("propose-from-resonance")
    propose.add_argument("cell_path", type=_cell_path)
    propose.add_argument("--resonance-json", required=True)
    propose.add_argument("--scope", required=True)
    propose.add_argument("--statement", default=None)
    ls = rule_sub.add_parser("list")
    ls.add_argument("cell_path", type=_cell_path)
    ls.add_argument("--status", default=None)
    for name in ("approve", "reject"):
        parser = rule_sub.add_parser(name)
        parser.add_argument("cell_path", type=_cell_path)
        parser.add_argument("rule_id")
        parser.add_argument("--reviewer", default="operator")
        parser.add_argument("--rationale", required=True)


def _add_import(sub: argparse.ArgumentParser) -> None:
    import_sub = sub.add_subparsers(dest="import_action", required=True)
    ls = import_sub.add_parser("list")
    ls.add_argument("cell_path", type=_cell_path)
    ls.add_argument("--status", default=None)
    for name in ("approve", "reject"):
        parser = import_sub.add_parser(name)
        parser.add_argument("cell_path", type=_cell_path)
        parser.add_argument("import_id")
        parser.add_argument("--reviewer", default="operator")
        parser.add_argument("--rationale", required=True)

# ---------------------------------------------------------------------------
# Subcommand: hygiene
# ---------------------------------------------------------------------------


def cmd_hygiene(args: argparse.Namespace) -> None:
    from shyftr.reports.hygiene import hygiene_report

    report = hygiene_report(args.cell_path)
    _print_json(report)


def _add_hygiene(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")


# ---------------------------------------------------------------------------
# Subcommand: counters
# ---------------------------------------------------------------------------


def cmd_counters(args: argparse.Namespace) -> None:
    from shyftr.outcomes import get_trace_counters_as_dicts

    counters = get_trace_counters_as_dicts(args.cell_path)
    _print_json(counters)


def _add_counters(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")


# ---------------------------------------------------------------------------
# Subcommand: metrics
# ---------------------------------------------------------------------------


def cmd_metrics(args: argparse.Namespace) -> None:
    from shyftr.metrics import metrics_summary

    _print_json(metrics_summary(args.cell_path))


def _add_metrics(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")


# ---------------------------------------------------------------------------
# Subcommand: decay
# ---------------------------------------------------------------------------


def cmd_decay(args: argparse.Namespace) -> None:
    from shyftr.decay import cell_decay_report, decay_summary

    _print_json(
        {
            "proposal_summary": decay_summary(args.cell_path),
            "scoring_summary": cell_decay_report(args.cell_path),
        }
    )


def _add_decay(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")


# ---------------------------------------------------------------------------
# Subcommand: adapter
# ---------------------------------------------------------------------------


def _config_to_dict(config: Any) -> Dict[str, Any]:
    return {
        "adapter_id": config.adapter_id,
        "cell_id": config.cell_id,
        "external_system": config.external_system,
        "external_scope": config.external_scope,
        "source_root": config.source_root,
        "inputs": [
            {
                "kind": inp.kind,
                "path": inp.path,
                "source_kind": inp.source_kind,
                "identity_mapping": dict(inp.identity_mapping),
            }
            for inp in config.inputs
        ],
        "identity_mapping": dict(config.identity_mapping),
        "ingest_options": dict(config.ingest_options),
    }


def _discovery_summary_to_dict(summary: Any) -> Dict[str, Any]:
    return {
        "adapter_id": summary.adapter_id,
        "total_sources": summary.total_sources,
        "by_kind": dict(summary.by_kind),
        "by_input_kind": dict(summary.by_input_kind),
        "inputs_processed": summary.inputs_processed,
        "errors": list(summary.errors),
    }


def _resolve_adapter_cell_path(config_path: str, config: Any, explicit_cell_path: Optional[str]) -> Path:
    if explicit_cell_path:
        return _cell_path(explicit_cell_path)
    inferred = Path(config_path).resolve().parent / config.cell_id
    if inferred.is_dir() and (inferred / "config" / "cell_manifest.json").exists():
        return inferred
    raise ValueError(
        "adapter ingest requires --cell-path unless a Cell directory named "
        f"'{config.cell_id}' exists beside the adapter config"
    )


def cmd_adapter_validate(args: argparse.Namespace) -> None:
    from shyftr.integrations.config import load_config, validate_config

    config = load_config(args.config)
    validate_config(config)
    _print_json({"status": "ok", "config": _config_to_dict(config)})


def cmd_adapter_discover(args: argparse.Namespace) -> None:
    from shyftr.integrations.config import load_config
    from shyftr.integrations.file_adapter import FileSourceAdapter

    if not args.dry_run:
        raise ValueError("adapter discover currently requires --dry-run")
    config = load_config(args.config)
    summary = FileSourceAdapter(config).dry_run_discovery()
    _print_json({"status": "ok", "dry_run": True, "discovery_summary": _discovery_summary_to_dict(summary)})


def cmd_adapter_ingest(args: argparse.Namespace) -> None:
    from shyftr.ingest import ingest_from_adapter
    from shyftr.integrations.config import load_config

    config = load_config(args.config)
    cell_path = _resolve_adapter_cell_path(args.config, config, args.cell_path)
    result = ingest_from_adapter(cell_path, config, dry_run=False)
    _print_json({"status": "ok", "cell_path": str(cell_path), **result})


def cmd_adapter_backfill(args: argparse.Namespace) -> None:
    from shyftr.ingest import ingest_from_adapter
    from shyftr.integrations.config import load_config

    if not args.dry_run:
        raise ValueError("adapter backfill requires --dry-run until sync state lands")
    config = load_config(args.config)
    cell_path = _resolve_adapter_cell_path(args.config, config, args.cell_path)
    result = ingest_from_adapter(cell_path, config, dry_run=True)
    _print_json({"status": "ok", "dry_run": True, "cell_path": str(cell_path), **result})


def cmd_adapter_sync(args: argparse.Namespace) -> None:
    from shyftr.ingest import sync_from_adapter
    from shyftr.integrations.config import load_config

    config = load_config(args.config)
    cell_path = _resolve_adapter_cell_path(args.config, config, args.cell_path)
    result = sync_from_adapter(cell_path, config, dry_run=False)
    _print_json({"status": "ok", "cell_path": str(cell_path), **result})


def cmd_adapter_sync_status(args: argparse.Namespace) -> None:
    from shyftr.integrations.config import load_config
    from shyftr.integrations.sync_state import SyncStateStore

    config = load_config(args.config)
    cell_path = _resolve_adapter_cell_path(args.config, config, args.cell_path)
    store = SyncStateStore.load(cell_path)
    entries = [entry.to_dict() for entry in store.list_entries() if entry.adapter_id == config.adapter_id]
    _print_json({
        "status": "ok",
        "cell_path": str(cell_path),
        "sync_state_path": str(cell_path / "indexes" / "adapter_sync_state.json"),
        "adapter_id": config.adapter_id,
        "entries": entries,
    })


def cmd_adapter_list(args: argparse.Namespace) -> None:
    from shyftr.integrations.plugins import adapter_plugins_payload

    _print_json(adapter_plugins_payload())


def _add_adapter(sub: argparse.ArgumentParser) -> None:
    adapter_sub = sub.add_subparsers(dest="adapter_action", required=True)

    validate = adapter_sub.add_parser("validate", help="Validate an adapter config")
    validate.add_argument("--config", required=True, help="runtime adapter config path")
    validate.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")

    discover = adapter_sub.add_parser("discover", help="Discover adapter sources")
    discover.add_argument("--config", required=True, help="runtime adapter config path")
    discover.add_argument("--dry-run", action="store_true", default=False, help="report discovered sources without ingesting")
    discover.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")

    ingest = adapter_sub.add_parser("ingest", help="Ingest adapter-discovered Sources append-only")
    ingest.add_argument("--config", required=True, help="runtime adapter config path")
    ingest.add_argument("--cell-path", default=None, help="target Cell path; defaults to config parent / cell_id")
    ingest.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")

    backfill = adapter_sub.add_parser("backfill", help="Preview adapter backfill")
    backfill.add_argument("--config", required=True, help="runtime adapter config path")
    backfill.add_argument("--cell-path", default=None, help="target Cell path; defaults to config parent / cell_id")
    backfill.add_argument("--dry-run", action="store_true", default=False, help="required: report backfill without writing Sources")
    backfill.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")

    sync = adapter_sub.add_parser("sync", help="Incrementally ingest append-only adapter sources")
    sync.add_argument("--config", required=True, help="runtime adapter config path")
    sync.add_argument("--cell-path", default=None, help="target Cell path; defaults to config parent / cell_id")
    sync.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")

    sync_status = adapter_sub.add_parser("sync-status", help="Show incremental adapter sync state")
    sync_status.add_argument("--config", required=True, help="runtime adapter config path")
    sync_status.add_argument("--cell-path", default=None, help="target Cell path; defaults to config parent / cell_id")
    sync_status.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")

    adapter_list = adapter_sub.add_parser("list", help="List built-in and optional adapter plugins")
    adapter_list.add_argument("--json", action="store_true", default=False, help="emit machine-readable JSON")


# ---------------------------------------------------------------------------
# Subcommand: audit
# ---------------------------------------------------------------------------


def cmd_audit_list(args: argparse.Namespace) -> None:
    """List audit findings (sparks and audit rows) for a Cell."""
    from shyftr.audit import read_audit_rows, read_audit_sparks

    cell_path = args.cell if args.cell is not None else args.cell_path
    if cell_path is None:
        raise SystemExit("audit list requires cell_path or --cell")

    sparks = read_audit_sparks(cell_path)
    rows = read_audit_rows(cell_path)
    output: Dict[str, Any] = {
        "cell_path": str(cell_path),
        "spark_count": len(sparks),
        "sparks": sparks,
        "audit_row_count": len(rows),
        "audit_rows": rows,
    }
    _print_json(output)


def cmd_audit_review(args: argparse.Namespace) -> None:
    """Record a review decision on an audit finding."""
    from shyftr.audit import append_audit_review

    cell_path = args.cell if args.cell is not None else args.cell_path
    if cell_path is None:
        raise SystemExit("audit review requires cell_path or --cell")

    # Parse --actions as comma-separated list
    actions = None
    if args.actions:
        actions = [a.strip() for a in args.actions.split(",") if a.strip()]

    review = append_audit_review(
        cell_path=cell_path,
        audit_id=args.audit_id,
        resolution=args.resolution,
        reviewer=args.reviewer,
        rationale=args.rationale,
        review_actions=actions,
    )
    _print_json(review)


def cmd_audit_resolve(args: argparse.Namespace) -> None:
    """Mark a resolution on existing audit reviews for a finding."""
    from shyftr.audit import append_audit_review

    cell_path = args.cell if args.cell is not None else args.cell_path
    if cell_path is None:
        raise SystemExit("audit resolve requires cell_path or --cell")

    review = append_audit_review(
        cell_path=cell_path,
        audit_id=args.audit_id,
        resolution="accept",
        reviewer=args.reviewer or "system",
        rationale=args.rationale or "resolved via audit resolve",
        review_actions=["no_action"],
    )
    _print_json(review)


def _add_audit(sub: argparse.ArgumentParser) -> None:
    audit_sub = sub.add_subparsers(dest="audit_action", required=True)

    # audit list
    list_parser = audit_sub.add_parser("list", help="List audit findings (sparks and audit rows) for a Cell")
    list_parser.add_argument("cell_path", nargs="?", type=_cell_path, help="path to the Cell directory")
    list_parser.add_argument("--cell", type=_cell_path, default=None, help="path to the Cell directory")

    # audit review
    review_parser = audit_sub.add_parser("review", help="Record a review decision on an audit finding")
    review_parser.add_argument("cell_path", nargs="?", type=_cell_path, help="path to the Cell directory")
    review_parser.add_argument("--cell", type=_cell_path, default=None, help="path to the Cell directory")
    review_parser.add_argument("--audit-id", type=str, required=True, help="audit finding identifier to review")
    review_parser.add_argument("--resolution", type=str, required=True, choices=("accept", "reject"), help="review resolution")
    review_parser.add_argument("--reviewer", type=str, required=True, help="reviewer identifier")
    review_parser.add_argument("--rationale", type=str, required=True, help="review rationale")
    review_parser.add_argument("--actions", type=str, default=None, help="comma-separated follow-up actions (e.g. mark_challenged,propose_isolation)")

    # audit resolve
    resolve_parser = audit_sub.add_parser("resolve", help="Mark a resolution on audit reviews for a finding")
    resolve_parser.add_argument("cell_path", nargs="?", type=_cell_path, help="path to the Cell directory")
    resolve_parser.add_argument("--cell", type=_cell_path, default=None, help="path to the Cell directory")
    resolve_parser.add_argument("--audit-id", type=str, required=True, help="audit finding identifier to resolve")
    resolve_parser.add_argument("--reviewer", type=str, default=None, help="reviewer identifier (default: system)")
    resolve_parser.add_argument("--rationale", type=str, default=None, help="resolution rationale")


# ---------------------------------------------------------------------------
# Subcommand: grid
# ---------------------------------------------------------------------------


def cmd_grid_status(args: argparse.Namespace) -> None:
    from shyftr.retrieval.vector import grid_status

    status = grid_status(args.cell)
    if args.backend != "auto":
        if status.get("metadata") is None:
            status["requested_backend"] = args.backend
        elif status["metadata"].get("backend") != args.backend:
            status["backend_mismatch"] = {
                "requested": args.backend,
                "stored": status["metadata"].get("backend"),
            }
    _print_json({"status": "ok", "grid": status})


def cmd_grid_rebuild(args: argparse.Namespace) -> None:
    from shyftr.retrieval.vector import rebuild_grid_metadata

    metadata = rebuild_grid_metadata(args.cell, backend=args.backend)
    _print_json({"status": "ok", "grid": metadata})


def cmd_grid_smoke(args: argparse.Namespace) -> None:
    from shyftr.retrieval.embeddings import DeterministicEmbeddingProvider
    from shyftr.retrieval.vector import InMemoryVectorIndex, query_vector

    provider = DeterministicEmbeddingProvider()
    if args.backend == "in-memory":
        index = InMemoryVectorIndex(backend="in-memory", embedding_model="deterministic-test", embedding_version="v1")
    elif args.backend == "lancedb":
        from shyftr.retrieval.lancedb_adapter import LanceDBVectorIndex
        index = LanceDBVectorIndex(args.cell / "grid" / "lancedb", embedding_model="deterministic-test", embedding_version="v1")
    else:
        raise ValueError(f"Unsupported Grid backend: {args.backend}")
    indexed = index.rebuild(args.cell, provider)
    results = query_vector(index, args.query, provider, top_k=args.limit)
    _print_json({
        "status": "ok",
        "grid": {
            "backend": args.backend,
            "indexed": indexed,
            "result_count": len(results),
            "results": [r.__dict__ for r in results],
            "metadata": index.export_metadata(),
            "canonical_truth": "cell_ledgers",
        },
    })


def _add_grid(sub: argparse.ArgumentParser) -> None:
    grid_sub = sub.add_subparsers(dest="grid_action", required=True)

    status = grid_sub.add_parser("status", help="Show Grid metadata and staleness for a Cell")
    status.add_argument("--cell", type=_cell_path, required=True, help="path to the Cell directory")
    status.add_argument("--backend", choices=("auto", "in-memory", "lancedb"), default="auto", help="expected Grid backend (default: auto)")

    rebuild = grid_sub.add_parser("rebuild", help="Rebuild disk-backed Grid metadata for a Cell")
    rebuild.add_argument("--cell", type=_cell_path, required=True, help="path to the Cell directory")
    rebuild.add_argument("--backend", choices=("in-memory", "lancedb"), default="in-memory", help="Grid backend to rebuild (default: in-memory)")

    smoke = grid_sub.add_parser("smoke", help="Rebuild and query a Grid backend for local comparison")
    smoke.add_argument("--cell", type=_cell_path, required=True, help="path to the Cell directory")
    smoke.add_argument("--backend", choices=("in-memory", "lancedb"), default="in-memory", help="Grid backend to smoke-test (default: in-memory)")
    smoke.add_argument("--query", required=True, help="query text for smoke comparison")
    smoke.add_argument("--limit", type=int, default=5, help="max results (default: 5)")


# ---------------------------------------------------------------------------
# Subcommand: backup / restore / verify-ledger
# ---------------------------------------------------------------------------


def cmd_backup(args: argparse.Namespace) -> None:
    from shyftr.backup import backup_cell

    _print_json(backup_cell(args.cell, args.output))


def _add_backup(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--cell", type=_cell_path, required=True, help="path to the Cell directory")
    sub.add_argument("--output", type=str, required=True, help="backup tar.gz path or output directory")


def cmd_restore(args: argparse.Namespace) -> None:
    from shyftr.backup import restore_cell

    _print_json(restore_cell(args.backup, args.target, force=args.force))


def _add_restore(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("backup", type=str, help="backup tar.gz path")
    sub.add_argument("target", type=str, help="restore target Cell directory")
    sub.add_argument("--force", action="store_true", default=False, help="allow restore into a non-empty directory")


def cmd_verify_ledger(args: argparse.Namespace) -> None:
    from shyftr.ledger_verify import adopt_ledger_heads, verify_ledgers

    if args.adopt:
        _print_json({"status": "ok", "manifest": adopt_ledger_heads(args.cell)})
    else:
        _print_json(verify_ledgers(args.cell))


def _add_verify_ledger(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--cell", type=_cell_path, required=True, help="path to the Cell directory")
    sub.add_argument("--adopt", action="store_true", default=False, help="write current ledger head manifest before verification")


# ---------------------------------------------------------------------------
# Subcommand: diagnostics / readiness
# ---------------------------------------------------------------------------


def cmd_diagnostics(args: argparse.Namespace) -> None:
    from shyftr.observability import read_diagnostic_logs, summarize_diagnostics

    if args.summary:
        _print_json(summarize_diagnostics(args.cell_path))
    else:
        _print_json({"status": "ok", "logs": read_diagnostic_logs(args.cell_path, operation=args.operation, limit=args.limit)})


def _add_diagnostics(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--operation", type=str, default=None, help="filter by operation")
    sub.add_argument("--limit", type=int, default=50, help="max log rows (default: 50)")
    sub.add_argument("--summary", action="store_true", default=False, help="emit diagnostic summary")


def cmd_readiness(args: argparse.Namespace) -> None:
    from shyftr.readiness import replacement_pilot_readiness

    report = replacement_pilot_readiness(
        args.cell_path,
        run_replay=bool(args.replacement_pilot),
        fixture_path=args.fixture,
    )
    _print_json(report.to_dict())


def _add_readiness(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--replacement-pilot", action="store_true", default=False, help="run replacement replay before readiness checks")
    sub.add_argument("--fixture", type=str, default=None, help="optional replay fixture JSON path")


# ---------------------------------------------------------------------------
# Frontier public-safe surfaces
# ---------------------------------------------------------------------------


def cmd_simulate(args: argparse.Namespace) -> None:
    from shyftr.simulation import SimulationRequest, simulate_policy
    report = simulate_policy(SimulationRequest(
        cell_path=str(args.cell_path),
        query=args.query,
        task_id=args.task_id,
        current_mode=args.current_mode,
        proposed_mode=args.proposed_mode,
        max_items=args.max_items,
        max_tokens=args.max_tokens,
    ))
    _print_json(report)


def _add_simulate(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("query", type=str, help="query to replay read-only")
    sub.add_argument("--task-id", type=str, default="simulation", help="simulation task id")
    sub.add_argument("--current-mode", type=str, default="balanced", help="baseline retrieval mode")
    sub.add_argument("--proposed-mode", type=str, default="balanced", help="proposed retrieval mode")
    sub.add_argument("--max-items", type=int, default=20, help="max items")
    sub.add_argument("--max-tokens", type=int, default=4000, help="max tokens")


def cmd_graph(args: argparse.Namespace) -> None:
    from shyftr.graph import list_graph_edges
    _print_json({"status": "ok", "edges": list_graph_edges(args.cell_path, source_id=args.source_id, target_id=args.target_id, edge_type=args.edge_type)})


def _add_graph(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--source-id", type=str, default=None, help="filter by source memory id")
    sub.add_argument("--target-id", type=str, default=None, help="filter by target memory id")
    sub.add_argument("--edge-type", type=str, default=None, help="filter by edge type")


def cmd_reputation(args: argparse.Namespace) -> None:
    from shyftr.reputation import reputation_summary
    _print_json(reputation_summary(args.cell_path, target_type=args.target_type, target_id=args.target_id))


def _add_reputation(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--target-type", type=str, default=None, help="filter by target type")
    sub.add_argument("--target-id", type=str, default=None, help="filter by target id")


def cmd_regulator_proposals(args: argparse.Namespace) -> None:
    from shyftr.regulator_proposals import append_regulator_proposals, generate_regulator_proposals
    proposals = generate_regulator_proposals(args.cell_path, min_repeated=args.min_repeated)
    if args.append:
        append_regulator_proposals(args.cell_path, proposals)
    _print_json({"status": "ok", "proposals": proposals, "total": len(proposals), "appended": bool(args.append)})


def _add_regulator_proposals(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--min-repeated", type=int, default=2, help="minimum repeated synthetic events")
    sub.add_argument("--append", action="store_true", default=False, help="append proposals to the review queue ledger")


def cmd_evalgen(args: argparse.Namespace) -> None:
    from shyftr.evalgen import export_eval_tasks
    _print_json(export_eval_tasks(args.cell_path, output_path=args.output, jsonl=args.jsonl))


def _add_evalgen(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    sub.add_argument("--output", type=str, default=None, help="optional JSON/JSONL output path")
    sub.add_argument("--jsonl", action="store_true", default=False, help="write JSONL when --output is set")


def cmd_evolve_scan(args: argparse.Namespace) -> None:
    from shyftr.evolution import scan_cell
    write = bool(args.write_proposals)
    _print_json(scan_cell(args.cell_path, write_proposals=write, max_candidate_chars=args.max_candidate_chars, rate_limit=args.rate_limit))


def cmd_evolve_proposals(args: argparse.Namespace) -> None:
    from shyftr.evolution import read_evolution_proposals
    proposals = read_evolution_proposals(args.cell_path, include_reviewed=bool(args.include_reviewed))
    _print_json({"status": "ok", "proposals": proposals, "total": len(proposals), "review_gated": True})


def cmd_evolve_simulate(args: argparse.Namespace) -> None:
    from shyftr.evolution import simulate_evolution_proposal
    _print_json(simulate_evolution_proposal(args.cell_path, args.proposal_id, append_report=bool(args.append_report)))


def cmd_evolve_review(args: argparse.Namespace) -> None:
    from shyftr.evolution import review_evolution_proposal
    event = review_evolution_proposal(
        args.cell_path,
        args.proposal_id,
        decision=args.decision,
        rationale=args.rationale,
        actor=args.actor,
        simulation_ref=args.simulation_ref,
    )
    _print_json({"status": "ok", "event": event})


def _add_evolve(sub: argparse.ArgumentParser) -> None:
    evolve_sub = sub.add_subparsers(dest="evolve_action", required=True)
    scan = evolve_sub.add_parser("scan", help="Scan a Cell for review-gated evolution proposals")
    scan.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    scan.add_argument("--dry-run", action="store_true", default=False, help="emit proposals without writing ledgers (default)")
    scan.add_argument("--write-proposals", action="store_true", default=False, help="append proposals only; never apply lifecycle changes")
    scan.add_argument("--max-candidate-chars", type=int, default=360, help="split-proposal threshold for candidate text")
    scan.add_argument("--rate-limit", type=int, default=100, help="maximum proposals emitted per scan")
    proposals = evolve_sub.add_parser("proposals", help="List memory evolution proposals")
    proposals.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    proposals.add_argument("--include-reviewed", action="store_true", default=True, help="include accepted/rejected/deferred proposals")
    simulate = evolve_sub.add_parser("simulate", help="Run read-only projection simulation for an evolution proposal")
    simulate.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    simulate.add_argument("proposal_id", type=str, help="evolution proposal id")
    simulate.add_argument("--append-report", action="store_true", default=False, help="append the simulation report to the simulation ledger")
    review = evolve_sub.add_parser("review", help="Record a review decision for an evolution proposal")
    review.add_argument("cell_path", type=_cell_path, help="path to the Cell directory")
    review.add_argument("proposal_id", type=str, help="evolution proposal id")
    review.add_argument("--decision", required=True, choices=("accept", "reject", "defer"), help="review decision")
    review.add_argument("--rationale", required=True, type=str, help="operator rationale")
    review.add_argument("--actor", default="operator", type=str, help="review actor")
    review.add_argument("--simulation-ref", default=None, type=str, help="required for accepting retrieval-affecting proposals")


# ---------------------------------------------------------------------------
# Subcommand: serve
# ---------------------------------------------------------------------------


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the optional local HTTP service."""
    from shyftr.server import run as run_server

    run_server(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


def _add_serve(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--host", type=str, default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    sub.add_argument("--port", type=int, default=8014, help="bind port (default: 8014)")
    sub.add_argument("--log-level", type=str, default="info", choices=("critical", "error", "warning", "info", "debug", "trace"), help="uvicorn log level (default: info)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _canonicalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    aliases = {
        "source_id": "evidence_id",
        "fragment_id": "candidate_id",
        "trace_id": "memory_id",
        "alloy_id": "pattern_id",
        "doctrine_id": "rule_id",
        "loadout_id": "pack_id",
        "outcome_id": "feedback_id",
        "source_fragment_ids": "candidate_ids",
        "source_trace_ids": "memory_ids",
        "source_alloy_ids": "pattern_ids",
        "trace_ids": "memory_ids",
        "alloy_ids": "pattern_ids",
        "doctrine_ids": "rule_ids",
        "boundary_status": "regulator_status",
        "source_excerpt": "evidence_excerpt",
        "ignored_charge_ids": "ignored_memory_ids",
        "contradicted_charge_ids": "contradicted_memory_ids",
        "over_retrieved_charge_ids": "over_retrieved_memory_ids",
    }
    out = dict(record)
    for old_name, new_name in aliases.items():
        if old_name in record and new_name not in out:
            out[new_name] = record[old_name]
        if old_name in out and new_name in out:
            del out[old_name]
    return out


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, sort_keys=True, indent=2, default=str)
    sys.stdout.write("\n")


def _fail(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def _resolve_subcommand(args: argparse.Namespace) -> None:
    cmd_map: Dict[str, Any] = {
        "init": cmd_init,
        "init-cell": cmd_init,
        "ingest": cmd_ingest,
        "feed": cmd_ingest,
        "candidate": cmd_candidate,
        "candidates": cmd_candidate,
        "fragment": cmd_candidate,
        "fragments": cmd_candidate,
        "spark": cmd_candidate,
        "sparks": cmd_candidate,
        "approve": cmd_review_approve,
        "reject": cmd_review_reject,
        "promote": cmd_memory,
        "charge": cmd_memory,
        "memory": cmd_memory,
        "search": _do_search,
        "retrieve": _do_search,
        "profile": cmd_profile,
        "loadout": cmd_pack,
        "pack": cmd_pack,
        "outcome": cmd_feedback,
        "signal": cmd_feedback,
        "feedback": cmd_feedback,
        "proposals": cmd_proposals_export,
        "hygiene": cmd_hygiene,
        "counters": cmd_counters,
        "metrics": cmd_metrics,
        "decay": cmd_decay,
        "sweep": cmd_sweep,
        "challenge": cmd_challenge,
        "grid": cmd_grid_status,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "verify-ledger": cmd_verify_ledger,
        "diagnostics": cmd_diagnostics,
        "readiness": cmd_readiness,
        "simulate": cmd_simulate,
        "graph": cmd_graph,
        "reputation": cmd_reputation,
        "regulator-proposals": cmd_regulator_proposals,
        "evalgen": cmd_evalgen,
        "evolve": cmd_evolve_scan,
        "serve": cmd_serve,
    }

    cmd_name = args.command

    # Handle nested subcommands (review approve / review reject)
    if cmd_name == "review":
        if args.review_action == "approve":
            return cmd_review_approve(args)
        elif args.review_action == "reject":
            return cmd_review_reject(args)
        else:
            _fail(f"unknown review action: {args.review_action}")

    if cmd_name == "proposals":
        if args.proposals_action == "export":
            return cmd_proposals_export(args)
        _fail(f"unknown proposals action: {args.proposals_action}")

    if cmd_name == "evolve":
        if args.evolve_action == "scan":
            return cmd_evolve_scan(args)
        if args.evolve_action == "proposals":
            return cmd_evolve_proposals(args)
        if args.evolve_action == "simulate":
            return cmd_evolve_simulate(args)
        if args.evolve_action == "review":
            return cmd_evolve_review(args)
        _fail(f"unknown evolve action: {args.evolve_action}")

    if cmd_name == "adapter":
        if args.adapter_action == "validate":
            return cmd_adapter_validate(args)
        if args.adapter_action == "discover":
            return cmd_adapter_discover(args)
        if args.adapter_action == "ingest":
            return cmd_adapter_ingest(args)
        if args.adapter_action == "backfill":
            return cmd_adapter_backfill(args)
        if args.adapter_action == "sync":
            return cmd_adapter_sync(args)
        if args.adapter_action == "sync-status":
            return cmd_adapter_sync_status(args)
        if args.adapter_action == "list":
            return cmd_adapter_list(args)
        _fail(f"unknown adapter action: {args.adapter_action}")

    if cmd_name == "cell":
        return {
            "register": cmd_cell_register,
            "list": cmd_cell_list,
            "info": cmd_cell_info,
            "unregister": cmd_cell_unregister,
            "export": cmd_cell_export,
            "import": cmd_cell_import,
        }[args.cell_action](args)

    if cmd_name == "resonance":
        if args.resonance_action == "scan":
            return cmd_resonance_scan(args)
        _fail(f"unknown resonance action: {args.resonance_action}")

    if cmd_name == "rule":
        return {
            "propose-from-resonance": cmd_rule_propose_from_resonance,
            "list": cmd_rule_list,
            "approve": cmd_rule_approve,
            "reject": cmd_rule_reject,
        }[args.rule_action](args)

    if cmd_name == "import":
        return {
            "list": cmd_import_list,
            "approve": cmd_import_approve,
            "reject": cmd_import_reject,
        }[args.import_action](args)

    if cmd_name == "audit":
        if args.audit_action == "list":
            return cmd_audit_list(args)
        if args.audit_action == "review":
            return cmd_audit_review(args)
        if args.audit_action == "resolve":
            return cmd_audit_resolve(args)
        _fail(f"unknown audit action: {args.audit_action}")

    if cmd_name == "grid":
        if args.grid_action == "status":
            return cmd_grid_status(args)
        if args.grid_action == "rebuild":
            return cmd_grid_rebuild(args)
        if args.grid_action == "smoke":
            return cmd_grid_smoke(args)
        _fail(f"unknown grid action: {args.grid_action}")

    handler = cmd_map.get(cmd_name)
    if handler:
        handler(args)
    else:
        _fail(f"unknown command: {cmd_name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shyftr",
        description="ShyftR — Attachable recursive memory cells for AI agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True, title="commands")

    _add_init(sub.add_parser("init", help="Create a new ShyftR Cell layout"))
    _add_init(sub.add_parser("init-cell", help="Create a new ShyftR Cell layout"))
    _add_ingest(sub.add_parser("ingest", help="Ingest an evidence file into a cell"))
    _add_ingest(sub.add_parser("feed", help="Deprecated alias: ingest an evidence file into a cell"))
    _add_candidate(sub.add_parser("candidate", help="Extract candidates from ingested evidence"))
    _add_candidate(sub.add_parser("candidates", help="Extract candidates from ingested evidence"))
    _add_candidate(sub.add_parser("fragment", help="Deprecated alias: extract candidates from evidence"))
    _add_candidate(sub.add_parser("fragments", help="Deprecated alias: extract candidates from evidence"))
    _add_candidate(sub.add_parser("spark", help="Deprecated alias: extract candidates from evidence"))
    _add_candidate(sub.add_parser("sparks", help="Deprecated alias: extract candidates from evidence"))
    _add_review(sub.add_parser("review", help="Approve or reject a candidate"))
    _add_review_action(sub.add_parser("approve", help="Approve a candidate"), required_action="approve")
    _add_review_action(sub.add_parser("reject", help="Reject a candidate"), required_action="reject")
    _add_memory(sub.add_parser("promote", help="Deprecated alias: promote an approved candidate to memory"))
    _add_memory(sub.add_parser("charge", help="Deprecated alias: promote an approved candidate to memory"))
    _add_memory(sub.add_parser("memory", help="Promote an approved candidate to memory"))
    _add_search(sub.add_parser("search", help="Search approved traces via sparse FTS5 index"))
    _add_search(sub.add_parser("retrieve", help="Alias for the search command"))
    _add_profile(sub.add_parser("profile", help="Build rebuildable profile projection artifacts"))
    _add_pack(sub.add_parser("loadout", help="Deprecated alias: assemble a bounded memory pack"))
    _add_pack(sub.add_parser("pack", help="Assemble a bounded memory pack"))
    _add_feedback(sub.add_parser("outcome", help="Deprecated alias: record feedback for a pack"))
    _add_feedback(sub.add_parser("signal", help="Deprecated alias: record feedback for a pack"))
    _add_feedback(sub.add_parser("feedback", help="Record feedback for a pack"))
    _add_proposals(sub.add_parser("proposals", help="Export advisory runtime proposals"))
    _add_cell(sub.add_parser("cell", help="Register, list, export, and import Cells"))
    _add_resonance(sub.add_parser("resonance", help="Run explicit cross-cell resonance scans"))
    _add_rule(sub.add_parser("rule", help="Review-gated shared rule workflow"))
    _add_import(sub.add_parser("import", help="Review imported federation records"))
    _add_hygiene(sub.add_parser("hygiene", help="Run a hygiene report on a Cell"))
    _add_counters(sub.add_parser("counters", help="Show trace usage counters"))
    _add_metrics(sub.add_parser("metrics", help="Show local memory effectiveness metrics"))
    _add_decay(sub.add_parser("decay", help="Show review-gated memory decay scoring and proposal summaries"))
    _add_sweep(sub.add_parser("sweep", help="Run a sweep dry-run analysis"))
    _add_challenge(sub.add_parser("challenge", help="Run a challenger audit loop analysis"))
    _add_grid(sub.add_parser("grid", help="Inspect and rebuild the rebuildable retrieval Grid"))
    _add_backup(sub.add_parser("backup", help="Create a portable Cell backup archive"))
    _add_restore(sub.add_parser("restore", help="Restore a Cell backup archive into a new path"))
    _add_verify_ledger(sub.add_parser("verify-ledger", help="Verify or adopt tamper-evident ledger head hashes"))
    _add_adapter(sub.add_parser("adapter", help="Validate, discover, ingest, list, and backfill runtime adapters"))
    _add_audit(sub.add_parser("audit", help="Inspect and review audit findings for a Cell"))
    _add_diagnostics(sub.add_parser("diagnostics", help="Read structured ShyftR diagnostic logs"))
    _add_readiness(sub.add_parser("readiness", help="Run replacement-readiness checks for bounded pilots"))
    _add_simulate(sub.add_parser("simulate", help="Run a read-only retrieval policy simulation"))
    _add_graph(sub.add_parser("graph", help="List append-only causal memory graph edges"))
    _add_reputation(sub.add_parser("reputation", help="Summarize append-only reputation events"))
    _add_regulator_proposals(sub.add_parser("regulator-proposals", help="Generate review-gated regulator proposals"))
    _add_evalgen(sub.add_parser("evalgen", help="Generate synthetic public-safe eval tasks"))
    _add_evolve(sub.add_parser("evolve", help="Scan, simulate, and review memory evolution proposals"))
    _add_serve(sub.add_parser("serve", help="Start the optional local HTTP service"))

    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _resolve_subcommand(args)
    except Exception as e:
        _fail(str(e))


if __name__ == "__main__":
    main()
