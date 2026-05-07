from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]

CELL_DIRECTORIES = (
    "ledger",
    "ledger/memories",
    "ledger/patterns",
    "ledger/rules",
    "memories",
    "patterns",
    "rules",
    "grid",
    "summaries",
    "reports",
    "config",
    # Legacy compatibility directories. Existing cells may still refer to these
    # while public vocabulary uses evidence/candidate/memory/pattern/rule.
    "charges",
    "coils",
    "rails",
    "traces",
    "alloys",
    "doctrine",
    "indexes",
)

SEEDED_JSONL_FILES = (
    # Preferred plain-language ledgers.
    "ledger/evidence.jsonl",
    "ledger/candidates.jsonl",
    "ledger/reviews.jsonl",
    "ledger/promotions.jsonl",
    "ledger/retrieval_logs.jsonl",
    "ledger/graph_edges.jsonl",
    "ledger/reputation/events.jsonl",
    "ledger/regulator_events.jsonl",
    "ledger/regulator_proposals.jsonl",
    "ledger/regulator_proposal_reviews.jsonl",
    "ledger/evolution/proposals.jsonl",
    "ledger/evolution/reviews.jsonl",
    "ledger/evolution/simulations.jsonl",
    "ledger/simulation_reports.jsonl",
    "ledger/feedback.jsonl",
    "ledger/confidence_events.jsonl",
    "ledger/retrieval_affinity_events.jsonl",
    "ledger/audit_candidates.jsonl",
    "ledger/audit_reviews.jsonl",
    "ledger/status_events.jsonl",
    "ledger/supersession_events.jsonl",
    "ledger/deprecation_events.jsonl",
    "ledger/quarantine_events.jsonl",
    "ledger/conflict_events.jsonl",
    "ledger/redaction_events.jsonl",
    "ledger/proposal_decisions.jsonl",
    "ledger/access_policy_events.jsonl",
    "ledger/cell_registry.jsonl",
    "ledger/federation_events.jsonl",
    "ledger/import_candidates.jsonl",
    "ledger/import_reviews.jsonl",
    "ledger/memories/approved.jsonl",
    "ledger/memories/decayed.jsonl",
    "ledger/patterns/proposed.jsonl",
    "ledger/patterns/approved.jsonl",
    "ledger/rules/proposed.jsonl",
    "ledger/rules/approved.jsonl",
    "ledger/packs.jsonl",
    "ledger/continuity_events.jsonl",
    "ledger/continuity_packs.jsonl",
    "ledger/continuity_checkpoints.jsonl",
    "ledger/continuity_feedback.jsonl",
    "ledger/continuity_promotion_proposals.jsonl",
    "ledger/continuity_eval_reports.jsonl",
    "ledger/live_context_events.jsonl",
    "ledger/live_context_entries.jsonl",
    "ledger/live_context_packs.jsonl",
    "ledger/session_harvests.jsonl",
    "ledger/session_harvest_proposals.jsonl",
    "ledger/session_archive.jsonl",
    # Legacy compatibility ledgers used by existing cells and APIs.
    "ledger/pulses.jsonl",
    "ledger/sparks.jsonl",
    "ledger/signals.jsonl",
    "ledger/audit_sparks.jsonl",
    "ledger/isolation_events.jsonl",
    "charges/approved.jsonl",
    "charges/decayed.jsonl",
    "coils/proposed.jsonl",
    "coils/approved.jsonl",
    "rails/proposed.jsonl",
    "rails/approved.jsonl",
    "ledger/sources.jsonl",
    "ledger/fragments.jsonl",
    "ledger/outcomes.jsonl",
    "traces/approved.jsonl",
    "traces/deprecated.jsonl",
    "alloys/proposed.jsonl",
    "alloys/approved.jsonl",
    "doctrine/proposed.jsonl",
    "doctrine/approved.jsonl",
)

_CELL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _validate_cell_id(cell_id: str) -> None:
    if not cell_id:
        raise ValueError("cell_id is required")
    if not _CELL_ID_PATTERN.fullmatch(cell_id):
        raise ValueError("cell_id must be a single safe path segment")


def init_cell(root: PathLike, cell_id: str, cell_type: str = "domain") -> Path:
    """Create an idempotent ShyftR Cell layout under root/cell_id."""
    _validate_cell_id(cell_id)
    if not cell_type:
        raise ValueError("cell_type is required")

    root_path = Path(root)
    cell_path = root_path / cell_id
    cell_path.mkdir(parents=True, exist_ok=True)

    for relative_directory in CELL_DIRECTORIES:
        (cell_path / relative_directory).mkdir(parents=True, exist_ok=True)

    for relative_file in SEEDED_JSONL_FILES:
        seeded_file = cell_path / relative_file
        seeded_file.parent.mkdir(parents=True, exist_ok=True)
        seeded_file.touch(exist_ok=True)

    manifest = {"cell_id": cell_id, "cell_type": cell_type}
    (cell_path / "config" / "cell_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return cell_path
