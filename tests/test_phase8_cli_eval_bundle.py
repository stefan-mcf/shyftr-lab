from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run the shyftr CLI via python -m."""
    cmd = [sys.executable, "-m", "shyftr.cli", *args]
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}"
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


def test_phase8_eval_bundle_cli_help_includes_subcommand() -> None:
    result = _cli("--help")
    assert result.returncode == 0
    assert "eval-bundle" in result.stdout


def test_phase8_eval_bundle_cli_runs_and_writes_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = _cli(
        "eval-bundle",
        "--cell-root",
        str(tmp_path),
        "--cell-id",
        "eval-cell",
        "--output-dir",
        str(out_dir),
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    bundle_path = out_dir / "evaluation-bundle.json"
    assert bundle_path.exists()

    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert data["schema_version"].startswith("shyftr-eval-bundle/")
    assert data["paths"]["bundle_json"].endswith("evaluation-bundle.json")


def test_phase8_eval_bundle_cli_is_not_cwd_bound(tmp_path: Path) -> None:
    out_dir = tmp_path / "out-cwd"
    repo_tests_dir = Path(__file__).resolve().parent
    result = _cli(
        "eval-bundle",
        "--cell-root",
        str(tmp_path),
        "--cell-id",
        "eval-cell-cwd",
        "--output-dir",
        str(out_dir),
        cwd=str(repo_tests_dir),
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    data = json.loads((out_dir / "evaluation-bundle.json").read_text(encoding="utf-8"))
    assert data["git_sha"] != "unknown"
    assert data["baseline"]["summary_path"].endswith("docs/status/current-state-baseline-summary.json")


def test_phase8_eval_bundle_cli_refuses_escape_output_dir(tmp_path: Path) -> None:
    out_dir = tmp_path / ".." / "escape"
    result = _cli(
        "eval-bundle",
        "--cell-root",
        str(tmp_path),
        "--cell-id",
        "eval-cell",
        "--output-dir",
        str(out_dir),
    )
    assert result.returncode != 0
    assert "output-dir must be within" in (result.stdout + result.stderr)
