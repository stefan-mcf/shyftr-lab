#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_SUMMARY = REPO_ROOT / "docs" / "status" / "current-state-baseline-summary.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-ablation-report.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-ablation-report.md"


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


def _metric(summary: Mapping[str, Any], key: str) -> float:
    value = summary.get(key, 0.0)
    return round(float(value), 4)


def _measured_row(*, row_id: str, label: str, command: str, summary: Mapping[str, Any], notes: Sequence[str]) -> Dict[str, Any]:
    return {
        "row_id": row_id,
        "label": label,
        "status": "measured",
        "command": command,
        "metrics": {
            "average_useful_memory_inclusion_rate": _metric(summary, "average_useful_memory_inclusion_rate"),
            "average_missing_memory_rate": _metric(summary, "average_missing_memory_rate"),
            "average_resume_state_score": _metric(summary, "average_resume_state_score"),
            "average_harmful_memory_inclusion_rate": _metric(summary, "average_harmful_memory_inclusion_rate"),
            "average_stale_memory_inclusion_rate": _metric(summary, "average_stale_memory_inclusion_rate"),
            "average_ignored_memory_inclusion_rate": _metric(summary, "average_ignored_memory_inclusion_rate"),
            "total_raw_items": int(summary.get("total_raw_items", 0)),
            "fixture_count": int(summary.get("fixture_count", 0)),
        },
        "notes": list(notes),
    }


def _deferred_row(*, row_id: str, label: str, reason: str, command: Optional[str] = None) -> Dict[str, Any]:
    return {
        "row_id": row_id,
        "label": label,
        "status": "deferred",
        "command": command,
        "metrics": {},
        "notes": [reason],
    }


def build_report(summary: Mapping[str, Any]) -> Dict[str, Any]:
    from shyftr.frontier import RETRIEVAL_MODES

    mode_summaries = dict(summary.get("mode_summaries") or {})
    rows = [
        _deferred_row(
            row_id="no_memory_baseline",
            label="No memory baseline",
            reason="No canonical repo-local no-memory evaluation path exists in the current Phase 8 track; defer until a deterministic no-memory harness is added.",
        ),
        _measured_row(
            row_id="durable_memory_only",
            label="Durable memory only",
            command="python scripts/current_state_baseline.py --mode durable",
            summary=mode_summaries.get("durable", {}),
            notes=["Measured from the current-state baseline durable mode summary."],
        ),
        _measured_row(
            row_id="durable_plus_continuity",
            label="Durable memory + continuity",
            command="python scripts/current_state_baseline.py --mode carry",
            summary=mode_summaries.get("carry", {}),
            notes=["Measured from the current-state baseline carry mode summary."],
        ),
        _measured_row(
            row_id="durable_plus_continuity_plus_live_context",
            label="Durable memory + continuity + live context",
            command="python scripts/current_state_baseline.py --mode live",
            summary=mode_summaries.get("live", {}),
            notes=["Measured from the current-state baseline live mode summary."],
        ),
        {
            "row_id": "frontier_foundations_snapshot",
            "label": "Current frontier foundations snapshot",
            "status": "measured_foundations",
            "command": "PYTHONPATH=.:src python -m shyftr.cli eval-bundle --cell-root /tmp/shyftr-phase8-eval --cell-id eval-cell --output-dir docs/status/phase-8-evaluation-bundle",
            "metrics": {
                "retrieval_mode_count": len(RETRIEVAL_MODES),
                "retrieval_modes": sorted(RETRIEVAL_MODES.keys()),
            },
            "notes": [
                "This row inventories currently implemented frontier foundations and review surfaces.",
                "It is not an external benchmark row and does not imply an unqualified frontier-readiness claim.",
            ],
        },
        _deferred_row(
            row_id="long_context_only_baseline",
            label="Long-context-only baseline",
            reason="Stretch row deferred: no stable repo-local long-context-only comparison harness is implemented in the current track.",
        ),
        _deferred_row(
            row_id="vanilla_rag_baseline",
            label="Vanilla RAG baseline",
            reason="Stretch row deferred: no stable repo-local vanilla RAG comparison harness is implemented in the current track.",
        ),
    ]

    measured_rows = [row for row in rows if row["status"].startswith("measured")]
    deferred_rows = [row for row in rows if row["status"] == "deferred"]

    return {
        "schema_version": "shyftr-phase8-ablation-report/v1",
        "generated_at": _now(),
        "baseline_summary_path": str(DEFAULT_BASELINE_SUMMARY),
        "source_summary_schema": summary.get("output_schema_version"),
        "rows": rows,
        "measured_row_ids": [row["row_id"] for row in measured_rows],
        "deferred_row_ids": [row["row_id"] for row in deferred_rows],
        "claim_boundaries": [
            "Measured rows are repo-local and synthetic-first.",
            "Deferred rows are documented explicitly instead of being implied or guessed.",
            "Proxy metrics remain deterministic local evidence rather than external task-success claims.",
        ],
        "next_research_backlog": [
            "Add a deterministic no-memory comparison path if a canonical harness is approved.",
            "Add stretch rows only when long-context-only and vanilla RAG routes are reproducible and repo-local.",
            "Keep external benchmark adapters out of scope unless explicitly approved later.",
        ],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Phase 8 (Evaluation Track) ablation report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- baseline summary: `{report['baseline_summary_path']}`",
        f"- source summary schema: `{report.get('source_summary_schema')}`",
        "",
        "## Row table",
        "",
        "| Row | Status | Useful inclusion | Missing rate | Resume score | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["rows"]:
        metrics = row.get("metrics", {})
        useful = metrics.get("average_useful_memory_inclusion_rate", "-")
        missing = metrics.get("average_missing_memory_rate", "-")
        resume = metrics.get("average_resume_state_score", "-")
        note = " ".join(row.get("notes", []))
        lines.append(f"| {row['label']} | {row['status']} | {useful} | {missing} | {resume} | {note} |")

    lines.extend(
        [
            "",
            "## Claim boundaries",
            "",
            *[f"- {item}" for item in report["claim_boundaries"]],
            "",
            "## Next research backlog",
            "",
            *[f"- {item}" for item in report["next_research_backlog"]],
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Phase 8 (Evaluation Track) ablation report from current-state baseline summaries.")
    parser.add_argument("--summary-json", default=str(DEFAULT_BASELINE_SUMMARY), help="path to the current-state baseline summary JSON")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="path for the ablation report JSON")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="path for the ablation report markdown")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    summary_path = Path(args.summary_json).resolve()
    output_json = Path(args.output_json).resolve()
    output_md = Path(args.output_md).resolve()

    summary = _read_json(summary_path)
    report = build_report(summary)
    report["baseline_summary_path"] = str(summary_path)

    _write_json(output_json, report)
    _write_text(output_md, render_markdown(report))
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
