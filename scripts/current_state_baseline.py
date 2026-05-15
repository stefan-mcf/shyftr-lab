from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from shyftr.layout import init_cell
from shyftr.provider.memory import remember
from shyftr.continuity import (  # noqa: E402
    ContinuityFeedback,
    ContinuityPackRequest,
    assemble_continuity_pack,
    continuity_status,
)
from shyftr.live_context import (  # noqa: E402
    CarryStateCheckpointRequest,
    LiveContextCaptureRequest,
    LiveContextPackRequest,
    SessionHarvestRequest,
    build_carry_state_checkpoint,
    build_live_context_pack,
    capture_live_context,
    harvest_session,
    live_context_metrics,
    live_context_status,
    reconstruct_resume_state,
)
from shyftr import loadout as loadout_module  # noqa: E402
from shyftr import pack as pack_module  # noqa: E402
from shyftr.integrations.loadout_api import (  # noqa: E402
    RuntimeLoadoutRequest,
    process_runtime_loadout_request,
)

SCHEMA_VERSION = "current-state-baseline.v1"
FIXTURE_DIR = REPO_ROOT / "examples" / "evals" / "current-state-baseline" / "fixtures"
EXPECTED_DIR = REPO_ROOT / "examples" / "evals" / "current-state-baseline" / "expected"
DEFAULT_STATUS_DIR = REPO_ROOT / "docs" / "status"
MODE_ALIASES = {
    "durable": "Mode A: durable-memory-only",
    "carry": "Mode B: durable + carry/continuity",
    "live": "Mode C: durable + carry/continuity + live-context",
    "behavior": "Mode D: current pack/loadout behavior capture and normalization",
}


@dataclass
class SeededFixture:
    fixture: Dict[str, Any]
    memory_cell: Path
    continuity_cell: Path
    live_cell: Path
    memory_by_logical_id: Dict[str, Dict[str, Any]]
    live_entry_by_logical_id: Dict[str, Dict[str, Any]]


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _fixture_paths(selected_fixture: Optional[str]) -> List[Path]:
    paths = sorted(FIXTURE_DIR.glob("*.json"))
    if selected_fixture:
        paths = [path for path in paths if path.stem == selected_fixture or _read_json(path).get("fixture_id") == selected_fixture]
    if not paths:
        raise SystemExit(f"No fixtures matched: {selected_fixture!r}")
    return paths


def _validate_fixture(fixture: Mapping[str, Any]) -> None:
    required = [
        "fixture_id",
        "title",
        "mode_support",
        "task_prompt",
        "durable_memories",
        "continuity_entries",
        "live_context_entries",
        "expected_useful_ids",
        "expected_stale_ids",
        "expected_harmful_ids",
        "expected_ignored_ids",
        "expected_required_ids",
        "expected_resume_state",
        "notes",
    ]
    missing = [key for key in required if key not in fixture]
    if missing:
        raise ValueError(f"fixture {fixture.get('fixture_id', '<unknown>')} missing keys: {missing}")
    if not isinstance(fixture["mode_support"], list) or not fixture["mode_support"]:
        raise ValueError(f"fixture {fixture['fixture_id']} must define non-empty mode_support")
    for key in [
        "expected_useful_ids",
        "expected_stale_ids",
        "expected_harmful_ids",
        "expected_ignored_ids",
        "expected_required_ids",
    ]:
        if not isinstance(fixture[key], list):
            raise ValueError(f"fixture {fixture['fixture_id']} field {key} must be a list")
    logical_ids = {entry["id"] for entry in fixture["durable_memories"]} | {entry["id"] for entry in fixture["live_context_entries"]}
    labeled_ids = set(fixture["expected_useful_ids"]) | set(fixture["expected_stale_ids"]) | set(fixture["expected_harmful_ids"]) | set(fixture["expected_ignored_ids"])
    unknown_labeled = sorted(labeled_ids - logical_ids)
    if unknown_labeled:
        raise ValueError(f"fixture {fixture['fixture_id']} references unknown labeled ids: {unknown_labeled}")
    resume_state = fixture["expected_resume_state"]
    resume_known_ids = set(resume_state.get("excluded_ids", [])) | set(resume_state.get("constraint_ids", [])) | set(resume_state.get("decision_ids", [])) | set(resume_state.get("artifact_ref_ids", [])) | set(resume_state.get("open_question_ids", []))
    unknown_resume = sorted(resume_known_ids - logical_ids)
    if unknown_resume:
        raise ValueError(f"fixture {fixture['fixture_id']} references unknown resume-state ids: {unknown_resume}")
    if not isinstance(resume_state, dict):
        raise ValueError(f"fixture {fixture['fixture_id']} expected_resume_state must be a dict")
    for key in ["required_ids", "excluded_ids", "constraint_ids", "decision_ids", "artifact_ref_ids", "open_question_ids"]:
        if not isinstance(resume_state.get(key, []), list):
            raise ValueError(f"fixture {fixture['fixture_id']} expected_resume_state.{key} must be a list")


def _validate_expected_contract(expected: Mapping[str, Any], fixture_id: str) -> None:
    if expected.get("fixture_id") != fixture_id:
        raise ValueError(f"expected contract fixture_id mismatch for {fixture_id}")
    if not isinstance(expected.get("mode_expectations"), dict):
        raise ValueError(f"expected contract for {fixture_id} must have mode_expectations")


def load_fixtures(selected_fixture: Optional[str] = None) -> List[Dict[str, Any]]:
    fixtures: List[Dict[str, Any]] = []
    for path in _fixture_paths(selected_fixture):
        fixture = _read_json(path)
        _validate_fixture(fixture)
        expected_path = EXPECTED_DIR / path.name
        if expected_path.exists():
            fixture["expected_contract"] = _read_json(expected_path)
            _validate_expected_contract(fixture["expected_contract"], fixture["fixture_id"])
        else:
            fixture["expected_contract"] = {"fixture_id": fixture["fixture_id"], "mode_expectations": {}}
        fixtures.append(fixture)
    return fixtures


def _logical_id_from_statement(seed: SeededFixture, statement: str) -> Optional[str]:
    for logical_id, payload in seed.memory_by_logical_id.items():
        if payload["statement"] == statement:
            return logical_id
    return None


def _logical_id_from_live_content(seed: SeededFixture, content: str) -> Optional[str]:
    for logical_id, payload in seed.live_entry_by_logical_id.items():
        if payload["content"] == content:
            return logical_id
    return None


def _rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def _serialize_resume_counts(surfaced_ids: Sequence[str], resume_state: Mapping[str, Any]) -> Dict[str, Any]:
    surfaced = set(surfaced_ids)
    required = set(resume_state.get("required_ids", []))
    excluded = set(resume_state.get("excluded_ids", []))
    matched_required = len(required & surfaced)
    matched_excluded = len(excluded - surfaced)
    total_checks = len(required) + len(excluded)
    resume_state_score = round((matched_required + matched_excluded) / total_checks, 4) if total_checks else None

    def category_rate(key: str) -> float:
        values = set(resume_state.get(key, []))
        return _rate(len(values & surfaced), len(values))

    return {
        "resume_state_score": resume_state_score,
        "preserved_constraint_rate": category_rate("constraint_ids"),
        "preserved_decision_rate": category_rate("decision_ids"),
        "preserved_artifact_ref_rate": category_rate("artifact_ref_ids"),
        "preserved_open_loop_rate": category_rate("open_question_ids"),
    }


def _score_fixture(
    fixture: Mapping[str, Any],
    mode: str,
    surfaced_ids: Sequence[str],
    *,
    raw_item_count: Optional[int] = None,
    total_tokens: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    surfaced = list(surfaced_ids)
    unique_surfaced = list(dict.fromkeys(surfaced))
    useful = set(fixture["expected_useful_ids"])
    stale = set(fixture["expected_stale_ids"])
    harmful = set(fixture["expected_harmful_ids"])
    ignored = set(fixture["expected_ignored_ids"])
    required = set(fixture["expected_required_ids"])
    all_labeled = useful | stale | harmful | ignored

    matched_useful = len(useful & set(unique_surfaced))
    stale_count = len(stale & set(unique_surfaced))
    harmful_count = len(harmful & set(unique_surfaced))
    ignored_count = len(ignored & set(unique_surfaced))
    missing_required_count = len(required - set(unique_surfaced))
    duplicate_count = max(0, len(surfaced) - len(unique_surfaced))
    redundant_ids = [item for item in unique_surfaced if item not in all_labeled]

    result = {
        "fixture_id": fixture["fixture_id"],
        "mode": mode,
        "surfaced_ids": unique_surfaced,
        "expected_useful_ids": fixture["expected_useful_ids"],
        "expected_required_ids": fixture["expected_required_ids"],
        "matched_useful_count": matched_useful,
        "stale_count": stale_count,
        "harmful_count": harmful_count,
        "ignored_count": ignored_count,
        "missing_required_count": missing_required_count,
        "useful_memory_inclusion_rate": _rate(matched_useful, len(useful)),
        "stale_memory_inclusion_rate": _rate(stale_count, len(stale)),
        "harmful_memory_inclusion_rate": _rate(harmful_count, len(harmful)),
        "ignored_memory_inclusion_rate": _rate(ignored_count, len(ignored)),
        "missing_memory_rate": _rate(missing_required_count, len(required)),
        "duplicate_or_redundant_inclusion_rate": _rate(duplicate_count + len(redundant_ids), max(1, len(unique_surfaced))),
        "duplicate_count": duplicate_count,
        "redundant_ids": redundant_ids,
        "raw_item_count": raw_item_count if raw_item_count is not None else len(unique_surfaced),
        "total_tokens": total_tokens,
        "notes": list(fixture.get("notes", [])),
    }
    result.update(_serialize_resume_counts(unique_surfaced, fixture["expected_resume_state"]))
    if extra:
        result.update(extra)
    return result


def _apply_expected_contract(result: Mapping[str, Any], contract: Mapping[str, Any], mode: str) -> Dict[str, Any]:
    expectations = dict(contract.get("mode_expectations", {}).get(mode, {}))
    evaluation: Dict[str, Any] = {"mode": mode, "checked": {}, "pass": True}
    for key, expected_value in expectations.items():
        actual = result.get(key)
        check_pass = True
        if key.startswith("min_"):
            metric = key[4:]
            actual = result.get(metric)
            check_pass = actual is not None and actual >= expected_value
        elif key.startswith("max_"):
            metric = key[4:]
            actual = result.get(metric)
            check_pass = actual is not None and actual <= expected_value
        else:
            check_pass = actual == expected_value
        evaluation["checked"][key] = {"expected": expected_value, "actual": actual, "pass": check_pass}
        evaluation["pass"] = evaluation["pass"] and check_pass
    return evaluation


def _seed_fixture(fixture: Mapping[str, Any]) -> SeededFixture:
    temp_root = Path(tempfile.mkdtemp(prefix=f"shyftr-baseline-{fixture['fixture_id']}-"))
    memory_cell = init_cell(temp_root, "memory", cell_type="memory")
    continuity_cell = init_cell(temp_root, "continuity", cell_type="continuity")
    live_cell = init_cell(temp_root, "live", cell_type="live_context")

    memory_by_logical_id: Dict[str, Dict[str, Any]] = {}
    for memory in fixture["durable_memories"]:
        result = remember(
            memory_cell,
            memory["statement"],
            memory["kind"],
            metadata={
                "actor": "current-state-baseline",
                "tags": [fixture["fixture_id"], memory["id"], memory.get("kind", "memory")],
                "fixture_memory_id": memory["id"],
            },
            allow_direct_durable_memory=True,
        )
        if result.memory_id is None:
            raise ValueError(f"fixture durable memory did not promote: {fixture['fixture_id']}:{memory['id']}")
        memory_by_logical_id[memory["id"]] = {
            **memory,
            "memory_id": result.memory_id,
            "statement": memory["statement"],
        }

    live_entry_by_logical_id: Dict[str, Dict[str, Any]] = {}
    for entry in fixture["live_context_entries"]:
        capture = capture_live_context(
            LiveContextCaptureRequest(
                cell_path=str(live_cell),
                runtime_id=f"baseline-{fixture['fixture_id']}",
                session_id=f"session-{fixture['fixture_id']}",
                task_id=f"task-{fixture['fixture_id']}",
                entry_kind=entry["entry_kind"],
                content=entry["content"],
                source_ref=entry.get("source_ref", f"synthetic:{fixture['fixture_id']}"),
                retention_hint=entry.get("retention_hint", "session"),
                sensitivity_hint=entry.get("sensitivity_hint", "public"),
                metadata=entry.get("metadata", {}),
                write=True,
            )
        )
        live_entry_by_logical_id[entry["id"]] = {
            **entry,
            "entry_id": capture["entry"]["entry_id"],
            "content": entry["content"],
        }

    return SeededFixture(
        fixture=dict(fixture),
        memory_cell=memory_cell,
        continuity_cell=continuity_cell,
        live_cell=live_cell,
        memory_by_logical_id=memory_by_logical_id,
        live_entry_by_logical_id=live_entry_by_logical_id,
    )


def run_durable_fixture(fixture: Mapping[str, Any]) -> Dict[str, Any]:
    seed = _seed_fixture(fixture)
    loadout = loadout_module.assemble_loadout(
        loadout_module.LoadoutTaskInput(
            cell_path=str(seed.memory_cell),
            query=fixture["task_prompt"],
            task_id=f"durable-{fixture['fixture_id']}",
            max_items=int(fixture.get("mode_config", {}).get("durable", {}).get("max_items", 8)),
            max_tokens=int(fixture.get("mode_config", {}).get("durable", {}).get("max_tokens", 1200)),
            runtime_id="current-state-baseline",
            dry_run=False,
        )
    )
    surfaced_ids = [
        logical_id
        for item in loadout.items
        for logical_id in [ _logical_id_from_statement(seed, item.statement) ]
        if logical_id is not None
    ]
    result = _score_fixture(
        fixture,
        "durable",
        surfaced_ids,
        raw_item_count=len(loadout.items),
        total_tokens=loadout.total_tokens,
        extra={
            "top_level_keys": sorted(loadout.to_dict().keys()),
            "selected_item_roles": [item.loadout_role for item in loadout.items],
            "selected_memory_ids": [item.item_id for item in loadout.items],
        },
    )
    result["expectation_evaluation"] = _apply_expected_contract(result, fixture.get("expected_contract", {}), "durable")
    return result


def run_carry_fixture(fixture: Mapping[str, Any]) -> Dict[str, Any]:
    seed = _seed_fixture(fixture)
    config = fixture.get("mode_config", {}).get("carry", {})
    runtime_id = f"baseline-{fixture['fixture_id']}"
    session_id = f"session-{fixture['fixture_id']}"
    compaction_id = f"carry-{fixture['fixture_id']}"

    pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(seed.memory_cell),
            continuity_cell_path=str(seed.continuity_cell),
            runtime_id=runtime_id,
            session_id=session_id,
            compaction_id=compaction_id,
            query=fixture["task_prompt"],
            trigger="current_state_baseline",
            mode=config.get("mode", "advisory"),
            max_items=int(config.get("max_items", 6)),
            max_tokens=int(config.get("max_tokens", 120)),
            write=True,
        )
    )
    phase2_pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(seed.memory_cell),
            continuity_cell_path=str(seed.continuity_cell),
            live_cell_path=str(seed.live_cell),
            runtime_id=runtime_id,
            session_id=session_id,
            compaction_id=f"{compaction_id}-phase2",
            query=fixture["task_prompt"],
            trigger="current_state_baseline",
            mode=config.get("mode", "advisory"),
            max_items=int(config.get("max_items", 6)),
            max_tokens=int(config.get("max_tokens", 120)),
            write=True,
        )
    )
    feedback_summaries: List[Dict[str, Any]] = []
    for entry in fixture.get("continuity_entries", []):
        feedback = record = ContinuityFeedback(
            continuity_cell_path=str(seed.continuity_cell),
            continuity_pack_id=phase2_pack.continuity_pack_id,
            runtime_id=runtime_id,
            session_id=session_id,
            compaction_id=compaction_id,
            result=entry.get("result", "synthetic_observation"),
            useful_memory_ids=[seed.memory_by_logical_id[item]["memory_id"] for item in entry.get("useful_ids", []) if item in seed.memory_by_logical_id],
            harmful_memory_ids=[seed.memory_by_logical_id[item]["memory_id"] for item in entry.get("harmful_ids", []) if item in seed.memory_by_logical_id],
            ignored_memory_ids=[seed.memory_by_logical_id[item]["memory_id"] for item in entry.get("ignored_ids", []) if item in seed.memory_by_logical_id],
            missing_notes=entry.get("missing_notes", []),
            promote_notes=entry.get("promote_notes", []),
            write=True,
        )
        from shyftr.continuity import record_continuity_feedback  # local import to keep top import list compact
        feedback_summaries.append(record_continuity_feedback(feedback))
    surfaced_ids = [
        logical_id
        for item in pack.items
        for logical_id in [_logical_id_from_statement(seed, item.statement)]
        if logical_id is not None
    ]
    status = continuity_status(seed.continuity_cell)
    result = _score_fixture(
        fixture,
        "carry",
        surfaced_ids,
        raw_item_count=len(pack.items),
        total_tokens=pack.total_tokens,
        extra={
            "continuity_mode": phase2_pack.mode,
            "continuity_roles": [item.continuity_role for item in pack.items],
            "continuity_status_counts": status["counts"],
            "feedback_events_recorded": len(feedback_summaries),
            "preserved_open_loop_rate": _serialize_resume_counts(surfaced_ids, fixture["expected_resume_state"])["preserved_open_loop_rate"],
            "carry_state_present": bool(phase2_pack.carry_state),
            "carry_candidate_count": int(phase2_pack.diagnostics.get("carry_candidate_count") or 0),
            "memory_candidate_count": int(phase2_pack.diagnostics.get("memory_candidate_count") or 0),
            "phase2_raw_item_count": len(phase2_pack.items),
            "phase2_total_tokens": phase2_pack.total_tokens,
            "phase2_surfaced_ids": list(dict.fromkeys([
                logical_id
                for item in phase2_pack.items
                for logical_id in [
                    _logical_id_from_statement(seed, item.statement)
                    or _logical_id_from_live_content(seed, item.statement)
                ]
                if logical_id is not None
            ])),
        },
    )
    result["expectation_evaluation"] = _apply_expected_contract(result, fixture.get("expected_contract", {}), "carry")
    return result


def run_live_fixture(fixture: Mapping[str, Any]) -> Dict[str, Any]:
    seed = _seed_fixture(fixture)
    runtime_id = f"baseline-{fixture['fixture_id']}"
    session_id = f"session-{fixture['fixture_id']}"
    config = fixture.get("mode_config", {}).get("live", {})
    pack = build_live_context_pack(
        LiveContextPackRequest(
            cell_path=str(seed.live_cell),
            query=fixture["task_prompt"],
            runtime_id=runtime_id,
            session_id=session_id,
            max_items=int(config.get("max_items", 6)),
            max_tokens=int(config.get("max_tokens", 120)),
            current_prompt_excerpts=config.get("current_prompt_excerpts", []),
            write=True,
        )
    )
    checkpoint = build_carry_state_checkpoint(
        CarryStateCheckpointRequest(
            live_cell_path=str(seed.live_cell),
            continuity_cell_path=str(seed.continuity_cell),
            runtime_id=runtime_id,
            session_id=session_id,
            max_items=int(config.get("max_items", 6)),
            max_tokens=int(config.get("max_tokens", 120)),
            write=True,
        )
    )
    resume = reconstruct_resume_state(
        seed.continuity_cell,
        runtime_id=runtime_id,
        session_id=session_id,
        max_items=int(config.get("max_items", 6)),
        max_tokens=int(config.get("max_tokens", 120)),
    )
    harvest = harvest_session(
        SessionHarvestRequest(
            live_cell_path=str(seed.live_cell),
            continuity_cell_path=str(seed.continuity_cell),
            memory_cell_path=str(seed.memory_cell),
            runtime_id=runtime_id,
            session_id=session_id,
            write=True,
            allow_direct_durable_memory=bool(config.get("allow_direct_durable_memory", False)),
        )
    )
    surfaced_ids = [
        logical_id
        for item in pack.items
        for logical_id in [_logical_id_from_live_content(seed, item["content"])]
        if logical_id is not None
    ]
    metrics = live_context_metrics(seed.live_cell, runtime_id=runtime_id, session_id=session_id)
    status = live_context_status(seed.live_cell)
    result = _score_fixture(
        fixture,
        "live",
        surfaced_ids,
        raw_item_count=len(pack.items),
        total_tokens=pack.total_tokens,
        extra={
            "duplicate_suppression_count": pack.duplicate_suppression_count,
            "stale_suppression_count": pack.stale_suppression_count,
            "memory_proposal_count": harvest.memory_proposal_count,
            "continuity_improvement_proposal_count": harvest.continuity_improvement_proposal_count,
            "live_context_status_counts": status["counts"],
            "live_context_metrics": metrics,
            "harvest_review_gated": harvest.review_gated,
            "carry_state_checkpoint_count": metrics.get("carry_state_checkpoint_count"),
            "carry_state_checkpoint_tokens": metrics.get("carry_state_checkpoint_tokens"),
            "resume_validation": resume.validation,
            "checkpoint_total_items": checkpoint.total_items,
            "checkpoint_total_tokens": checkpoint.total_tokens,
            "phase2_resume_surfaced_ids": list(dict.fromkeys([
                logical_id
                for section_items in resume.sections.values()
                for item in section_items
                for logical_id in [_logical_id_from_live_content(seed, item.get("content", ""))]
                if logical_id is not None
            ])),
        },
    )
    result["expectation_evaluation"] = _apply_expected_contract(result, fixture.get("expected_contract", {}), "live")
    return result


def analyze_pack_loadout_behavior(reference_fixture: Mapping[str, Any]) -> Dict[str, Any]:
    seed = _seed_fixture(reference_fixture)
    query = reference_fixture["task_prompt"]
    loadout = loadout_module.assemble_loadout(
        loadout_module.LoadoutTaskInput(
            cell_path=str(seed.memory_cell),
            query=query,
            task_id="behavior-loadout",
            max_items=8,
            max_tokens=120,
            runtime_id="current-state-baseline",
        )
    )
    pack_like = pack_module.assemble_loadout(
        pack_module.LoadoutTaskInput(
            cell_path=str(seed.memory_cell),
            query=query,
            task_id="behavior-pack",
            max_items=8,
            max_tokens=120,
            runtime_id="current-state-baseline",
        )
    )
    api_response = process_runtime_loadout_request(
        RuntimeLoadoutRequest(
            cell_path_or_id=str(seed.memory_cell),
            query=query,
            task_kind="baseline-behavior",
            external_system="current-state-baseline",
            max_items=8,
            max_tokens=120,
        )
    )
    raw_shapes = {
        "module_loadout": {
            "top_level_keys": sorted(loadout.to_dict().keys()),
            "item_keys": sorted(loadout.to_dict()["items"][0].keys()) if loadout.items else [],
            "category_counts": {
                "guidance": len(loadout.guidance_items),
                "caution": len(loadout.caution_items),
                "background": len(loadout.background_items),
                "conflict": len(loadout.conflict_items),
            },
        },
        "module_pack_compat": {
            "top_level_keys": sorted(pack_like.to_dict().keys()),
            "item_keys": sorted(pack_like.to_dict()["items"][0].keys()) if pack_like.items else [],
            "category_counts": {
                "guidance": len(pack_like.guidance_items),
                "caution": len(pack_like.caution_items),
                "background": len(pack_like.background_items),
                "conflict": len(pack_like.conflict_items),
            },
        },
        "runtime_loadout_api": {
            "top_level_keys": sorted(api_response.to_dict().keys()),
            "category_keys": ["guidance_items", "caution_items", "background_items", "conflict_items"],
            "category_counts": {
                "guidance": len(api_response.guidance_items),
                "caution": len(api_response.caution_items),
                "background": len(api_response.background_items),
                "conflict": len(api_response.conflict_items),
            },
        },
    }
    divergences = []
    if raw_shapes["module_loadout"]["top_level_keys"] != raw_shapes["runtime_loadout_api"]["top_level_keys"]:
        divergences.append("Module pack/loadout surfaces expose loadout_id/items/retrieval_log, while the runtime API exposes categorized guidance/caution/background/conflict groups.")
    if raw_shapes["module_loadout"]["item_keys"]:
        divergences.append("Module item records preserve loadout_role on each item; the runtime API normalizes items into category-specific arrays.")
    divergences.append("The CLI command name is 'shyftr pack' even though the underlying implementation object and ids are named loadout/loadout_id.")
    normalized_shape = {
        "shared_identifier_field": "loadout_id",
        "shared_selected_item_count": loadout.total_items,
        "shared_total_tokens": loadout.total_tokens,
        "normalized_categories": raw_shapes["runtime_loadout_api"]["category_counts"],
    }
    return {
        "fixture_id": reference_fixture["fixture_id"],
        "mode": "behavior",
        "raw_shapes": raw_shapes,
        "normalized_shape": normalized_shape,
        "divergences": divergences,
    }


def aggregate_results(mode_results: Mapping[str, Sequence[Mapping[str, Any]]]) -> Dict[str, Any]:
    summaries: Dict[str, Any] = {}
    for mode, results in mode_results.items():
        if mode == "behavior":
            continue
        fixture_count = len(results)
        summaries[mode] = {
            "fixture_count": fixture_count,
            "average_useful_memory_inclusion_rate": round(sum(float(r["useful_memory_inclusion_rate"]) for r in results) / max(1, fixture_count), 4),
            "average_stale_memory_inclusion_rate": round(sum(float(r["stale_memory_inclusion_rate"]) for r in results) / max(1, fixture_count), 4),
            "average_harmful_memory_inclusion_rate": round(sum(float(r["harmful_memory_inclusion_rate"]) for r in results) / max(1, fixture_count), 4),
            "average_ignored_memory_inclusion_rate": round(sum(float(r["ignored_memory_inclusion_rate"]) for r in results) / max(1, fixture_count), 4),
            "average_missing_memory_rate": round(sum(float(r["missing_memory_rate"]) for r in results) / max(1, fixture_count), 4),
            "average_resume_state_score": round(sum(float(r["resume_state_score"] or 0.0) for r in results) / max(1, fixture_count), 4),
            "total_raw_items": sum(int(r.get("raw_item_count") or 0) for r in results),
        }
    return summaries


def _mode_rows(results: Sequence[Mapping[str, Any]], mode: str) -> str:
    lines = ["| fixture | useful | stale | harmful | ignored | missing | resume |", "|---|---:|---:|---:|---:|---:|---:|"]
    for result in results:
        lines.append(
            f"| {result['fixture_id']} | {result['useful_memory_inclusion_rate']:.4f} | {result['stale_memory_inclusion_rate']:.4f} | {result['harmful_memory_inclusion_rate']:.4f} | {result['ignored_memory_inclusion_rate']:.4f} | {result['missing_memory_rate']:.4f} | {result['resume_state_score'] if result['resume_state_score'] is not None else 'n/a'} |"
        )
    if not results:
        lines.append("| none | n/a | n/a | n/a | n/a | n/a | n/a |")
    return "\n".join(lines)


def _write_inventory_doc(path: Path) -> None:
    path.write_text(
        """# Current-state harness surface inventory

Status: generated for the 2026-05-07 current-state baseline harness

## Scope

This inventory freezes the actual current ShyftR surfaces used by the baseline harness. It records what the harness measures today without assuming future API changes.

## Durable memory path

CLI:
- `shyftr pack <cell_path> <query> --task-id <id>`
- `shyftr feedback <cell_path> <loadout_id> <result>`

Python/module:
- `shyftr.provider.memory.remember(...)`
- `shyftr.loadout.LoadoutTaskInput`
- `shyftr.loadout.assemble_loadout(...)`
- compatibility mirror: `shyftr.pack.LoadoutTaskInput` and `shyftr.pack.assemble_loadout(...)`
- runtime adapter: `shyftr.integrations.loadout_api.process_runtime_loadout_request(...)`

Write/dry-run boundary:
- durable memory seeding is an intentional synthetic write into a temp memory cell;
- loadout assembly appends retrieval logs to temp ledgers;
- no non-temp user cell is touched.

## Carry / continuity path

CLI:
- `shyftr continuity pack ...`
- `shyftr carry pack ...`
- `shyftr continuity feedback ...`
- `shyftr continuity eval ...`
- `shyftr continuity status ...`

Python/module:
- `shyftr.continuity.ContinuityPackRequest`
- `shyftr.continuity.assemble_continuity_pack(...)`
- `shyftr.continuity.ContinuityFeedback`
- `shyftr.continuity.record_continuity_feedback(...)`
- `shyftr.continuity.continuity_status(...)`
- `shyftr.continuity.evaluate_synthetic_continuity(...)`

Write/dry-run boundary:
- `mode=shadow` preserves the continuity path without exporting items to the runtime;
- continuity ledgers are written only inside temp continuity cells;
- Phase 2 continuity can merge durable memory with typed carry-state from the live context cell when available;
- outputs remain bounded and advisory even when carry-state is present.

## Live-context path

CLI:
- `shyftr live-context capture ...`
- `shyftr live-context pack ...`
- `shyftr live-context checkpoint ...`
- `shyftr live-context resume ...`
- `shyftr live-context harvest ...`
- `shyftr live-context status ...`
- `shyftr live-context metrics ...`

Python/module:
- `shyftr.live_context.LiveContextCaptureRequest`
- `shyftr.live_context.capture_live_context(...)`
- `shyftr.live_context.LiveContextPackRequest`
- `shyftr.live_context.build_live_context_pack(...)`
- `shyftr.live_context.CarryStateCheckpointRequest`
- `shyftr.live_context.build_carry_state_checkpoint(...)`
- `shyftr.live_context.reconstruct_resume_state(...)`
- `shyftr.live_context.SessionHarvestRequest`
- `shyftr.live_context.harvest_session(...)`
- `shyftr.live_context.live_context_status(...)`
- `shyftr.live_context.live_context_metrics(...)`

Write/dry-run boundary:
- capture, pack, and harvest remain dry-run unless `write=true` / `--write` is supplied;
- the harness uses explicit writes only inside temp live-context cells;
- harvest remains review-gated and does not silently mutate durable memory.

## Pack / loadout naming split preserved by the harness

Observed current seam:
- the CLI noun is `pack`;
- the core implementation object is `Loadout` with `loadout_id`;
- the runtime API also returns `loadout_id` but normalizes items into `guidance_items`, `caution_items`, `background_items`, and `conflict_items` arrays.

Harness policy:
- preserve raw current names in artifacts;
- normalize them only in the scoring layer;
- report semantic divergence instead of silently flattening it away.

## Known seams intentionally preserved

- continuity pack behavior is advisory/shadow/off today; stronger authority modes remain gated;
- live-context metrics preserve pack-based scoring while recording checkpoint/resume extras separately;
- pack/loadout terminology is split across CLI, module, and runtime API surfaces;
- the harness uses only temp cells and synthetic fixtures, so broader runtime or hosted claims remain out of scope.
""",
        encoding="utf-8",
    )


def _write_mode_doc(path: Path, title: str, intro: str, results: Sequence[Mapping[str, Any]]) -> None:
    sections = [f"# {title}", "", intro, "", _mode_rows(results, title)]
    for result in results:
        sections.extend(
            [
                "",
                f"## {result['fixture_id']}",
                "",
                f"- surfaced ids: {', '.join(result['surfaced_ids']) if result['surfaced_ids'] else 'none'}",
                f"- useful/stale/harmful/ignored/missing: {result['matched_useful_count']}/{result['stale_count']}/{result['harmful_count']}/{result['ignored_count']}/{result['missing_required_count']}",
                f"- raw item count: {result.get('raw_item_count')}",
                f"- estimated tokens: {result.get('total_tokens')}",
                f"- expectation pass: {result['expectation_evaluation']['pass']}",
            ]
        )
    path.write_text("\n".join(sections) + "\n", encoding="utf-8")


def _write_behavior_doc(path: Path, behavior: Mapping[str, Any]) -> None:
    lines = [
        "# Current pack/loadout behavior",
        "",
        "This note records the current pack/loadout naming split before any unification work.",
        "",
        "## Raw shapes",
        "",
        "```json",
        json.dumps(behavior["raw_shapes"], indent=2, sort_keys=True),
        "```",
        "",
        "## Normalized interpretation",
        "",
        "```json",
        json.dumps(behavior["normalized_shape"], indent=2, sort_keys=True),
        "```",
        "",
        "## Divergences",
        "",
    ]
    lines.extend([f"- {item}" for item in behavior["divergences"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary_docs(summary: Mapping[str, Any], output_dir: Path) -> None:
    _write_inventory_doc(output_dir / "current-state-harness-surface-inventory.md")
    _write_mode_doc(
        output_dir / "current-state-baseline-durable-only.md",
        "Current-state baseline durable only",
        "Mode A measures the current durable-memory-only path through loadout assembly.",
        summary["fixture_results"].get("durable", []),
    )
    _write_mode_doc(
        output_dir / "current-state-baseline-carry.md",
        "Current-state baseline carry",
        "Mode B measures the current carry/continuity path relative to durable memory.",
        summary["fixture_results"].get("carry", []),
    )
    _write_mode_doc(
        output_dir / "current-state-baseline-live-context.md",
        "Current-state baseline live context",
        "Mode C measures live-context capture, pack, and harvest behavior without redesigning those surfaces.",
        summary["fixture_results"].get("live", []),
    )
    if summary.get("behavior"):
        _write_behavior_doc(output_dir / "current-pack-loadout-behavior.md", summary["behavior"])

    durable_results = summary["fixture_results"].get("durable", [])
    carry_results = summary["fixture_results"].get("carry", [])
    live_results = summary["fixture_results"].get("live", [])
    notable_outcomes = [
        f"- durable: {sum(1 for result in durable_results if result['expectation_evaluation']['pass'])}/{len(durable_results)} fixtures met their declared durable expectations;",
        f"- carry: {sum(1 for result in carry_results if result['expectation_evaluation']['pass'])}/{len(carry_results)} fixtures met their declared carry expectations;",
        f"- live: {sum(1 for result in live_results if result['expectation_evaluation']['pass'])}/{len(live_results)} fixtures met their declared live expectations;",
    ]
    report_lines = [
        "# Current-state baseline report",
        "",
        "## Scope",
        "",
        "Synthetic, repo-local baseline for current durable memory, continuity, and live-context behavior.",
        "",
        "## Fixtures included",
        "",
        ", ".join(summary["fixtures_included"]),
        "",
        "## Execution modes",
        "",
        "- Mode A: durable-memory-only",
        "- Mode B: durable + carry/continuity",
        "- Mode C: durable + carry/continuity + live-context",
        "- Mode D: pack/loadout behavior capture and normalization",
        "",
        "## Metric definitions",
        "",
        "- useful_memory_inclusion_rate: fraction of labeled useful ids surfaced by the current mode;",
        "- stale_memory_inclusion_rate: fraction of labeled stale ids incorrectly surfaced;",
        "- harmful_memory_inclusion_rate: fraction of labeled harmful ids incorrectly surfaced;",
        "- ignored_memory_inclusion_rate: fraction of labeled ignored ids surfaced;",
        "- missing_memory_rate: fraction of required ids that were absent;",
        "- resume_state_score: combined score over required inclusion plus excluded-id suppression for the fixture's expected resume state.",
        "",
        "## Aggregate results by mode",
        "",
        "```json",
        json.dumps(summary["mode_summaries"], indent=2, sort_keys=True),
        "```",
        "",
        "## Notable fixture outcomes",
        "",
    ]
    report_lines.extend(notable_outcomes)
    report_lines.extend(
        [
            "",
            "## What this baseline proves",
            "",
            "- current synthetic fixtures are rerunnable against temp cells;",
            "- durable/loadout, continuity, and live-context surfaces can be measured today;",
            "- pack/loadout naming drift is explicit and normalized rather than hidden;",
            "- Phase 2 checkpoint and resume validation can be measured deterministically with synthetic fixtures.",
            "",
            "## What this baseline does not prove",
            "",
            "- no hosted or multi-tenant performance claim;",
            "- no real runtime profile, user transcript, or regulated-data result;",
            "- no broader market/runtime superiority claim.",
            "",
            "## Known limitations",
            "",
        ]
    )
    report_lines.extend([f"- {item}" for item in summary["known_limitations"]])
    report_lines.extend(
        [
            "",
            "## Recommended use in later tranches",
            "",
            "Run this harness before judging schema/model unification, typed live-context evolution, retrieval redesign, or memory-class expansion complete.",
        ]
    )
    (output_dir / "current-state-baseline-report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    closeout_lines = [
        "# Current-state baseline closeout",
        "",
        "## Built artifacts",
        "",
        "- examples/evals/current-state-baseline/README.md",
        "- examples/evals/current-state-baseline/metrics-contract.md",
        "- examples/evals/current-state-baseline/fixtures/*.json",
        "- examples/evals/current-state-baseline/expected/*.json",
        "- scripts/current_state_baseline.py",
        "- scripts/compare_current_state_baseline.py",
        "- tests/test_current_state_baseline_smoke.py",
        "- tests/test_current_state_metrics_schema.py",
        "- docs/status/current-state-baseline-*.md",
        "- docs/status/current-state-baseline-summary.json",
        "- docs/status/current-state-baseline-comparison.md",
        "",
        "## Rerun commands",
        "",
        "```bash",
        "python scripts/current_state_baseline.py --mode durable",
        "python scripts/current_state_baseline.py --mode carry",
        "python scripts/current_state_baseline.py --mode live",
        "python scripts/current_state_baseline.py --mode all",
        "python scripts/current_state_baseline.py --mode all --summary-path docs/status/current-state-baseline-summary.phase2.json",
        "python scripts/compare_current_state_baseline.py docs/status/current-state-baseline-summary.json docs/status/current-state-baseline-summary.json",
        "```",
        "",
        "## Contract",
        "",
        "The latest `docs/status/current-state-baseline-summary.json` is the machine-comparable regression contract until a broader benchmark layer explicitly replaces it.",
    ]
    (output_dir / "current-state-baseline-closeout.md").write_text("\n".join(closeout_lines) + "\n", encoding="utf-8")


def run_baseline(mode: str, fixture_id: Optional[str]) -> Dict[str, Any]:
    fixtures = load_fixtures(fixture_id)
    fixture_results: Dict[str, List[Dict[str, Any]]] = {"durable": [], "carry": [], "live": []}

    if mode in {"durable", "all"}:
        for fixture in fixtures:
            if "durable" in fixture["mode_support"]:
                fixture_results["durable"].append(run_durable_fixture(fixture))
    if mode in {"carry", "all"}:
        for fixture in fixtures:
            if "carry" in fixture["mode_support"]:
                fixture_results["carry"].append(run_carry_fixture(fixture))
    if mode in {"live", "all"}:
        for fixture in fixtures:
            if "live" in fixture["mode_support"]:
                fixture_results["live"].append(run_live_fixture(fixture))

    behavior = analyze_pack_loadout_behavior(fixtures[0]) if mode == "all" else None
    known_limitations = [
        "continuity currently packages durable memory into advisory/shadow/off continuity packs rather than consuming a separate continuity-entry corpus before pack assembly.",
        "live-context metrics distinguish advisory pack utility from session-harvest utility; they do not claim broader runtime-continuation success.",
        "pack/loadout terminology remains split across CLI, module, and runtime API surfaces.",
        "all evidence is synthetic and temp-cell scoped by design.",
    ]
    summary = {
        "run_id": f"current-state-baseline-{mode}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "fixture_count": len(fixtures),
        "fixtures_included": [fixture["fixture_id"] for fixture in fixtures],
        "mode": mode,
        "mode_summaries": aggregate_results({**fixture_results, "behavior": [behavior] if behavior else []}),
        "fixture_results": fixture_results,
        "behavior": behavior,
        "known_limitations": known_limitations,
        "output_schema_version": SCHEMA_VERSION,
    }
    return summary


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the synthetic current-state ShyftR baseline harness.")
    parser.add_argument("--mode", choices=("durable", "carry", "live", "all"), default="all")
    parser.add_argument("--fixture", default=None, help="optional fixture id filter")
    parser.add_argument("--output-dir", default=str(DEFAULT_STATUS_DIR), help="directory for markdown outputs")
    parser.add_argument("--summary-path", default=str(DEFAULT_STATUS_DIR / "current-state-baseline-summary.json"), help="path for the summary JSON")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).resolve()
    summary_path = Path(args.summary_path).resolve()
    summary = run_baseline(args.mode, args.fixture)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(summary_path, summary)
    _write_summary_docs(summary, output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
