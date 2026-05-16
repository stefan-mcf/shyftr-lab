from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_ablation(tmp_path: Path) -> tuple[dict, str]:
    output_json = tmp_path / "phase8-ablation.json"
    output_md = tmp_path / "phase8-ablation.md"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/phase8_ablation_report.py",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": ".:src"},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert output_json.exists()
    assert output_md.exists()
    return json.loads(output_json.read_text(encoding="utf-8")), output_md.read_text(encoding="utf-8")


def test_phase8_ablation_report_emits_expected_rows_and_ids(tmp_path: Path) -> None:
    report, _md = _run_ablation(tmp_path)
    assert report["schema_version"] == "shyftr-phase8-ablation-report/v1"
    assert len(report["rows"]) == 7
    assert report["measured_row_ids"] == [
        "durable_memory_only",
        "durable_plus_continuity",
        "durable_plus_continuity_plus_live_context",
        "frontier_foundations_snapshot",
    ]
    assert report["deferred_row_ids"] == [
        "no_memory_baseline",
        "long_context_only_baseline",
        "vanilla_rag_baseline",
    ]


def test_phase8_ablation_report_marks_deferred_and_measured_rows_honestly(tmp_path: Path) -> None:
    report, _md = _run_ablation(tmp_path)
    rows = {row["row_id"]: row for row in report["rows"]}

    assert rows["no_memory_baseline"]["status"] == "deferred"
    assert "No canonical repo-local no-memory evaluation path" in rows["no_memory_baseline"]["notes"][0]

    measured = rows["durable_memory_only"]
    assert measured["status"] == "measured"
    assert measured["command"] == "python scripts/current_state_baseline.py --mode durable"
    assert measured["metrics"]["fixture_count"] >= 1

    foundations = rows["frontier_foundations_snapshot"]
    assert foundations["status"] == "measured_foundations"
    assert foundations["metrics"]["retrieval_mode_count"] >= 1
    assert sorted(foundations["metrics"]["retrieval_modes"])


def test_phase8_ablation_report_markdown_contains_claim_boundaries_and_table(tmp_path: Path) -> None:
    report, md = _run_ablation(tmp_path)
    assert report["claim_boundaries"]
    assert report["next_research_backlog"]
    assert "# Phase 8 (Evaluation Track) ablation report" in md
    assert "## Row table" in md
    assert "## Claim boundaries" in md
    assert "## Next research backlog" in md
    assert "No memory baseline" in md
