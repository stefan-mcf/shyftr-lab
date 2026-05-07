"""Public-safe retrieval usage log contract for runtime clients.

This module exposes bounded reads of ``ledger/retrieval_logs.jsonl`` so generic
clients can audit pack/loadout usage without starting local evaluation track effectiveness
metrics or leaking raw operational state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from shyftr.ledger import read_jsonl

PathLike = Union[str, Path]

_PUBLIC_RETRIEVAL_LOG_FIELDS = (
    "retrieval_id",
    "loadout_id",
    "query",
    "generated_at",
    "selected_ids",
    "candidate_ids",
    "caution_ids",
    "suppressed_ids",
    "score_traces",
    "total_items",
    "total_tokens",
    "max_items",
    "max_tokens",
    "runtime_id",
    "task_id",
    "cell_id",
)


def list_retrieval_logs(
    cell_path: PathLike,
    *,
    loadout_id: Optional[str] = None,
    query: Optional[str] = None,
    selected_memory_id: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Return sanitized retrieval usage logs for a Cell.

    Filters are exact for loadout id and selected memory id, case-insensitive
    substring for query, and newest-last ledger order is preserved. This is
    usage evidence only; it does not compute effectiveness metrics.
    """

    if limit < 1:
        raise ValueError("limit must be at least 1")
    if limit > 200:
        raise ValueError("limit must be at most 200")

    ledger = Path(cell_path) / "ledger" / "retrieval_logs.jsonl"
    if not ledger.exists():
        raise ValueError(f"retrieval logs ledger does not exist for Cell: {ledger}")

    records: List[Dict[str, Any]] = []
    query_filter = query.lower() if query else None
    for line_number, row in read_jsonl(ledger):
        sanitized = sanitize_retrieval_log(row)
        if loadout_id and sanitized.get("loadout_id") != loadout_id:
            continue
        if query_filter and query_filter not in str(sanitized.get("query") or "").lower():
            continue
        if selected_memory_id and selected_memory_id not in set(_ids(sanitized.get("selected_ids"))):
            continue
        sanitized["line_number"] = line_number
        records.append(sanitized)

    return {
        "status": "ok",
        "usage_evidence_only": True,
        "total_matched": len(records),
        "logs": records[-limit:],
    }


def sanitize_retrieval_log(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return only public contract fields from a retrieval log row."""

    sanitized = {key: row[key] for key in _PUBLIC_RETRIEVAL_LOG_FIELDS if key in row}
    for key in ("selected_ids", "candidate_ids", "caution_ids", "suppressed_ids"):
        if key in sanitized:
            sanitized[key] = _ids(sanitized[key])
    score_traces = sanitized.get("score_traces")
    selected_ids = set(_ids(sanitized.get("selected_ids")))
    if isinstance(score_traces, dict):
        sanitized["score_traces"] = {
            str(item_id): trace
            for item_id, trace in score_traces.items()
            if item_id in selected_ids
        }
    return sanitized


def _ids(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


__all__ = ["list_retrieval_logs", "sanitize_retrieval_log"]
