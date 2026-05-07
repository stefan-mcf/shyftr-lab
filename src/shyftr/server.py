"""Optional local HTTP service wrapper for runtimes that cannot shell out to the CLI.

This module is an optional, local-first convenience layer. It delegates to
existing ShyftR modules and does NOT create a second truth path. The CLI
remains the primary interface; the HTTP service is purely a runtime adapter.

Usage:
    pip install shyftr[service]
    python -m shyftr.server

Endpoints:
    POST /validate         - Validate an adapter config file
    POST /ingest           - Ingest a Pulse via an adapter config
    POST /pack             - Request a Loadout/Pack
    POST /signal           - Report a Signal/Outcome
    POST /proposals/export - Export advisory runtime proposals
    GET  /health           - Health check
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Graceful optional-dependency import
# ---------------------------------------------------------------------------

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, PlainTextResponse
    import uvicorn
except ImportError:  # pragma: no cover - covered by optional-dependency checks
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    Request = Any  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]
    uvicorn = None  # type: ignore[assignment]


def service_dependencies_available() -> bool:
    """Return whether the optional local HTTP service dependencies are installed."""

    return FastAPI is not None and JSONResponse is not None and uvicorn is not None


def _require_service_dependencies() -> None:
    if not service_dependencies_available():
        raise ImportError(
            "The local HTTP service requires 'shyftr[service]'. "
            "Install it with: pip install shyftr[service]"
        )


# ---------------------------------------------------------------------------
# Create the app (lazy so importing the module doesn't require FastAPI)
# ---------------------------------------------------------------------------

_app_instance: Optional[FastAPI] = None


def _get_app() -> Any:
    global _app_instance
    _require_service_dependencies()
    if _app_instance is None:
        app = FastAPI(
            title="ShyftR Local Service",
            description="Optional local HTTP service for runtime integration",
            version="1.0.0-alpha",
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:4173",
                "http://localhost:4173",
            ],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        _register_routes(app)
        _register_v1_aliases(app)

        @app.middleware("http")
        async def api_version_headers(request: Request, call_next: Any) -> Any:
            response = await call_next(request)
            response.headers.setdefault("X-ShyftR-API-Version", "v1")
            if _is_unversioned_public_path(request.url.path):
                response.headers.setdefault("Deprecation", "true")
                response.headers.setdefault("Link", '</v1>; rel="successor-version"')
            return response

        _app_instance = app
    return _app_instance


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


def _register_routes(app: FastAPI) -> None:
    @app.get("/v1")
    @app.get("/v1/")
    async def api_versions() -> Dict[str, Any]:
        return {
            "status": "ok",
            "api_versions": ["v1"],
            "latest": "v1",
            "api_version": "v1",
            "schema_version": "1.0.0",
            "posture": "stable local-first release",
            "deprecated": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"status": "ok", "service": "shyftr-local-http"}

    @app.get("/frontier")
    async def frontier(cell_path: str) -> JSONResponse:
        """Read-only frontier review surfaces for a local Cell."""
        try:
            from shyftr.console_api import frontier_review_surfaces
            return JSONResponse(content=frontier_review_surfaces(cell_path))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/simulate")
    async def simulate(request: Request) -> JSONResponse:
        """Run a read-only retrieval policy simulation."""
        body = await _parse_body(request)
        try:
            from shyftr.simulation import SimulationRequest, simulate_policy
            sim = SimulationRequest(**{k: v for k, v in body.items() if k in SimulationRequest.__dataclass_fields__})
            return JSONResponse(content=simulate_policy(sim))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    def _carry_alias_payload(body: dict[str, Any]) -> dict[str, Any]:
        payload = dict(body)
        if "continuity_cell_path" not in payload and "carry_cell_path" in payload:
            payload["continuity_cell_path"] = payload["carry_cell_path"]
        if "continuity_pack_id" not in payload and "carry_pack_id" in payload:
            payload["continuity_pack_id"] = payload["carry_pack_id"]
        return payload

    async def _continuity_pack_response(request: Request) -> JSONResponse:
        body = _carry_alias_payload(await _parse_body(request))
        try:
            from shyftr.continuity import ContinuityPackRequest, assemble_continuity_pack
            payload = {k: v for k, v in body.items() if k in ContinuityPackRequest.__dataclass_fields__}
            return JSONResponse(content=assemble_continuity_pack(ContinuityPackRequest(**payload)).to_dict())
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/carry/pack")
    async def carry_pack(request: Request) -> JSONResponse:
        return await _continuity_pack_response(request)

    @app.post("/continuity/pack")
    async def continuity_pack(request: Request) -> JSONResponse:
        return await _continuity_pack_response(request)

    async def _continuity_feedback_response(request: Request) -> JSONResponse:
        body = _carry_alias_payload(await _parse_body(request))
        try:
            from shyftr.continuity import ContinuityFeedback, record_continuity_feedback
            payload = {k: v for k, v in body.items() if k in ContinuityFeedback.__dataclass_fields__}
            return JSONResponse(content=record_continuity_feedback(ContinuityFeedback(**payload)))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/carry/feedback")
    async def carry_feedback(request: Request) -> JSONResponse:
        return await _continuity_feedback_response(request)

    @app.post("/continuity/feedback")
    async def continuity_feedback(request: Request) -> JSONResponse:
        return await _continuity_feedback_response(request)

    async def _continuity_status_response(cell_path: str) -> JSONResponse:
        try:
            from shyftr.continuity import continuity_status
            return JSONResponse(content=continuity_status(cell_path))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/carry/status")
    async def carry_status_route(carry_cell_path: str) -> JSONResponse:
        return await _continuity_status_response(carry_cell_path)

    @app.get("/continuity/status")
    async def continuity_status_route(continuity_cell_path: str) -> JSONResponse:
        return await _continuity_status_response(continuity_cell_path)

    @app.post("/live-context/capture")
    async def live_context_capture(request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.live_context import LiveContextCaptureRequest, capture_live_context
            payload = {k: v for k, v in body.items() if k in LiveContextCaptureRequest.__dataclass_fields__}
            return JSONResponse(content=capture_live_context(LiveContextCaptureRequest(**payload)))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/live-context/pack")
    async def live_context_pack(request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.live_context import LiveContextPackRequest, build_live_context_pack
            payload = {k: v for k, v in body.items() if k in LiveContextPackRequest.__dataclass_fields__}
            return JSONResponse(content=build_live_context_pack(LiveContextPackRequest(**payload)).to_dict())
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/live-context/harvest")
    async def live_context_harvest(request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.live_context import SessionHarvestRequest, harvest_session
            payload = {k: v for k, v in body.items() if k in SessionHarvestRequest.__dataclass_fields__}
            return JSONResponse(content=harvest_session(SessionHarvestRequest(**payload)).to_dict())
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/live-context/status")
    async def live_context_status_route(cell_path: str) -> JSONResponse:
        try:
            from shyftr.live_context import live_context_status
            return JSONResponse(content=live_context_status(cell_path))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/evolution")
    async def evolution_list(cell_path: str, include_reviewed: bool = True) -> Dict[str, Any]:
        from shyftr.evolution import read_evolution_proposals
        proposals = read_evolution_proposals(cell_path, include_reviewed=include_reviewed)
        return {"status": "ok", "proposals": proposals, "total": len(proposals), "review_gated": True}

    @app.post("/evolution/scan")
    async def evolution_scan(request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.evolution import scan_cell
            payload = scan_cell(
                body["cell_path"],
                write_proposals=bool(body.get("write_proposals", False)),
                max_candidate_chars=int(body.get("max_candidate_chars", 360)),
                rate_limit=int(body.get("rate_limit", 100)),
            )
            return JSONResponse(content=payload)
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/evolution/{proposal_id}/simulate")
    async def evolution_simulate(proposal_id: str, request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.evolution import simulate_evolution_proposal
            return JSONResponse(content=simulate_evolution_proposal(body["cell_path"], proposal_id, append_report=bool(body.get("append_report", False))))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/evolution/{proposal_id}/review")
    async def evolution_review(proposal_id: str, request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.evolution import review_evolution_proposal
            event = review_evolution_proposal(
                body["cell_path"],
                proposal_id,
                decision=str(body.get("decision") or ""),
                rationale=str(body.get("rationale") or ""),
                actor=str(body.get("actor") or "operator"),
                simulation_ref=body.get("simulation_ref"),
            )
            return JSONResponse(content={"status": "ok", "event": event})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    # -- Adapter validation -------------------------------------------------

    @app.post("/validate")
    async def validate_adapter(request: Request) -> JSONResponse:
        """Validate a runtime adapter config file.

        Expects JSON body: {"config_path": "/path/to/adapter.yaml"}
        Delegates to shyftr.integrations.config.{load_config, validate_config}.
        """
        body = await _parse_body(request)
        config_path = body.get("config_path")
        if not config_path:
            return JSONResponse(
                status_code=422,
                content={"status": "error", "message": "config_path is required"},
            )

        try:
            from shyftr.integrations.config import load_config, validate_config

            config = load_config(config_path)
            validate_config(config)
            return JSONResponse(
                content={
                    "status": "ok",
                    "adapter_id": config.adapter_id,
                    "cell_id": config.cell_id,
                    "external_system": config.external_system,
                    "external_scope": config.external_scope,
                    "source_root": config.source_root,
                    "inputs": [
                        {"kind": inp.kind, "path": inp.path, "source_kind": inp.source_kind}
                        for inp in config.inputs
                    ],
                }
            )
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(exc)},
            )

    # -- Pulse ingest -------------------------------------------------------

    @app.post("/ingest")
    async def ingest_pulse(request: Request) -> JSONResponse:
        """Ingest a Pulse / adapter-discovered Sources.

        Expects JSON body:
          {"config_path": "...", "cell_path": "...", "dry_run": false}
        Delegates to shyftr.ingest.ingest_from_adapter.
        """
        body = await _parse_body(request)
        config_path = body.get("config_path")
        cell_path = body.get("cell_path")
        dry_run = body.get("dry_run", False)

        if not config_path:
            return JSONResponse(
                status_code=422,
                content={"status": "error", "message": "config_path is required"},
            )
        if not cell_path:
            return JSONResponse(
                status_code=422,
                content={"status": "error", "message": "cell_path is required"},
            )

        try:
            from shyftr.ingest import ingest_from_adapter

            result = ingest_from_adapter(
                cell_path=cell_path,
                adapter_config_or_path=config_path,
                dry_run=bool(dry_run),
            )
            return JSONResponse(content={"status": "ok", **result})
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(exc)},
            )

    # -- Pack request -------------------------------------------------------

    @app.post("/pack")
    async def request_pack(request: Request) -> JSONResponse:
        """Request a Loadout / Pack.

        Expects JSON body conforming to RuntimeLoadoutRequest schema.
        Delegates to shyftr.integrations.pack_api.process_runtime_loadout_request.
        """
        body = await _parse_body(request)

        try:
            from shyftr.integrations.pack_api import (
                RuntimeLoadoutRequest,
                process_runtime_loadout_request,
            )

            runtime_request = RuntimeLoadoutRequest.from_dict(body)
            response = process_runtime_loadout_request(runtime_request)
            return JSONResponse(content=response.to_dict())
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(exc)},
            )

    @app.get("/retrieval-logs")
    async def retrieval_logs(
        cell_path: str,
        loadout_id: Optional[str] = None,
        query: Optional[str] = None,
        selected_memory_id: Optional[str] = None,
        limit: int = 20,
    ) -> JSONResponse:
        """Return public-safe retrieval usage logs for generic clients."""
        try:
            from shyftr.integrations.retrieval_logs import list_retrieval_logs

            return JSONResponse(
                content=list_retrieval_logs(
                    cell_path,
                    loadout_id=loadout_id,
                    query=query,
                    selected_memory_id=selected_memory_id,
                    limit=int(limit),
                )
            )
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(exc)},
            )

    # -- Signal report ------------------------------------------------------

    @app.post("/feedback")
    @app.post("/signal")
    async def report_signal(request: Request) -> JSONResponse:
        """Report feedback from a runtime pack use.

        Expects JSON body conforming to RuntimeOutcomeReport schema.
        Delegates to shyftr.integrations.outcome_api.process_runtime_outcome_report.
        """
        body = await _parse_body(request)

        try:
            from shyftr.integrations.outcome_api import (
                RuntimeOutcomeReport,
                process_runtime_outcome_report,
            )

            report = RuntimeOutcomeReport.from_dict(body)
            response = process_runtime_outcome_report(report)
            return JSONResponse(content=response.to_dict())
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(exc)},
            )

    # -- Proposal export ----------------------------------------------------

    @app.post("/proposals/export")
    async def export_proposals(request: Request) -> JSONResponse:
        """Export advisory runtime proposals.

        Expects JSON body:
          {"cell_path": "...", "external_system": "...", "include_accepted": false}
        Delegates to shyftr.integrations.proposals.export_runtime_proposals.
        """
        body = await _parse_body(request)
        cell_path = body.get("cell_path")
        external_system = body.get("external_system")
        include_accepted = body.get("include_accepted", False)
        output_path = body.get("output_path")

        if not cell_path:
            return JSONResponse(
                status_code=422,
                content={"status": "error", "message": "cell_path is required"},
            )

        try:
            from shyftr.integrations.proposals import export_runtime_proposals

            payload = export_runtime_proposals(
                cell_path=cell_path,
                external_system=external_system,
                output_path=output_path,
                include_accepted=bool(include_accepted),
            )
            return JSONResponse(content=payload)
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(exc)},
            )
    # -- Diagnostics/readiness and Cell inspection --------------------------

    @app.get("/cells")
    async def list_cells(root: str = ".") -> Dict[str, Any]:
        base = Path(root).expanduser()
        cells = []
        if base.exists():
            for manifest in sorted(base.glob("*/config/cell_manifest.json")):
                try:
                    import json as _json
                    data = _json.loads(manifest.read_text(encoding="utf-8"))
                    cells.append({"cell_id": data.get("cell_id"), "cell_type": data.get("cell_type"), "cell_path": str(manifest.parents[1])})
                except Exception:
                    continue
        return {"status": "ok", "cells": cells}

    @app.get("/cell/{cell_id}/summary")
    async def cell_dashboard_summary(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.console_api import cell_summary
        return cell_summary(_resolve_cell(root, cell_id))

    @app.get("/cell/{cell_id}/status")
    async def cell_status(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.console_api import cell_summary
        return cell_summary(_resolve_cell(root, cell_id))

    @app.get("/cell/{cell_id}/memories")
    async def cell_memories(
        cell_id: str,
        root: str = ".",
        query: str = "",
        kind: str = "",
        status: str = "",
        tag: str = "",
    ) -> Dict[str, Any]:
        from shyftr.console_api import memory_explorer
        return memory_explorer(_resolve_cell(root, cell_id), query=query, kind=kind, status=status, tag=tag)

    @app.get("/cell/{cell_id}/sparks")
    async def cell_sparks(
        cell_id: str,
        root: str = ".",
        status: Optional[str] = None,
        kind: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        from shyftr.console_api import spark_review_queue
        return spark_review_queue(_resolve_cell(root, cell_id), status=status, kind=kind, tag=tag)

    @app.post("/cell/{cell_id}/sparks/{spark_id}/review")
    async def review_spark(cell_id: str, spark_id: str, request: Request, root: str = ".") -> JSONResponse:
        body = await _parse_body(request)
        action = str(body.get("action") or "")
        rationale = str(body.get("rationale") or "").strip()
        reviewer = str(body.get("reviewer") or "console")
        if not rationale:
            return JSONResponse(status_code=422, content={"status": "error", "message": "rationale is required"})
        try:
            from shyftr.review import approve_fragment, reject_fragment, split_fragment, merge_fragments
            cell = _resolve_cell(root, cell_id)
            if action == "approve":
                event = approve_fragment(cell, spark_id, reviewer=reviewer, rationale=rationale, metadata=body.get("metadata") or {})
            elif action == "reject":
                event = reject_fragment(cell, spark_id, reviewer=reviewer, rationale=rationale, metadata=body.get("metadata") or {})
            elif action == "split":
                event = split_fragment(cell, spark_id, reviewer=reviewer, rationale=rationale, proposed_texts=list(body.get("proposed_texts") or []), metadata=body.get("metadata") or {})
            elif action == "merge":
                event = merge_fragments(cell, list(body.get("fragment_ids") or [spark_id]), reviewer=reviewer, rationale=rationale, proposed_text=str(body.get("proposed_text") or ""), metadata=body.get("metadata") or {})
            else:
                return JSONResponse(status_code=422, content={"status": "error", "message": "action must be approve, reject, split, or merge"})
            return JSONResponse(content={"status": "ok", "event": event})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/cell/{cell_id}/memories/{charge_id}/action")
    @app.post("/cell/{cell_id}/charges/{charge_id}/action")
    async def charge_lifecycle_action(cell_id: str, charge_id: str, request: Request, root: str = ".") -> JSONResponse:
        body = await _parse_body(request)
        action = str(body.get("action") or "")
        reason = str(body.get("reason") or "").strip()
        actor = str(body.get("actor") or "console")
        if not reason:
            return JSONResponse(status_code=422, content={"status": "error", "message": "reason is required"})
        try:
            from shyftr.mutations import deprecate_charge, forget_charge, isolation_charge, replace_charge
            cell = _resolve_cell(root, cell_id)
            if action == "deprecate":
                result = deprecate_charge(cell, charge_id, reason=reason, actor=actor)
            elif action == "forget":
                result = forget_charge(cell, charge_id, reason=reason, actor=actor)
            elif action == "challenge":
                result = isolation_charge(cell, charge_id, reason=reason, actor=actor)
            elif action == "replace":
                result = replace_charge(cell, charge_id, str(body.get("new_statement") or ""), reason=reason, actor=actor)
            else:
                return JSONResponse(status_code=422, content={"status": "error", "message": "action must be deprecate, forget, challenge, or replace"})
            return JSONResponse(content={"status": "ok", "event": result.__dict__})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/cell/{cell_id}/hygiene")
    async def cell_hygiene(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.reports.hygiene import hygiene_report
        return hygiene_report(_resolve_cell(root, cell_id))

    @app.get("/cell/{cell_id}/sweep")
    async def cell_sweep(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.sweep import run_sweep
        return run_sweep(_resolve_cell(root, cell_id), dry_run=True)

    @app.get("/cell/{cell_id}/proposals")
    async def cell_proposals(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.console_api import proposal_inbox
        return proposal_inbox(_resolve_cell(root, cell_id))

    @app.post("/cell/{cell_id}/proposals/{proposal_id}/decision")
    async def proposal_decision(cell_id: str, proposal_id: str, request: Request, root: str = ".") -> JSONResponse:
        body = await _parse_body(request)
        rationale = str(body.get("rationale") or "").strip()
        decision = str(body.get("decision") or "")
        if decision not in {"accept", "reject", "defer"}:
            return JSONResponse(status_code=422, content={"status": "error", "message": "decision must be accept, reject, or defer"})
        if not rationale:
            return JSONResponse(status_code=422, content={"status": "error", "message": "rationale is required"})
        try:
            from datetime import datetime, timezone
            from uuid import uuid4
            from shyftr.ledger import append_jsonl
            cell = _resolve_cell(root, cell_id)
            event = {
                "decision_id": f"proposal-decision-{uuid4().hex}",
                "proposal_id": proposal_id,
                "decision": decision,
                "rationale": rationale,
                "actor": str(body.get("actor") or "console"),
                "decided_at": datetime.now(timezone.utc).isoformat(),
            }
            append_jsonl(cell / "ledger" / "proposal_decisions.jsonl", event)
            return JSONResponse(content={"status": "ok", "event": event})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/cell/{cell_id}/metrics")
    async def cell_metrics(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.console_api import pilot_metrics
        return pilot_metrics(_resolve_cell(root, cell_id))

    @app.get("/cell/{cell_id}/metrics.csv")
    async def cell_metrics_csv(cell_id: str, root: str = ".") -> PlainTextResponse:
        from shyftr.console_api import pilot_metrics_csv
        return PlainTextResponse(pilot_metrics_csv(_resolve_cell(root, cell_id)), media_type="text/csv")

    @app.get("/cell/{cell_id}/operator-burden")
    async def cell_operator_burden(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.console_api import pilot_metrics
        payload = pilot_metrics(_resolve_cell(root, cell_id))
        keys = {"pending_sparks", "pending_proposals", "average_review_time_minutes", "stale_review_items", "rejected_item_ratio", "review_pressure_score"}
        return {"status": "ok", "operator_burden": {k: v for k, v in payload["metrics"].items() if k in keys}}

    @app.get("/cell/{cell_id}/policy-tuning")
    async def cell_policy_tuning(cell_id: str, root: str = ".") -> Dict[str, Any]:
        from shyftr.console_api import policy_tuning_report
        return policy_tuning_report(_resolve_cell(root, cell_id))

    @app.post("/cell/{cell_id}/pack")
    async def cell_pack(cell_id: str, request: Request, root: str = ".") -> JSONResponse:
        body = await _parse_body(request)
        body.setdefault("cell_path_or_id", str(_resolve_cell(root, cell_id)))
        try:
            from shyftr.integrations.pack_api import RuntimeLoadoutRequest, process_runtime_loadout_request
            response = process_runtime_loadout_request(RuntimeLoadoutRequest.from_dict(body))
            return JSONResponse(content=response.to_dict())
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/cell/{cell_id}/feedback")
    @app.post("/cell/{cell_id}/signal")
    async def cell_signal(cell_id: str, request: Request, root: str = ".") -> JSONResponse:
        body = await _parse_body(request)
        body.setdefault("cell_path_or_id", str(_resolve_cell(root, cell_id)))
        try:
            from shyftr.integrations.outcome_api import RuntimeOutcomeReport, process_runtime_outcome_report
            response = process_runtime_outcome_report(RuntimeOutcomeReport.from_dict(body))
            return JSONResponse(content=response.to_dict())
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/diagnostics")
    async def diagnostics(cell_path: str, operation: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        from shyftr.observability import read_diagnostic_logs
        return {"status": "ok", "logs": read_diagnostic_logs(cell_path, operation=operation, limit=limit)}

    @app.post("/readiness")
    async def readiness(request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.readiness import replacement_pilot_readiness
            report = replacement_pilot_readiness(body["cell_path"], run_replay=bool(body.get("replacement_pilot", False)), fixture_path=body.get("fixture_path"))
            return JSONResponse(content=report.to_dict())
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})


    # -- multi-cell milestone explicit multi-cell surfaces -------------------------------

    @app.get("/registry/cells")
    async def registry_cells(registry: str, cell_type: Optional[str] = None, tag: Optional[str] = None) -> Dict[str, Any]:
        from shyftr.console_api import registered_cells
        return registered_cells(registry, cell_type=cell_type, tag=tag)

    @app.get("/cells/{cell_id}")
    async def registered_cell_detail(cell_id: str, registry: str) -> Dict[str, Any]:
        from shyftr.console_api import cell_detail
        return cell_detail(registry, cell_id)

    @app.post("/cells/register")
    async def register_cell_route(request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.registry import register_cell, CellRegistryEntry
            registry = body.pop("registry")
            entry = CellRegistryEntry.from_dict(body)
            return JSONResponse(content={"status": "ok", "cell": register_cell(registry, entry).to_dict()})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/resonance/scan")
    async def resonance_scan_route(request: Request) -> JSONResponse:
        body = await _parse_body(request)
        registry = body.get("registry")
        cell_ids = body.get("cell_ids") or body.get("cells") or []
        if not registry or len(cell_ids) < 2:
            return JSONResponse(status_code=422, content={"status": "error", "message": "registry and at least two explicit cell_ids are required"})
        try:
            from shyftr.resonance import scan_registry_resonance
            return JSONResponse(content={"status": "ok", "dry_run": True, "results": scan_registry_resonance(registry, cell_ids, threshold=float(body.get("threshold", 0.25)))})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/rules/proposed")
    async def rules_proposed(cell_path: str, status: Optional[str] = None) -> Dict[str, Any]:
        from shyftr.console_api import rule_review_queue
        return rule_review_queue(cell_path, status=status)

    @app.post("/rules/{rule_id}/approve")
    async def approve_rule_route(rule_id: str, request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.distill.rules import approve_rule_proposal
            return JSONResponse(content={"status": "ok", "event": approve_rule_proposal(body["cell_path"], rule_id, reviewer_id=body.get("reviewer", "operator"), rationale=body.get("rationale", "approved"))})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/rules/{rule_id}/reject")
    async def reject_rule_route(rule_id: str, request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.distill.rules import reject_rule_proposal
            return JSONResponse(content={"status": "ok", "event": reject_rule_proposal(body["cell_path"], rule_id, reviewer_id=body.get("reviewer", "operator"), rationale=body.get("rationale", "rejected"))})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/cells/{cell_id}/export")
    async def export_cell_route(cell_id: str, request: Request, root: str = ".") -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.federation import export_cell
            cell = body.get("cell_path") or str(_resolve_cell(root, cell_id))
            return JSONResponse(content=export_cell(cell, body["output_path"]))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/cells/{cell_id}/import")
    async def import_cell_route(cell_id: str, request: Request, root: str = ".") -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.federation import import_package
            cell = body.get("cell_path") or str(_resolve_cell(root, cell_id))
            return JSONResponse(content=import_package(cell, body["package_path"]))
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.get("/imports/pending")
    async def imports_pending(cell_path: str) -> Dict[str, Any]:
        from shyftr.console_api import import_review_queue
        return import_review_queue(cell_path, status="pending")

    @app.post("/imports/{import_id}/approve")
    async def approve_import_route(import_id: str, request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.federation import approve_import
            return JSONResponse(content={"status": "ok", "event": approve_import(body["cell_path"], import_id, reviewer=body.get("reviewer", "operator"), rationale=body.get("rationale", "approved"))})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    @app.post("/imports/{import_id}/reject")
    async def reject_import_route(import_id: str, request: Request) -> JSONResponse:
        body = await _parse_body(request)
        try:
            from shyftr.federation import reject_import
            return JSONResponse(content={"status": "ok", "event": reject_import(body["cell_path"], import_id, reviewer=body.get("reviewer", "operator"), rationale=body.get("rationale", "rejected"))})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_unversioned_public_path(path: str) -> bool:
    if path.startswith("/v1"):
        return False
    if path in {"/docs", "/redoc", "/openapi.json", "/favicon.ico"}:
        return False
    return not path.startswith(("/docs/", "/redoc/"))


def _register_v1_aliases(app: FastAPI) -> None:
    """Expose the local HTTP API under /v1 while preserving old alpha aliases."""
    try:
        from fastapi.routing import APIRoute
    except Exception:  # pragma: no cover - optional FastAPI internals
        return

    existing_paths = {getattr(route, "path", "") for route in app.routes}
    for route in list(app.routes):
        if not isinstance(route, APIRoute):
            continue
        if route.path.startswith("/v1") or route.path in {"/openapi.json"}:
            continue
        versioned_path = f"/v1{route.path}"
        if versioned_path in existing_paths:
            continue
        app.add_api_route(
            versioned_path,
            route.endpoint,
            methods=list(route.methods or []),
            name=f"v1_{route.name}",
            response_class=route.response_class,
            status_code=route.status_code,
            tags=["v1"],
            include_in_schema=True,
        )
        existing_paths.add(versioned_path)


async def _parse_body(request: Request) -> Dict[str, Any]:
    """Parse request body as JSON, handling edge cases."""
    try:
        return await request.json()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc


def _resolve_cell(root: str, cell_id: str) -> Path:
    base = Path(root).expanduser()
    cell = base / cell_id
    if not (cell / "config" / "cell_manifest.json").exists():
        raise HTTPException(status_code=404, detail=f"Cell not found: {cell_id}")
    return cell


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def run(
    host: str = "127.0.0.1",
    port: int = 8014,
    log_level: str = "info",
) -> None:
    """Start the local HTTP service.

    Args:
        host: Bind address (default: 127.0.0.1 — localhost only).
        port: Bind port (default: 8014).
        log_level: Uvicorn log level (default: info).
    """
    if not service_dependencies_available():
        print(
            "shyftr[service] is not installed. "
            "Run: pip install shyftr[service]",
            file=sys.stderr,
        )
        sys.exit(1)

    app = _get_app()
    uvicorn.run(app, host=host, port=port, log_level=log_level)


def main(argv: Optional[list[str]] = None) -> None:
    """CLI entrypoint for `python -m shyftr.server`."""

    parser = argparse.ArgumentParser(description="Start the optional ShyftR local HTTP service.")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8014, help="bind port (default: 8014)")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=("critical", "error", "warning", "info", "debug", "trace"),
        help="uvicorn log level (default: info)",
    )
    args = parser.parse_args(argv)
    run(host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
