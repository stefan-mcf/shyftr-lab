from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from shyftr.layout import init_cell
from shyftr.retrieval.embeddings import DeterministicEmbeddingProvider
from shyftr.retrieval.lancedb_adapter import LanceDBVectorIndex, lancedb_available


def _append_charge(cell: Path, *, trace_id: str, statement: str) -> None:
    approved = cell / "traces" / "approved.jsonl"
    approved.parent.mkdir(parents=True, exist_ok=True)
    with approved.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "trace_id": trace_id,
            "cell_id": "lancedb-cell",
            "statement": statement,
            "source_fragment_ids": [f"frag-{trace_id}"],
            "rationale": "stable charge",
            "status": "approved",
            "confidence": 0.82,
            "tags": ["grid", "lancedb"],
            "kind": "lesson",
        }, sort_keys=True) + "\n")


def _make_cell(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "lancedb-cell")
    _append_charge(cell, trace_id="charge-1", statement="LanceDB is optional Grid acceleration")
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


def test_grid_cli_smoke_compares_default_backend(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)

    smoke = _cli("grid", "smoke", "--cell", str(cell), "--query", "Grid acceleration")

    assert smoke.returncode == 0, smoke.stderr
    payload = json.loads(smoke.stdout)
    assert payload["status"] == "ok"
    assert payload["grid"]["backend"] == "in-memory"
    assert payload["grid"]["result_count"] >= 1
    assert payload["grid"]["canonical_truth"] == "cell_ledgers"


def test_lancedb_adapter_imports_without_optional_dependency(tmp_path: Path) -> None:
    index = LanceDBVectorIndex(tmp_path / "grid" / "lancedb")

    status = index.status()

    assert status["backend"] == "lancedb"
    assert status["metadata"]["backend"] == "lancedb"
    assert status["canonical_truth"] == "cell_ledgers"
    if not lancedb_available():
        assert status["available"] is False
        assert status["stale"] is True
        assert "unavailable" in status["stale_reasons"]


def test_lancedb_missing_dependency_has_actionable_rebuild_error(tmp_path: Path) -> None:
    if lancedb_available():
        pytest.skip("missing-dependency behavior only applies without LanceDB installed")
    cell = _make_cell(tmp_path)
    index = LanceDBVectorIndex(cell / "grid" / "lancedb")

    with pytest.raises(RuntimeError, match="optional LanceDB Grid adapter"):
        index.rebuild(cell, DeterministicEmbeddingProvider(dim=16))


def test_cli_accepts_lancedb_backend_without_default_dependency(tmp_path: Path) -> None:
    if lancedb_available():
        pytest.skip("missing-dependency CLI behavior only applies without LanceDB installed")
    cell = _make_cell(tmp_path)

    result = _cli("grid", "rebuild", "--cell", str(cell), "--backend", "lancedb")

    assert result.returncode != 0
    assert "optional LanceDB Grid adapter" in result.stderr


def test_lancedb_adapter_rebuild_and_query_with_installed_backend_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tables: dict[str, dict[str, "FakeTable"]] = {}

    class FakeSearch:
        def __init__(self, rows: list[dict[str, object]]) -> None:
            self._rows = rows
            self._limit = len(rows)

        def limit(self, top_k: int) -> "FakeSearch":
            self._limit = top_k
            return self

        def to_list(self) -> list[dict[str, object]]:
            return [dict(row, _distance=0.0) for row in self._rows[: self._limit]]

    class FakeTable:
        def __init__(self, rows: list[dict[str, object]]) -> None:
            self.rows = list(rows)

        def add(self, rows: list[dict[str, object]]) -> None:
            self.rows.extend(rows)

        def search(self, vector: list[float]) -> FakeSearch:
            return FakeSearch(self.rows)

        def count_rows(self) -> int:
            return len(self.rows)

    class FakeDB:
        def __init__(self, path: str) -> None:
            self.path = path
            tables.setdefault(path, {})

        def open_table(self, name: str) -> FakeTable:
            if name not in tables[self.path]:
                raise KeyError(name)
            return tables[self.path][name]

        def create_table(self, name: str, data: list[dict[str, object]], mode: str = "overwrite") -> FakeTable:
            table = FakeTable(data)
            tables[self.path][name] = table
            return table

        def drop_table(self, name: str, ignore_missing: bool = False) -> None:
            if name in tables[self.path]:
                del tables[self.path][name]
            elif not ignore_missing:
                raise KeyError(name)

    class FakeLanceDB:
        @staticmethod
        def connect(path: str) -> FakeDB:
            return FakeDB(path)

    monkeypatch.setitem(sys.modules, "lancedb", FakeLanceDB)
    cell = _make_cell(tmp_path)
    provider = DeterministicEmbeddingProvider(dim=16)
    index = LanceDBVectorIndex(cell / "grid" / "lancedb", embedding_model="deterministic-test", embedding_version="v1")

    count = index.rebuild(cell, provider)
    results = index.query(provider.embed("optional Grid acceleration"), top_k=1)

    assert count == 1
    assert index.size() == 1
    assert index.export_metadata()["backend"] == "lancedb"
    assert index.export_metadata()["embedding_dimension"] == 16
    assert index.export_metadata()["charge_count"] == 1
    assert results[0][0] == "charge-1"
    assert results[0][2]["statement"] == "LanceDB is optional Grid acceleration"


def test_pyproject_declares_lancedb_as_optional_extra() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")

    assert "lancedb" in text
    assert "dependencies = []" in text
