from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from shyftr.confidence import adjust_confidence
from shyftr.layout import init_cell
from shyftr.profile import build_profile, write_profile_projections
from shyftr.provider.memory import MemoryProvider, profile, remember


def _cli(*args: str) -> subprocess.CompletedProcess:
    import os

    cmd = [sys.executable, "-m", "shyftr.cli", *args]
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}"
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def test_build_profile_creates_rebuildable_structured_markdown_and_compact_projection(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    pref = remember(cell, "User prefers precise ShyftR vocabulary.", "preference", metadata={"tags": ["style"]})
    workflow = remember(cell, "Run pytest before pushing Python changes.", "workflow")

    projection = build_profile(cell, max_tokens=22)

    assert projection.projection_id.startswith("profile-")
    assert projection.cell_id == "core"
    assert projection.max_tokens == 22
    assert projection.source_charge_ids == [pref.charge_id, workflow.charge_id]
    assert [entry["charge_id"] for entry in projection.profile_json["entries"]] == [pref.charge_id, workflow.charge_id]
    assert projection.profile_json["canonical_truth"] == "cell_ledgers"
    assert projection.profile_json["projection_status"] == "rebuildable"
    assert "User prefers precise ShyftR vocabulary." in projection.markdown
    assert "Run pytest before pushing Python changes." in projection.compact_markdown
    assert projection.index_json["source_charge_ids"] == [pref.charge_id, workflow.charge_id]
    assert projection.index_json["artifacts"] == {
        "json": "summaries/profile.json",
        "markdown": "summaries/profile.md",
        "compact_markdown": "summaries/profile.compact.md",
        "index": "summaries/profile.index.json",
    }


def test_write_profile_projections_overwrites_only_rebuildable_summary_artifacts(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "User wants local-first memory Cells.", "preference")

    paths = write_profile_projections(cell, max_tokens=40)

    assert paths == {
        "json": cell / "summaries" / "profile.json",
        "markdown": cell / "summaries" / "profile.md",
        "compact_markdown": cell / "summaries" / "profile.compact.md",
        "index": cell / "summaries" / "profile.index.json",
    }
    profile_json = json.loads(paths["json"].read_text(encoding="utf-8"))
    index_json = json.loads(paths["index"].read_text(encoding="utf-8"))
    assert profile_json["entries"][0]["charge_id"] == remembered.charge_id
    assert remembered.charge_id in paths["markdown"].read_text(encoding="utf-8")
    assert "local-first memory Cells" in paths["compact_markdown"].read_text(encoding="utf-8")
    assert index_json["source_charge_ids"] == [remembered.charge_id]
    assert list((cell / "traces").glob("*.jsonl"))


def test_profile_builder_collapses_append_only_updates_and_excludes_replaced_charges(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    kept = remember(cell, "Use pytest before pushing Python changes.", "workflow")
    replaced = remember(cell, "User prefers verbose status reports.", "preference")
    replacement = MemoryProvider(cell).replace(
        replaced.charge_id,
        "User prefers concise status reports.",
        reason="user corrected style preference",
        actor="user",
    )
    adjust_confidence(cell, outcome_id="outcome-1", useful_trace_ids=[kept.charge_id], harmful_trace_ids=[], result="success")

    projection = build_profile(cell)

    charge_ids = [entry["charge_id"] for entry in projection.profile_json["entries"]]
    assert charge_ids == [kept.charge_id, replacement.replacement_charge_id]
    assert "verbose status" not in projection.markdown
    confidence_by_id = {entry["charge_id"]: entry["confidence"] for entry in projection.profile_json["entries"]}
    assert confidence_by_id[kept.charge_id] == 0.85


def test_provider_profile_delegates_to_richer_builder_without_writing_artifacts(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "User likes compact profile projections.", "preference")

    projection = profile(cell, max_tokens=30)

    assert remembered.charge_id in projection.markdown
    assert projection.profile_json["entries"][0]["charge_id"] == remembered.charge_id
    assert projection.compact_markdown.startswith("# ShyftR Compact Profile")
    assert not (cell / "summaries" / "profile.md").exists()


def test_profile_cli_writes_projection_artifacts_and_reports_paths(tmp_path):
    cell = init_cell(tmp_path, "core", cell_type="user")
    remembered = remember(cell, "CLI can rebuild compact profiles.", "workflow")

    result = _cli("profile", str(cell), "--max-tokens", "40")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["cell_id"] == "core"
    assert payload["source_charge_ids"] == [remembered.charge_id]
    assert set(payload["paths"]) == {"json", "markdown", "compact_markdown", "index"}
    assert (cell / "summaries" / "profile.json").exists()
    assert "CLI can rebuild compact profiles." in (cell / "summaries" / "profile.compact.md").read_text(encoding="utf-8")
