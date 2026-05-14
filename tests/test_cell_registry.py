from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.layout import init_cell
from shyftr.registry import CellRegistryEntry, discover_initialized_cells, get_cell, list_cells, register_cell, registry_ledger_path, unregister_cell


def _entry(cell_id: str, path: Path, *, tags=None, cell_type="project") -> CellRegistryEntry:
    return CellRegistryEntry(
        cell_id=cell_id,
        cell_type=cell_type,
        path=str(path.resolve()),
        owner="operator",
        tags=list(tags or []),
        domain="synthetic",
        trust_boundary="local",
        registered_at="2026-05-06T00:00:00+00:00",
    )


def test_register_cell_appends_to_registry(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "project-alpha")
    registry = tmp_path / "registry.jsonl"
    registered = register_cell(registry, _entry("project-alpha", cell))
    assert registered.cell_id == "project-alpha"
    assert registry.exists()
    assert registry.read_text(encoding="utf-8").count("\n") == 1


def test_register_cell_without_required_fields_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="trust_boundary"):
        CellRegistryEntry.from_dict({
            "cell_id": "project-alpha",
            "cell_type": "project",
            "path": str(tmp_path.resolve()),
            "owner": "operator",
            "tags": [],
            "domain": "synthetic",
            "registered_at": "2026-05-06T00:00:00+00:00",
        })


def test_register_cell_rejects_duplicate_cell_id(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "project-alpha")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", cell))
    with pytest.raises(ValueError, match="duplicate"):
        register_cell(registry, _entry("project-alpha", cell))


def test_list_cells_returns_all_registered_cells(tmp_path: Path) -> None:
    alpha = init_cell(tmp_path, "project-alpha")
    beta = init_cell(tmp_path, "project-beta")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", alpha))
    register_cell(registry, _entry("project-beta", beta))
    assert [entry.cell_id for entry in list_cells(registry)] == ["project-alpha", "project-beta"]


def test_list_cells_by_type_filters_correctly(tmp_path: Path) -> None:
    alpha = init_cell(tmp_path, "project-alpha", cell_type="project")
    beta = init_cell(tmp_path, "team-beta", cell_type="team")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", alpha, cell_type="project"))
    register_cell(registry, _entry("team-beta", beta, cell_type="team"))
    assert [entry.cell_id for entry in list_cells(registry, cell_type="team")] == ["team-beta"]


def test_list_cells_by_tag_filters_correctly(tmp_path: Path) -> None:
    alpha = init_cell(tmp_path, "project-alpha")
    beta = init_cell(tmp_path, "project-beta")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", alpha, tags=["agent", "api"]))
    register_cell(registry, _entry("project-beta", beta, tags=["agent"]))
    assert [entry.cell_id for entry in list_cells(registry, tags=["api"])] == ["project-alpha"]


def test_list_cells_on_empty_registry_returns_empty_list(tmp_path: Path) -> None:
    assert list_cells(tmp_path / "missing.jsonl") == []


def test_unregister_cell_removes_from_active_projection(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "project-alpha")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", cell))
    unregister_cell(registry, "project-alpha", "operator cleanup")
    assert list_cells(registry) == []


def test_unregister_nonexistent_cell_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown"):
        unregister_cell(tmp_path / "registry.jsonl", "missing", "cleanup")


def test_registry_file_is_append_only_not_overwritten(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "project-alpha")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", cell))
    size_before = registry.stat().st_size
    unregister_cell(registry, "project-alpha", "cleanup")
    assert registry.stat().st_size > size_before
    assert registry.read_text(encoding="utf-8").count("\n") == 2


def test_cell_discovery_returns_initialized_cells_only(tmp_path: Path) -> None:
    init_cell(tmp_path, "project-alpha")
    (tmp_path / "not-a-cell").mkdir()
    discovered = discover_initialized_cells(tmp_path)
    assert [entry.cell_id for entry in discovered] == ["project-alpha"]


def test_no_accidental_cross_cell_leakage_when_cells_not_selected(tmp_path: Path) -> None:
    alpha = init_cell(tmp_path, "project-alpha")
    beta = init_cell(tmp_path, "project-beta")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", alpha))
    register_cell(registry, _entry("project-beta", beta))
    assert get_cell(registry, "project-alpha").cell_id == "project-alpha"
    with pytest.raises(ValueError):
        get_cell(registry, "project-gamma")


def test_cell_registry_persists_across_sessions(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "project-alpha")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", cell))
    assert list_cells(registry)[0].to_dict()["cell_id"] == "project-alpha"


def test_cell_registry_rejects_invalid_cell_id_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="safe path segment"):
        _entry("../escape", tmp_path)


def test_cell_registry_round_trip_to_jsonl(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "project-alpha")
    registry_dir = tmp_path / "registry-cell"
    register_cell(registry_dir, _entry("project-alpha", cell))
    assert registry_ledger_path(registry_dir) == registry_dir / "ledger" / "cell_registry.jsonl"
    row = json.loads(registry_ledger_path(registry_dir).read_text(encoding="utf-8").splitlines()[0])
    assert row["entry"]["cell_id"] == "project-alpha"
