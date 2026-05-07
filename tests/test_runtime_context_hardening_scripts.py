from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from shyftr.continuity import ContinuityFeedback, record_continuity_feedback
from shyftr.layout import init_cell

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_context_smoke_generates_advisory_flow_without_direct_memory_write(tmp_path: Path) -> None:
    smoke = _load_script("shyftr_runtime_context_smoke.py")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")

    result = smoke.run_smoke(
        memory_cell=memory_cell,
        continuity_cell=continuity_cell,
        live_cell=live_cell,
        runtime_id="synthetic-runtime-test",
        session_id="synthetic-session-test",
        write=True,
    )

    assert result["status"] == "ok"
    assert result["checks"] == {
        "live_pack_generated": True,
        "carry_pack_generated": True,
        "harvest_written_or_dry_run": True,
        "review_gated": True,
        "no_direct_durable_memory_write": True,
        "approved_memory_ledger_unchanged_by_harvest": True,
    }
    assert result["live_pack"]["advisory_only"] is True
    assert result["carry_pack"]["mode"] == "advisory"
    assert result["harvest"]["direct_durable_memory_writes"] == 0
    assert result["after"]["continuity"]["packs"] == result["before"]["continuity"]["packs"] + 1
    assert result["after"]["live_context"]["harvests"] == result["before"]["live_context"]["harvests"] + 1


def test_runtime_context_smoke_dry_run_skips_pack_and_harvest_ledgers(tmp_path: Path) -> None:
    smoke = _load_script("shyftr_runtime_context_smoke.py")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")

    result = smoke.run_smoke(
        memory_cell=memory_cell,
        continuity_cell=continuity_cell,
        live_cell=live_cell,
        runtime_id="synthetic-runtime-test",
        session_id="synthetic-session-test-dry-run",
        write=False,
    )

    assert result["status"] == "ok"
    assert result["write_pack_and_harvest_ledgers"] is False
    assert result["harvest"]["status"] == "dry_run"
    assert result["after"]["continuity"]["packs"] == result["before"]["continuity"]["packs"]
    assert result["after"]["live_context"]["packs"] == result["before"]["live_context"]["packs"]
    assert result["after"]["live_context"]["harvests"] == result["before"]["live_context"]["harvests"]
    assert result["after"]["live_context"]["entries"] == result["before"]["live_context"]["entries"] + 4


def test_context_quality_evaluator_reads_continuity_feedback_ledger(tmp_path: Path) -> None:
    evaluator = _load_script("shyftr_context_quality_evaluator.py")
    smoke = _load_script("shyftr_runtime_context_smoke.py")
    memory_cell = init_cell(tmp_path, "memory", cell_type="memory")
    continuity_cell = init_cell(tmp_path, "continuity", cell_type="continuity")
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")

    smoke.run_smoke(
        memory_cell=memory_cell,
        continuity_cell=continuity_cell,
        live_cell=live_cell,
        runtime_id="synthetic-runtime-test",
        session_id="synthetic-session-test",
        write=True,
    )
    record_continuity_feedback(
        ContinuityFeedback(
            continuity_cell_path=str(continuity_cell),
            runtime_id="synthetic-runtime-test",
            session_id="synthetic-session-test",
            compaction_id="synthetic-compaction-test",
            continuity_pack_id="continuity-pack-test",
            useful_memory_ids=["memory-useful"],
            harmful_memory_ids=[],
            ignored_memory_ids=[],
            result="accepted",
            write=True,
        )
    )

    result = evaluator.evaluate(
        live_cell=live_cell,
        continuity_cell=continuity_cell,
        min_entries=4,
        min_packs=1,
        min_harvests=1,
        min_harvest_proposals=1,
        min_carry_packs=1,
        max_harmful_feedback_rate=0.0,
    )

    assert result["status"] == "ok"
    assert result["checks"]["harmful_feedback_rate_within_limit"] is True
    assert result["metrics"]["carry_feedback_rates"]["useful"] > 0.0
    assert result["metrics"]["carry_feedback_rates"]["harmful"] == 0.0
