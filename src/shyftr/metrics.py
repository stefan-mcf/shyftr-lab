"""Public-safe local evaluation metrics for ShyftR Cells.

Metrics are deterministic projections over append-only Cell ledgers. They do
not judge task quality with an LLM, mutate memory records, or change regulator
state. The output is intended for local controlled-pilot inspection and status
evidence.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

from .decay import cell_decay_report
from .ledger import read_jsonl

PathLike = Union[str, Path]
JsonRecord = Dict[str, Any]


def memory_effectiveness_metrics(cell_path: PathLike) -> Dict[str, Any]:
    """Return per-memory retrieval/usefulness metrics for a Cell.

    Counts are derived from ``ledger/retrieval_logs.jsonl`` and
    ``ledger/outcomes.jsonl``. ``memory_id`` is the primary public-facing key;
    raw compatibility ids are not needed in the returned rows.
    """
    cell = Path(cell_path)
    memories = _read_records(cell / "traces" / "approved.jsonl")
    retrieval_logs = _read_records(cell / "ledger" / "retrieval_logs.jsonl")
    feedback_rows = _read_records(cell / "ledger" / "outcomes.jsonl")

    memory_ids = [str(row.get("trace_id")) for row in memories if row.get("trace_id")]
    retrieval_count: Counter[str] = Counter()
    useful_count: Counter[str] = Counter()
    harmful_count: Counter[str] = Counter()
    missed_count: Counter[str] = Counter()
    candidate_count: Counter[str] = Counter()

    for row in retrieval_logs:
        for memory_id in _string_list(row.get("selected_ids")):
            retrieval_count[memory_id] += 1
        for memory_id in _string_list(row.get("candidate_ids")):
            candidate_count[memory_id] += 1

    for row in feedback_rows:
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        for memory_id in _dedupe(_memory_ids(row, "useful") + _memory_ids(meta, "useful")):
            useful_count[memory_id] += 1
        for memory_id in _dedupe(_memory_ids(row, "harmful") + _memory_ids(meta, "harmful")):
            harmful_count[memory_id] += 1
        for memory_id in _pack_miss_ids(row):
            missed_count[memory_id] += 1

    rows: List[JsonRecord] = []
    all_ids = sorted(set(memory_ids) | set(retrieval_count) | set(candidate_count) | set(useful_count) | set(harmful_count) | set(missed_count))
    for memory_id in all_ids:
        retrieved = retrieval_count[memory_id]
        useful = useful_count[memory_id]
        harmful = harmful_count[memory_id]
        missed = missed_count[memory_id]
        applied_feedback = useful + harmful
        precision = _ratio(useful, retrieved)
        reuse_success_rate = _ratio(useful, applied_feedback)
        miss_rate = _ratio(missed, retrieved)
        rows.append(
            {
                "memory_id": memory_id,
                "retrieval_count": retrieved,
                "candidate_count": candidate_count[memory_id],
                "successful_reuse_count": useful,
                "failed_reuse_count": harmful + missed,
                "harmful_feedback_count": harmful,
                "pack_miss_count": missed,
                "precision_proxy": precision,
                "reuse_success_rate": reuse_success_rate,
                "miss_rate": miss_rate,
                "confidence_adjustment": confidence_adjustment_from_counts(useful, harmful + missed),
            }
        )
    return {
        "memory_count": len(memory_ids),
        "retrieval_log_count": len(retrieval_logs),
        "feedback_count": len(feedback_rows),
        "memories": rows,
    }


def retrieval_quality_metrics(cell_path: PathLike) -> Dict[str, Any]:
    """Return cell-level retrieval quality proxies.

    ``precision_proxy`` is useful feedback divided by selected retrievals.
    ``recall_proxy`` is useful feedback divided by useful feedback plus pack
    misses. Both are deterministic feedback-derived proxies, not external task
    evaluation claims.
    """
    effectiveness = memory_effectiveness_metrics(cell_path)
    rows = effectiveness["memories"]
    selected_total = sum(int(row["retrieval_count"]) for row in rows)
    useful_total = sum(int(row["successful_reuse_count"]) for row in rows)
    failed_total = sum(int(row["failed_reuse_count"]) for row in rows)
    miss_total = sum(int(row["pack_miss_count"]) for row in rows)
    precision = _ratio(useful_total, selected_total)
    recall = _ratio(useful_total, useful_total + miss_total)
    f1 = 0.0 if precision + recall == 0 else round(2 * precision * recall / (precision + recall), 4)
    return {
        "selected_memory_count": selected_total,
        "useful_feedback_count": useful_total,
        "failed_feedback_count": failed_total,
        "pack_miss_count": miss_total,
        "precision_proxy": precision,
        "recall_proxy": recall,
        "f1_proxy": f1,
        "notes": [
            "metrics are local deterministic proxies derived from pack usage and feedback ledgers",
            "no external evaluator, hosted service, or production claim is implied",
        ],
    }


def confidence_adjustment_from_counts(successful_reuse_count: int, failed_reuse_count: int) -> float:
    """Return a bounded confidence delta from feedback counts.

    This mirrors the existing public-safe feedback model: useful feedback raises
    confidence modestly; failed or missed reuse lowers confidence more strongly.
    The result is a proposed adjustment, not a direct write.
    """
    delta = (successful_reuse_count * 0.05) - (failed_reuse_count * 0.10)
    return round(max(-1.0, min(1.0, delta)), 4)


def cell_health_metrics(cell_path: PathLike) -> Dict[str, Any]:
    """Return aggregate health metrics combining retrieval, confidence, and decay."""
    quality = retrieval_quality_metrics(cell_path)
    effectiveness = memory_effectiveness_metrics(cell_path)
    decay = cell_decay_report(cell_path)
    confidence_values = [
        float(row.get("confidence"))
        for row in _read_records(Path(cell_path) / "traces" / "approved.jsonl")
        if isinstance(row.get("confidence"), (int, float))
    ]
    average_confidence = _ratio(sum(confidence_values), len(confidence_values)) if confidence_values else 0.0
    average_decay = float(decay.get("average_decay_score") or 0.0)

    health_score = round(
        max(
            0.0,
            min(
                1.0,
                (0.35 * quality["precision_proxy"])
                + (0.20 * quality["recall_proxy"])
                + (0.25 * average_confidence)
                + (0.20 * (1.0 - average_decay)),
            ),
        ),
        4,
    )
    return {
        "memory_count": effectiveness["memory_count"],
        "retrieval_quality": quality,
        "average_confidence": round(average_confidence, 4),
        "decay_summary": decay,
        "health_score": health_score,
        "posture": "local controlled-pilot metric; review-gated and append-only",
    }


def metrics_summary(cell_path: PathLike) -> Dict[str, Any]:
    """Return the complete Phase 10 metrics summary for a Cell."""
    return {
        "retrieval_quality": retrieval_quality_metrics(cell_path),
        "effectiveness": memory_effectiveness_metrics(cell_path),
        "cell_health": cell_health_metrics(cell_path),
    }


def _read_records(path: PathLike) -> List[JsonRecord]:
    path = Path(path)
    if not path.exists():
        return []
    return [record for _line, record in read_jsonl(path)]


def _string_list(value: Any) -> List[str]:
    if not value:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _memory_ids(container: Mapping[str, Any], kind: str) -> List[str]:
    keys = (
        f"{kind}_memory_ids",
        f"{kind}_trace_ids",
        f"{kind}_charge_ids",
    )
    ids: List[str] = []
    for key in keys:
        ids.extend(_string_list(container.get(key)))
    return list(dict.fromkeys(ids))


def _pack_miss_ids(row: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    details = row.get("pack_miss_details") or []
    if isinstance(details, list):
        for item in details:
            if isinstance(item, Mapping):
                memory_id = item.get("memory_id") or item.get("charge_id") or item.get("trace_id")
                if memory_id:
                    ids.append(str(memory_id))
            elif item:
                ids.append(str(item))
    ids.extend(_string_list(row.get("pack_misses")))
    return list(dict.fromkeys(ids))


def _dedupe(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(values))


def _ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)
