from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def _repo_root() -> Optional[Path]:
    """Return the nearest repository root above the package, if any.

    Source checkouts resolve under ``src/shyftr`` and should return the checkout
    root. Installed wheels normally have no surrounding git repo and therefore
    return ``None`` instead of treating ``site-packages`` as the project root.
    """

    package_dir = _package_dir()
    for candidate in [package_dir, *package_dir.parents]:
        if (candidate / ".git").exists():
            return candidate

    return None


def _project_root() -> Path:
    """Return stable local context without misidentifying site-packages as a repo.

    Source checkouts place this module under ``src/shyftr``; installed wheels
    place it under the import package. For installed wheels, keep context bound
    to the package directory itself rather than its parent ``site-packages``.
    """
    return _repo_root() or _package_dir()


def _baseline_contract_path() -> Optional[Path]:
    repo_root = _repo_root()
    if repo_root is None:
        return None
    return repo_root / "docs" / "status" / "current-state-baseline-summary.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_sha() -> str:
    repo_root = _repo_root()
    if repo_root is None:
        return "unknown"
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        sha = (proc.stdout or "").strip()
        return sha if sha else "unknown"
    except Exception:
        return "unknown"


def _safe_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _require_output_dir_within_project_or_cell_root(output_dir: Path, *, cell_root: Path) -> None:
    output_dir = output_dir.resolve()
    cell_root = cell_root.resolve()
    allowed_roots = [cell_root]
    repo_root = _repo_root()
    if repo_root is not None:
        allowed_roots.append(repo_root)

    if any(_safe_within(output_dir, root) for root in allowed_roots):
        return

    allowed_str = ", ".join(str(r) for r in allowed_roots)
    raise SystemExit(f"output-dir must be within one of: {allowed_str}")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _python_payload() -> Dict[str, Any]:
    return {
        "executable": sys.executable,
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
    }


def _frontier_snapshot(cell_path: Path) -> Dict[str, Any]:
    from shyftr.frontier import RETRIEVAL_MODES

    # Minimal deterministic snapshot for P8-1: surfaces and shape only.
    return {
        "schema_version": "shyftr-frontier-snapshot/v1",
        "cell_path": str(cell_path),
        "retrieval_modes": {k: dict(v) for k, v in sorted(RETRIEVAL_MODES.items())},
        "notes": [
            "frontier snapshot is a foundations/review surface inventory",
            "no frontier-ready claim is implied",
        ],
    }


def build_bundle(cell_path: Path, *, output_dir: Path, manifest_commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    from shyftr.audit import audit_summary
    from shyftr.metrics import metrics_summary
    from shyftr.reports.hygiene import hygiene_report

    baseline_path = _baseline_contract_path()
    baseline_summary: Dict[str, Any] = {}
    if baseline_path is not None and baseline_path.exists():
        baseline_summary = json.loads(baseline_path.read_text(encoding="utf-8"))

    bundle_path = (output_dir / "evaluation-bundle.json").resolve()

    return {
        "schema_version": "shyftr-eval-bundle/v1",
        "generated_at": _now(),
        "git_sha": _git_sha(),
        "python": _python_payload(),
        "commands": manifest_commands,
        "cell": {"cell_path": str(cell_path)},
        "baseline": {
            "summary_path": str(baseline_path) if baseline_path is not None else "",
            "summary": baseline_summary,
        },
        "metrics_summary": metrics_summary(cell_path),
        "hygiene_report": hygiene_report(cell_path),
        "audit_summary": audit_summary(cell_path),
        "frontier_snapshot": _frontier_snapshot(cell_path),
        "claims_allowed": [
            "local-first evaluation bundle",
            "deterministic proxy metrics (local evidence only)",
            "frontier foundations and frontier review surfaces",
        ],
        "claims_not_allowed": [
            "unqualified frontier-ready claims",
            "production-ready claims",
            "hosted or multi-tenant benchmark claims",
        ],
        "paths": {
            "output_dir": str(output_dir.resolve()),
            "bundle_json": str(bundle_path),
        },
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local-first evaluation bundle from existing ShyftR surfaces.")
    parser.add_argument("--cell-root", required=True, help="directory under which to create or locate the evaluation Cell")
    parser.add_argument("--cell-id", required=True, help="cell id to create under --cell-root")
    parser.add_argument("--output-dir", required=True, help="output directory for the evaluation bundle")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    cell_root = Path(args.cell_root).resolve()
    cell_id = str(args.cell_id)
    output_dir = Path(args.output_dir).resolve()

    _require_output_dir_within_project_or_cell_root(output_dir, cell_root=cell_root)

    from shyftr.layout import init_cell

    cell_path = cell_root / cell_id
    if not (cell_path / "config" / "cell_manifest.json").exists():
        cell_path = init_cell(cell_root, cell_id, cell_type="user")
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_root = _repo_root()
    commands = [
        {
            "argv": [sys.executable, "-m", "shyftr.evaluation_bundle", "--cell-root", str(cell_root), "--cell-id", cell_id, "--output-dir", str(output_dir)],
            "cwd": str(repo_root or cell_root),
            "env": {"PYTHONPATH": ".:src"} if repo_root is not None else {},
        }
    ]

    bundle = build_bundle(cell_path, output_dir=output_dir, manifest_commands=commands)
    _write_json(output_dir / "evaluation-bundle.json", bundle)
    print(json.dumps(bundle, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
