from __future__ import annotations

import json
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.mutations import challenge_charge, effective_state_for_charge, isolation_charge, mark_isolation_candidate, restore_charge


def _append_charge(cell: Path, trace_id: str) -> None:
    row = {
        "trace_id": trace_id,
        "cell_id": "isolation-cell",
        "statement": f"statement for {trace_id}",
        "source_fragment_ids": [f"frag-{trace_id}"],
        "status": "approved",
        "kind": "workflow",
        "confidence": 0.8,
    }
    path = cell / "traces" / "approved.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def test_challenged_warns_but_isolation_candidate_and_isolated_exclude_from_normal_packs(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "isolation-cell")
    for charge_id in ("challenged", "candidate", "isolated"):
        _append_charge(cell, charge_id)

    challenge_charge(cell, "challenged", reason="counter evidence", actor="reviewer")
    mark_isolation_candidate(cell, "candidate", reason="risky", actor="reviewer")
    isolation_charge(cell, "isolated", reason="confirmed risky", actor="reviewer")

    assert effective_state_for_charge(cell, "challenged").include_in_pack is True
    assert effective_state_for_charge(cell, "candidate").include_in_pack is False
    assert effective_state_for_charge(cell, "isolated").include_in_pack is False

    restore_charge(cell, "candidate", reason="review cleared", actor="reviewer")
    restored = effective_state_for_charge(cell, "candidate")
    assert restored.lifecycle_status == "active"
    assert restored.include_in_pack is True
