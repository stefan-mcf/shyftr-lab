from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from shyftr.benchmarks.adapters.no_memory import NoMemoryBackendAdapter
from shyftr.benchmarks.adapters.shyftr_backend import ShyftRBackendAdapter
from shyftr.benchmarks.fixture import synthetic_mini_fixture
from shyftr.benchmarks.runner import run_fixture_benchmark


def test_p11_2_mem0_oss_missing_dependency_is_reported_as_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (repo_root / "tmp").mkdir(parents=True, exist_ok=True)

    fixture = synthetic_mini_fixture()
    cell_root = repo_root / "tmp" / "bench_cells" / "run-003"
    out_path = repo_root / "artifacts" / "benchmarks" / "report.json"

    # Importing the adapter itself must not require mem0 installed. Force the
    # missing-dependency path so this test is deterministic on machines that do
    # have mem0 available.
    mem0_backend = importlib.import_module("shyftr.benchmarks.adapters.mem0_backend")
    from shyftr.benchmarks.adapters.mem0_backend import Mem0OSSBackendAdapter

    original_find_spec = mem0_backend.importlib.util.find_spec
    monkeypatch.setattr(
        mem0_backend.importlib.util,
        "find_spec",
        lambda name: None if name == "mem0" else original_find_spec(name),
    )

    adapters = [
        ShyftRBackendAdapter(cell_root=cell_root, cell_id="bench-cell"),
        Mem0OSSBackendAdapter(),
        NoMemoryBackendAdapter(),
    ]

    report = run_fixture_benchmark(
        fixture=fixture,
        adapters=adapters,
        run_id="run-003",
        output_path=out_path,
        repo_root=repo_root,
        top_k_values=[5],
        include_retrieval_details=False,
        runner_name="pytest",
        command_argv=["pytest"],
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    by_name = {r["backend_name"]: r for r in payload["backend_results"]}

    assert "mem0-oss" in by_name
    assert by_name["mem0-oss"]["status"] == "skipped"
    assert isinstance(by_name["mem0-oss"]["status_reason"], str)
    assert by_name["mem0-oss"]["status_reason"]

    # ensure report object matches payload and we didn't fail the run
    assert any(r.backend_name == "mem0-oss" and r.status == "skipped" for r in report.backend_results)


def test_p11_1_fixture_safe_harness_writes_report_under_artifacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (repo_root / "tmp").mkdir(parents=True, exist_ok=True)

    fixture = synthetic_mini_fixture()

    # Ensure the ShyftR adapter writes only inside tmp_path (fixture-safe).
    cell_root = repo_root / "tmp" / "bench_cells" / "run-001"

    adapters = [
        ShyftRBackendAdapter(cell_root=cell_root, cell_id="bench-cell"),
        NoMemoryBackendAdapter(),
    ]

    out_path = repo_root / "artifacts" / "benchmarks" / "report.json"

    report = run_fixture_benchmark(
        fixture=fixture,
        adapters=adapters,
        run_id="run-001",
        output_path=out_path,
        repo_root=repo_root,
        top_k_values=[5],
        include_retrieval_details=True,
        runner_name="pytest",
        command_argv=["pytest"],
    )

    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "shyftr-memory-benchmark-report/v0"
    assert payload["run_id"] == "run-001"
    assert payload["dataset"]["contains_private_data"] is False
    assert len(payload["backend_results"]) == 2

    by_name = {r["backend_name"]: r for r in payload["backend_results"]}
    assert "shyftr" in by_name
    assert "no-memory" in by_name

    assert by_name["shyftr"]["status"] == "ok"
    assert by_name["no-memory"]["status"] == "ok"
    assert by_name["shyftr"]["metrics"]["retrieval"]["recall_at_k"] > by_name["no-memory"]["metrics"]["retrieval"]["recall_at_k"]
    assert by_name["shyftr"]["control_audit"]["provenance_coverage"] == 1.0

    # Harness object should match payload round-trip.
    assert report.schema_version == payload["schema_version"]


def test_p11_1_safe_write_rejects_paths_outside_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (repo_root / "reports").mkdir(parents=True, exist_ok=True)
    (repo_root / "tmp").mkdir(parents=True, exist_ok=True)

    fixture = synthetic_mini_fixture()
    cell_root = repo_root / "tmp" / "bench_cells" / "run-002"
    adapters = [NoMemoryBackendAdapter()]

    with pytest.raises(ValueError):
        run_fixture_benchmark(
            fixture=fixture,
            adapters=adapters,
            run_id="run-002",
            output_path=tmp_path / "outside.json",
            repo_root=repo_root,
            top_k_values=[3],
            include_retrieval_details=False,
            runner_name="pytest",
            command_argv=["pytest"],
        )
