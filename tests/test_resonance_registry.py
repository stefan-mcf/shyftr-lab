from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.registry import CellRegistryEntry, register_cell
from shyftr.resonance import detect_similar_memories, detect_similar_patterns, scan_registry_resonance
from shyftr.models import Memory, Pattern


def _entry(cell_id: str, path: Path) -> CellRegistryEntry:
    return CellRegistryEntry(
        cell_id=cell_id,
        cell_type="project",
        path=str(path.resolve()),
        owner="operator",
        tags=["demo"],
        domain="synthetic",
        trust_boundary="local",
        registered_at="2026-05-06T00:00:00+00:00",
    )


def _seed_memory(cell: Path, memory_id: str, statement: str) -> None:
    manifest = json.loads((cell / "config" / "cell_manifest.json").read_text(encoding="utf-8"))
    append_jsonl(cell / "traces" / "approved.jsonl", {
        "trace_id": memory_id,
        "cell_id": manifest["cell_id"],
        "statement": statement,
        "source_fragment_ids": [f"frag-{memory_id}"],
        "status": "approved",
        "confidence": 0.8,
        "tags": ["workflow"],
    })


def _seed_pattern(cell: Path, pattern_id: str, summary: str) -> None:
    manifest = json.loads((cell / "config" / "cell_manifest.json").read_text(encoding="utf-8"))
    append_jsonl(cell / "alloys" / "approved.jsonl", {
        "alloy_id": pattern_id,
        "cell_id": manifest["cell_id"],
        "theme": "workflow",
        "summary": summary,
        "source_trace_ids": [f"trace-{pattern_id}"],
        "proposal_status": "approved",
        "confidence": 0.8,
    })


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    alpha = init_cell(tmp_path, "project-alpha")
    beta = init_cell(tmp_path, "project-beta")
    registry = tmp_path / "registry.jsonl"
    register_cell(registry, _entry("project-alpha", alpha))
    register_cell(registry, _entry("project-beta", beta))
    _seed_memory(alpha, "mem-alpha", "retry failed api calls with bounded backoff")
    _seed_memory(beta, "mem-beta", "retry failed api calls with bounded backoff")
    _seed_pattern(alpha, "pat-alpha", "bounded api backoff avoids duplicate work")
    _seed_pattern(beta, "pat-beta", "bounded api backoff avoids duplicate work")
    return registry, alpha, beta


def test_resonance_filters_by_registry_cells_only(tmp_path: Path) -> None:
    registry, _alpha, _beta = _fixture(tmp_path)
    results = scan_registry_resonance(registry, ["project-alpha", "project-beta"], threshold=0.2)
    assert results
    assert {cell for row in results for cell in row["source_cell_ids"]} <= {"project-alpha", "project-beta"}


def test_resonance_provenance_tracks_all_source_cell_ids(tmp_path: Path) -> None:
    registry, _alpha, _beta = _fixture(tmp_path)
    result = scan_registry_resonance(registry, ["project-alpha", "project-beta"], threshold=0.2)[0]
    assert sorted(result["provenance"]["source_cell_ids"]) == ["project-alpha", "project-beta"]
    assert result["proposal_status"] == "advisory"


def test_resonance_requires_cross_cell_by_default(tmp_path: Path) -> None:
    registry, _alpha, _beta = _fixture(tmp_path)
    assert scan_registry_resonance(registry, ["project-alpha"], threshold=0.2) == []


def test_cross_cell_resonance_does_not_mutate_local_memories(tmp_path: Path) -> None:
    registry, alpha, _beta = _fixture(tmp_path)
    before = (alpha / "traces" / "approved.jsonl").read_text(encoding="utf-8")
    scan_registry_resonance(registry, ["project-alpha", "project-beta"], threshold=0.2)
    after = (alpha / "traces" / "approved.jsonl").read_text(encoding="utf-8")
    assert after == before


def test_resonance_score_includes_cell_diversity_factor(tmp_path: Path) -> None:
    registry, _alpha, _beta = _fixture(tmp_path)
    result = scan_registry_resonance(registry, ["project-alpha", "project-beta"], threshold=0.2)[0]
    assert result["score"] > 0.2
    assert len(set(result["source_cell_ids"])) == 2


def test_resonance_with_one_cell_returns_empty_when_cross_cell_required(tmp_path: Path) -> None:
    registry, _alpha, _beta = _fixture(tmp_path)
    assert scan_registry_resonance(registry, ["project-alpha"]) == []


def test_resonance_output_is_deterministic(tmp_path: Path) -> None:
    registry, _alpha, _beta = _fixture(tmp_path)
    first = [(r["source_record_ids"], r["score"]) for r in scan_registry_resonance(registry, ["project-alpha", "project-beta"], threshold=0.2)]
    second = [(r["source_record_ids"], r["score"]) for r in scan_registry_resonance(registry, ["project-alpha", "project-beta"], threshold=0.2)]
    assert first == second


def test_resonance_rejects_nonexistent_cell_ids_in_registry(tmp_path: Path) -> None:
    registry, _alpha, _beta = _fixture(tmp_path)
    with pytest.raises(ValueError, match="Unknown"):
        scan_registry_resonance(registry, ["project-alpha", "missing"])


def test_public_model_resonance_helpers_support_memory_and_pattern() -> None:
    memories = [
        Memory("mem-a", "a", "retry api with backoff", ["cand-a"]),
        Memory("mem-b", "b", "retry api with backoff", ["cand-b"]),
    ]
    patterns = [
        Pattern("pat-a", "a", "api", "retry api with backoff", ["mem-a"]),
        Pattern("pat-b", "b", "api", "retry api with backoff", ["mem-b"]),
    ]
    assert detect_similar_memories(memories, threshold=0.5)
    assert detect_similar_patterns(patterns, threshold=0.5)
