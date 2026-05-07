#!/usr/bin/env python3
"""Read-only evaluator for ShyftR live-context and carry/continuity ledgers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shyftr.continuity import continuity_status
from shyftr.ledger import read_jsonl
from shyftr.live_context import live_context_metrics, live_context_status


def _continuity_feedback_rates(continuity_cell: Path) -> dict[str, float]:
    rows = [record for _, record in read_jsonl(continuity_cell / "ledger" / "continuity_feedback.jsonl")]
    if not rows:
        return {"useful": 0.0, "ignored": 0.0, "harmful": 0.0}
    counts = {"useful": 0, "ignored": 0, "harmful": 0}
    for row in rows:
        if row.get("useful_memory_ids"):
            counts["useful"] += 1
        if row.get("ignored_memory_ids"):
            counts["ignored"] += 1
        if row.get("harmful_memory_ids"):
            counts["harmful"] += 1
    return {key: value / len(rows) for key, value in counts.items()}


def evaluate(
    *,
    live_cell: Path,
    continuity_cell: Path,
    runtime_id: str | None = None,
    session_id: str | None = None,
    min_entries: int = 0,
    min_packs: int = 0,
    min_harvests: int = 0,
    min_harvest_proposals: int = 0,
    min_carry_packs: int = 0,
    max_harmful_feedback_rate: float = 0.0,
) -> dict[str, Any]:
    live = live_context_status(live_cell)
    carry = continuity_status(continuity_cell)
    metrics = live_context_metrics(live_cell, runtime_id=runtime_id, session_id=session_id)
    feedback_rates = _continuity_feedback_rates(continuity_cell)
    live_counts = live["counts"]
    carry_counts = carry["counts"]
    checks = {
        "live_status_ok": live.get("status") == "ok",
        "carry_status_ok": carry.get("status") == "ok",
        "live_advisory_only": live.get("advisory_only") is True,
        "carry_review_gated": carry.get("review_gated_promotions") is True,
        "min_live_entries": live_counts.get("entries", 0) >= min_entries,
        "min_live_packs": live_counts.get("packs", 0) >= min_packs,
        "min_harvests": live_counts.get("harvests", 0) >= min_harvests,
        "min_harvest_proposals": live_counts.get("harvest_proposals", 0) >= min_harvest_proposals,
        "min_carry_packs": carry_counts.get("packs", 0) >= min_carry_packs,
        "harmful_feedback_rate_within_limit": feedback_rates["harmful"] <= max_harmful_feedback_rate,
    }
    failed = [key for key, passed in checks.items() if not passed]
    return {
        "status": "ok" if not failed else "failed",
        "failed_checks": failed,
        "live_context": live,
        "carry": carry,
        "metrics": {**metrics, "carry_feedback_rates": feedback_rates},
        "checks": checks,
        "filters": {"runtime_id": runtime_id, "session_id": session_id},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-cell", type=Path, required=True)
    parser.add_argument("--continuity-cell", "--carry-cell", dest="continuity_cell", type=Path, required=True)
    parser.add_argument("--runtime-id")
    parser.add_argument("--session-id")
    parser.add_argument("--min-entries", type=int, default=0)
    parser.add_argument("--min-packs", type=int, default=0)
    parser.add_argument("--min-harvests", type=int, default=0)
    parser.add_argument("--min-harvest-proposals", type=int, default=0)
    parser.add_argument("--min-carry-packs", type=int, default=0)
    parser.add_argument("--max-harmful-feedback-rate", type=float, default=0.0)
    parser.add_argument("--quiet-ok", action="store_true")
    args = parser.parse_args()
    result = evaluate(
        live_cell=args.live_cell,
        continuity_cell=args.continuity_cell,
        runtime_id=args.runtime_id,
        session_id=args.session_id,
        min_entries=args.min_entries,
        min_packs=args.min_packs,
        min_harvests=args.min_harvests,
        min_harvest_proposals=args.min_harvest_proposals,
        min_carry_packs=args.min_carry_packs,
        max_harmful_feedback_rate=args.max_harmful_feedback_rate,
    )
    if not (args.quiet_ok and result["status"] == "ok"):
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
