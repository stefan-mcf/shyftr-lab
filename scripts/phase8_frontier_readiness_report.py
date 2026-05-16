#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_BUNDLE = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-bundle" / "evaluation-bundle.json"
DEFAULT_ABLATION_JSON = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-ablation-report.json"
DEFAULT_LATENCY_JSON = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-latency-contract.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-frontier-readiness-report.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-frontier-readiness-report.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _implemented_surfaces(eval_bundle: Mapping[str, Any]) -> List[Dict[str, Any]]:
    snap = dict(eval_bundle.get("frontier_snapshot") or {})
    return [
        {"surface": "evaluation_bundle", "status": "measured", "evidence": str(eval_bundle.get("paths", {}).get("bundle_json", DEFAULT_EVAL_BUNDLE))},
        {"surface": "proxy_metrics", "status": "measured", "evidence": "metrics_summary.retrieval_quality / effectiveness / cell_health"},
        {"surface": "hygiene_report", "status": "measured", "evidence": "hygiene_report.audit_findings"},
        {"surface": "audit_summary", "status": "measured", "evidence": "audit_summary.findings"},
        {"surface": "frontier_foundations", "status": "inventory", "evidence": ", ".join(sorted((snap.get("retrieval_modes") or {}).keys()))},
    ]


def build_report(
    eval_bundle: Mapping[str, Any],
    ablation: Mapping[str, Any],
    latency: Mapping[str, Any],
    *,
    eval_bundle_json: Path = DEFAULT_EVAL_BUNDLE,
    ablation_json: Path = DEFAULT_ABLATION_JSON,
    latency_json: Path = DEFAULT_LATENCY_JSON,
) -> Dict[str, Any]:
    metrics_summary = dict(eval_bundle.get("metrics_summary") or {})
    hygiene = dict(eval_bundle.get("hygiene_report") or {})
    audit = dict(eval_bundle.get("audit_summary") or {})

    return {
        "schema_version": "shyftr-phase8-frontier-readiness-report/v1",
        "generated_at": _now(),
        "inputs": {
            "evaluation_bundle": str(eval_bundle_json),
            "ablation_report": str(ablation_json),
            "latency_contract": str(latency_json),
        },
        "implemented_surfaces_inventory": _implemented_surfaces(eval_bundle),
        "ablation_table": list(ablation.get("rows") or []),
        "proxy_metrics_table": {
            "retrieval_quality": metrics_summary.get("retrieval_quality", {}),
            "effectiveness": {
                "memory_count": metrics_summary.get("effectiveness", {}).get("memory_count", 0),
                "retrieval_log_count": metrics_summary.get("effectiveness", {}).get("retrieval_log_count", 0),
                "feedback_count": metrics_summary.get("effectiveness", {}).get("feedback_count", 0),
            },
            "cell_health": metrics_summary.get("cell_health", {}),
        },
        "hygiene_and_safety_signals": {
            "hygiene": hygiene,
            "audit": audit,
        },
        "latency_throughput_notes": latency,
        "limitations": [
            "Measured evidence is synthetic-first and local-only.",
            "Proxy metrics are not direct task-success or external benchmark proof.",
            "Deferred rows remain unimplemented comparison paths rather than implied wins.",
            "Machine-specific timing should be treated as informational rather than universal truth.",
        ],
        "claim_boundaries": [
            "Implemented surfaces are measurable and reviewable locally.",
            "The report does not justify hosted, production, or unqualified frontier-ready claims.",
            "The report does not claim context-window expansion or benchmark superiority.",
        ],
        "next_research_backlog": [
            *list(ablation.get("next_research_backlog") or []),
            "Add synthetic fixture expansion for continuity/resume, harmful-memory survival, and stale/duplicate hygiene if Phase 8 continues.",
        ],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Phase 8 (Evaluation Track) frontier-readiness report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        "",
        "## Implemented surfaces inventory",
        "",
    ]
    for item in report["implemented_surfaces_inventory"]:
        lines.append(f"- {item['surface']}: {item['status']} ({item['evidence']})")

    lines.extend([
        "",
        "## Ablation table",
        "",
        "| Row | Status | Notes |",
        "| --- | --- | --- |",
    ])
    for row in report["ablation_table"]:
        lines.append(f"| {row['label']} | {row['status']} | {' '.join(row.get('notes', []))} |")

    lines.extend([
        "",
        "## Proxy metrics table",
        "",
        f"- retrieval_quality: `{json.dumps(report['proxy_metrics_table']['retrieval_quality'], sort_keys=True)}`",
        f"- effectiveness: `{json.dumps(report['proxy_metrics_table']['effectiveness'], sort_keys=True)}`",
        f"- cell_health: `{json.dumps(report['proxy_metrics_table']['cell_health'], sort_keys=True)}`",
        "",
        "## Hygiene and safety signals",
        "",
        f"- hygiene: `{json.dumps(report['hygiene_and_safety_signals']['hygiene'], sort_keys=True)}`",
        f"- audit: `{json.dumps(report['hygiene_and_safety_signals']['audit'], sort_keys=True)}`",
        "",
        "## Latency and throughput notes",
        "",
        f"- latency_contract: `{json.dumps(report['latency_throughput_notes']['metrics'], sort_keys=True)}`",
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
        "## Claim boundaries",
        "",
        *[f"- {item}" for item in report["claim_boundaries"]],
        "",
        "## Next research backlog",
        "",
        *[f"- {item}" for item in report["next_research_backlog"]],
        "",
    ])
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble the Phase 8 frontier-readiness report from measured local artifacts.")
    parser.add_argument("--eval-bundle-json", default=str(DEFAULT_EVAL_BUNDLE), help="path to evaluation bundle JSON")
    parser.add_argument("--ablation-json", default=str(DEFAULT_ABLATION_JSON), help="path to ablation report JSON")
    parser.add_argument("--latency-json", default=str(DEFAULT_LATENCY_JSON), help="path to latency contract JSON")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="path for frontier-readiness report JSON")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="path for frontier-readiness report markdown")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    eval_bundle_path = Path(args.eval_bundle_json).resolve()
    ablation_path = Path(args.ablation_json).resolve()
    latency_path = Path(args.latency_json).resolve()
    eval_bundle = _read_json(eval_bundle_path)
    ablation = _read_json(ablation_path)
    latency = _read_json(latency_path)
    report = build_report(
        eval_bundle,
        ablation,
        latency,
        eval_bundle_json=eval_bundle_path,
        ablation_json=ablation_path,
        latency_json=latency_path,
    )
    _write_json(Path(args.output_json).resolve(), report)
    _write_text(Path(args.output_md).resolve(), render_markdown(report))
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
