from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.retrieval.embeddings import DeterministicEmbeddingProvider
from shyftr.retrieval.vector import InMemoryVectorIndex, rebuild_vector_index


def _append_charge(cell: Path, *, trace_id: str, statement: str, confidence: float = 0.8) -> None:
    approved = cell / "traces" / "approved.jsonl"
    approved.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "trace_id": trace_id,
        "cell_id": "grid-cell",
        "statement": statement,
        "source_fragment_ids": [f"frag-{trace_id}"],
        "rationale": "stable charge",
        "status": "approved",
        "confidence": confidence,
        "tags": ["grid"],
        "kind": "lesson",
    }
    with approved.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _make_cell(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "grid-cell")
    _append_charge(cell, trace_id="charge-1", statement="Rebuild the Grid from Cell ledgers")
    _append_charge(cell, trace_id="charge-2", statement="Treat indexes as acceleration only")
    return cell


def _cli(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "shyftr.cli", *map(str, args)],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_vector_index_rebuild_records_exportable_grid_metadata(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    provider = DeterministicEmbeddingProvider(dim=16)
    index = InMemoryVectorIndex(
        index_id="grid-test",
        backend="in-memory",
        embedding_model="deterministic-test",
        embedding_version="v1",
    )

    count = index.rebuild(cell, provider)

    assert count == 2
    metadata = index.export_metadata()
    assert metadata["index_id"] == "grid-test"
    assert metadata["cell_id"] == "grid-cell"
    assert metadata["backend"] == "in-memory"
    assert metadata["embedding_model"] == "deterministic-test"
    assert metadata["embedding_dimension"] == 16
    assert metadata["embedding_version"] == "v1"
    assert metadata["charge_count"] == 2
    assert metadata["created_at"]
    assert metadata["ledger_offsets"]["traces/approved.jsonl"] > 0
    assert len(metadata["ledger_hashes"]["traces/approved.jsonl"]) == 64
    assert metadata["canonical_truth"] == "cell_ledgers"


def test_grid_status_detects_stale_ledger_and_embedding_changes(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    provider = DeterministicEmbeddingProvider(dim=16)
    index = InMemoryVectorIndex(
        index_id="grid-test",
        embedding_model="deterministic-test",
        embedding_version="v1",
    )
    index.rebuild(cell, provider)

    assert index.status(cell, provider)["stale"] is False

    _append_charge(cell, trace_id="charge-3", statement="A new Charge changes the ledger offset")
    ledger_status = index.status(cell, provider)
    assert ledger_status["stale"] is True
    assert "ledger_offsets" in ledger_status["stale_reasons"]

    fresh_index = InMemoryVectorIndex(
        index_id="grid-test",
        embedding_model="deterministic-test",
        embedding_version="v1",
    )
    fresh_index.rebuild(cell, provider)
    changed_provider = DeterministicEmbeddingProvider(dim=32)
    embedding_status = fresh_index.status(cell, changed_provider)
    assert embedding_status["stale"] is True
    assert embedding_status["stale_reasons"] == ["embedding_dimension"]


def test_grid_status_detects_ledger_hash_change_without_created_at_noise(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    provider = DeterministicEmbeddingProvider(dim=16)
    index = InMemoryVectorIndex(
        index_id="grid-test",
        embedding_model="deterministic-test",
        embedding_version="v1",
    )
    index.rebuild(cell, provider)

    metadata = index.export_metadata()
    metadata["created_at"] = "2099-01-01T00:00:00+00:00"
    metadata["ledger_hashes"]["traces/approved.jsonl"] = "0" * 64
    index._metadata = metadata

    status = index.status(cell, provider)
    assert status["stale"] is True
    assert "ledger_hashes" in status["stale_reasons"]
    assert "created_at" not in status["stale_reasons"]


def test_grid_cli_rebuild_and_status_are_disk_backed(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)

    rebuild = _cli("grid", "rebuild", "--cell", str(cell))
    assert rebuild.returncode == 0, rebuild.stderr
    rebuild_payload = json.loads(rebuild.stdout)
    assert rebuild_payload["status"] == "ok"
    assert rebuild_payload["grid"]["charge_count"] == 2
    assert rebuild_payload["grid"]["backend"] == "in-memory"

    metadata_path = cell / "indexes" / "grid_metadata.json"
    assert metadata_path.exists()

    status = _cli("grid", "status", "--cell", str(cell))
    assert status.returncode == 0, status.stderr
    status_payload = json.loads(status.stdout)
    assert status_payload["status"] == "ok"
    assert status_payload["grid"]["stale"] is False
    assert status_payload["grid"]["metadata"]["charge_count"] == 2

    _append_charge(cell, trace_id="charge-3", statement="New ledger row makes the Grid stale")
    stale = _cli("grid", "status", "--cell", str(cell))
    assert stale.returncode == 0, stale.stderr
    stale_payload = json.loads(stale.stdout)
    assert stale_payload["grid"]["stale"] is True
    assert "ledger_offsets" in stale_payload["grid"]["stale_reasons"]
