from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from uuid import uuid4

from .ledger import append_jsonl, read_jsonl
from .memory_classes import resolve_memory_type
from .models import Fragment, Trace
from .review import latest_review

PathLike = Union[str, Path]


class PromotionError(ValueError):
    """Raised when a Fragment cannot be promoted to a Trace."""


def promote_fragment(
    cell_path: PathLike,
    fragment_id: str,
    *,
    promoter: str,
    statement: Optional[str] = None,
    rationale: Optional[str] = None,
    memory_type: Optional[str] = None,
) -> Trace:
    """Promote the latest-approved Fragment into an approved Trace."""
    cell = Path(cell_path)
    if not promoter:
        raise PromotionError("promoter is required")

    existing = _existing_promotion(cell, fragment_id)
    if existing is not None:
        trace_id = existing["trace_id"]
        trace = _find_trace(cell, trace_id)
        if trace is None:
            raise PromotionError(f"Promotion references missing Trace: {trace_id}")
        return trace

    review = latest_review(cell, fragment_id)
    if review is None or review.get("review_status") != "approved":
        raise PromotionError("Fragment must have latest review approved before promotion")

    fragment = _find_fragment(cell, fragment_id)
    if fragment is None:
        raise PromotionError(f"Unknown fragment id: {fragment_id}")

    trace = Trace(
        trace_id=f"trace-{uuid4().hex}",
        cell_id=fragment.cell_id,
        statement=statement or fragment.text,
        source_fragment_ids=[fragment.fragment_id],
        kind=fragment.kind,
        memory_type=resolve_memory_type(memory_type, kind=fragment.kind, trust_tier="trace"),
        rationale=rationale or review.get("rationale"),
        status="approved",
        confidence=fragment.confidence,
        tags=fragment.tags,
    )
    append_jsonl(cell / "traces" / "approved.jsonl", trace.to_dict())
    append_jsonl(
        cell / "ledger" / "promotions.jsonl",
        {
            "promotion_id": f"promo-{uuid4().hex}",
            "fragment_id": fragment.fragment_id,
            "candidate_id": fragment.fragment_id,
            "trace_id": trace.trace_id,
            "memory_id": trace.trace_id,
            "source_id": fragment.source_id,
            "evidence_id": fragment.source_id,
            "source_fragment_ids": [fragment.fragment_id],
            "candidate_ids": [fragment.fragment_id],
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "promoter": promoter,
            "review_id": review.get("review_id"),
        },
    )
    return trace


def _existing_promotion(cell: Path, fragment_id: str) -> Optional[Dict[str, Any]]:
    for _, record in read_jsonl(cell / "ledger" / "promotions.jsonl"):
        if record.get("fragment_id") == fragment_id:
            return record
    return None


def _find_fragment(cell: Path, fragment_id: str) -> Optional[Fragment]:
    for _, record in read_jsonl(cell / "ledger" / "fragments.jsonl"):
        if record.get("fragment_id") == fragment_id:
            return Fragment.from_dict(record)
    return None


def _find_trace(cell: Path, trace_id: str) -> Optional[Trace]:
    for _, record in read_jsonl(cell / "traces" / "approved.jsonl"):
        if record.get("trace_id") == trace_id:
            return Trace.from_dict(record)
    return None
