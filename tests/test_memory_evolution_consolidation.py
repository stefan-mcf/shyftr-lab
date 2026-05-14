from __future__ import annotations

from pathlib import Path

from shyftr.evolution import propose_memory_consolidation, scan_cell
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl


def test_exact_duplicate_memories_generate_merge_proposal() -> None:
    memories = [
        {"memory_id": "mem-1", "statement": "Run alpha gate before tester outreach.", "candidate_ids": ["cand-1"], "kind": "workflow"},
        {"memory_id": "mem-2", "statement": "Run alpha gate before tester outreach.", "candidate_ids": ["cand-2"], "kind": "workflow"},
    ]
    proposals = propose_memory_consolidation(memories)
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["proposal_type"] == "merge_memories"
    assert proposal["target_ids"] == ["mem-1", "mem-2"]
    assert proposal["projection_delta"]["active_memory_delta"] == -1
    assert proposal["requires_simulation"] is True
    assert proposal["auto_apply"] is False


def test_close_but_distinct_memory_is_high_risk_or_not_proposed() -> None:
    memories = [
        {"memory_id": "mem-1", "statement": "Run alpha gate before tester outreach on public clones.", "candidate_ids": ["cand-1"], "kind": "workflow"},
        {"memory_id": "mem-2", "statement": "Run alpha gate before private migration work on local cells.", "candidate_ids": ["cand-2"], "kind": "constraint"},
    ]
    proposals = propose_memory_consolidation(memories, overlap_threshold=0.35)
    assert proposals == [] or proposals[0]["risk_level"] == "high"


def test_scan_cell_writes_proposals_only_not_memory_ledgers(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "evo-cell")
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-1", "cell_id": "evo-cell", "statement": "Run alpha gate before tester outreach.", "source_fragment_ids": ["cand-1"], "kind": "workflow", "status": "approved"})
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-2", "cell_id": "evo-cell", "statement": "Run alpha gate before tester outreach.", "source_fragment_ids": ["cand-2"], "kind": "workflow", "status": "approved"})
    before = (cell / "traces" / "approved.jsonl").read_text(encoding="utf-8")
    result = scan_cell(cell, write_proposals=True)
    after = (cell / "traces" / "approved.jsonl").read_text(encoding="utf-8")
    assert result["written_count"] == 1
    assert before == after
    assert (cell / "ledger" / "evolution" / "proposals.jsonl").read_text(encoding="utf-8").count("\n") == 1
