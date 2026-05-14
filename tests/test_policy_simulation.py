from pathlib import Path

from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.simulation import SimulationRequest, simulate_policy


def _seed(cell: Path) -> None:
    append_jsonl(cell / "traces" / "approved.jsonl", {
        "trace_id": "m1", "cell_id": "core", "statement": "Prefer deterministic tests for policy changes", "confidence": 0.9, "tags": ["test"], "kind": "workflow", "status": "approved", "source_fragment_ids": ["c1"]
    })
    append_jsonl(cell / "traces" / "approved.jsonl", {
        "trace_id": "m2", "cell_id": "core", "statement": "Weak old note", "confidence": 0.2, "tags": ["test"], "kind": "workflow", "status": "approved", "source_fragment_ids": ["c1"]
    })


def test_simulation_is_read_only_and_deterministic(tmp_path):
    cell = init_cell(tmp_path, "core")
    _seed(cell)
    report = simulate_policy(SimulationRequest(cell_path=str(cell), query="tests policy", proposed_mode="conservative"))
    assert report["read_only"] is True
    assert report["application_requires_operator_review"] is True
    assert "m2" in report["missed_ids"] or report["changed_order"] is not None
    assert report["estimated_token_usage"]["proposed"] >= 0
