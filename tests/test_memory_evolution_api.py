from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.server import _get_app


def _seed(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "evo-cell")
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-1", "cell_id": "evo-cell", "statement": "Run alpha gate before tester outreach.", "source_fragment_ids": ["cand-1"], "kind": "workflow", "status": "approved"})
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-2", "cell_id": "evo-cell", "statement": "Run alpha gate before tester outreach.", "source_fragment_ids": ["cand-2"], "kind": "workflow", "status": "approved"})
    return cell


def test_evolution_http_scan_list_simulate_review(tmp_path: Path) -> None:
    cell = _seed(tmp_path)
    client = TestClient(_get_app())

    scan = client.post("/evolution/scan", json={"cell_path": str(cell), "write_proposals": True})
    assert scan.status_code == 200
    proposal_id = scan.json()["proposals"][0]["proposal_id"]

    listed = client.get("/evolution", params={"cell_path": str(cell)})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    sim = client.post(f"/evolution/{proposal_id}/simulate", json={"cell_path": str(cell), "append_report": True})
    assert sim.status_code == 200
    assert sim.json()["read_only"] is True

    review = client.post(f"/evolution/{proposal_id}/review", json={"cell_path": str(cell), "decision": "defer", "rationale": "needs operator review"})
    assert review.status_code == 200
    assert review.json()["event"]["decision"] == "defer"


def test_console_frontier_includes_evolution_dry_run(tmp_path: Path) -> None:
    cell = _seed(tmp_path)
    client = TestClient(_get_app())
    frontier = client.get("/frontier", params={"cell_path": str(cell)})
    assert frontier.status_code == 200
    evolution = frontier.json()["evolution"]
    assert evolution["dry_run_scan"]["review_gated"] is True
    assert evolution["dry_run_scan"]["auto_apply"] is False
