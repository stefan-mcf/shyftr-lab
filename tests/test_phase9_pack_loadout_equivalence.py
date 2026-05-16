from __future__ import annotations

import json
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl


def _seed_cell(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "core")
    manifest = json.loads((cell / "config" / "cell_manifest.json").read_text(encoding="utf-8"))
    cell_id = manifest["cell_id"]

    # Doctrine/rules are always included and deterministic.
    append_jsonl(
        cell / "doctrine" / "approved.jsonl",
        {
            "rule_id": "rule-1",
            "cell_id": cell_id,
            "statement": "Always write focused tests before refactors.",
            "scope": "repo",
            "review_status": "approved",
            "tags": ["process"],
            "confidence_summary": {"max_score": 1.0},
        },
    )

    # One approved trace that should be selected for queries containing "backoff".
    append_jsonl(
        cell / "traces" / "approved.jsonl",
        {
            "trace_id": "mem-1",
            "cell_id": cell_id,
            "statement": "Retry API requests with bounded exponential backoff.",
            "status": "approved",
            "sensitivity": "public",
            "source_fragment_ids": ["frag-1"],
            "confidence": 0.9,
        },
    )

    return cell


def test_pack_and_loadout_entrypoints_are_equivalent_for_same_input(tmp_path: Path) -> None:
    """Pack is canonical, but loadout entrypoints must remain equivalent wrappers."""

    cell = _seed_cell(tmp_path)

    from shyftr.pack import LoadoutTaskInput as PackTaskInput, assemble_pack
    from shyftr.loadout import LoadoutTaskInput as LoadoutTaskInput, assemble_loadout

    pack_task = PackTaskInput(cell_path=str(cell), query="backoff", task_id="task-1", dry_run=True)
    loadout_task = LoadoutTaskInput(cell_path=str(cell), query="backoff", task_id="task-1", dry_run=True)

    pack_result = assemble_pack(pack_task)
    loadout_result = assemble_loadout(loadout_task)

    # to_dict() is the public-safe contract representation.
    pack_dict = pack_result.to_dict()
    loadout_dict = loadout_result.to_dict()

    # IDs and timestamps are generated per-call; align them for equivalence comparison.
    loadout_dict["loadout_id"] = pack_dict["loadout_id"]
    loadout_dict["logged_at"] = pack_dict.get("logged_at")
    loadout_dict["generated_at"] = pack_dict.get("generated_at")
    if "pack_id" in loadout_dict:
        loadout_dict["pack_id"] = pack_dict.get("pack_id")
    if "retrieval_log" in loadout_dict and "retrieval_log" in pack_dict:
        loadout_dict["retrieval_log"]["retrieval_id"] = pack_dict["retrieval_log"]["retrieval_id"]
        loadout_dict["retrieval_log"]["pack_id"] = pack_dict["retrieval_log"]["pack_id"]
        loadout_dict["retrieval_log"]["loadout_id"] = pack_dict["retrieval_log"]["loadout_id"]
        loadout_dict["retrieval_log"]["logged_at"] = pack_dict["retrieval_log"].get("logged_at")
        loadout_dict["retrieval_log"]["generated_at"] = pack_dict["retrieval_log"].get("generated_at")

    # Equivalence: same selected items and same structural contract.
    assert loadout_dict == pack_dict


def test_pack_and_loadout_types_are_alias_compatible() -> None:
    from shyftr.pack import LoadoutTaskInput as PackTaskInput
    from shyftr.loadout import LoadoutTaskInput as LoadoutTaskInput

    assert PackTaskInput is LoadoutTaskInput
