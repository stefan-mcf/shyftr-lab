"""Proposal-only decay and deprecation analysis for ShyftR Traces."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from shyftr.ledger import append_jsonl, read_jsonl

PathLike = Union[str, Path]
JsonRecord = Dict[str, Any]

DEFAULT_MIN_USES_FOR_FAILURE_RATE = 3
DEFAULT_LOW_SUCCESS_RATE = 0.30
DEFAULT_DECAY_HALF_LIFE_DAYS = 90


@dataclass(frozen=True)
class DecayScore:
    """Explainable local decay score for an approved memory record.

    Scores are normalized to 0.0-1.0. They are retrieval signals and review
    evidence only; they do not mutate memory ledgers.
    """

    memory_id: str
    age_decay: float
    failure_decay: float
    confidence_decay: float
    supersession_decay: float
    combined: float
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "age_decay": self.age_decay,
            "failure_decay": self.failure_decay,
            "confidence_decay": self.confidence_decay,
            "supersession_decay": self.supersession_decay,
            "combined": self.combined,
            "reasons": list(self.reasons),
        }


def score_memory_decay(
    memory: JsonRecord,
    *,
    reference_time: Optional[str] = None,
    half_life_days: int = DEFAULT_DECAY_HALF_LIFE_DAYS,
    superseded_ids: Optional[set[str]] = None,
) -> DecayScore:
    """Return an explainable decay score without writing any ledger rows.

    The score combines transparent public-safe factors: age, failed reuse,
    low confidence, and supersession. It intentionally avoids private ranking
    heuristics and does not deprecate anything automatically.
    """
    memory_id = str(memory.get("trace_id") or memory.get("memory_id") or "")
    reference = _parse_time(reference_time) or datetime.now(timezone.utc)
    age_decay = _age_decay(memory, reference=reference, half_life_days=half_life_days)
    failure_decay = _failure_decay(memory)
    confidence_decay = _confidence_decay(memory)
    supersession_decay = 1.0 if memory_id and superseded_ids and memory_id in superseded_ids else 0.0

    combined = _clamp01(
        (0.35 * age_decay)
        + (0.30 * failure_decay)
        + (0.20 * confidence_decay)
        + (0.15 * supersession_decay)
    )
    reasons: List[str] = []
    if age_decay >= 0.5:
        reasons.append("stale")
    if failure_decay >= 0.5:
        reasons.append("failed_reuse")
    if confidence_decay >= 0.5:
        reasons.append("low_confidence")
    if supersession_decay > 0:
        reasons.append("superseded")
    return DecayScore(
        memory_id=memory_id,
        age_decay=round(age_decay, 4),
        failure_decay=round(failure_decay, 4),
        confidence_decay=round(confidence_decay, 4),
        supersession_decay=round(supersession_decay, 4),
        combined=round(combined, 4),
        reasons=reasons,
    )


def cell_decay_report(
    cell_path: PathLike,
    *,
    reference_time: Optional[str] = None,
    half_life_days: int = DEFAULT_DECAY_HALF_LIFE_DAYS,
) -> Dict[str, Any]:
    """Return aggregate decay scoring for a Cell."""
    memories = _read_records(Path(cell_path) / "traces" / "approved.jsonl")
    superseded_ids = _superseded_trace_ids(memories)
    scores = [
        score_memory_decay(
            memory,
            reference_time=reference_time,
            half_life_days=half_life_days,
            superseded_ids=superseded_ids,
        ).to_dict()
        for memory in memories
    ]
    reason_counts: Counter[str] = Counter()
    for score in scores:
        reason_counts.update(score.get("reasons", []))
    average = round(sum(float(score["combined"]) for score in scores) / len(scores), 4) if scores else 0.0
    high = [score for score in scores if float(score["combined"]) >= 0.6]
    return {
        "memory_count": len(memories),
        "average_decay_score": average,
        "high_decay_count": len(high),
        "reason_counts": {key: reason_counts[key] for key in sorted(reason_counts)},
        "scores": scores,
        "notes": [
            "decay scoring is a transparent retrieval signal and review aid",
            "deprecation remains proposal-only and review-gated",
        ],
    }


def propose_deprecations(
    cell_path: PathLike,
    *,
    max_deprecations: Optional[int] = None,
    proposed_at: Optional[str] = None,
    min_uses_for_failure_rate: int = DEFAULT_MIN_USES_FOR_FAILURE_RATE,
    low_success_rate: float = DEFAULT_LOW_SUCCESS_RATE,
) -> List[JsonRecord]:
    """Return deprecation proposals without mutating Trace ledgers.

    Reasons currently emitted:
    - ``stale``: no recorded use.
    - ``harmful``: failures outnumber successes.
    - ``underperforming``: established success rate is below threshold.
    - ``unsupported``: source Fragment references are missing.
    - ``superseded``: another approved Trace has the same normalized statement.
    """
    cell = Path(cell_path)
    traces = _read_records(cell / "traces" / "approved.jsonl")
    known_fragments = {
        str(row.get("fragment_id"))
        for row in _read_records(cell / "ledger" / "fragments.jsonl")
        if row.get("fragment_id") is not None
    }
    duplicate_ids = _superseded_trace_ids(traces)
    timestamp = proposed_at or datetime.now(timezone.utc).isoformat()

    proposals: List[JsonRecord] = []
    for trace in traces:
        trace_id = str(trace.get("trace_id") or "")
        use_count = int(trace.get("use_count") or 0)
        success_count = int(trace.get("success_count") or 0)
        failure_count = int(trace.get("failure_count") or 0)
        reasons: List[str] = []
        details: Dict[str, Any] = {}

        if use_count == 0:
            reasons.append("stale")
        if failure_count > success_count and failure_count > 0:
            reasons.append("harmful")
        if use_count >= min_uses_for_failure_rate:
            success_rate = success_count / use_count if use_count else 0.0
            if success_rate < low_success_rate:
                reasons.append("underperforming")
                details["success_rate"] = round(success_rate, 4)

        missing_fragments = [
            fragment_id
            for fragment_id in trace.get("source_fragment_ids", [])
            if str(fragment_id) not in known_fragments
        ]
        if missing_fragments:
            reasons.append("unsupported")
            details["missing_fragment_ids"] = missing_fragments
        if trace_id in duplicate_ids:
            reasons.append("superseded")
            details["duplicate_statement"] = trace.get("statement")

        if reasons:
            proposals.append(
                {
                    "proposal_id": _proposal_id(trace_id, reasons),
                    "proposal_status": "proposed",
                    "trace_id": trace.get("trace_id"),
                    "statement": trace.get("statement"),
                    "reasons": sorted(reasons),
                    "details": details,
                    "confidence": trace.get("confidence"),
                    "use_count": use_count,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "proposed_at": timestamp,
                }
            )

    proposals.sort(key=lambda item: (-len(item["reasons"]), str(item.get("trace_id") or "")))
    if max_deprecations is not None:
        return proposals[:max_deprecations]
    return proposals


def append_deprecation_proposals(
    cell_path: PathLike, proposals: List[JsonRecord]
) -> int:
    """Append deprecation proposals to ledger/deprecation_proposals.jsonl."""
    path = Path(cell_path) / "ledger" / "deprecation_proposals.jsonl"
    for proposal in proposals:
        append_jsonl(path, proposal)
    return len(proposals)


def decay_summary(cell_path: PathLike) -> Dict[str, Any]:
    """Return aggregate proposal counts by reason for a Cell."""
    traces = _read_records(Path(cell_path) / "traces" / "approved.jsonl")
    proposals = propose_deprecations(cell_path)
    counts: Counter[str] = Counter()
    for proposal in proposals:
        counts.update(proposal.get("reasons", []))
    return {
        "total_approved": len(traces),
        "total_deprecation_proposals": len(proposals),
        "reasons_breakdown": {key: counts[key] for key in sorted(counts)},
        "stale_count": counts.get("stale", 0),
        "harmful_count": counts.get("harmful", 0),
        "underperforming_count": counts.get("underperforming", 0),
        "superseded_count": counts.get("superseded", 0),
        "unsupported_count": counts.get("unsupported", 0),
    }


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_decay(memory: JsonRecord, *, reference: datetime, half_life_days: int) -> float:
    if half_life_days <= 0:
        return 0.0
    timestamp = None
    for key in ("last_used_at", "last_retrieved_at", "promoted_at", "created_at", "observed_at"):
        timestamp = _parse_time(memory.get(key))
        if timestamp is not None:
            break
    if timestamp is None:
        return 0.0
    age_days = max(0.0, (reference - timestamp).total_seconds() / 86400.0)
    return _clamp01(1.0 - math.exp(-math.log(2) * age_days / half_life_days))


def _failure_decay(memory: JsonRecord) -> float:
    success_count = int(memory.get("success_count") or 0)
    failure_count = int(memory.get("failure_count") or 0)
    total = success_count + failure_count
    if total <= 0:
        return 0.0
    return _clamp01(failure_count / total)


def _confidence_decay(memory: JsonRecord) -> float:
    confidence = memory.get("confidence")
    if not isinstance(confidence, (int, float)):
        return 0.0
    return _clamp01(1.0 - float(confidence))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _read_records(path: PathLike) -> List[JsonRecord]:
    path = Path(path)
    if not path.exists():
        return []
    return [record for _line, record in read_jsonl(path)]


def _superseded_trace_ids(traces: List[JsonRecord]) -> set[str]:
    by_statement: Dict[str, List[JsonRecord]] = defaultdict(list)
    for trace in traces:
        statement = str(trace.get("statement") or "").strip().lower()
        if statement:
            by_statement[statement].append(trace)

    superseded: set[str] = set()
    for group in by_statement.values():
        if len(group) < 2:
            continue
        ranked = sorted(
            group,
            key=lambda item: (
                float(item.get("confidence") or 0.0),
                int(item.get("success_count") or 0),
                str(item.get("trace_id") or ""),
            ),
            reverse=True,
        )
        for trace in ranked[1:]:
            if trace.get("trace_id") is not None:
                superseded.add(str(trace["trace_id"]))
    return superseded


def _proposal_id(trace_id: str, reasons: List[str]) -> str:
    reason_slug = "-".join(sorted(reasons))
    return f"deprecate-{trace_id}-{reason_slug}"
