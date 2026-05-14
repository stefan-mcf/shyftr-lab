from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from shyftr.backup import backup_cell, restore_cell
from shyftr.layout import init_cell


def _append_charge(cell: Path, trace_id: str, statement: str = "backup me") -> None:
    row = {
        "trace_id": trace_id,
        "cell_id": "durable-cell",
        "statement": statement,
        "source_fragment_ids": [f"frag-{trace_id}"],
        "status": "approved",
        "confidence": 0.8,
        "kind": "workflow",
        "rationale": "fixture",
    }
    for rel in ("traces/approved.jsonl", "charges/approved.jsonl"):
        path = cell / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _make_cell(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "durable-cell")
    _append_charge(cell, "charge-1", "Cell ledgers are canonical truth")
    (cell / "grid" / "transient.bin").write_bytes(b"cache")
    (cell / "grid" / "grid_metadata.json").write_text('{"backend":"test"}\n', encoding="utf-8")
    return cell


def _cli(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run([sys.executable, "-m", "shyftr.cli", *args], text=True, capture_output=True, env=env, check=False)


def test_cell_backup_restore_round_trip_validates_ledgers_and_excludes_transient_grid(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    backup_path = tmp_path / "backup.tar.gz"

    result = backup_cell(cell, backup_path)
    assert result["manifest"]["includes_ledgers"] is True
    assert result["manifest"]["grid_rebuild_required"] is True
    assert any(f["path"] == "traces/approved.jsonl" for f in result["manifest"]["files"])
    assert not any(f["path"] == "grid/transient.bin" for f in result["manifest"]["files"])

    restored = restore_cell(backup_path, tmp_path / "restored-cell")
    assert restored["validation"]["valid"] is True
    assert restored["validation"]["ledger_counts"]["traces/approved.jsonl"] == 1
    assert (tmp_path / "restored-cell" / "config" / "cell_manifest.json").exists()
    assert not (tmp_path / "restored-cell" / "grid" / "transient.bin").exists()


def test_restore_refuses_existing_non_empty_target_without_force(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    backup_path = tmp_path / "backup.tar.gz"
    backup_cell(cell, backup_path)
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        restore_cell(backup_path, target)


def test_backup_restore_cli_round_trip(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    backup_path = tmp_path / "cli-backup.tar.gz"
    backup = _cli("backup", "--cell", str(cell), "--output", str(backup_path))
    assert backup.returncode == 0, backup.stderr
    assert json.loads(backup.stdout)["status"] == "ok"

    restore = _cli("restore", str(backup_path), str(tmp_path / "cli-restored"))
    assert restore.returncode == 0, restore.stderr
    payload = json.loads(restore.stdout)
    assert payload["validation"]["valid"] is True
