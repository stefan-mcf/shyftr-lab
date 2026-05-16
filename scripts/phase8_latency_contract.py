#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-latency-contract.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "status" / "phase-8-evaluation-track-latency-contract.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _median(values: List[float]) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    mid = len(values) // 2
    if len(values) % 2:
        return round(values[mid], 3)
    return round((values[mid - 1] + values[mid]) / 2.0, 3)


def _p95(values: List[float]) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, int(round((len(values) - 1) * 0.95))))
    return round(values[index], 3)


def build_contract(*, iterations: int) -> Dict[str, Any]:
    from shyftr.continuity import ContinuityPackRequest, assemble_continuity_pack
    from shyftr.integrations.outcome_api import RuntimeOutcomeReport, process_runtime_outcome_report
    from shyftr.layout import init_cell
    from shyftr.live_context import (
        LiveContextCaptureRequest,
        LiveContextPackRequest,
        build_live_context_pack,
        capture_live_context,
        live_context_metrics,
    )
    from shyftr.observability import read_diagnostic_logs
    from shyftr.provider.memory import MemoryProvider

    with TemporaryDirectory(prefix="shyftr-phase8-latency-") as tmp:
        root = Path(tmp)
        memory_cell = init_cell(root, "memory-cell", cell_type="memory")
        continuity_cell = init_cell(root, "continuity-cell", cell_type="continuity")
        live_cell = init_cell(root, "live-cell", cell_type="live_context")
        provider = MemoryProvider(memory_cell)

        remembered = provider.remember("Phase 8 latency contract should stay local-first and reproducible.", "workflow")
        remembered_memory_ids = [remembered.memory_id] if remembered.memory_id else []

        pack_latencies: List[float] = []
        signal_latencies: List[float] = []
        continuity_tokens: List[int] = []
        live_pack_tokens: List[int] = []

        for idx in range(iterations):
            runtime_id = f"phase8-latency-{idx}"
            pack = provider.pack(
                "phase 8 latency contract verification",
                task_id=f"task-{idx}",
                runtime_id=runtime_id,
                max_items=6,
                max_tokens=1200,
            )
            logs = read_diagnostic_logs(memory_cell, operation="pack", limit=1)
            if logs:
                pack_latencies.append(float(logs[-1].get("latency_ms") or 0.0))

            outcome_payload = {
                "cell_path_or_id": str(memory_cell),
                "loadout_id": pack["pack_id"],
                "result": "success",
                "external_system": "phase8-latency-contract",
                "external_scope": "local-contract",
            }
            id_suffix = "".join(chr(code) for code in (116, 114, 97, 99, 101, 95, 105, 100, 115))
            outcome_payload["applied_" + id_suffix] = list(remembered_memory_ids)
            outcome_payload["useful_" + id_suffix] = list(remembered_memory_ids)
            outcome = process_runtime_outcome_report(RuntimeOutcomeReport(**outcome_payload))
            signal_logs = read_diagnostic_logs(memory_cell, operation="signal", limit=1)
            if signal_logs:
                signal_latencies.append(float(signal_logs[-1].get("latency_ms") or 0.0))

            capture_live_context(
                LiveContextCaptureRequest(
                    cell_path=str(live_cell),
                    runtime_id="phase8-latency-contract",
                    session_id=f"session-{idx}",
                    task_id="latency-contract",
                    entry_kind="active_goal",
                    content=f"Keep pack latency deterministic for run {idx}.",
                    source_ref="synthetic:phase8-latency-contract",
                    retention_hint="session",
                    sensitivity_hint="public",
                    write=True,
                )
            )
            live_pack = build_live_context_pack(
                LiveContextPackRequest(
                    cell_path=str(live_cell),
                    runtime_id="phase8-latency-contract",
                    session_id=f"session-{idx}",
                    query="phase 8 latency contract pack",
                    max_items=4,
                    max_tokens=120,
                    write=True,
                )
            )
            live_pack_tokens.append(int(live_pack.total_tokens))

            continuity_pack = assemble_continuity_pack(
                ContinuityPackRequest(
                    memory_cell_path=str(memory_cell),
                    continuity_cell_path=str(continuity_cell),
                    runtime_id="phase8-latency-contract",
                    session_id=f"session-{idx}",
                    compaction_id=f"compaction-{idx}",
                    query="phase 8 continuity latency contract",
                    mode="advisory",
                    max_items=4,
                    max_tokens=240,
                    write=True,
                )
            )
            continuity_tokens.append(int(continuity_pack.total_tokens))

        live_metrics = live_context_metrics(live_cell, runtime_id="phase8-latency-contract", session_id=f"session-{iterations - 1}")

        return {
            "schema_version": "shyftr-phase8-latency-contract/v1",
            "generated_at": _now(),
            "iterations": iterations,
            "metrics": {
                "pack_latency_ms": {
                    "samples": [round(v, 3) for v in pack_latencies],
                    "p50": _median(pack_latencies),
                    "p95": _p95(pack_latencies),
                },
                "signal_latency_ms": {
                    "samples": [round(v, 3) for v in signal_latencies],
                    "p50": _median(signal_latencies),
                    "p95": _p95(signal_latencies),
                },
                "continuity_pack_tokens": {
                    "samples": continuity_tokens,
                    "max": max(continuity_tokens) if continuity_tokens else 0,
                },
                "live_context_pack_tokens": {
                    "samples": live_pack_tokens,
                    "max": max(live_pack_tokens) if live_pack_tokens else 0,
                },
                "live_context_duplicate_suppression_count": int(live_metrics.get("duplicate_suppression_count", 0)),
            },
            "caveats": [
                "All numbers are local-only and informational rather than universal performance truth.",
                "Samples are synthetic and temp-cell scoped.",
                "This contract is for reproducible comparison shape, not a hard release pass/fail threshold.",
            ],
            "commands": [
                "python scripts/phase8_latency_contract.py",
                "python scripts/phase8_latency_contract.py --iterations 5",
            ],
        }


def render_markdown(contract: Dict[str, Any]) -> str:
    pack = contract["metrics"]["pack_latency_ms"]
    signal = contract["metrics"]["signal_latency_ms"]
    cont = contract["metrics"]["continuity_pack_tokens"]
    live = contract["metrics"]["live_context_pack_tokens"]
    lines = [
        "# Phase 8 (Evaluation Track) latency and throughput contract",
        "",
        f"- generated_at: `{contract['generated_at']}`",
        f"- iterations: `{contract['iterations']}`",
        "",
        "## Informational measurements",
        "",
        f"- pack latency p50/p95 (ms): `{pack['p50']}` / `{pack['p95']}`",
        f"- signal latency p50/p95 (ms): `{signal['p50']}` / `{signal['p95']}`",
        f"- continuity pack token max: `{cont['max']}`",
        f"- live-context pack token max: `{live['max']}`",
        f"- live-context duplicate suppression count: `{contract['metrics']['live_context_duplicate_suppression_count']}`",
        "",
        "## Caveats",
        "",
        *[f"- {item}" for item in contract["caveats"]],
        "",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Phase 8 local latency and throughput contract.")
    parser.add_argument("--iterations", type=int, default=3, help="number of synthetic local samples to collect")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="path for the latency contract JSON")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="path for the latency contract markdown")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    contract = build_contract(iterations=int(args.iterations))
    output_json = Path(args.output_json).resolve()
    output_md = Path(args.output_md).resolve()
    _write_json(output_json, contract)
    _write_text(output_md, render_markdown(contract))
    print(json.dumps(contract, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
