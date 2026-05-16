from __future__ import annotations

from shyftr.layout import init_cell
from shyftr.provider.memory import remember, search


def test_provider_accepts_memory_alias_for_trace_tier_and_keeps_return_label(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "Prefer deterministic provider filters.", "preference")

    memory_results = search(cell, "provider filters", trust_tiers=["memory"])
    trace_results = search(cell, "provider filters", trust_tiers=["trace"])

    assert [item.memory_id for item in memory_results] == [remembered.memory_id]
    assert [item.memory_id for item in trace_results] == [remembered.memory_id]
    assert memory_results[0].trust_tier == "memory"
    assert trace_results[0].trust_tier == "memory"


def test_provider_filter_semantics_combine_tier_kind_and_memory_type(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    semantic = remember(cell, "User prefers local-first answers.", "preference")
    procedural = remember(cell, "Run focused tests before refactors.", "workflow")

    assert [
        item.memory_id
        for item in search(
            cell,
            "local-first answers focused tests",
            trust_tiers=["memory"],
            kinds=["preference"],
            memory_types=["semantic"],
        )
    ] == [semantic.memory_id]

    assert [
        item.memory_id
        for item in search(
            cell,
            "focused tests refactors local-first",
            trust_tiers=["trace"],
            kinds=["workflow"],
            memory_types=["procedural"],
        )
    ] == [procedural.memory_id]

    assert search(
        cell,
        "focused tests",
        trust_tiers=["memory"],
        kinds=["workflow"],
        memory_types=["semantic"],
    ) == []
