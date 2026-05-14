from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.layout import init_cell


def _cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "shyftr.cli", *args]
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}"
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)


def test_live_context_cli_capture_checkpoint_and_resume_support_typed_fields(tmp_path: Path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")

    capture = _cli(
        "live-context",
        "capture",
        str(live_cell),
        "Finish typed resume reconstruction.",
        "--runtime-id",
        "runtime",
        "--session-id",
        "session",
        "--task-id",
        "task",
        "--kind",
        "goal",
        "--status",
        "active",
        "--scope",
        "session",
        "--related-entry-id",
        "external-ref-1",
        "--confidence",
        "0.9",
        "--evidence-ref",
        "docs/plan.md",
        "--grounding-ref",
        "tests/test_cli_phase2_live_context.py",
        "--write",
        cwd=str(Path(__file__).parents[1]),
    )
    assert capture.returncode == 0, capture.stderr
    capture_payload = json.loads(capture.stdout)
    assert capture_payload["entry"]["entry_kind"] == "goal"
    assert capture_payload["entry"]["status"] == "active"
    assert capture_payload["entry"]["related_entry_ids"] == ["external-ref-1"]

    checkpoint = _cli(
        "live-context",
        "checkpoint",
        str(live_cell),
        str(continuity_cell),
        "--runtime-id",
        "runtime",
        "--session-id",
        "session",
        "--write",
        cwd=str(Path(__file__).parents[1]),
    )
    assert checkpoint.returncode == 0, checkpoint.stderr
    checkpoint_payload = json.loads(checkpoint.stdout)
    assert checkpoint_payload["checkpoint_id"].startswith("carry-state-checkpoint-")
    assert checkpoint_payload["sections"]["unresolved_goals"][0]["entry_id"] == capture_payload["entry"]["entry_id"]

    resume = _cli(
        "live-context",
        "resume",
        str(continuity_cell),
        "--runtime-id",
        "runtime",
        "--session-id",
        "session",
        cwd=str(Path(__file__).parents[1]),
    )
    assert resume.returncode == 0, resume.stderr
    resume_payload = json.loads(resume.stdout)
    assert resume_payload["sections"]["unresolved_goals"][0]["entry_id"] == capture_payload["entry"]["entry_id"]
    assert resume_payload["validation"]["status"] == "ok"
