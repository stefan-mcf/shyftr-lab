from __future__ import annotations

import json
from pathlib import Path

from shyftr.cli import main
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl


def _seed(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "evo-cell")
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-1", "cell_id": "evo-cell", "statement": "Run alpha gate before tester outreach.", "source_fragment_ids": ["cand-1"], "kind": "workflow", "status": "approved"})
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "mem-2", "cell_id": "evo-cell", "statement": "Run alpha gate before tester outreach.", "source_fragment_ids": ["cand-2"], "kind": "workflow", "status": "approved"})
    return cell


def _json_from_stdout(capsys):
    return json.loads(capsys.readouterr().out)


def test_evolve_scan_defaults_to_dry_run(tmp_path: Path, capsys) -> None:
    cell = _seed(tmp_path)
    main(["evolve", "scan", str(cell), "--dry-run"])
    payload = _json_from_stdout(capsys)
    assert payload["dry_run"] is True
    assert payload["proposal_count"] == 1
    assert (cell / "ledger" / "evolution" / "proposals.jsonl").read_text(encoding="utf-8") == ""


def test_evolve_write_list_simulate_and_review(tmp_path: Path, capsys) -> None:
    cell = _seed(tmp_path)
    main(["evolve", "scan", str(cell), "--write-proposals"])
    written = _json_from_stdout(capsys)
    proposal_id = written["proposals"][0]["proposal_id"]

    main(["evolve", "proposals", str(cell)])
    listed = _json_from_stdout(capsys)
    assert listed["total"] == 1

    main(["evolve", "simulate", str(cell), proposal_id])
    sim = _json_from_stdout(capsys)
    assert sim["read_only"] is True

    main(["evolve", "review", str(cell), proposal_id, "--decision", "defer", "--rationale", "needs operator review"])
    review = _json_from_stdout(capsys)
    assert review["event"]["decision"] == "defer"
