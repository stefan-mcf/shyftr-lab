from __future__ import annotations

import json
from pathlib import Path

from shyftr.distill.rules import approve_rule_proposal, propose_rule_from_resonance
from shyftr.federation import approve_import, export_cell, import_package
from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.loadout import LoadoutTaskInput, assemble_loadout
from shyftr.registry import CellRegistryEntry, register_cell
from shyftr.resonance import scan_registry_resonance


def _entry(cell_id: str, path: Path) -> CellRegistryEntry:
    return CellRegistryEntry(
        cell_id=cell_id,
        cell_type="project",
        path=str(path.resolve()),
        owner="operator",
        tags=["synthetic"],
        domain="demo",
        trust_boundary="local",
        registered_at="2026-05-06T00:00:00+00:00",
    )


def _setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    alpha = init_cell(tmp_path, "project-alpha")
    beta = init_cell(tmp_path, "project-beta")
    for cell, mem_id in ((alpha, "alpha-memory"), (beta, "beta-memory")):
        cell_id = json.loads((cell / "config" / "cell_manifest.json").read_text(encoding="utf-8"))["cell_id"]
        append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": mem_id, "cell_id": cell_id, "statement": "retry api requests with bounded backoff", "source_fragment_ids": [f"frag-{mem_id}"], "status": "approved", "sensitivity": "public"})
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", alpha))
    register_cell(registry, _entry("project-beta", beta))
    return registry, alpha, beta


def test_multi_cell_demo_runs_end_to_end(tmp_path: Path) -> None:
    registry, alpha, beta = _setup(tmp_path)
    results = scan_registry_resonance(registry, ["project-alpha", "project-beta"], threshold=0.25)
    proposal = propose_rule_from_resonance(alpha, results, scope="project-alpha", statement="Use bounded backoff for retryable API calls")
    approve_rule_proposal(alpha, proposal["rule_id"], reviewer_id="operator", rationale="synthetic demo")
    package = tmp_path / "alpha-export.json"
    export_cell(alpha, package)
    import_result = import_package(beta, package)
    approve_import(beta, import_result["imports"][0]["import_id"], reviewer="operator", rationale="synthetic demo")
    pack = assemble_loadout(LoadoutTaskInput(str(alpha), "bounded backoff api", "demo"))
    assert results and proposal["rule_id"] in [item.item_id for item in pack.items]


def test_multi_cell_demo_requires_explicit_cross_cell_scope(tmp_path: Path) -> None:
    registry, _alpha, _beta = _setup(tmp_path)
    assert scan_registry_resonance(registry, ["project-alpha"], threshold=0.25) == []


def test_multi_cell_demo_import_requires_review(tmp_path: Path) -> None:
    _registry, alpha, beta = _setup(tmp_path)
    package = tmp_path / "alpha-export.json"
    export_cell(alpha, package)
    import_package(beta, package)
    assert (beta / "traces" / "approved.jsonl").read_text(encoding="utf-8").count("verified") == 0


def test_multi_cell_demo_pack_excludes_unreviewed_imports(tmp_path: Path) -> None:
    _registry, alpha, beta = _setup(tmp_path)
    package = tmp_path / "alpha-export.json"
    export_cell(alpha, package)
    import_package(beta, package)
    pack = assemble_loadout(LoadoutTaskInput(str(beta), "api backoff", "demo"))
    assert all(item.item_id != "alpha-memory" for item in pack.items)
