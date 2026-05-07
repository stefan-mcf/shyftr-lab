"""Doctrine proposal generation from high-resonance Alloys.

Doctrine is intentionally review-gated.  This module can append proposed
Doctrine records to ``doctrine/proposed.jsonl`` and can perform an explicit
approval step, but the proposal pipeline never writes to
``doctrine/approved.jsonl`` on its own.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from ..ledger import append_jsonl, read_jsonl
from ..models import Alloy, DoctrineProposal
from ..resonance import ResonanceScore

PathLike = Union[str, Path]


def _doctrine_id_for(alloy_ids: Sequence[str], scope: str) -> str:
    """Return a deterministic Doctrine proposal ID."""
    seed = f"{'|'.join(sorted(alloy_ids))}|{scope.strip().lower()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"doctrine-{digest}"


def _build_doctrine_statement(alloys: Sequence[Alloy], scope: str) -> str:
    summaries = "; ".join(alloy.summary for alloy in sorted(alloys, key=lambda item: item.alloy_id))
    return f"Doctrine proposal ({scope}): {summaries}"


def propose_doctrine(
    high_resonance_alloys: Sequence[Alloy],
    *,
    scope: str = "cross-cell",
    require_min_alloys: int = 1,
) -> List[DoctrineProposal]:
    """Create pending Doctrine proposals from already-filtered Alloys."""
    if len(high_resonance_alloys) < require_min_alloys:
        return []
    alloy_ids = sorted(alloy.alloy_id for alloy in high_resonance_alloys)
    return [
        DoctrineProposal(
            doctrine_id=_doctrine_id_for(alloy_ids, scope),
            source_alloy_ids=alloy_ids,
            scope=scope,
            statement=_build_doctrine_statement(high_resonance_alloys, scope),
            review_status="pending",
        )
    ]


def propose_doctrine_from_resonance(
    alloys: Sequence[Alloy],
    resonance_scores: Iterable[ResonanceScore],
    *,
    min_resonance: float = 0.50,
    scope: str = "cross-cell",
    require_min_alloys: int = 1,
) -> List[DoctrineProposal]:
    """Filter high-resonance Alloys and create pending Doctrine proposals."""
    high_ids = {
        score.alloy_id
        for score in resonance_scores
        if score.score >= min_resonance and score.cell_diversity >= 2
    }
    selected = [alloy for alloy in sorted(alloys, key=lambda item: item.alloy_id) if alloy.alloy_id in high_ids]
    return propose_doctrine(
        selected,
        scope=scope,
        require_min_alloys=require_min_alloys,
    )


def append_doctrine_proposals(
    cell_path: PathLike,
    proposals: Sequence[DoctrineProposal],
) -> int:
    """Append proposals to doctrine/proposed.jsonl and return write count."""
    ledger_path = Path(cell_path) / "doctrine" / "proposed.jsonl"
    count = 0
    for proposal in proposals:
        append_jsonl(ledger_path, proposal.to_dict())
        count += 1
    return count


def read_proposed_doctrines(cell_path: PathLike) -> List[DoctrineProposal]:
    """Read Doctrine proposals from doctrine/proposed.jsonl."""
    ledger_path = Path(cell_path) / "doctrine" / "proposed.jsonl"
    if not ledger_path.exists():
        return []
    return [DoctrineProposal.from_dict(record) for _line, record in read_jsonl(ledger_path)]


def read_approved_doctrines(cell_path: PathLike) -> List[DoctrineProposal]:
    """Read reviewed Doctrine records from doctrine/approved.jsonl."""
    ledger_path = Path(cell_path) / "doctrine" / "approved.jsonl"
    if not ledger_path.exists():
        return []
    return [DoctrineProposal.from_dict(record) for _line, record in read_jsonl(ledger_path)]


def approve_doctrine(cell_path: PathLike, doctrine_id: str) -> Optional[DoctrineProposal]:
    """Explicitly approve one pending Doctrine proposal.

    Approval appends an approved copy to ``doctrine/approved.jsonl`` and leaves
    ``doctrine/proposed.jsonl`` untouched for auditability.  Re-approving the
    same Doctrine ID is idempotent.
    """
    approved = {proposal.doctrine_id: proposal for proposal in read_approved_doctrines(cell_path)}
    if doctrine_id in approved:
        return approved[doctrine_id]

    for proposal in read_proposed_doctrines(cell_path):
        if proposal.doctrine_id != doctrine_id:
            continue
        approved_proposal = DoctrineProposal(
            doctrine_id=proposal.doctrine_id,
            source_alloy_ids=proposal.source_alloy_ids,
            scope=proposal.scope,
            statement=proposal.statement,
            review_status="approved",
        )
        append_jsonl(Path(cell_path) / "doctrine" / "approved.jsonl", approved_proposal.to_dict())
        return approved_proposal
    return None


def distill_doctrine(
    cell_path: PathLike,
    high_resonance_alloys: Sequence[Alloy],
    *,
    scope: str = "cross-cell",
    require_min_alloys: int = 1,
) -> Dict[str, Any]:
    """Append Doctrine proposals only; never silently approve them."""
    before_approved = len(read_approved_doctrines(cell_path))
    proposals = propose_doctrine(
        high_resonance_alloys,
        scope=scope,
        require_min_alloys=require_min_alloys,
    )
    appended = append_doctrine_proposals(cell_path, proposals)
    after_approved = len(read_approved_doctrines(cell_path))
    return {
        "proposal_count": appended,
        "proposal_ids": [proposal.doctrine_id for proposal in proposals],
        "source_alloy_ids": sorted(
            {alloy_id for proposal in proposals for alloy_id in proposal.source_alloy_ids}
        ),
        "scope": scope,
        "approved_count_delta": after_approved - before_approved,
    }


# ---------------------------------------------------------------------------
# multi-cell milestone public shared-rule proposal workflow
# ---------------------------------------------------------------------------
from datetime import datetime as _datetime, timezone as _timezone
from uuid import uuid4 as _uuid4


def _now() -> str:
    return _datetime.now(_timezone.utc).isoformat()


def _public_rule_fingerprint(source_record_ids: Sequence[str], source_cell_ids: Sequence[str], scope: str, statement: str) -> str:
    seed = "|".join(sorted(source_record_ids)) + "|" + "|".join(sorted(source_cell_ids)) + "|" + scope + "|" + statement.strip().lower()
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _read_rows(path: Path) -> List[Dict[str, Any]]:
    return [record for _, record in read_jsonl(path)] if path.exists() else []


def propose_rule_from_resonance(
    cell_path: PathLike,
    resonance_results: Sequence[Dict[str, Any]],
    *,
    scope: str,
    statement: Optional[str] = None,
    reviewer_status: str = "pending",
    min_cell_diversity: int = 2,
) -> Dict[str, Any]:
    if not scope:
        raise ValueError("rule scope is required")
    source_cell_ids = sorted({cell for row in resonance_results for cell in row.get("source_cell_ids", [])})
    if len(source_cell_ids) < min_cell_diversity and scope in {"global", "cross-cell", "shared"}:
        raise ValueError("global/shared rule proposals require minimum cell diversity")
    source_record_ids = sorted({record_id for row in resonance_results for record_id in row.get("source_record_ids", [])})
    source_resonance_ids = sorted({row.get("resonance_id") for row in resonance_results if row.get("resonance_id")})
    if not source_record_ids:
        raise ValueError("rule proposal requires source records")
    rule_statement = statement or f"Shared scoped rule from {len(source_cell_ids)} cells: {', '.join(source_record_ids)}"
    fingerprint = _public_rule_fingerprint(source_record_ids, source_cell_ids, scope, rule_statement)
    proposed_path = Path(cell_path) / "ledger" / "rules" / "proposed.jsonl"
    rejected_fingerprints = {row.get("fingerprint") for row in _read_rows(proposed_path) if row.get("reviewer_status") == "rejected" or row.get("review_status") == "rejected"}
    if fingerprint in rejected_fingerprints:
        raise ValueError("rejected duplicate rule proposal from same evidence")
    for row in _read_rows(proposed_path):
        if row.get("fingerprint") == fingerprint:
            return row
    proposal = {
        "rule_id": f"rule-{fingerprint}",
        "source_resonance_ids": source_resonance_ids,
        "source_pattern_ids": [rid for rid in source_record_ids if str(rid).startswith(("pat", "alloy"))],
        "source_memory_ids": [rid for rid in source_record_ids if not str(rid).startswith(("pat", "alloy"))],
        "source_record_ids": source_record_ids,
        "source_cell_ids": source_cell_ids,
        "proposed_scope": scope,
        "scope": scope,
        "minimum_cell_diversity_evidence": len(source_cell_ids),
        "confidence_summary": {"max_score": max(float(row.get("score", 0.0)) for row in resonance_results), "result_count": len(resonance_results)},
        "reviewer_status": reviewer_status,
        "review_status": reviewer_status,
        "reviewer_id": None,
        "decision_timestamp": None,
        "provenance": {"source_cell_ids": source_cell_ids, "source_record_ids": source_record_ids, "source_resonance_ids": source_resonance_ids, "derivation_kind": "shared_rule_proposal"},
        "statement": rule_statement,
        "fingerprint": fingerprint,
        "created_at": _now(),
    }
    append_jsonl(proposed_path, proposal)
    return proposal


def list_rule_proposals(cell_path: PathLike, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _read_rows(Path(cell_path) / "ledger" / "rules" / "proposed.jsonl")
    if status:
        rows = [row for row in rows if row.get("review_status") == status or row.get("reviewer_status") == status]
    return rows


def review_rule_proposal(cell_path: PathLike, rule_id: str, decision: str, reviewer_id: str = "operator", rationale: str = "reviewed") -> Dict[str, Any]:
    if decision not in {"approve", "reject"}:
        raise ValueError("decision must be approve or reject")
    rows = {row.get("rule_id"): row for row in list_rule_proposals(cell_path)}
    if rule_id not in rows:
        raise ValueError(f"Unknown rule_id: {rule_id}")
    original = rows[rule_id]
    status = "approved" if decision == "approve" else "rejected"
    event = dict(original)
    event.update({"review_status": status, "reviewer_status": status, "reviewer_id": reviewer_id, "decision_timestamp": _now(), "review_rationale": rationale})
    append_jsonl(Path(cell_path) / "ledger" / "rules" / "proposed.jsonl", event)
    if decision == "approve":
        approved = dict(event)
        approved["review_status"] = "approved"
        approved["trust_label"] = "local"
        append_jsonl(Path(cell_path) / "ledger" / "rules" / "approved.jsonl", approved)
    return event


def approve_rule_proposal(cell_path: PathLike, rule_id: str, reviewer_id: str = "operator", rationale: str = "approved") -> Dict[str, Any]:
    return review_rule_proposal(cell_path, rule_id, "approve", reviewer_id=reviewer_id, rationale=rationale)


def reject_rule_proposal(cell_path: PathLike, rule_id: str, reviewer_id: str = "operator", rationale: str = "rejected") -> Dict[str, Any]:
    return review_rule_proposal(cell_path, rule_id, "reject", reviewer_id=reviewer_id, rationale=rationale)
