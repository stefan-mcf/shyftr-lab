from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl


def _cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "shyftr.cli", *args]
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}"
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)


def _write_runtime(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "runtime"
    root.mkdir()
    (root / "closeout.md").write_text("Runtime note: adapter CLI evidence captured.\n", encoding="utf-8")
    (root / "events.jsonl").write_text(
        json.dumps({"task_id": "task-1", "result": "success", "external_run_id": "run-1"}) + "\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "adapter.json"
    config_path.write_text(
        json.dumps(
            {
                "adapter_id": "cli-adapter",
                "cell_id": "cell-main",
                "external_system": "generic-runtime",
                "external_scope": "cli-test",
                "source_root": str(root),
                "identity_mapping": {"external_run_id": "external_run_id"},
                "inputs": [
                    {"kind": "file", "path": "closeout.md", "source_kind": "closeout"},
                    {
                        "kind": "jsonl",
                        "path": "events.jsonl",
                        "source_kind": "outcome",
                        "identity_mapping": {"external_task_id": "task_id"},
                    },
                ],
                "ingest_options": {"deduplicate": True},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return root, config_path


def test_adapter_help_lists_runtime_integration_commands() -> None:
    result = _cli("adapter", "--help")

    assert result.returncode == 0
    assert "validate" in result.stdout
    assert "discover" in result.stdout
    assert "ingest" in result.stdout
    assert "backfill" in result.stdout


def test_adapter_validate_and_discover_dry_run_emit_json(tmp_path: Path) -> None:
    _, config_path = _write_runtime(tmp_path)

    validate = _cli("adapter", "validate", "--config", str(config_path), "--json")
    assert validate.returncode == 0, validate.stderr
    validate_payload = json.loads(validate.stdout)
    assert validate_payload["status"] == "ok"
    assert validate_payload["config"]["adapter_id"] == "cli-adapter"

    discover = _cli("adapter", "discover", "--config", str(config_path), "--dry-run", "--json")
    assert discover.returncode == 0, discover.stderr
    discover_payload = json.loads(discover.stdout)
    assert discover_payload["status"] == "ok"
    assert discover_payload["dry_run"] is True
    assert discover_payload["discovery_summary"]["total_sources"] == 2
    assert discover_payload["discovery_summary"]["by_kind"] == {"closeout": 1, "outcome": 1}


def test_adapter_ingest_appends_sources_and_is_idempotent(tmp_path: Path) -> None:
    _, config_path = _write_runtime(tmp_path)
    cell = init_cell(tmp_path, "cell-main")

    first = _cli("adapter", "ingest", "--config", str(config_path), "--json")
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)
    assert first_payload["status"] == "ok"
    assert first_payload["sources_ingested"] == 2
    assert first_payload["sources_skipped"] == 0

    second = _cli("adapter", "ingest", "--config", str(config_path), "--json")
    assert second.returncode == 0, second.stderr
    second_payload = json.loads(second.stdout)
    assert second_payload["sources_ingested"] == 0
    assert second_payload["sources_skipped"] == 2

    rows = [record for _, record in read_jsonl(cell / "ledger" / "sources.jsonl")]
    assert len(rows) == 2
    assert all(row["metadata"]["adapter_id"] == "cli-adapter" for row in rows)


def test_adapter_backfill_dry_run_writes_no_sources(tmp_path: Path) -> None:
    _, config_path = _write_runtime(tmp_path)
    cell = init_cell(tmp_path, "cell-main")

    result = _cli("adapter", "backfill", "--config", str(config_path), "--dry-run", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["dry_run"] is True
    assert payload["sources_ingested"] == 0
    assert payload["discovery_summary"]["total_sources"] == 2
    assert list(read_jsonl(cell / "ledger" / "sources.jsonl")) == []
