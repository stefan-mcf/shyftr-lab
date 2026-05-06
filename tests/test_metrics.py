from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.metrics import (
    cell_health_metrics,
    confidence_adjustment_from_counts,
    memory_effectiveness_metrics,
    retrieval_quality_metrics,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "core")


def _memory(memory_id: str, *, confidence: float = 0.8) -> dict:
    return {
        "trace_id": memory_id,
        "cell_id": "core",
        "statement": f"{memory_id} lesson",
        "source_fragment_ids": [],
        "status": "approved",
        "confidence": confidence,
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
    }


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "shyftr.cli", *args],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_memory_effectiveness_counts_retrieval_success_failure_and_miss(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _memory("mem-useful"))
    append_jsonl(cell / "traces" / "approved.jsonl", _memory("mem-missed"))
    append_jsonl(
        cell / "ledger" / "retrieval_logs.jsonl",
        {
            "retrieval_id": "rl-1",
            "loadout_id": "lo-1",
            "selected_ids": ["mem-useful", "mem-missed"],
            "candidate_ids": ["mem-useful", "mem-missed"],
            "score_traces": {},
            "query": "demo",
            "generated_at": "2026-05-06T00:00:00+00:00",
        },
    )
    append_jsonl(
        cell / "ledger" / "outcomes.jsonl",
        {
            "outcome_id": "oc-1",
            "cell_id": "core",
            "loadout_id": "lo-1",
            "task_id": "task-1",
            "verdict": "partial",
            "trace_ids": ["mem-useful"],
            "pack_miss_details": [{"charge_id": "mem-missed", "miss_type": "not_actionable"}],
            "metadata": {
                "useful_trace_ids": ["mem-useful"],
                "harmful_trace_ids": [],
            },
        },
    )

    metrics = memory_effectiveness_metrics(cell)
    by_id = {row["memory_id"]: row for row in metrics["memories"]}

    assert by_id["mem-useful"]["retrieval_count"] == 1
    assert by_id["mem-useful"]["successful_reuse_count"] == 1
    assert by_id["mem-useful"]["confidence_adjustment"] == 0.05
    assert by_id["mem-missed"]["failed_reuse_count"] == 1
    assert by_id["mem-missed"]["pack_miss_count"] == 1
    assert by_id["mem-missed"]["confidence_adjustment"] == -0.1


def test_retrieval_quality_uses_feedback_derived_proxy_metrics(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _memory("mem-a"))
    append_jsonl(cell / "traces" / "approved.jsonl", _memory("mem-b"))
    append_jsonl(
        cell / "ledger" / "retrieval_logs.jsonl",
        {"retrieval_id": "rl-1", "loadout_id": "lo-1", "selected_ids": ["mem-a", "mem-b"]},
    )
    append_jsonl(
        cell / "ledger" / "outcomes.jsonl",
        {
            "outcome_id": "oc-1",
            "cell_id": "core",
            "loadout_id": "lo-1",
            "task_id": "task-1",
            "verdict": "partial",
            "pack_miss_details": [{"charge_id": "mem-b", "miss_type": "not_relevant"}],
            "metadata": {"useful_trace_ids": ["mem-a"], "harmful_trace_ids": []},
        },
    )

    quality = retrieval_quality_metrics(cell)

    assert quality["selected_memory_count"] == 2
    assert quality["useful_feedback_count"] == 1
    assert quality["pack_miss_count"] == 1
    assert quality["precision_proxy"] == 0.5
    assert quality["recall_proxy"] == 0.5
    assert quality["f1_proxy"] == 0.5


def test_retrieval_quality_counts_top_level_outcome_ids_once(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _memory("mem-a"))
    append_jsonl(
        cell / "ledger" / "retrieval_logs.jsonl",
        {"retrieval_id": "rl-1", "loadout_id": "lo-1", "selected_ids": ["mem-a"]},
    )
    append_jsonl(
        cell / "ledger" / "outcomes.jsonl",
        {
            "outcome_id": "oc-1",
            "cell_id": "core",
            "loadout_id": "lo-1",
            "task_id": "task-1",
            "verdict": "success",
            "useful_trace_ids": ["mem-a"],
            "metadata": {"useful_trace_ids": ["mem-a"]},
        },
    )

    quality = retrieval_quality_metrics(cell)

    assert quality["selected_memory_count"] == 1
    assert quality["useful_feedback_count"] == 1
    assert quality["precision_proxy"] == 1.0


def test_cell_health_combines_confidence_quality_and_decay(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _memory("mem-a", confidence=0.9))
    append_jsonl(cell / "ledger" / "retrieval_logs.jsonl", {"retrieval_id": "rl-1", "loadout_id": "lo-1", "selected_ids": ["mem-a"]})
    append_jsonl(
        cell / "ledger" / "outcomes.jsonl",
        {
            "outcome_id": "oc-1",
            "cell_id": "core",
            "loadout_id": "lo-1",
            "task_id": "task-1",
            "verdict": "success",
            "metadata": {"useful_trace_ids": ["mem-a"], "harmful_trace_ids": []},
        },
    )

    health = cell_health_metrics(cell)

    assert health["memory_count"] == 1
    assert health["average_confidence"] == 0.9
    assert 0.0 < health["health_score"] <= 1.0
    assert health["posture"] == "local release metric; review-gated and append-only"


def test_metrics_and_decay_cli_commands_return_json(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    append_jsonl(cell / "traces" / "approved.jsonl", _memory("mem-a"))

    metrics_result = _cli("metrics", str(cell))
    assert metrics_result.returncode == 0, metrics_result.stderr
    metrics_payload = json.loads(metrics_result.stdout)
    assert "retrieval_quality" in metrics_payload
    assert metrics_payload["effectiveness"]["memory_count"] == 1

    decay_result = _cli("decay", str(cell))
    assert decay_result.returncode == 0, decay_result.stderr
    decay_payload = json.loads(decay_result.stdout)
    assert "proposal_summary" in decay_payload
    assert "scoring_summary" in decay_payload


def test_confidence_adjustment_is_bounded() -> None:
    assert confidence_adjustment_from_counts(100, 0) == 1.0
    assert confidence_adjustment_from_counts(0, 100) == -1.0
