"""Append-only audit helpers for ShyftR Cell ledgers."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from shyftr.ledger import append_jsonl, read_jsonl

PathLike = Union[str, Path]
JsonRecord = Dict[str, Any]


def append_audit_row(
    cell_path: PathLike,
    *,
    action: str,
    target_type: str,
    target_id: str,
    actor: str,
    rationale: str,
    metadata: Optional[Dict[str, Any]] = None,
    audit_id: Optional[str] = None,
    recorded_at: Optional[str] = None,
) -> JsonRecord:
    """Append one audit row to ``ledger/audit.jsonl``.

    The function never rewrites existing rows.  Optional ``audit_id`` and
    ``recorded_at`` parameters make deterministic tests and reproducible imports
    possible while production callers can rely on generated values.
    """
    row = build_audit_row(
        action=action,
        target_type=target_type,
        target_id=target_id,
        actor=actor,
        rationale=rationale,
        metadata=metadata,
        audit_id=audit_id,
        recorded_at=recorded_at,
    )
    append_jsonl(Path(cell_path) / "ledger" / "audit.jsonl", row)
    return row


def build_audit_row(
    *,
    action: str,
    target_type: str,
    target_id: str,
    actor: str,
    rationale: str,
    metadata: Optional[Dict[str, Any]] = None,
    audit_id: Optional[str] = None,
    recorded_at: Optional[str] = None,
) -> JsonRecord:
    """Build an audit row without writing it."""
    for field_name, value in {
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "actor": actor,
        "rationale": rationale,
    }.items():
        if not value:
            raise ValueError(f"{field_name} is required")
    return {
        "audit_id": audit_id or f"audit-{uuid4().hex}",
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "actor": actor,
        "rationale": rationale,
        "metadata": metadata or {},
        "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
    }


def read_audit_rows(cell_path: PathLike) -> List[JsonRecord]:
    """Read audit rows in append order."""
    path = Path(cell_path) / "ledger" / "audit.jsonl"
    if not path.exists():
        return []
    return [record for _line, record in read_jsonl(path)]


def read_audit_rows_for_target(cell_path: PathLike, target_id: str) -> List[JsonRecord]:
    """Read audit rows for one target ID in append order."""
    return [row for row in read_audit_rows(cell_path) if row.get("target_id") == target_id]


def read_audit_rows_by_action(cell_path: PathLike, action: str) -> List[JsonRecord]:
    """Read audit rows for one action in append order."""
    return [row for row in read_audit_rows(cell_path) if row.get("action") == action]


# ---------------------------------------------------------------------------
# Audit Sparks (low-authority challenger findings)
# ---------------------------------------------------------------------------


CHALLENGER_FINDING_CLASSIFICATIONS = frozenset({
    "direct_contradiction",
    "supersession",
    "scope_exception",
    "environment_specific",
    "temporal_update",
    "ambiguous_counterevidence",
    "policy_conflict",
    "implementation_drift",
})


def build_audit_spark(
    *,
    trace_id: str,
    classification: str,
    challenger: str,
    rationale: str,
    counter_evidence_source: str,
    cell_id: str = "",
    fragment_id: str = "",
    spark_id: Optional[str] = None,
    proposed_at: Optional[str] = None,
) -> JsonRecord:
    """Build an audit spark record without writing it.

    Parameters
    ----------
    trace_id : the Trace/Charge being challenged
    classification : one of CHALLENGER_FINDING_CLASSIFICATIONS
    challenger : identifier of the challenger (e.g. 'challenger-bot')
    rationale : human-readable explanation for the finding
    counter_evidence_source : where the counter-evidence was found
        (e.g. 'ledger/outcomes.jsonl:oc-a', 'charges/approved.jsonl:trace-b')
    cell_id : required cell identifier
    fragment_id : optional source fragment identifier
    spark_id : explicit id for deterministic tests; auto-generated if omitted
    proposed_at : explicit timestamp; auto-generated if omitted
    """
    if not classification:
        raise ValueError("classification is required")
    if classification not in CHALLENGER_FINDING_CLASSIFICATIONS:
        raise ValueError(
            f"Invalid classification '{classification}'. "
            f"Must be one of: {sorted(CHALLENGER_FINDING_CLASSIFICATIONS)}"
        )
    if not trace_id:
        raise ValueError("trace_id is required")
    if not cell_id:
        raise ValueError("cell_id is required")
    if not challenger:
        raise ValueError("challenger is required")
    cid = spark_id or f"spark-{uuid4().hex}"
    timestamp = proposed_at or datetime.now(timezone.utc).isoformat()
    return {
        "spark_id": cid,
        "trace_id": trace_id,
        "classification": classification,
        "action": "challenge",
        "challenger": challenger,
        "rationale": rationale,
        "counter_evidence_source": counter_evidence_source,
        "cell_id": cell_id,
        "fragment_id": fragment_id,
        "proposed_at": timestamp,
        "observed_at": timestamp,
    }


def append_audit_spark(
    cell_path: PathLike,
    *,
    trace_id: str,
    classification: str,
    challenger: str,
    rationale: str,
    counter_evidence_source: str,
    cell_id: str = "",
    fragment_id: str = "",
    spark_id: Optional[str] = None,
    proposed_at: Optional[str] = None,
) -> JsonRecord:
    """Append one audit spark to ``ledger/audit_sparks.jsonl``.

    Audit sparks are low-authority challenger findings that do not directly
    mutate Trace/Charge lifecycle ledgers. They are append-only and serve
    as evidence for human review or downstream sweep/proposal processing.
    """
    spark = build_audit_spark(
        trace_id=trace_id,
        classification=classification,
        challenger=challenger,
        rationale=rationale,
        counter_evidence_source=counter_evidence_source,
        cell_id=cell_id,
        fragment_id=fragment_id,
        spark_id=spark_id,
        proposed_at=proposed_at,
    )
    append_jsonl(Path(cell_path) / "ledger" / "audit_sparks.jsonl", spark)
    return spark


def read_audit_sparks(cell_path: PathLike) -> List[JsonRecord]:
    """Read audit sparks in append order."""
    path = Path(cell_path) / "ledger" / "audit_sparks.jsonl"
    if not path.exists():
        return []
    return [record for _line, record in read_jsonl(path)]


# ---------------------------------------------------------------------------
# Audit Reviews (human review decisions on audit findings)
# ---------------------------------------------------------------------------

AUDIT_REVIEW_RESOLUTIONS = frozenset({"accept", "reject"})

AUDIT_REVIEW_ACTIONS = frozenset({
    "mark_challenged",
    "propose_isolation",
    "propose_supersession",
    "propose_confidence_decrease",
    "request_rewrite",
    "no_action",
})


def build_audit_review(
    *,
    audit_id: str,
    resolution: str,
    reviewer: str,
    rationale: str,
    review_actions: Optional[List[str]] = None,
    review_id: Optional[str] = None,
    reviewed_at: Optional[str] = None,
) -> JsonRecord:
    """Build an audit review record without writing it.

    Parameters
    ----------
    audit_id : the audit finding being reviewed (from audit.jsonl or audit_sparks.jsonl)
    resolution : ``accept`` or ``reject``
    reviewer : identifier of the human or automated reviewer
    rationale : human-readable justification for the review decision
    review_actions : optional list of follow-up actions taken on accepted findings
        (e.g. ``["mark_challenged"]``, ``["propose_isolation", "propose_confidence_decrease"]``)
    review_id : explicit id for deterministic tests; auto-generated if omitted
    reviewed_at : explicit timestamp; auto-generated if omitted
    """
    if not audit_id:
        raise ValueError("audit_id is required")
    if not resolution:
        raise ValueError("resolution is required")
    if resolution not in AUDIT_REVIEW_RESOLUTIONS:
        raise ValueError(
            f"Invalid resolution '{resolution}'. "
            f"Must be one of: {sorted(AUDIT_REVIEW_RESOLUTIONS)}"
        )
    if not reviewer:
        raise ValueError("reviewer is required")
    if not rationale:
        raise ValueError("rationale is required")
    if review_actions:
        invalid = [a for a in review_actions if a not in AUDIT_REVIEW_ACTIONS]
        if invalid:
            raise ValueError(
                f"Invalid review action(s): {invalid}. "
                f"Valid actions: {sorted(AUDIT_REVIEW_ACTIONS)}"
            )
    rid = review_id or f"review-{uuid4().hex}"
    timestamp = reviewed_at or datetime.now(timezone.utc).isoformat()
    return {
        "review_id": rid,
        "audit_id": audit_id,
        "resolution": resolution,
        "reviewer": reviewer,
        "rationale": rationale,
        "review_actions": review_actions or [],
        "reviewed_at": timestamp,
    }


def append_audit_review(
    cell_path: PathLike,
    *,
    audit_id: str,
    resolution: str,
    reviewer: str,
    rationale: str,
    review_actions: Optional[List[str]] = None,
    review_id: Optional[str] = None,
    reviewed_at: Optional[str] = None,
) -> JsonRecord:
    """Append one audit review to ``ledger/audit_reviews.jsonl``.

    Audit reviews represent human or automated decisions on earlier audit
    findings (sparks or rows). They are append-only and never rewrite past
    records.

    On an ``accept`` resolution, the caller should execute the
    ``review_actions`` (e.g. mark a Charge as challenged, propose isolation)
    as a follow-up step.
    """
    review = build_audit_review(
        audit_id=audit_id,
        resolution=resolution,
        reviewer=reviewer,
        rationale=rationale,
        review_actions=review_actions,
        review_id=review_id,
        reviewed_at=reviewed_at,
    )
    append_jsonl(Path(cell_path) / "ledger" / "audit_reviews.jsonl", review)
    return review


def read_audit_reviews(cell_path: PathLike) -> List[JsonRecord]:
    """Read audit reviews in append order."""
    path = Path(cell_path) / "ledger" / "audit_reviews.jsonl"
    if not path.exists():
        return []
    return [record for _line, record in read_jsonl(path)]


def read_audit_reviews_for_audit(cell_path: PathLike, audit_id: str) -> List[JsonRecord]:
    """Read audit reviews for a specific audit finding, in append order."""
    return [
        row for row in read_audit_reviews(cell_path)
        if row.get("audit_id") == audit_id
    ]


def audit_summary(cell_path: PathLike) -> JsonRecord:
    """Return a read-only summary of audit sparks and their review state.

    This review-surface helper makes challenger findings legible without
    mutating ledgers or introducing any new durable state.
    """
    sparks = read_audit_sparks(cell_path)
    reviews_by_audit_id: Dict[str, List[JsonRecord]] = {}
    for review in read_audit_reviews(cell_path):
        audit_id = str(review.get("audit_id") or "")
        if not audit_id:
            continue
        reviews_by_audit_id.setdefault(audit_id, []).append(review)

    counts: Dict[str, int] = {}
    review_state_counts: Dict[str, int] = {"reviewed": 0, "unreviewed": 0}
    findings: List[JsonRecord] = []
    for spark in sparks:
        classification = str(spark.get("classification") or "unknown")
        counts[classification] = counts.get(classification, 0) + 1
        audit_id = str(spark.get("spark_id") or "")
        linked_reviews = reviews_by_audit_id.get(audit_id, [])
        review_state = "reviewed" if linked_reviews else "unreviewed"
        review_state_counts[review_state] += 1
        findings.append(
            {
                "audit_id": audit_id,
                "trace_id": spark.get("trace_id"),
                "classification": classification,
                "review_state": review_state,
                "review_count": len(linked_reviews),
                "latest_resolution": linked_reviews[-1].get("resolution") if linked_reviews else None,
                "latest_review_actions": linked_reviews[-1].get("review_actions", []) if linked_reviews else [],
                "counter_evidence_source": spark.get("counter_evidence_source", ""),
                "proposed_at": spark.get("proposed_at") or spark.get("observed_at"),
            }
        )

    findings.sort(key=lambda item: (str(item.get("classification") or ""), str(item.get("audit_id") or "")))
    return {
        "spark_count": len(sparks),
        "counts": dict(sorted(counts.items())),
        "review_state_counts": review_state_counts,
        "findings": findings,
    }
