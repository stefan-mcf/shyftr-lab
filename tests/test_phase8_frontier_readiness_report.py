from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _generate_dependencies(tmp_path: Path) -> tuple[Path, Path, Path]:
    ablation_json = tmp_path / "ablation.json"
    ablation_md = tmp_path / "ablation.md"
    latency_json = tmp_path / "latency.json"
    latency_md = tmp_path / "latency.md"
    cell_root = tmp_path / "cell-root"
    bundle_dir = cell_root / "bundle"

    env = {**os.environ, "PYTHONPATH": ".:src"}

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/evaluation_bundle.py",
            "--cell-root",
            str(cell_root),
            "--cell-id",
            "eval-cell",
            "--output-dir",
            str(bundle_dir),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/phase8_ablation_report.py",
            "--output-json",
            str(ablation_json),
            "--output-md",
            str(ablation_md),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/phase8_latency_contract.py",
            "--iterations",
            "2",
            "--output-json",
            str(latency_json),
            "--output-md",
            str(latency_md),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    return bundle_dir / "evaluation-bundle.json", ablation_json, latency_json


def _run_report(tmp_path: Path) -> tuple[dict, str]:
    eval_json, ablation_json, latency_json = _generate_dependencies(tmp_path)
    output_json = tmp_path / "frontier.json"
    output_md = tmp_path / "frontier.md"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/phase8_frontier_readiness_report.py",
            "--eval-bundle-json",
            str(eval_json),
            "--ablation-json",
            str(ablation_json),
            "--latency-json",
            str(latency_json),
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


def test_phase8_frontier_readiness_report_records_actual_input_paths(tmp_path: Path) -> None:
    eval_json, ablation_json, latency_json = _generate_dependencies(tmp_path)
    output_json = tmp_path / "frontier.json"
    output_md = tmp_path / "frontier.md"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/phase8_frontier_readiness_report.py",
            "--eval-bundle-json",
            str(eval_json),
            "--ablation-json",
            str(ablation_json),
            "--latency-json",
            str(latency_json),
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
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["inputs"] == {
        "evaluation_bundle": str(eval_json.resolve()),
        "ablation_report": str(ablation_json.resolve()),
        "latency_contract": str(latency_json.resolve()),
    }


def test_phase8_frontier_readiness_report_emits_required_sections(tmp_path: Path) -> None:
    report, _md = _run_report(tmp_path)
    assert report["schema_version"] == "shyftr-phase8-frontier-readiness-report/v1"
    assert set(report) == {
        "schema_version",
        "generated_at",
        "inputs",
        "implemented_surfaces_inventory",
        "ablation_table",
        "proxy_metrics_table",
        "hygiene_and_safety_signals",
        "latency_throughput_notes",
        "limitations",
        "claim_boundaries",
        "next_research_backlog",
    }
    assert report["implemented_surfaces_inventory"]
    assert report["ablation_table"]
    assert report["limitations"]
    assert report["claim_boundaries"]


def test_phase8_frontier_readiness_report_preserves_local_only_boundaries(tmp_path: Path) -> None:
    report, _md = _run_report(tmp_path)
    assert any("local-only" in item for item in report["limitations"])
    assert any("frontier-ready" in item for item in report["claim_boundaries"])
    assert any("context-window expansion" in item for item in report["claim_boundaries"])


def test_phase8_frontier_readiness_report_markdown_contains_named_sections(tmp_path: Path) -> None:
    _report, md = _run_report(tmp_path)
    assert "# Phase 8 (Evaluation Track) frontier-readiness report" in md
    assert "## Implemented surfaces inventory" in md
    assert "## Ablation table" in md
    assert "## Proxy metrics table" in md
    assert "## Hygiene and safety signals" in md
    assert "## Latency and throughput notes" in md
    assert "## Limitations" in md
    assert "## Claim boundaries" in md
    assert "## Next research backlog" in md
