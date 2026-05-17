from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.benchmarks.adapters.no_memory import NoMemoryBackendAdapter
from shyftr.benchmarks.adapters.shyftr_backend import ShyftRBackendAdapter
from shyftr.benchmarks.fixture import load_fixture_json, resolve_benchmark_fixture
from shyftr.benchmarks.runner import run_fixture_benchmark


def test_locomo_mini_fixture_json_loads_and_is_public_safe() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path = repo_root / "fixtures" / "benchmarks" / "locomo-mini.fixture.json"

    fixture = load_fixture_json(path)

    assert fixture.dataset_name == "locomo-mini"
    assert fixture.contains_private_data is False
    assert len(fixture.conversations) >= 2
    assert len(fixture.questions) >= 3


def test_locomo_mini_fixture_resolves_by_name() -> None:
    fixture = resolve_benchmark_fixture(fixture_name="locomo-mini")
    assert fixture.dataset_name == "locomo-mini"


def test_locomo_mini_fixture_run_shyftr_beats_no_memory(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (repo_root / "tmp").mkdir(parents=True, exist_ok=True)

    # Load the checked-in fixture, but write report under tmp repo_root.
    fixture = resolve_benchmark_fixture(fixture_name="locomo-mini")

    cell_root = repo_root / "tmp" / "bench_cells" / "locomo-mini"
    out_path = repo_root / "artifacts" / "benchmarks" / "locomo_mini_report.json"

    adapters = [
        ShyftRBackendAdapter(cell_root=cell_root, cell_id="bench-cell", trust_reason="fixture:locomo-mini"),
        NoMemoryBackendAdapter(),
    ]

    run_fixture_benchmark(
        fixture=fixture,
        adapters=adapters,
        run_id="locomo-mini",
        output_path=out_path,
        repo_root=repo_root,
        top_k_values=[5],
        include_retrieval_details=False,
        runner_name="pytest",
        command_argv=["pytest"],
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    by_name = {r["backend_name"]: r for r in payload["backend_results"]}

    assert by_name["shyftr"]["status"] == "ok"
    assert by_name["no-memory"]["status"] == "ok"

    # No-memory should have no relevant retrieval on this fixture.
    assert by_name["no-memory"]["metrics"]["retrieval"]["recall_at_k"] == 0.0

    # ShyftR should retrieve at least one expected item.
    assert by_name["shyftr"]["metrics"]["retrieval"]["recall_at_k"] > by_name["no-memory"]["metrics"]["retrieval"]["recall_at_k"]


def test_fixture_loader_rejects_private_by_default(tmp_path: Path) -> None:
    private_fixture = {
        "schema_version": "shyftr-memory-benchmark-fixture/v0",
        "fixture_id": "private-001",
        "dataset_name": "private",
        "dataset_version": "v0",
        "contains_private_data": True,
        "conversations": [],
        "questions": [],
    }
    p = tmp_path / "private.fixture.json"
    p.write_text(json.dumps(private_fixture), encoding="utf-8")

    with pytest.raises(ValueError):
        _ = load_fixture_json(p)

    # But can be explicitly allowed.
    ok = load_fixture_json(p, allow_private_data=True)
    assert ok.contains_private_data is True
