"""Confidence adjustment for ShyftR Traces based on Outcome learning.

Raises confidence for applied useful Traces after verified success.
Lowers confidence for harmful, failed, or contradicted Traces.

ShyftR doctrine: JSONL ledgers are canonical truth; confidence
adjustments append new Trace rows rather than mutating history.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .ledger import append_jsonl, read_jsonl
from .ledger_state import latest_record_by_key
from .frontier import ConfidenceState, confidence_from_feedback, project_confidence_state

PathLike = Union[str, Path]

# Confidence bounds
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0

# Adjustment deltas
USEFUL_SUCCESS_DELTA = 0.05
HARMFUL_FAILURE_DELTA = -0.10
CONTRADICTED_DELTA = -0.15

# Pack miss exemption: pack miss classification is informational only and
# MUST NOT lower the global confidence of any Trace. The identity of a
# Charge as "missed" (not_relevant, not_actionable, contradicted, etc.) is
# a loadout-coverage observation, not a performance signal that reduces
# confidence. Pack miss deltas are zero by explicit constant so callers
# can reference PACK_MISS_EXEMPT_DELTA in documentation or assertions.
PACK_MISS_EXEMPT_DELTA = 0.0


# ---------------------------------------------------------------------------
# Confidence adjustment result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfidenceAdjustment:
    """Record of a single confidence adjustment."""

    trace_id: str
    old_confidence: Optional[float]
    new_confidence: Optional[float]
    reason: str
    delta: float
    adjusted_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "old_confidence": self.old_confidence,
            "new_confidence": self.new_confidence,
            "reason": self.reason,
            "delta": self.delta,
            "adjusted_at": self.adjusted_at,
        }


# ---------------------------------------------------------------------------
# Cell data readers
# ---------------------------------------------------------------------------

def _read_cell_id(cell_path: Path) -> str:
    """Read cell_id from the Cell manifest."""
    manifest_path = cell_path / "config" / "cell_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Cell manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cell_id = manifest.get("cell_id")
    if not cell_id:
        raise ValueError("Cell manifest is missing cell_id")
    return str(cell_id)


def _read_traces(cell_path: Path) -> List[Dict[str, Any]]:
    """Read approved traces from traces/approved.jsonl."""
    ledger = cell_path / "traces" / "approved.jsonl"
    if not ledger.exists():
        return []
    return [record for _, record in read_jsonl(ledger)]


def _read_outcomes(cell_path: Path) -> List[Dict[str, Any]]:
    """Read all Outcome rows from ledger/outcomes.jsonl."""
    ledger = cell_path / "ledger" / "outcomes.jsonl"
    if not ledger.exists():
        return []
    return [record for _, record in read_jsonl(ledger)]


def _trace_by_id(cell_path: Path, trace_id: str) -> Optional[Dict[str, Any]]:
    """Find the latest trace row by logical id and require it to be approved.

    Phase-9 contract: traces/approved.jsonl is append-only; multiple rows may exist
    for the same logical id. We must apply latest-row-wins semantics AND respect
    the lifecycle status of that latest row.
    """
    records = _read_traces(cell_path)
    latest = latest_record_by_key(records, "trace_id", trace_id)
    if latest is None:
        latest = latest_record_by_key(records, "memory_id", trace_id)

    if latest is None:
        return None

    # Explicitly require approved status; if a later row marks it rejected/retired,
    # it must not participate in confidence adjustment. Legacy approved rows may
    # omit status, matching pack retrieval's compatibility default.
    if latest.get("status", "approved") != "approved":
        return None

    return latest


def _clamp(value: float) -> float:
    """Clamp confidence to [MIN_CONFIDENCE, MAX_CONFIDENCE]."""
    return max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, value))


# ---------------------------------------------------------------------------
# Core: adjust_confidence
# ---------------------------------------------------------------------------

def adjust_confidence(
    cell_path: PathLike,
    outcome_id: str,
    useful_trace_ids: List[str],
    harmful_trace_ids: List[str],
    result: str,
) -> List[ConfidenceAdjustment]:
    """Adjust Trace confidence based on an Outcome.

    - useful_trace_ids: raise confidence (verified success)
    - harmful_trace_ids: lower confidence (harmful/failed/contradicted)
    - Traces in both lists are treated as harmful (contradicted takes priority)
    - **Pack misses are explicitly excluded** from confidence adjustment.
      ``pack_misses`` and ``pack_miss_details`` on an Outcome are
      loadout-coverage observations, not performance signals. They are
      never passed to ``adjust_confidence`` and have zero effect on
      Trace confidence. See ``PACK_MISS_EXEMPT_DELTA = 0.0``.

    Appends updated Trace rows to traces/approved.jsonl (append-only).
    Appends adjustment records to ledger/confidence_adjustments.jsonl.

    Returns list of adjustments made.
    """
    cell = Path(cell_path)
    now = datetime.now(timezone.utc).isoformat()
    adjustments: List[ConfidenceAdjustment] = []

    # Contradicted takes priority: remove harmful traces from the useful pass,
    # then handle overlap in the harmful pass with the stronger penalty.
    harmful_set = set(harmful_trace_ids)
    original_useful_set = set(useful_trace_ids)
    useful_set = original_useful_set - harmful_set

    for tid in useful_set:
        trace = _trace_by_id(cell, tid)
        if trace is None:
            continue
        old_conf = trace.get("confidence")
        if old_conf is None:
            old_conf = 0.5  # default starting confidence
        new_conf = _clamp(old_conf + USEFUL_SUCCESS_DELTA)
        adjustment = ConfidenceAdjustment(
            trace_id=tid,
            old_confidence=old_conf,
            new_confidence=new_conf,
            reason=f"useful_after_{result}",
            delta=USEFUL_SUCCESS_DELTA,
            adjusted_at=now,
        )
        adjustments.append(adjustment)

        # Append updated trace row (append-only, does not remove old)
        updated_trace = dict(trace)
        updated_trace["confidence"] = new_conf
        append_jsonl(cell / "traces" / "approved.jsonl", updated_trace)

    for tid in harmful_set:
        trace = _trace_by_id(cell, tid)
        if trace is None:
            continue
        old_conf = trace.get("confidence")
        if old_conf is None:
            old_conf = 0.5
        # Use the larger contradicted penalty when either the Outcome verdict
        # is explicit contradiction or the same Trace was reported as both
        # useful and harmful. Overlap is the stronger signal: the Trace helped
        # in one respect but contradicted the task outcome in another.
        is_overlapping_signal = tid in original_useful_set
        if result == "contradicted" or is_overlapping_signal:
            delta = CONTRADICTED_DELTA
            reason = f"contradicted_after_{result}"
        else:
            delta = HARMFUL_FAILURE_DELTA
            reason = f"harmful_after_{result}"
        new_conf = _clamp(old_conf + delta)
        adjustment = ConfidenceAdjustment(
            trace_id=tid,
            old_confidence=old_conf,
            new_confidence=new_conf,
            reason=reason,
            delta=delta,
            adjusted_at=now,
        )
        adjustments.append(adjustment)

        updated_trace = dict(trace)
        updated_trace["confidence"] = new_conf
        append_jsonl(cell / "traces" / "approved.jsonl", updated_trace)

    # Append adjustment ledger
    if adjustments:
        adj_ledger = cell / "ledger" / "confidence_adjustments.jsonl"
        for adj in adjustments:
            append_jsonl(adj_ledger, adj.to_dict())

    return adjustments


def adjust_confidence_from_outcome(
    cell_path: PathLike,
    outcome: Dict[str, Any],
) -> List[ConfidenceAdjustment]:
    """Convenience: adjust confidence directly from an Outcome record dict."""
    metadata = outcome.get("metadata", {})
    return adjust_confidence(
        cell_path=cell_path,
        outcome_id=outcome.get("outcome_id", ""),
        useful_trace_ids=metadata.get("useful_trace_ids", []),
        harmful_trace_ids=metadata.get("harmful_trace_ids", []),
        result=outcome.get("verdict", "unknown"),
    )
