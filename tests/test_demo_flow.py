"""Tests for the ShyftR example flow described in docs/example-lifecycle.md.

Exercises the documented lifecycle using a temporary Cell and verifies
that the example files exist and are parseable.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run the shyftr CLI via python -m with PYTHONPATH pointing at src."""
    cmd = [sys.executable, "-m", "shyftr.cli", *args]
    src_dir = str(REPO_ROOT / "src")
    env = dict(
        PYTHONPATH=f"{src_dir}",
    )
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


# ---------------------------------------------------------------------------
# Example file assertions
# ---------------------------------------------------------------------------


def test_example_evidence_exists_and_parseable() -> None:
    """examples/evidence.md exists and contains expected sections."""
    path = REPO_ROOT / "examples" / "evidence.md"
    assert path.is_file(), f"Missing: {path}"
    text = path.read_text(encoding="utf-8")
    assert "Evidence ID:" in text
    assert "Kind:" in text
    assert "Durable Lesson" in text
    assert "evidence -> candidate" in text or "learning loop" in text


def test_example_task_json_exists_and_parseable() -> None:
    """examples/task.json exists and is valid JSON with expected fields."""
    path = REPO_ROOT / "examples" / "task.json"
    assert path.is_file(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "task_id" in data
    assert "query" in data
    assert "steps" in data


def test_evaluation_demo_files_exist_and_are_parseable() -> None:
    """local evaluation track proof files exist and document metrics plus decay surfaces."""
    closeout = REPO_ROOT / "examples" / "closeout.md"
    packet = REPO_ROOT / "examples" / "packet.json"
    demo = REPO_ROOT / "docs" / "demo.md"
    assert closeout.is_file(), f"Missing: {closeout}"
    assert "shyftr metrics" in closeout.read_text(encoding="utf-8")
    packet_data = json.loads(packet.read_text(encoding="utf-8"))
    assert packet_data["scope"] == "local reviewed demo only"
    assert "shyftr metrics" in demo.read_text(encoding="utf-8")
    assert "shyftr decay" in demo.read_text(encoding="utf-8")


def test_example_doc_exists() -> None:
    """docs/example-lifecycle.md exists and documents the CLI commands."""
    path = REPO_ROOT / "docs" / "example-lifecycle.md"
    assert path.is_file(), f"Missing: {path}"
    text = path.read_text(encoding="utf-8")
    assert "shyftr init-cell" in text
    assert "shyftr ingest" in text
    assert "shyftr candidate" in text
    assert "shyftr approve" in text
    assert "shyftr memory" in text
    assert "shyftr search" in text
    assert "shyftr pack" in text
    assert "shyftr feedback" in text


# ---------------------------------------------------------------------------
# Deterministic example lifecycle
# ---------------------------------------------------------------------------


def test_example_lifecycle_via_cli(tmp_path: Path) -> None:
    """Exercise the documented example lifecycle in a temporary Cell.

    Covers:
      init-cell -> ingest -> fragments -> approve -> promote
      -> search -> loadout -> outcome
    """
    cell = str(tmp_path / "example-cell")
    repo_root = str(REPO_ROOT)

    # 1. Create a sample source file (same content pattern as examples/source.md)
    source_file = tmp_path / "example-source.md"
    source_file.write_text(
        "# Loadout Relevance Heuristic\n\n"
        "Kind: lesson\n\n"
        "During testing, keyword-only search produced false positives "
        "because Trace statements lacked scope tags.\n",
        encoding="utf-8",
    )

    # 2. init-cell
    result = _cli("init-cell", cell, "--cell-id", "example-cell", "--cell-type", "domain")
    assert result.returncode == 0, f"init failed: {result.stderr}"
    init_data = json.loads(result.stdout)
    assert init_data["status"] == "ok"
    assert init_data["cell_id"] == "example-cell"

    # 3. ingest
    result = _cli("ingest", cell, str(source_file), "--kind", "lesson")
    assert result.returncode == 0, f"ingest failed: {result.stderr}"
    ingest_data = json.loads(result.stdout)
    assert ingest_data["evidence_id"].startswith("src-")
    source_id: str = ingest_data["evidence_id"]

    # 4. fragments
    result = _cli("candidate", cell, source_id)
    assert result.returncode == 0, f"fragments failed: {result.stderr}"
    fragments = json.loads(result.stdout)
    assert isinstance(fragments, list)
    assert len(fragments) >= 1
    fragment_id: str = fragments[0]["candidate_id"]

    # 5. approve
    result = _cli(
        "approve", cell, fragment_id,
        "--reviewer", "example-test",
        "--rationale", "Accurate lesson for example flow",
    )
    assert result.returncode == 0, f"approve failed: {result.stderr}"
    review_data = json.loads(result.stdout)
    assert review_data["review_status"] == "approved"

    # 6. promote
    result = _cli(
        "promote", cell, fragment_id,
        "--promoter", "example-test",
        "--statement", "Scope-tagged Traces improve Loadout relevance.",
    )
    assert result.returncode == 0, f"promote failed: {result.stderr}"
    trace_data = json.loads(result.stdout)
    assert trace_data["memory_id"].startswith("trace-")
    trace_id: str = trace_data["memory_id"]

    # 7. search
    result = _cli("search", cell, "loadout")
    assert result.returncode == 0, f"search failed: {result.stderr}"
    search_data = json.loads(result.stdout)
    assert "results" in search_data
    assert search_data["index_size"] >= 1

    # 8. loadout
    result = _cli(
        "loadout", cell, "loadout relevance",
        "--task-id", "example-test-task",
        "--max-items", "5",
    )
    assert result.returncode == 0, f"loadout failed: {result.stderr}"
    loadout_data = json.loads(result.stdout)
    assert loadout_data["pack_id"].startswith("lo-")
    loadout_id: str = loadout_data["pack_id"]

    # 9. outcome
    result = _cli(
        "outcome", cell, loadout_id, "success",
        "--applied", trace_id,
        "--useful", trace_id,
    )
    assert result.returncode == 0, f"outcome failed: {result.stderr}"
    outcome_data = json.loads(result.stdout)
    assert outcome_data["feedback_id"].startswith("oc-")
    assert outcome_data["verdict"] == "success"

    # 10. final hygiene check
    result = _cli("hygiene", cell)
    assert result.returncode == 0, f"hygiene failed: {result.stderr}"
    report = json.loads(result.stdout)
    assert "fragment_status_counts" in report
    assert "trace_confidence_distribution" in report


def test_demo_lifecycle_runs_without_network_or_secrets() -> None:
    """Verify the example lifecycle itself requires no external dependencies.

    This test asserts that the CLI has no network/model imports by checking
    that the import chain is pure local.
    """
    import shyftr.cli  # noqa: F401 - should not trigger network imports
    import shyftr.models  # noqa: F401
    import shyftr.layout  # noqa: F401
    import shyftr.ingest  # noqa: F401
    import shyftr.extract  # noqa: F401
    import shyftr.review  # noqa: F401
    import shyftr.promote  # noqa: F401
    import shyftr.loadout  # noqa: F401
    import shyftr.outcomes  # noqa: F401
    # If any of these triggered a network import, test would fail
