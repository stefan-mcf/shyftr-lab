from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.integrations.loadout_api import RuntimeLoadoutRequest, process_runtime_loadout_request
from shyftr.layout import init_cell
from shyftr.loadout import LoadoutTaskInput, assemble_loadout
from shyftr.privacy import AccessPolicy, filter_charge_records, is_charge_export_allowed, redact_charge_projection


def _append_charge(cell: Path, trace_id: str, *, sensitivity: str = "internal", user_id: str = "reviewer-1", project_id: str = "shyftr") -> dict:
    row = {
        "trace_id": trace_id,
        "cell_id": "privacy-cell",
        "statement": f"{sensitivity} statement for {trace_id}",
        "source_fragment_ids": [f"frag-{trace_id}"],
        "status": "approved",
        "kind": "workflow",
        "confidence": 0.8,
        "sensitivity": sensitivity,
        "user_id": user_id,
        "project_id": project_id,
        "runtime_id": "runtime-a",
    }
    path = cell / "traces" / "approved.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _make_cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "privacy-cell")


def test_privacy_policy_excludes_sensitive_or_cross_scope_memory_by_default(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    public = _append_charge(cell, "public", sensitivity="public")
    secret = _append_charge(cell, "secret", sensitivity="secret")
    other_project = _append_charge(cell, "other", sensitivity="internal", project_id="other")
    policy = AccessPolicy(runtime_id="runtime-a", user_id="reviewer-1", project_id="shyftr")

    assert is_charge_export_allowed(public, policy, cell_path=cell)[0] is True
    assert is_charge_export_allowed(secret, policy, cell_path=cell)[0] is False
    assert is_charge_export_allowed(other_project, policy, cell_path=cell)[0] is False

    projection = filter_charge_records(cell, [public, secret, other_project], policy)
    assert [row["trace_id"] for row in projection["included"]] == ["public"]
    assert {row["charge_id"] for row in projection["excluded"]} == {"secret", "other"}


def test_default_pack_generation_excludes_secret_and_cross_scope_charges(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    _append_charge(cell, "public", sensitivity="public")
    _append_charge(cell, "secret", sensitivity="secret")
    _append_charge(cell, "other", sensitivity="internal", project_id="other")

    loadout = assemble_loadout(LoadoutTaskInput(
        cell_path=str(cell),
        query="statement",
        task_id="task-privacy",
        max_items=5,
        runtime_id="runtime-a",
        user_id="reviewer-1",
        project_id="shyftr",
    ))

    assert [item.item_id for item in loadout.items] == ["public"]
    assert "secret" in loadout.retrieval_log.suppressed_ids
    assert "other" in loadout.retrieval_log.suppressed_ids


def test_runtime_loadout_api_forwards_identity_policy_to_pack_generation(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    _append_charge(cell, "public", sensitivity="public")
    _append_charge(cell, "secret", sensitivity="secret")

    default_response = process_runtime_loadout_request(RuntimeLoadoutRequest(
        cell_path_or_id=str(cell),
        query="statement",
        external_system="runtime-a",
        external_scope="shyftr",
        user_id="reviewer-1",
        project_id="shyftr",
    ))
    assert default_response.selected_ids == ["public"]

    explicit_response = process_runtime_loadout_request(RuntimeLoadoutRequest(
        cell_path_or_id=str(cell),
        query="statement",
        external_system="runtime-a",
        external_scope="shyftr",
        user_id="reviewer-1",
        project_id="shyftr",
        allowed_sensitivity=["public", "internal", "secret"],
    ))
    assert set(explicit_response.selected_ids) == {"public", "secret"}


def test_pack_cli_accepts_sensitivity_policy_identity_flags(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    _append_charge(cell, "public", sensitivity="public")
    _append_charge(cell, "secret", sensitivity="secret")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([
        sys.executable,
        "-m",
        "shyftr.cli",
        "pack",
        str(cell),
        "statement",
        "--task-id",
        "cli-privacy",
        "--runtime-id",
        "runtime-a",
        "--user-id",
        "reviewer-1",
        "--project-id",
        "shyftr",
        "--allowed-sensitivity",
        "public,internal,secret",
    ], text=True, capture_output=True, env=env, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload["retrieval_log"]["selected_ids"]) == {"public", "secret"}


def test_redaction_projection_hides_sensitive_text_without_destroying_provenance(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    secret = _append_charge(cell, "secret", sensitivity="secret")
    redacted = redact_charge_projection(secret)
    assert redacted["statement"] == "[REDACTED]"
    assert redacted["trace_id"] == secret["trace_id"]
    assert redacted["source_fragment_ids"] == secret["source_fragment_ids"]

    audit_policy = AccessPolicy(runtime_id="runtime-a", user_id="reviewer-1", project_id="shyftr", allowed_sensitivity=("public", "internal"), allow_audit_sensitive=True)
    allowed, warnings = is_charge_export_allowed(secret, audit_policy, cell_path=cell, audit_mode=True)
    assert allowed is True
    assert warnings and "audit only" in warnings[0]
