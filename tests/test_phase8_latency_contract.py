from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_contract(tmp_path: Path, *, iterations: int = 2) -> tuple[dict, str]:
    output_json = tmp_path / "phase8-latency.json"
    output_md = tmp_path / "phase8-latency.md"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/phase8_latency_contract.py",
            "--iterations",
            str(iterations),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": ".:src"},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert output_json.exists()
    assert output_md.exists()
    return json.loads(output_json.read_text(encoding="utf-8")), output_md.read_text(encoding="utf-8")


def test_phase8_latency_contract_emits_expected_schema_and_metric_keys(tmp_path: Path) -> None:
    contract, _md = _run_contract(tmp_path, iterations=2)
    assert contract["schema_version"] == "shyftr-phase8-latency-contract/v1"
    assert contract["iterations"] == 2
    assert set(contract["metrics"]) == {
        "pack_latency_ms",
        "signal_latency_ms",
        "continuity_pack_tokens",
        "live_context_pack_tokens",
        "live_context_duplicate_suppression_count",
    }


def test_phase8_latency_contract_collects_samples_and_caveats(tmp_path: Path) -> None:
    contract, _md = _run_contract(tmp_path, iterations=2)
    pack = contract["metrics"]["pack_latency_ms"]
    signal = contract["metrics"]["signal_latency_ms"]
    continuity = contract["metrics"]["continuity_pack_tokens"]
    live = contract["metrics"]["live_context_pack_tokens"]

    assert len(pack["samples"]) == 2
    assert len(signal["samples"]) == 0 or len(signal["samples"]) == 2
    assert continuity["max"] >= 0
    assert live["max"] >= 0
    assert contract["caveats"]
    assert any("local-only" in item for item in contract["caveats"])
    assert any("synthetic" in item for item in contract["caveats"])


def test_phase8_latency_contract_markdown_contains_measurements_and_caveats(tmp_path: Path) -> None:
    _contract, md = _run_contract(tmp_path, iterations=2)
    assert "# Phase 8 (Evaluation Track) latency and throughput contract" in md
    assert "## Informational measurements" in md
    assert "## Caveats" in md
    assert "pack latency p50/p95" in md
