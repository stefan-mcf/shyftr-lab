from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl, read_jsonl
from shyftr.ledger_verify import adopt_ledger_heads, verify_ledgers


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _make_cell(tmp_path: Path) -> Path:
    cell = init_cell(tmp_path, "ledger-cell")
    _append(cell / "traces" / "approved.jsonl", {
        "trace_id": "charge-1",
        "cell_id": "ledger-cell",
        "statement": "tamper evidence matters",
        "source_fragment_ids": ["frag-1"],
        "status": "approved",
    })
    _append(cell / "ledger" / "signals.jsonl", {"signal_id": "sig-1", "result": "success"})
    return cell


def _cli(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run([sys.executable, "-m", "shyftr.cli", *args], text=True, capture_output=True, env=env, check=False)


def test_append_jsonl_persists_row_hash_chain_and_legacy_reader_hides_envelope(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    append_jsonl(path, {"event_id": "one", "value": 1})
    append_jsonl(path, {"event_id": "two", "value": 2})

    raw_rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert raw_rows[0]["previous_row_hash"] == ""
    assert len(raw_rows[0]["row_hash"]) == 64
    assert raw_rows[1]["previous_row_hash"] == raw_rows[0]["row_hash"]
    assert len(raw_rows[1]["row_hash"]) == 64
    assert list(read_jsonl(path))[0][1] == {"event_id": "one", "value": 1}


def test_ledger_adoption_and_verification_detects_historical_mutation(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    manifest = adopt_ledger_heads(cell)
    assert manifest["ledgers"]["traces/approved.jsonl"]["row_count"] == 1

    clean = verify_ledgers(cell)
    assert clean["valid"] is True
    assert clean["ledgers"]["traces/approved.jsonl"]["head_matches"] is True

    approved = cell / "traces" / "approved.jsonl"
    approved.write_text(approved.read_text(encoding="utf-8").replace("tamper evidence", "tampered evidence"), encoding="utf-8")

    tampered = verify_ledgers(cell)
    assert tampered["valid"] is False
    assert "traces/approved.jsonl" in tampered["tampered_ledgers"]


def test_verify_ledger_detects_missing_adopted_ledger(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    adopt_ledger_heads(cell)

    (cell / "traces" / "approved.jsonl").unlink()

    missing = verify_ledgers(cell)
    assert missing["valid"] is False
    assert "traces/approved.jsonl" in missing["tampered_ledgers"]
    assert missing["ledgers"]["traces/approved.jsonl"]["missing"] is True


def test_verify_ledger_cli_adopt_then_detect_remove(tmp_path: Path) -> None:
    cell = _make_cell(tmp_path)
    adopt = _cli("verify-ledger", "--cell", str(cell), "--adopt")
    assert adopt.returncode == 0, adopt.stderr
    assert json.loads(adopt.stdout)["manifest"]["format"] == "shyftr.ledger_heads.v1"

    ok = _cli("verify-ledger", "--cell", str(cell))
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["valid"] is True

    (cell / "ledger" / "signals.jsonl").write_text("", encoding="utf-8")
    bad = _cli("verify-ledger", "--cell", str(cell))
    assert bad.returncode == 0, bad.stderr
    payload = json.loads(bad.stdout)
    assert payload["valid"] is False
    assert "ledger/signals.jsonl" in payload["tampered_ledgers"]
