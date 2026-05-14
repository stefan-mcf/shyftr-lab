from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from shyftr.extract import extract_fragments
from shyftr.ingest import ingest_from_adapter
from shyftr.integrations.config import load_config
from shyftr.integrations.loadout_api import (
    RuntimeLoadoutRequest,
    RuntimeLoadoutResponse,
    process_runtime_loadout_request,
)
from shyftr.integrations.outcome_api import (
    RuntimeOutcomeReport,
    RuntimeOutcomeResponse,
    process_runtime_outcome_report,
)
from shyftr.layout import init_cell
from shyftr.ledger import read_jsonl
from shyftr.models import Source
from shyftr.promote import promote_fragment
from shyftr.review import approve_fragment


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "examples" / "integrations" / "worker-runtime"
DEMO_DOC = REPO_ROOT / "docs" / "runtime-integration-example.md"


def _copy_fixture(tmp_path: Path) -> tuple[Path, Path]:
    runtime_root = tmp_path / "worker-runtime"
    shutil.copytree(FIXTURE_ROOT, runtime_root)
    config_path = runtime_root / "adapter.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_data["source_root"] = str(runtime_root)
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    return runtime_root, config_path


def _first_source(cell: Path) -> Source:
    rows = [record for _, record in read_jsonl(cell / "ledger" / "sources.jsonl")]
    assert rows, "runtime fixture ingest should append Sources"
    closeouts = [row for row in rows if row.get("kind") == "closeout"]
    assert closeouts, "fixture should include a closeout Pulse Source"
    return Source.from_dict(closeouts[0])


def _promote_demo_charge(cell: Path) -> str:
    source = _first_source(cell)
    fragments = extract_fragments(cell, source)
    assert fragments, "closeout evidence should extract at least one candidate"
    fragment = fragments[0]
    approve_fragment(
        cell,
        fragment.fragment_id,
        reviewer="runtime-example-reviewer",
        rationale="Fixture evidence is bounded and relevant to adapter validation.",
    )
    trace = promote_fragment(
        cell,
        fragment.fragment_id,
        promoter="runtime-example-promoter",
        statement="Validate adapter configuration before syncing runtime evidence.",
        rationale="Promoted from RI-8 runtime integration fixture.",
    )
    return trace.trace_id


def test_worker_runtime_fixture_files_are_present_and_runtime_neutral() -> None:
    expected = [
        FIXTURE_ROOT / "adapter.yaml",
        FIXTURE_ROOT / "evidence-closeout.md",
        FIXTURE_ROOT / "feedback-log.jsonl",
        FIXTURE_ROOT / "task-request.json",
        FIXTURE_ROOT / "feedback-report.json",
        DEMO_DOC,
    ]
    for path in expected:
        assert path.is_file(), f"missing RI-8 fixture file: {path}"

    joined = "\n".join(path.read_text(encoding="utf-8") for path in expected)
    assert "generic-worker-runtime" in joined
    assert "evidence: Successful Workflow" in joined
    assert "Repeated Failure Signature" in joined
    assert "recovery pattern" in joined
    assert "Caution / Anti-pattern" in joined
    assert "private runtime" not in joined


def test_worker_runtime_demo_closes_loop_end_to_end(tmp_path: Path) -> None:
    runtime_root, config_path = _copy_fixture(tmp_path)
    cell = init_cell(tmp_path / "cells", "worker-runtime-demo-cell")

    config = load_config(str(config_path))
    ingest_summary = ingest_from_adapter(cell, config)
    assert ingest_summary["errors"] == []
    assert ingest_summary["sources_ingested"] >= 4

    trace_id = _promote_demo_charge(cell)

    request_data = json.loads((runtime_root / "task-request.json").read_text(encoding="utf-8"))
    request_data["cell_path_or_id"] = str(cell)
    request_data["requested_trust_tiers"] = ["trace"]
    request = RuntimeLoadoutRequest.from_dict(request_data)
    loadout_response = process_runtime_loadout_request(request)
    assert isinstance(loadout_response, RuntimeLoadoutResponse)
    assert loadout_response.loadout_id
    assert trace_id in loadout_response.selected_ids
    assert loadout_response.total_items >= 1

    report_data = json.loads((runtime_root / "feedback-report.json").read_text(encoding="utf-8"))
    report_data["cell_path_or_id"] = str(cell)
    report_data["loadout_id"] = loadout_response.loadout_id
    report_data["applied_trace_ids"] = [trace_id]
    report_data["useful_trace_ids"] = [trace_id]
    report = RuntimeOutcomeReport.from_dict(report_data)
    outcome_response = process_runtime_outcome_report(report)
    assert isinstance(outcome_response, RuntimeOutcomeResponse)
    assert outcome_response.status == "accepted"
    assert outcome_response.accepted is True
    assert any(counter["trace_id"] == trace_id for counter in outcome_response.trace_counters)


def test_demo_doc_mentions_contract_and_fixture_paths() -> None:
    text = DEMO_DOC.read_text(encoding="utf-8")
    assert "examples/integrations/worker-runtime/" in text
    assert "shyftr adapter validate" in text
    assert "shyftr adapter ingest" in text
    assert "evidence -> candidate -> memory" in text
    assert "pack" in text
    assert "feedback" in text
