from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.server import _get_app


def _seed_cell(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "pilot-cell", cell_type="pilot")
    append_jsonl(cell / "ledger" / "sources.jsonl", {"source_id": "src-1", "cell_id": "pilot-cell", "kind": "task_closeout", "sha256": "abc", "captured_at": "2026-05-06T00:00:00Z"})
    append_jsonl(cell / "ledger" / "fragments.jsonl", {"fragment_id": "frag-1", "source_id": "src-1", "cell_id": "pilot-cell", "kind": "workflow", "text": "Always verify runtime adapters.", "review_status": "pending", "tags": ["pilot"]})
    append_jsonl(cell / "ledger" / "reviews.jsonl", {"review_id": "rev-1", "fragment_id": "frag-1", "review_status": "approved", "review_action": "approve", "reviewer": "test", "rationale": "solid", "reviewed_at": "2026-05-06T00:00:00Z"})
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "trace-1", "cell_id": "pilot-cell", "statement": "Verify adapter smoke tests before replacement pilots.", "source_fragment_ids": ["frag-1"], "kind": "workflow", "status": "approved", "confidence": 0.8, "tags": ["pilot"]})
    append_jsonl(cell / "ledger" / "retrieval_logs.jsonl", {"loadout_id": "loadout-1", "trace_ids": ["trace-1"], "query": "pilot"})
    append_jsonl(cell / "ledger" / "outcomes.jsonl", {"outcome_id": "out-1", "cell_id": "pilot-cell", "loadout_id": "loadout-1", "task_id": "task-1", "result": "success", "applied_trace_ids": ["trace-1"], "useful_trace_ids": ["trace-1"], "harmful_trace_ids": [], "missing_memory": []})
    append_jsonl(cell / "reports" / "runtime_proposals.jsonl", {"proposal_id": "prop-1", "proposal_type": "manual_review", "status": "open"})
    return cell


def test_console_dashboard_metrics_and_csv(tmp_path: Path) -> None:
    _seed_cell(tmp_path)
    client = TestClient(_get_app())

    summary = client.get("/cell/pilot-cell/summary", params={"root": str(tmp_path)})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["counts"]["pulses"] == 1
    assert payload["counts"]["approved_memories"] == 1
    assert payload["counts"]["feedback"] == 1

    memories = client.get("/cell/pilot-cell/memories", params={"root": str(tmp_path), "query": "adapter"})
    assert memories.status_code == 200
    assert memories.json()["total"] == 1
    assert memories.json()["memories"][0]["memory_id"] == "trace-1"

    metrics = client.get("/cell/pilot-cell/metrics", params={"root": str(tmp_path)})
    assert metrics.status_code == 200
    assert metrics.json()["metrics"]["pack_application_rate"] == 1.0
    assert metrics.json()["can_answer_improvement"] is True

    csv_resp = client.get("/cell/pilot-cell/metrics.csv", params={"root": str(tmp_path)})
    assert csv_resp.status_code == 200
    assert "pack_application_rate,1.0" in csv_resp.text


def test_console_review_and_proposal_decision_require_rationale(tmp_path: Path) -> None:
    _seed_cell(tmp_path)
    client = TestClient(_get_app())

    no_rationale = client.post("/cell/pilot-cell/sparks/frag-1/review", params={"root": str(tmp_path)}, json={"action": "reject"})
    assert no_rationale.status_code == 422

    review = client.post(
        "/cell/pilot-cell/sparks/frag-1/review",
        params={"root": str(tmp_path)},
        json={"action": "reject", "rationale": "duplicate"},
    )
    assert review.status_code == 200
    assert review.json()["event"]["review_status"] == "rejected"

    decision = client.post(
        "/cell/pilot-cell/proposals/prop-1/decision",
        params={"root": str(tmp_path)},
        json={"decision": "accept", "rationale": "pilot evidence is sufficient"},
    )
    assert decision.status_code == 200
    assert decision.json()["event"]["decision"] == "accept"

    proposals = client.get("/cell/pilot-cell/proposals", params={"root": str(tmp_path)})
    assert proposals.status_code == 200
    assert proposals.json()["proposals"][0]["status"] == "accepted"

    summary = client.get("/cell/pilot-cell/summary", params={"root": str(tmp_path)})
    assert summary.status_code == 200
    assert summary.json()["counts"]["open_proposals"] == 0

    metrics = client.get("/cell/pilot-cell/metrics", params={"root": str(tmp_path)})
    assert metrics.status_code == 200
    assert metrics.json()["metrics"]["proposal_acceptance_rate"] == 1.0


def test_operator_burden_and_policy_tuning_endpoints(tmp_path: Path) -> None:
    cell = _seed_cell(tmp_path)
    append_jsonl(cell / "ledger" / "diagnostic_logs.jsonl", {"operation": "managed_memory_import", "regulator_decisions": [{"status": "rejected", "reason": "secret"}], "warnings": ["rejected:1"]})
    client = TestClient(_get_app())

    burden = client.get("/cell/pilot-cell/operator-burden", params={"root": str(tmp_path)})
    assert burden.status_code == 200
    assert "review_pressure_score" in burden.json()["operator_burden"]

    tuning = client.get("/cell/pilot-cell/policy-tuning", params={"root": str(tmp_path)})
    assert tuning.status_code == 200
    assert tuning.json()["recommended_fixture_count"] >= 1
