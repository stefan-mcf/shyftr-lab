from __future__ import annotations

from pathlib import Path

from shyftr.evolution import append_evolution_proposal, propose_forgetting_from_policies, simulate_evolution_proposal
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl


def test_evolution_simulation_is_read_only_and_reports_delta(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-1", "cell_id": "evo-cell", "statement": "Synthetic retention-limited note.", "source_fragment_ids": ["cand-1"], "kind": "preference", "status": "approved", "tags": ["retention_expired"]})
    append_jsonl(cell / "ledger" / "retrieval_logs.jsonl", {"pack_id": "pack-1", "memory_ids": ["mem-1"], "query": "retention"})
    proposal = propose_forgetting_from_policies([{"memory_id": "mem-1", "statement": "Synthetic retention-limited note.", "candidate_ids": ["cand-1"], "tags": ["retention_expired"]}])[0]
    append_evolution_proposal(cell, proposal)
    report = simulate_evolution_proposal(cell, proposal["proposal_id"])
    assert report["read_only"] is True
    assert report["ledger_line_counts_before"] == report["ledger_line_counts_after"]
    assert report["affected_memory_ids"] == ["mem-1"]
    assert report["current_active_memory_count"] == 1
    assert report["proposed_active_memory_count"] == 0
    assert report["projection_delta"]["active_memory_delta"] == -1
    assert report["pack_query_examples"] == ["retention"]
