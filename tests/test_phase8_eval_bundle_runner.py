from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import shyftr.evaluation_bundle as evaluation_bundle
from shyftr.evaluation_bundle import build_bundle
from shyftr.layout import init_cell


def _run_bundle(tmp_path: Path, *, extra_args: list[str] | None = None) -> tuple[dict, Path]:
    out_dir = tmp_path / "bundle_out"
    args = [
        sys.executable,
        "scripts/evaluation_bundle.py",
        "--cell-root",
        str(tmp_path),
        "--cell-id",
        "eval-cell",
        "--output-dir",
        str(out_dir),
    ]
    if extra_args:
        args.extend(extra_args)
    proc = subprocess.run(
        args,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": ".:src"},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    bundle_path = out_dir / "evaluation-bundle.json"
    assert bundle_path.exists()
    return json.loads(bundle_path.read_text(encoding="utf-8")), out_dir


def test_phase8_bundle_runner_emits_canonical_top_level_keys(tmp_path: Path) -> None:
    bundle, _out = _run_bundle(tmp_path)
    assert set(bundle) == {
        "schema_version",
        "generated_at",
        "git_sha",
        "python",
        "commands",
        "cell",
        "baseline",
        "metrics_summary",
        "hygiene_report",
        "audit_summary",
        "frontier_snapshot",
        "episode_contract_coverage",
        "claims_allowed",
        "claims_not_allowed",
        "paths",
    }


def test_phase8_bundle_runner_includes_baseline_contract_reference_and_payload(tmp_path: Path) -> None:
    bundle, _out = _run_bundle(tmp_path)
    baseline = bundle["baseline"]
    assert set(baseline) == {"summary_path", "summary"}
    assert baseline["summary_path"].endswith("docs/status/current-state-baseline-summary.json")
    assert isinstance(baseline["summary"], dict)
    assert "output_schema_version" in baseline["summary"]


def test_phase8_bundle_runner_includes_metrics_hygiene_audit_payloads(tmp_path: Path) -> None:
    bundle, _out = _run_bundle(tmp_path)
    assert set(bundle["metrics_summary"]) == {"retrieval_quality", "effectiveness", "cell_health"}
    assert "audit_findings" in bundle["hygiene_report"]
    assert set(bundle["audit_summary"]) == {"spark_count", "counts", "review_state_counts", "findings"}


def test_phase8_bundle_runner_includes_frontier_snapshot_and_manifest(tmp_path: Path) -> None:
    bundle, _out = _run_bundle(tmp_path)
    snap = bundle["frontier_snapshot"]
    assert snap["schema_version"].startswith("shyftr-frontier-snapshot/")
    assert "retrieval_modes" in snap

    assert isinstance(bundle["claims_allowed"], list)
    assert isinstance(bundle["claims_not_allowed"], list)
    assert any("local-first evaluation bundle" in item for item in bundle["claims_allowed"])
    assert any("frontier-ready" in item for item in bundle["claims_not_allowed"])


def test_phase8_bundle_runner_writes_only_under_output_dir(tmp_path: Path) -> None:
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    bundle, out_dir = _run_bundle(tmp_path)
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}

    created = sorted(after - before)
    # Allowed writes are inside output dir and the temp cell dir under tmp_path.
    assert created, "expected files to be created"
    for rel in created:
        assert rel.parts[0] in {"bundle_out", "eval-cell"}

    # And the bundle should self-report its output path under paths.
    assert bundle["paths"]["bundle_json"].endswith("evaluation-bundle.json")


def test_phase8_bundle_runner_does_not_rewrite_existing_cell_manifest(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "eval-cell", cell_type="user")
    manifest = cell / "config" / "cell_manifest.json"
    original = '{"cell_id":"eval-cell","cell_type":"user","owner":"operator"}\n'
    manifest.write_text(original, encoding="utf-8")

    _run_bundle(tmp_path)

    assert manifest.read_text(encoding="utf-8") == original


def test_phase8_bundle_runner_without_repo_does_not_fabricate_site_packages_baseline_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cell = init_cell(tmp_path, "wheel-cell", cell_type="user")
    monkeypatch.setattr(evaluation_bundle, "_repo_root", lambda: None)
    monkeypatch.setattr(evaluation_bundle, "_project_root", lambda: evaluation_bundle._package_dir())

    bundle = build_bundle(cell, output_dir=tmp_path / "bundle_out", manifest_commands=[])

    assert bundle["git_sha"] == "unknown"
    assert bundle["baseline"]["summary_path"] == ""
    assert bundle["baseline"]["summary"] == {}


def test_phase8_bundle_runner_without_repo_refuses_output_outside_cell_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluation_bundle, "_repo_root", lambda: None)
    monkeypatch.setattr(evaluation_bundle, "_project_root", lambda: evaluation_bundle._package_dir())

    with pytest.raises(SystemExit, match="output-dir must be within"):
        evaluation_bundle._require_output_dir_within_project_or_cell_root(
            tmp_path.parent / "escape",
            cell_root=tmp_path,
        )


def test_phase8_bundle_runner_refuses_to_write_outside_repo_or_output(tmp_path: Path) -> None:
    out_dir = tmp_path / ".." / "escape"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/evaluation_bundle.py",
            "--cell-root",
            str(tmp_path),
            "--cell-id",
            "eval-cell",
            "--output-dir",
            str(out_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": ".:src"},
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "output-dir must be within" in (proc.stdout + proc.stderr)
