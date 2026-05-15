"""Tests for the ShyftR CLI MVP."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run the shyftr CLI via python -m."""
    import os
    cmd = [sys.executable, "-m", "shyftr.cli", *args]
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}"
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


def test_cli_help() -> None:
    """Top-level --help shows commands list."""
    result = _cli("--help")
    assert result.returncode == 0
    assert "ShyftR" in result.stdout
    assert "init-cell" in result.stdout
    assert "ingest" in result.stdout
    assert "fragments" in result.stdout
    assert "approve" in result.stdout
    assert "reject" in result.stdout
    assert "promote" in result.stdout
    assert "search" in result.stdout
    assert "profile" in result.stdout
    assert "loadout" in result.stdout
    assert "outcome" in result.stdout
    assert "hygiene" in result.stdout
    assert "adapter" in result.stdout
    assert "serve" in result.stdout
    assert "sweep" in result.stdout


def test_subcommand_help_init() -> None:
    """Subcommand --help works for init."""
    result = _cli("init", "--help")
    assert result.returncode == 0
    assert "cell_id" in result.stdout or "CELL_ID" in result.stdout


def test_subcommand_help_ingest() -> None:
    """Subcommand --help works for ingest."""
    result = _cli("ingest", "--help")
    assert result.returncode == 0
    assert "kind" in result.stdout or "KIND" in result.stdout


def test_subcommand_help_hygiene() -> None:
    """Subcommand --help works for hygiene."""
    result = _cli("hygiene", "--help")
    assert result.returncode == 0
    assert "cell_path" in result.stdout or "CELL_PATH" in result.stdout


def test_subcommand_help_audit_list_supports_summary_mode() -> None:
    """audit list --help advertises --summary review-surface mode."""
    result = _cli("audit", "list", "--help")
    assert result.returncode == 0
    assert "--summary" in result.stdout
    assert "audit" in result.stdout


def test_subcommand_help_serve() -> None:
    """Subcommand --help works for optional local service."""
    result = _cli("serve", "--help")
    assert result.returncode == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout


def test_invalid_command_exits_nonzero() -> None:
    """An unknown subcommand exits with nonzero and prints a useful message."""
    result = _cli("nonexistent")
    assert result.returncode != 0
    assert "error:" in result.stderr or "invalid choice" in result.stderr or "nonexistent" in result.stderr


def test_missing_required_arg_exits_nonzero() -> None:
    """A command missing required args exits nonzero."""
    result = _cli("ingest")
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# Full lifecycle flow via CLI
# ---------------------------------------------------------------------------


def test_full_cli_lifecycle(tmp_path: Path) -> None:
    """Exercise the full Source -> Fragment -> Trace -> Loadout -> Outcome
    flow through the CLI using a temporary Cell."""
    cell = str(tmp_path / "test-cell")
    source_file = tmp_path / "source.txt"
    source_file.write_text(
        "## ShyftR\n\nShyftR is an attachable recursive memory cell system for AI agents.\n",
        encoding="utf-8",
    )

    # 1. init-cell
    result = _cli("init-cell", cell, "--cell-id", "test-cell", "--cell-type", "domain")
    assert result.returncode == 0, f"init failed: {result.stderr}"
    init_data = json.loads(result.stdout)
    assert init_data["status"] == "ok"
    assert init_data["cell_id"] == "test-cell"

    # 2. ingest
    result = _cli("ingest", cell, str(source_file), "--kind", "document")
    assert result.returncode == 0, f"ingest failed: {result.stderr}"
    ingest_data = json.loads(result.stdout)
    assert ingest_data["evidence_id"].startswith("src-")
    source_id: str = ingest_data["evidence_id"]

    # 3. fragments
    result = _cli("candidate", cell, source_id)
    assert result.returncode == 0, f"fragment failed: {result.stderr}"
    fragments = json.loads(result.stdout)
    assert isinstance(fragments, list)
    assert len(fragments) >= 1
    fragment_id: str = fragments[0]["candidate_id"]

    # 4. review approve
    result = _cli(
        "approve", cell, fragment_id,
        "--reviewer", "test-bot",
        "--rationale", "Looks good",
    )
    assert result.returncode == 0, f"review failed: {result.stderr}"
    review_data = json.loads(result.stdout)
    assert review_data["review_status"] == "approved"

    # 5. promote
    result = _cli(
        "promote", cell, fragment_id,
        "--promoter", "test-bot",
        "--statement", "ShyftR is an attachable recursive memory cell system.",
    )
    assert result.returncode == 0, f"promote failed: {result.stderr}"
    trace_data = json.loads(result.stdout)
    assert trace_data["memory_id"].startswith("trace-")
    trace_id: str = trace_data["memory_id"]

    # 6. search
    result = _cli("search", cell, "ShyftR")
    assert result.returncode == 0, f"search failed: {result.stderr}"
    search_data = json.loads(result.stdout)
    assert "results" in search_data

    # 7. loadout
    result = _cli(
        "loadout", cell, "ShyftR memory",
        "--task-id", "test-task",
        "--max-items", "10",
    )
    assert result.returncode == 0, f"loadout failed: {result.stderr}"
    loadout_data = json.loads(result.stdout)
    assert loadout_data["pack_id"].startswith("lo-")
    loadout_id: str = loadout_data["pack_id"]

    # 8. outcome
    result = _cli(
        "outcome", cell, loadout_id, "success",
        "--applied", trace_id,
        "--useful", trace_id,
    )
    assert result.returncode == 0, f"outcome failed: {result.stderr}"
    outcome_data = json.loads(result.stdout)
    assert outcome_data["feedback_id"].startswith("oc-")
    assert outcome_data["verdict"] == "success"


def test_hygiene_is_callable_and_read_only(tmp_path: Path) -> None:
    """hygiene command runs successfully against a temp Cell without mutation."""
    cell = str(tmp_path / "hygiene-cell")

    result_init = _cli("init", cell, "--cell-id", "hygiene-cell")
    assert result_init.returncode == 0

    result = _cli("hygiene", cell)
    assert result.returncode == 0, f"hygiene failed: {result.stderr}"
    report = json.loads(result.stdout)
    assert "fragment_status_counts" in report
    assert "trace_confidence_distribution" in report
    assert "audit_findings" in report
    # Verify read-only: after hygiene, an unrelated command should work
    result2 = _cli("hygiene", cell)
    assert result2.returncode == 0
    assert json.loads(result2.stdout) == report  # deterministic


def test_sweep_help(tmp_path: Path) -> None:
    """sweep --help shows cell_path argument."""
    result = _cli("sweep", "--help")
    assert result.returncode == 0
    assert "cell_path" in result.stdout
    assert "--propose" in result.stdout
    assert "--apply-low-risk" in result.stdout


def test_challenge_help() -> None:
    """challenge --help shows challenge-specific arguments."""
    result = _cli("challenge", "--help")
    assert result.returncode == 0
    assert "cell_path" in result.stdout
    assert "--propose" in result.stdout
    assert "--charge-id" in result.stdout
    assert "--top-impact" in result.stdout


def test_challenge_in_empty_cell(tmp_path: Path) -> None:
    """challenge runs successfully against a temp Cell in default dry-run mode."""
    cell = str(tmp_path / "challenge-cell")

    result_init = _cli("init", cell, "--cell-id", "challenge-cell")
    assert result_init.returncode == 0

    result = _cli("challenge", cell)
    assert result.returncode == 0, f"challenge failed: {result.stderr}"
    report = json.loads(result.stdout)
    assert report["cell_id"] == "challenge-cell"
    assert report["dry_run"] is True
    assert report["target_count"] >= 0
    assert "findings" in report


def test_sweep_in_empty_cell(tmp_path: Path) -> None:
    """sweep runs successfully against a temp Cell without mutation."""
    cell = str(tmp_path / "sweep-cell")

    result_init = _cli("init", cell, "--cell-id", "sweep-cell")
    assert result_init.returncode == 0

    result = _cli("sweep", cell)
    assert result.returncode == 0, f"sweep failed: {result.stderr}"
    report = json.loads(result.stdout)
    assert report["cell_id"] == "sweep-cell"
    assert report["dry_run"] is True
    assert report["trace_count"] >= 0
    assert "proposed_actions" in report


def test_sweep_propose_cli_appends_and_deduplicates(tmp_path: Path) -> None:
    """sweep --propose appends proposal rows without duplicating open proposals."""
    cell = tmp_path / "sweep-propose"
    result_init = _cli("init", str(cell), "--cell-id", "sweep-propose")
    assert result_init.returncode == 0, result_init.stderr

    charges = cell / "charges" / "approved.jsonl"
    charges.parent.mkdir(parents=True, exist_ok=True)
    charges.write_text(
        json.dumps({
            "charge_id": "trace-a",
            "cell_id": "sweep-propose",
            "source_fragment_ids": ["frag-a"],
            "status": "approved",
            "confidence": 0.6,
        }) + "\n",
        encoding="utf-8",
    )
    retrieval = cell / "ledger" / "retrieval_logs.jsonl"
    retrieval.write_text(
        "".join(json.dumps({"loadout_id": f"lo-{i}", "selected_ids": ["trace-a"]}) + "\n" for i in range(4)),
        encoding="utf-8",
    )
    outcomes = cell / "ledger" / "outcomes.jsonl"
    outcomes.write_text(
        json.dumps({
            "outcome_id": "oc-a",
            "trace_ids": [],
            "metadata": {},
            "pack_miss_details": [{"charge_id": "trace-a"}] * 4,
        }) + "\n",
        encoding="utf-8",
    )

    first = _cli("sweep", "--cell", str(cell), "--propose", "--apply-low-risk")
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)
    assert first_payload["dry_run"] is False
    assert first_payload["written_proposal_ids"]
    assert first_payload["apply_low_risk_written_ids"]

    second = _cli("sweep", "--cell", str(cell), "--propose", "--apply-low-risk")
    assert second.returncode == 0, second.stderr
    second_payload = json.loads(second.stdout)
    assert second_payload["written_proposal_ids"] == []
    assert sorted(second_payload["skipped_proposal_ids"]) == sorted(first_payload["written_proposal_ids"])


def test_sweep_deterministic(tmp_path: Path) -> None:
    """Repeated sweep runs produce identical output except for scanned_at."""
    cell = str(tmp_path / "sweep-det")

    result_init = _cli("init", cell, "--cell-id", "sweep-det")
    assert result_init.returncode == 0

    result1 = _cli("sweep", cell)
    assert result1.returncode == 0
    result2 = _cli("sweep", cell)
    assert result2.returncode == 0
    d1 = json.loads(result1.stdout)
    d2 = json.loads(result2.stdout)
    d1.pop("scanned_at", None)
    d2.pop("scanned_at", None)
    assert d1 == d2


def test_invalid_cell_path_exits_nonzero(tmp_path: Path) -> None:
    """Calling a cell command with a nonexistent cell exits nonzero."""
    fake_cell = str(tmp_path / "nonexistent-cell")
    result = _cli("hygiene", fake_cell)
    assert result.returncode != 0
    assert "error:" in result.stderr or "not a directory" in result.stderr or "no cell_manifest" in result.stderr


def test_adapter_sync_and_sync_status_commands(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "events.jsonl").write_text(
        '{"external_run_id":"r1","task_id":"t1","verdict":"success"}\n',
        encoding="utf-8",
    )
    cell = tmp_path / "cell-main"
    result = _cli("init-cell", str(cell), "--cell-id", "cell-main")
    assert result.returncode == 0, result.stderr
    config = tmp_path / "adapter.json"
    config.write_text(json.dumps({
        "adapter_id": "cli-sync",
        "cell_id": "cell-main",
        "external_system": "generic-runtime",
        "external_scope": "runtime-session",
        "source_root": str(runtime),
        "identity_mapping": {"external_run_id": "external_run_id"},
        "inputs": [{
            "kind": "jsonl",
            "path": "events.jsonl",
            "source_kind": "outcome",
            "identity_mapping": {"external_task_id": "task_id"},
        }],
    }), encoding="utf-8")

    sync = _cli("adapter", "sync", "--config", str(config), "--json")
    status = _cli("adapter", "sync-status", "--config", str(config), "--json")

    assert sync.returncode == 0, sync.stderr
    assert status.returncode == 0, status.stderr
    sync_payload = json.loads(sync.stdout)
    status_payload = json.loads(status.stdout)
    assert sync_payload["sources_ingested"] == 1
    assert sync_payload["sync_state_path"].endswith("adapter_sync_state.json")
    assert status_payload["entries"][0]["last_line_number"] == 1

def test_sweep_accepts_cell_flag(tmp_path: Path) -> None:
    """sweep supports the planned --cell flag form."""
    cell = str(tmp_path / "sweep-flag")
    result_init = _cli("init", cell, "--cell-id", "sweep-flag")
    assert result_init.returncode == 0

    result = _cli("sweep", "--cell", cell, "--dry-run")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["cell_id"] == "sweep-flag"
    assert report["dry_run"] is True


# ---------------------------------------------------------------------------
# Audit CLI subcommands
# ---------------------------------------------------------------------------


def test_audit_help_shows_subcommands() -> None:
    """audit --help shows list, review, resolve."""
    result = _cli("audit", "--help")
    assert result.returncode == 0
    assert "list" in result.stdout
    assert "review" in result.stdout
    assert "resolve" in result.stdout


def test_audit_list_help_shows_args() -> None:
    """audit list --help shows arguments."""
    result = _cli("audit", "list", "--help")
    assert result.returncode == 0
    assert "cell_path" in result.stdout


def test_audit_review_help_shows_args() -> None:
    """audit review --help shows required arguments."""
    result = _cli("audit", "review", "--help")
    assert result.returncode == 0
    assert "--audit-id" in result.stdout
    assert "--resolution" in result.stdout
    assert "--reviewer" in result.stdout
    assert "--rationale" in result.stdout
    assert "--actions" in result.stdout


def test_audit_resolve_help_shows_args() -> None:
    """audit resolve --help shows required arguments."""
    result = _cli("audit", "resolve", "--help")
    assert result.returncode == 0
    assert "--audit-id" in result.stdout
    assert "--reviewer" in result.stdout


def test_audit_review_with_accept_resolution(tmp_path: Path) -> None:
    """audit review with accept resolution writes an audit_review record."""
    cell = str(tmp_path / "review-cell")
    init = _cli("init", cell, "--cell-id", "review-cell")
    assert init.returncode == 0, init.stderr

    result = _cli(
        "audit", "review", cell,
        "--audit-id", "spark-42",
        "--resolution", "accept",
        "--reviewer", "ci-bot",
        "--rationale", "Looks good to me",
    )
    assert result.returncode == 0, result.stderr
    review = json.loads(result.stdout)
    assert review["audit_id"] == "spark-42"
    assert review["resolution"] == "accept"
    assert review["reviewer"] == "ci-bot"
    assert review["rationale"] == "Looks good to me"


def test_audit_review_with_actions(tmp_path: Path) -> None:
    """audit review with --actions stores follow-up actions."""
    cell = str(tmp_path / "actions-cell")
    init = _cli("init", cell, "--cell-id", "actions-cell")
    assert init.returncode == 0, init.stderr

    result = _cli(
        "audit", "review", cell,
        "--audit-id", "spark-99",
        "--resolution", "accept",
        "--reviewer", "ci-bot",
        "--rationale", "Accept with actions",
        "--actions", "mark_challenged,propose_isolation",
    )
    assert result.returncode == 0, result.stderr
    review = json.loads(result.stdout)
    assert review["review_actions"] == ["mark_challenged", "propose_isolation"]


def test_audit_resolve_round_trips(tmp_path: Path) -> None:
    """audit resolve writes an accept resolution with no_action."""
    cell = str(tmp_path / "resolve-cell")
    init = _cli("init", cell, "--cell-id", "resolve-cell")
    assert init.returncode == 0, init.stderr

    result = _cli(
        "audit", "resolve", cell,
        "--audit-id", "spark-7",
    )
    assert result.returncode == 0, result.stderr
    review = json.loads(result.stdout)
    assert review["audit_id"] == "spark-7"
    assert review["resolution"] == "accept"
    assert review["review_actions"] == ["no_action"]


def test_audit_list_after_review(tmp_path: Path) -> None:
    """audit list shows findings after reviews have been recorded."""
    cell = str(tmp_path / "list-cell")
    init = _cli("init", cell, "--cell-id", "list-cell")
    assert init.returncode == 0, init.stderr

    # Record a review first
    review = _cli(
        "audit", "review", cell,
        "--audit-id", "spark-1",
        "--resolution", "accept",
        "--reviewer", "ci-bot",
        "--rationale", "OK",
    )
    assert review.returncode == 0, review.stderr

    # list should not error
    result = _cli("audit", "list", cell)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["audit_row_count"] >= 0


def test_audit_list_summary_returns_grouped_visibility_payload(tmp_path: Path) -> None:
    """audit list --summary groups findings and review state."""
    cell = str(tmp_path / "summary-cell")
    init = _cli("init", cell, "--cell-id", "summary-cell")
    assert init.returncode == 0, init.stderr

    ledger = Path(cell) / "ledger"
    with (ledger / "audit_sparks.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "spark_id": "spark-1",
            "trace_id": "t1",
            "classification": "policy_conflict",
            "action": "challenge",
            "challenger": "challenger-bot",
            "rationale": "policy issue",
            "counter_evidence_source": "ledger/sparks.jsonl:sp-1",
            "cell_id": "summary-cell",
            "fragment_id": "frag-1",
            "proposed_at": "2026-05-15T00:00:00+00:00",
            "observed_at": "2026-05-15T00:00:00+00:00"
        }) + "\n")

    review = _cli(
        "audit", "review", cell,
        "--audit-id", "spark-1",
        "--resolution", "accept",
        "--reviewer", "ci-bot",
        "--rationale", "Confirmed",
        "--actions", "no_action",
    )
    assert review.returncode == 0, review.stderr

    result = _cli("audit", "list", cell, "--summary")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["counts"]["policy_conflict"] == 1
    assert payload["summary"]["review_state_counts"]["reviewed"] == 1
    assert payload["summary"]["findings"][0]["latest_resolution"] == "accept"


def test_audit_review_missing_required_arg_exits_nonzero(tmp_path: Path) -> None:
    """audit review without --audit-id exits nonzero."""
    cell = str(tmp_path / "fail-cell")
    init = _cli("init", cell, "--cell-id", "fail-cell")
    assert init.returncode == 0, init.stderr

    result = _cli("audit", "review", cell, "--resolution", "accept")
    assert result.returncode != 0


def test_audit_resolve_with_explicit_reviewer(tmp_path: Path) -> None:
    """audit resolve accepts --reviewer and --rationale overrides."""
    cell = str(tmp_path / "resolve-custom")
    init = _cli("init", cell, "--cell-id", "resolve-custom")
    assert init.returncode == 0, init.stderr

    result = _cli(
        "audit", "resolve", cell,
        "--audit-id", "spark-12",
        "--reviewer", "admin",
        "--rationale", "Manually resolved",
    )
    assert result.returncode == 0, result.stderr
    review = json.loads(result.stdout)
    assert review["reviewer"] == "admin"
    assert review["rationale"] == "Manually resolved"
