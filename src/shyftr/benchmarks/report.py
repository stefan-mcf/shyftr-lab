from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPORT_SCHEMA_VERSION = "shyftr-memory-benchmark-report/v0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class BackendResult:
    backend_name: str
    status: str
    status_reason: Optional[str] = None
    config_summary: Dict[str, Any] = field(default_factory=dict)
    ingest: Dict[str, Any] = field(default_factory=dict)
    search: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    retrieval_details: Optional[Dict[str, Any]] = None
    cost_latency: Dict[str, Any] = field(default_factory=dict)
    control_audit: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "status": self.status,
            "status_reason": self.status_reason,
            "config_summary": dict(self.config_summary),
            "ingest": dict(self.ingest),
            "search": dict(self.search),
            "metrics": dict(self.metrics),
            "retrieval_details": dict(self.retrieval_details) if self.retrieval_details is not None else None,
            "cost_latency": dict(self.cost_latency),
            "control_audit": dict(self.control_audit),
            "errors": list(self.errors),
        }


@dataclass
class BenchmarkReport:
    schema_version: str
    run_id: str
    generated_at: str
    runner: Dict[str, Any]
    dataset: Dict[str, Any]
    fairness: Dict[str, Any]
    models: Dict[str, Any]
    backend_results: List[BackendResult] = field(default_factory=list)
    aggregate_metrics: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    claims_allowed: List[str] = field(default_factory=list)
    claims_not_allowed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "runner": dict(self.runner),
            "dataset": dict(self.dataset),
            "fairness": dict(self.fairness),
            "models": dict(self.models),
            "backend_results": [r.to_dict() for r in self.backend_results],
            "aggregate_metrics": dict(self.aggregate_metrics),
            "limitations": list(self.limitations),
            "claims_allowed": list(self.claims_allowed),
            "claims_not_allowed": list(self.claims_not_allowed),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent)

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(indent=2) + "\n", encoding="utf-8")


__all__ = ["BenchmarkReport", "BackendResult", "REPORT_SCHEMA_VERSION", "utc_now_iso"]
