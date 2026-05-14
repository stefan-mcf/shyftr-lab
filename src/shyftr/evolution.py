"""Review-gated memory evolution proposals for ShyftR.

This module is intentionally public-safe and deterministic. It scans append-only
cell ledgers, emits proposal records, simulates projection deltas, and applies
accepted lifecycle decisions only through existing append-only mutation helpers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union
from uuid import uuid4

from .ledger import append_jsonl, read_jsonl

PathLike = Union[str, Path]
JsonRecord = Dict[str, Any]

PROPOSALS_LEDGER = Path("ledger/evolution/proposals.jsonl")
REVIEWS_LEDGER = Path("ledger/evolution/reviews.jsonl")
SIMULATION_LEDGER = Path("ledger/evolution/simulations.jsonl")
ALLOWED_PROPOSAL_TYPES = {
    "split_candidate",
    "merge_memories",
    "supersede_memory",
    "challenge_memory",
    "deprecate_memory",
    "replace_memory",
    "forget_memory",
    "redact_memory",
    "promote_missing_memory",
}
RETRIEVAL_AFFECTING_TYPES = {
    "merge_memories",
    "supersede_memory",
    "challenge_memory",
    "deprecate_memory",
    "replace_memory",
    "forget_memory",
    "redact_memory",
}
VALID_DECISIONS = {"accept", "reject", "defer"}


@dataclass(frozen=True)
class EvolutionProposal:
    proposal_id: str
    proposal_type: str
    target_ids: List[str] = field(default_factory=list)
    candidate_ids: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 0.5
    risk_level: str = "medium"
    projection_delta: Dict[str, Any] = field(default_factory=dict)
    requires_review: bool = True
    auto_apply: bool = False
    requires_simulation: bool = False
    created_at: str = field(default_factory=lambda: _now())
    proposed_memory: Optional[Dict[str, Any]] = None
    proposed_children: List[Dict[str, Any]] = field(default_factory=list)
    review_status: str = "pending"
    rollback_notes: str = "Reject or supersede this proposal; ledger truth remains append-only."

    def __post_init__(self) -> None:
        if self.proposal_type not in ALLOWED_PROPOSAL_TYPES:
            raise ValueError(f"invalid proposal_type: {self.proposal_type}")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.evidence_refs:
            raise ValueError("evidence_refs must include at least one evidence or synthetic fixture reference")
        if not self.rationale.strip():
            raise ValueError("rationale is required")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool) or not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.risk_level not in {"low", "medium", "high"}:
            raise ValueError("risk_level must be low, medium, or high")
        if self.requires_review is not True:
            raise ValueError("evolution proposals always require review")
        if self.auto_apply is not False:
            raise ValueError("public evolution proposals cannot auto-apply")
        if self.proposal_type in RETRIEVAL_AFFECTING_TYPES and not self.requires_simulation:
            raise ValueError("retrieval-affecting proposals require simulation")

    def to_dict(self) -> JsonRecord:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "target_ids": list(self.target_ids),
            "candidate_ids": list(self.candidate_ids),
            "evidence_refs": list(self.evidence_refs),
            "rationale": self.rationale,
            "confidence": round(float(self.confidence), 4),
            "risk_level": self.risk_level,
            "projection_delta": dict(self.projection_delta),
            "requires_review": True,
            "auto_apply": False,
            "requires_simulation": bool(self.requires_simulation),
            "created_at": self.created_at,
            "proposed_memory": self.proposed_memory,
            "proposed_children": list(self.proposed_children),
            "review_status": self.review_status,
            "rollback_notes": self.rollback_notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvolutionProposal":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: payload[key] for key in allowed if key in payload})


def new_proposal_id(prefix: str = "evo") -> str:
    return f"{prefix}-{uuid4().hex}"


def append_evolution_proposal(cell_path: PathLike, proposal: EvolutionProposal | Mapping[str, Any]) -> JsonRecord:
    record = proposal.to_dict() if isinstance(proposal, EvolutionProposal) else EvolutionProposal.from_dict(proposal).to_dict()
    append_jsonl(Path(cell_path) / PROPOSALS_LEDGER, record)
    return record


def append_evolution_proposals(cell_path: PathLike, proposals: Sequence[EvolutionProposal | Mapping[str, Any]]) -> List[JsonRecord]:
    return [append_evolution_proposal(cell_path, proposal) for proposal in proposals]


def read_evolution_proposals(cell_path: PathLike, *, include_reviewed: bool = True) -> List[JsonRecord]:
    path = Path(cell_path) / PROPOSALS_LEDGER
    if not path.exists():
        return []
    reviews = latest_evolution_reviews(cell_path)
    rows: List[JsonRecord] = []
    for _, record in read_jsonl(path):
        row = _canonical_proposal_record(record)
        review = reviews.get(str(row.get("proposal_id") or ""))
        if review:
            row["latest_review"] = review
            row["review_status"] = {"accept": "accepted", "reject": "rejected", "defer": "deferred"}.get(str(review.get("decision")), str(review.get("decision")))
        if include_reviewed or row.get("review_status") in {None, "pending", "deferred"}:
            rows.append(row)
    return rows


def latest_evolution_reviews(cell_path: PathLike) -> Dict[str, JsonRecord]:
    path = Path(cell_path) / REVIEWS_LEDGER
    if not path.exists():
        return {}
    latest: Dict[str, JsonRecord] = {}
    for _, record in read_jsonl(path):
        proposal_id = str(record.get("proposal_id") or "")
        if proposal_id:
            latest[proposal_id] = record
    return latest


def propose_candidate_split(candidate: Mapping[str, Any], *, max_chars: int = 360, min_child_chars: int = 40) -> Optional[JsonRecord]:
    text = str(candidate.get("text") or candidate.get("statement") or "").strip()
    if len(text) <= max_chars and not _has_topic_shift(text):
        return None
    chunks = _split_text(text, max_chars=max_chars, min_child_chars=min_child_chars)
    if len(chunks) < 2:
        return None
    candidate_id = str(candidate.get("candidate_id") or candidate.get("fragment_id") or candidate.get("id") or "candidate")
    evidence_id = str(candidate.get("evidence_id") or candidate.get("source_id") or f"synthetic:{candidate_id}")
    children = [
        {
            "child_index": index,
            "text": chunk,
            "parent_candidate_id": candidate_id,
            "boundary": _boundary_label(chunk),
        }
        for index, chunk in enumerate(chunks, start=1)
    ]
    proposal = EvolutionProposal(
        proposal_id=new_proposal_id("split"),
        proposal_type="split_candidate",
        target_ids=[],
        candidate_ids=[candidate_id],
        evidence_refs=[evidence_id],
        rationale="Candidate appears oversized or multi-topic; propose review-gated child candidates before promotion.",
        confidence=0.74 if len(text) > max_chars else 0.62,
        risk_level="medium",
        projection_delta={"proposed_child_count": len(children), "auto_promotes_children": False},
        requires_simulation=False,
        proposed_children=children,
    )
    return proposal.to_dict()


def propose_memory_consolidation(memories: Sequence[Mapping[str, Any]], *, overlap_threshold: float = 0.82) -> List[JsonRecord]:
    proposals: List[JsonRecord] = []
    seen_pairs: set[tuple[str, str]] = set()
    rows = [_memory_row(memory) for memory in memories]
    for left_index, left in enumerate(rows):
        for right in rows[left_index + 1:]:
            left_id, right_id = left["memory_id"], right["memory_id"]
            if not left_id or not right_id or (left_id, right_id) in seen_pairs:
                continue
            seen_pairs.add((left_id, right_id))
            exact = _normalize(left["statement"]) == _normalize(right["statement"])
            overlap = _token_overlap(left["statement"], right["statement"])
            if not exact and overlap < overlap_threshold:
                continue
            risk = "low" if exact and left.get("kind") == right.get("kind") else "high"
            confidence = 0.95 if exact else round(min(0.9, overlap), 4)
            proposals.append(EvolutionProposal(
                proposal_id=new_proposal_id("merge"),
                proposal_type="merge_memories",
                target_ids=[left_id, right_id],
                candidate_ids=_unique(left.get("candidate_ids", []) + right.get("candidate_ids", [])),
                evidence_refs=_unique(left.get("evidence_refs", []) + right.get("evidence_refs", []) + [f"memory:{left_id}", f"memory:{right_id}"]),
                rationale="Likely duplicate or overlapping memories; propose review-gated consolidation while preserving source lineage.",
                confidence=confidence,
                risk_level=risk,
                projection_delta={"active_memory_delta": -1, "consolidated_statement": _consolidated_statement(left, right), "kept_distinctions": _kept_distinctions(left, right)},
                requires_simulation=True,
                proposed_memory={
                    "statement": _consolidated_statement(left, right),
                    "source_memory_ids": [left_id, right_id],
                    "candidate_ids": _unique(left.get("candidate_ids", []) + right.get("candidate_ids", [])),
                },
            ).to_dict())
    return proposals


def propose_supersession_from_feedback(feedback_records: Sequence[Mapping[str, Any]], memories: Sequence[Mapping[str, Any]], *, min_repeated: int = 2) -> List[JsonRecord]:
    known = {row["memory_id"]: row for row in (_memory_row(memory) for memory in memories)}
    counts: Dict[str, List[str]] = {}
    replacements: Dict[str, List[str]] = {}
    for record in feedback_records:
        evidence_ref = str(record.get("feedback_id") or record.get("outcome_id") or record.get("event_id") or "synthetic:feedback")
        ids = record.get("contradicted_memory_ids") or record.get("harmful_memory_ids") or record.get("contradicted_charge_ids") or record.get("harmful_trace_ids") or []
        if str(record.get("verdict") or record.get("result") or "").lower() in {"harmful", "contradicted", "false", "stale"}:
            ids = list(ids) + list(record.get("memory_ids") or record.get("trace_ids") or [])
        for memory_id in [str(item) for item in ids if item]:
            counts.setdefault(memory_id, []).append(evidence_ref)
            if record.get("replacement_statement"):
                replacements.setdefault(memory_id, []).append(str(record["replacement_statement"]))
    proposals: List[JsonRecord] = []
    for memory_id, refs in sorted(counts.items()):
        if len(refs) < min_repeated or memory_id not in known:
            continue
        ptype = "replace_memory" if replacements.get(memory_id) else "deprecate_memory"
        projection = {"active_memory_delta": 0 if ptype == "replace_memory" else -1, "suggested_graph_edge": "supersedes" if ptype == "replace_memory" else None}
        proposed_memory = {"statement": replacements[memory_id][-1], "supersedes": memory_id} if replacements.get(memory_id) else None
        proposals.append(EvolutionProposal(
            proposal_id=new_proposal_id("sup"),
            proposal_type=ptype,
            target_ids=[memory_id],
            candidate_ids=known[memory_id].get("candidate_ids", []),
            evidence_refs=_unique(refs),
            rationale="Repeated feedback contradicts or marks this memory stale; propose review-gated lifecycle update.",
            confidence=min(0.95, 0.45 + 0.2 * len(refs)),
            risk_level="high",
            projection_delta=projection,
            requires_simulation=True,
            proposed_memory=proposed_memory,
        ).to_dict())
    return proposals


def propose_forgetting_from_policies(memories: Sequence[Mapping[str, Any]], policy_records: Sequence[Mapping[str, Any]] | None = None) -> List[JsonRecord]:
    policy_records = list(policy_records or [])
    requested: Dict[str, JsonRecord] = {}
    for record in policy_records:
        memory_id = str(record.get("memory_id") or record.get("trace_id") or record.get("target_id") or "")
        action = str(record.get("action") or record.get("proposal_type") or "").lower()
        if memory_id and action in {"forget", "forget_memory", "redact", "redact_memory", "deprecate", "deprecate_memory"}:
            requested[memory_id] = dict(record)
    proposals: List[JsonRecord] = []
    for row in [_memory_row(memory) for memory in memories]:
        memory_id = row["memory_id"]
        tags = {str(tag).lower() for tag in row.get("tags", [])}
        explicit = requested.get(memory_id)
        if not explicit and not ({"retention_expired", "forget_requested", "redact_requested", "synthetic_sensitive"} & tags):
            continue
        if explicit:
            raw_action = str(explicit.get("action") or explicit.get("proposal_type") or "forget").lower()
        elif "redact_requested" in tags or "synthetic_sensitive" in tags:
            raw_action = "redact"
        elif "retention_expired" in tags or "forget_requested" in tags:
            raw_action = "forget"
        else:
            raw_action = "deprecate"
        ptype = "redact_memory" if "redact" in raw_action else "deprecate_memory" if "deprecate" in raw_action else "forget_memory"
        proposals.append(EvolutionProposal(
            proposal_id=new_proposal_id("policy"),
            proposal_type=ptype,
            target_ids=[memory_id],
            candidate_ids=row.get("candidate_ids", []),
            evidence_refs=[str((explicit or {}).get("policy_id") or (explicit or {}).get("event_id") or f"synthetic-policy:{memory_id}")],
            rationale="Explicit policy or synthetic retention marker requests review-gated logical memory lifecycle handling.",
            confidence=0.8,
            risk_level="high",
            projection_delta={"active_memory_delta": -1, "physical_delete": False},
            requires_simulation=True,
        ).to_dict())
    return proposals


def propose_challenges_from_feedback(feedback_records: Sequence[Mapping[str, Any]], memories: Sequence[Mapping[str, Any]], *, min_repeated: int = 2) -> List[JsonRecord]:
    known = {row["memory_id"]: row for row in (_memory_row(memory) for memory in memories)}
    counts: Dict[str, List[str]] = {}
    for record in feedback_records:
        verdict = str(record.get("verdict") or record.get("result") or "").lower()
        ids = record.get("challenged_memory_ids") or record.get("questioned_memory_ids") or []
        if verdict in {"questioned", "challenged", "uncertain", "doubtful"}:
            ids = list(ids) + list(record.get("memory_ids") or record.get("trace_ids") or [])
        evidence_ref = str(record.get("feedback_id") or record.get("outcome_id") or record.get("event_id") or "synthetic:feedback")
        for memory_id in [str(item) for item in ids if item]:
            counts.setdefault(memory_id, []).append(evidence_ref)
    proposals: List[JsonRecord] = []
    for memory_id, refs in sorted(counts.items()):
        if len(refs) < min_repeated or memory_id not in known:
            continue
        proposals.append(EvolutionProposal(
            proposal_id=new_proposal_id("challenge"),
            proposal_type="challenge_memory",
            target_ids=[memory_id],
            candidate_ids=known[memory_id].get("candidate_ids", []),
            evidence_refs=_unique(refs),
            rationale="Repeated questioning feedback indicates this memory should remain visible but be explicitly challenged pending operator review.",
            confidence=min(0.9, 0.4 + 0.15 * len(refs)),
            risk_level="high",
            projection_delta={"active_memory_delta": 0, "status_transition": "approved -> challenged"},
            requires_simulation=True,
        ).to_dict())
    return proposals


def propose_missing_memory_promotions(cell_path: PathLike) -> List[JsonRecord]:
    cell = Path(cell_path)
    path = cell / "ledger" / "missing_memory_candidates.jsonl"
    if not path.exists():
        return []
    proposals: List[JsonRecord] = []
    for _, record in read_jsonl(path):
        candidate_id = str(record.get("candidate_id") or "")
        text = str(record.get("source_text") or "").strip()
        if not candidate_id or not text:
            continue
        memory_type, kind = _infer_missing_memory_shape(text)
        proposals.append(EvolutionProposal(
            proposal_id=new_proposal_id("promote"),
            proposal_type="promote_missing_memory",
            target_ids=[],
            candidate_ids=[candidate_id],
            evidence_refs=[f"missing-memory:{candidate_id}"],
            rationale="Repeated missing-memory note suggests a stable durable memory should be proposed through the review-gated evolution track.",
            confidence=0.72 if memory_type == "semantic" else 0.68,
            risk_level="medium",
            projection_delta={"active_memory_delta": 1, "new_memory_type": memory_type},
            requires_simulation=False,
            proposed_memory={
                "statement": text,
                "memory_type": memory_type,
                "kind": kind,
                "candidate_ids": [candidate_id],
                "rationale": "Derived from a missing-memory candidate after outcome review.",
            },
        ).to_dict())
    return _dedupe_proposals(proposals)


def scan_cell(cell_path: PathLike, *, write_proposals: bool = False, max_candidate_chars: int = 360, rate_limit: int = 100) -> JsonRecord:
    cell = Path(cell_path)
    proposals: List[JsonRecord] = []
    for candidate in _read_candidates(cell):
        proposal = propose_candidate_split(candidate, max_chars=max_candidate_chars)
        if proposal:
            proposals.append(proposal)
    memories = _read_memories(cell)
    feedback = _read_feedback(cell)
    proposals.extend(propose_memory_consolidation(memories))
    proposals.extend(propose_supersession_from_feedback(feedback, memories))
    proposals.extend(propose_challenges_from_feedback(feedback, memories))
    proposals.extend(propose_forgetting_from_policies(memories, _read_policy_events(cell)))
    proposals.extend(propose_missing_memory_promotions(cell))
    proposals = _dedupe_proposals(proposals)[:rate_limit]
    written: List[JsonRecord] = []
    if write_proposals:
        written = append_evolution_proposals(cell, [EvolutionProposal.from_dict(p) for p in proposals])
    return {
        "status": "ok",
        "dry_run": not write_proposals,
        "review_gated": True,
        "auto_apply": False,
        "proposal_count": len(proposals),
        "written_count": len(written),
        "rate_limited": len(proposals) >= rate_limit,
        "proposals": written or proposals,
    }


def simulate_evolution_proposal(cell_path: PathLike, proposal_id: str | Mapping[str, Any], *, append_report: bool = False) -> JsonRecord:
    cell = Path(cell_path)
    proposal = _resolve_proposal(cell, proposal_id)
    before_lines = _ledger_line_counts(cell)
    active_before = _active_memory_ids(cell)
    excluded = set(_proposal_excluded_ids(proposal))
    added = 1 if proposal.get("proposal_type") in {"replace_memory", "merge_memories", "promote_missing_memory"} else 0
    active_after = (active_before - excluded)
    projected_count = len(active_after) + added
    report = {
        "simulation_id": new_proposal_id("evo-sim"),
        "proposal_id": proposal["proposal_id"],
        "status": "ok",
        "read_only": True,
        "ledger_line_counts_before": before_lines,
        "ledger_line_counts_after": _ledger_line_counts(cell),
        "current_active_memory_count": len(active_before),
        "proposed_active_memory_count": projected_count,
        "affected_memory_ids": sorted(set(proposal.get("target_ids") or [])),
        "retrieval_inclusion_changes": {memory_id: {"before": True, "after": memory_id not in excluded} for memory_id in sorted(excluded)},
        "graph_edge_changes": proposal.get("projection_delta", {}).get("suggested_graph_edge"),
        "confidence_delta": proposal.get("projection_delta", {}).get("confidence_delta", 0.0),
        "projection_delta": proposal.get("projection_delta", {}),
        "pack_query_examples": _pack_query_examples(cell),
        "created_at": _now(),
    }
    if report["ledger_line_counts_before"] != report["ledger_line_counts_after"]:
        raise RuntimeError("simulation changed ledger line counts")
    if append_report:
        append_jsonl(cell / SIMULATION_LEDGER, report)
    return report


def review_evolution_proposal(
    cell_path: PathLike,
    proposal_id: str,
    *,
    decision: str,
    rationale: str,
    actor: str = "operator",
    simulation_ref: Optional[str] = None,
) -> JsonRecord:
    if decision not in VALID_DECISIONS:
        raise ValueError("decision must be accept, reject, or defer")
    if not rationale.strip():
        raise ValueError("rationale is required")
    cell = Path(cell_path)
    proposal = _resolve_proposal(cell, proposal_id)
    if decision == "accept" and proposal.get("requires_simulation") and not simulation_ref:
        raise ValueError("simulation_ref is required to accept retrieval-affecting evolution proposals")
    applied_events: List[JsonRecord] = []
    if decision == "accept":
        applied_events = _apply_accepted_proposal(cell, proposal, actor=actor, rationale=rationale)
    review = {
        "review_id": new_proposal_id("evo-review"),
        "proposal_id": proposal_id,
        "decision": decision,
        "rationale": rationale,
        "actor": actor,
        "reviewed_at": _now(),
        "simulation_ref": simulation_ref,
        "applied_events": applied_events,
        "review_gated": True,
        "auto_apply": False,
    }
    append_jsonl(cell / REVIEWS_LEDGER, review)
    return review


def evolution_eval_tasks() -> List[JsonRecord]:
    tasks = [
        {"task_id": "evolution-split-oversized-candidate", "scenario": "Oversized candidate emits split proposal only", "expected": "split_candidate"},
        {"task_id": "evolution-duplicate-consolidation", "scenario": "Exact duplicate memories emit merge proposal", "expected": "merge_memories"},
        {"task_id": "evolution-distinct-memory-preserved", "scenario": "Similar but distinct memories are not silently merged", "expected": "no_auto_apply"},
        {"task_id": "evolution-supersession-feedback", "scenario": "Repeated contradiction feedback emits lifecycle proposal", "expected": "deprecate_memory"},
        {"task_id": "evolution-challenge-feedback", "scenario": "Repeated questioning feedback emits challenge proposal", "expected": "challenge_memory"},
        {"task_id": "evolution-logical-forgetting", "scenario": "Retention marker emits logical forgetting proposal", "expected": "forget_memory"},
        {"task_id": "evolution-missing-memory-promotion", "scenario": "Missing-memory candidates emit semantic or procedural promotion proposals", "expected": "promote_missing_memory"},
        {"task_id": "evolution-rehearsal-report", "scenario": "Deterministic rehearsal reports compare promoted memory against held-out tasks", "expected": "rehearsal_report"},
        {"task_id": "evolution-prompt-injection-safe", "scenario": "Malicious evidence cannot force auto apply", "expected": "auto_apply_false"},
        {"task_id": "evolution-rate-limit", "scenario": "Scanner caps proposal storms", "expected": "rate_limited"},
    ]
    for task in tasks:
        task.setdefault("source", "synthetic_evolution_safety_fixture")
        task.setdefault("private_data_allowed", False)
        task.setdefault("expected_agent_behavior", "preserve review gating, append-only ledgers, and public-safe proposal semantics")
    return tasks


def _apply_accepted_proposal(cell: Path, proposal: Mapping[str, Any], *, actor: str, rationale: str) -> List[JsonRecord]:
    from .mutations import challenge_charge, deprecate_charge, forget_charge, redact_charge, replace_charge
    from .provider.memory import remember

    events: List[JsonRecord] = []
    ptype = str(proposal.get("proposal_type") or "")
    targets = [str(item) for item in proposal.get("target_ids") or [] if item]
    reason = f"Accepted evolution proposal {proposal.get('proposal_id')}: {rationale}"
    if ptype == "forget_memory":
        for memory_id in targets:
            events.append(forget_charge(cell, memory_id, reason=reason, actor=actor).__dict__)
    elif ptype == "redact_memory":
        for memory_id in targets:
            events.append(redact_charge(cell, memory_id, reason=reason, actor=actor).__dict__)
    elif ptype in {"deprecate_memory", "supersede_memory"}:
        for memory_id in targets:
            events.append(deprecate_charge(cell, memory_id, reason=reason, actor=actor).__dict__)
    elif ptype == "challenge_memory":
        for memory_id in targets:
            events.append(challenge_charge(cell, memory_id, reason=reason, actor=actor).__dict__)
    elif ptype == "replace_memory":
        statement = str((proposal.get("proposed_memory") or {}).get("statement") or "").strip()
        if not statement:
            raise ValueError("replace_memory acceptance requires proposed_memory.statement")
        for memory_id in targets:
            events.append(replace_charge(cell, memory_id, statement, reason=reason, actor=actor).__dict__)
    elif ptype == "merge_memories":
        # Public baseline preserves auditability: accepting a merge proposal marks
        # duplicate source memories deprecated; creation of a new consolidated
        # memory stays review/operator controlled through existing promotion paths.
        for memory_id in targets[1:]:
            events.append(deprecate_charge(cell, memory_id, reason=reason, actor=actor).__dict__)
    elif ptype == "split_candidate":
        append_jsonl(cell / "ledger" / "reviews.jsonl", {
            "review_id": new_proposal_id("split-review"),
            "proposal_id": proposal.get("proposal_id"),
            "candidate_ids": proposal.get("candidate_ids") or [],
            "review_action": "split_proposal_accepted",
            "review_status": "accepted",
            "proposed_children": proposal.get("proposed_children") or [],
            "reviewer": actor,
            "rationale": rationale,
            "reviewed_at": _now(),
            "auto_promoted_children": False,
        })
        events.append({"action": "split_proposal_accepted", "auto_promoted_children": False})
    elif ptype == "promote_missing_memory":
        proposed = dict(proposal.get("proposed_memory") or {})
        statement = str(proposed.get("statement") or "").strip()
        kind = str(proposed.get("kind") or "preference").strip() or "preference"
        memory_type = proposed.get("memory_type")
        if not statement:
            raise ValueError("promote_missing_memory acceptance requires proposed_memory.statement")
        result = remember(
            cell,
            statement,
            kind,
            pulse_context={
                "actor": actor,
                "proposal_id": proposal.get("proposal_id"),
                "candidate_ids": proposal.get("candidate_ids") or [],
            },
            metadata={
                "actor": actor,
                "reason": reason,
                "provider_api": "evolution_accept_promote_missing_memory",
                "memory_type": memory_type,
                "tags": ["phase5_promotion"],
            },
            memory_type=memory_type,
        )
        events.append({
            "action": "promote_missing_memory",
            "memory_id": result.memory_id,
            "candidate_id": result.candidate_id,
            "evidence_id": result.evidence_id,
            "status": result.status,
            "memory_type": result.memory_type,
        })
    return events


def _resolve_proposal(cell: Path, proposal_id: str | Mapping[str, Any]) -> JsonRecord:
    if isinstance(proposal_id, Mapping):
        return _canonical_proposal_record(proposal_id)
    for proposal in read_evolution_proposals(cell):
        if proposal.get("proposal_id") == proposal_id:
            return proposal
    raise ValueError(f"Unknown evolution proposal: {proposal_id}")


def _canonical_proposal_record(record: Mapping[str, Any]) -> JsonRecord:
    return EvolutionProposal.from_dict(record).to_dict()


def _read_candidates(cell: Path) -> List[JsonRecord]:
    rows: List[JsonRecord] = []
    for rel in ("ledger/candidates.jsonl", "ledger/fragments.jsonl", "ledger/sparks.jsonl"):
        path = cell / rel
        if path.exists():
            rows.extend(record for _, record in read_jsonl(path))
    return rows


def _read_memories(cell: Path) -> List[JsonRecord]:
    rows: List[JsonRecord] = []
    for rel in ("ledger/memories/approved.jsonl", "memories/approved.jsonl", "traces/approved.jsonl", "charges/approved.jsonl"):
        path = cell / rel
        if path.exists():
            rows.extend(record for _, record in read_jsonl(path))
    return rows


def _read_feedback(cell: Path) -> List[JsonRecord]:
    rows: List[JsonRecord] = []
    for rel in ("ledger/feedback.jsonl", "ledger/outcomes.jsonl", "ledger/signals.jsonl"):
        path = cell / rel
        if path.exists():
            rows.extend(record for _, record in read_jsonl(path))
    return rows


def _read_policy_events(cell: Path) -> List[JsonRecord]:
    rows: List[JsonRecord] = []
    for rel in ("ledger/access_policy_events.jsonl", "ledger/regulator_events.jsonl"):
        path = cell / rel
        if path.exists():
            rows.extend(record for _, record in read_jsonl(path))
    return rows


def _memory_row(record: Mapping[str, Any]) -> JsonRecord:
    memory_id = str(record.get("memory_id") or record.get("trace_id") or record.get("charge_id") or "")
    candidate_ids = record.get("candidate_ids") or record.get("source_fragment_ids") or []
    evidence_refs = record.get("evidence_refs") or record.get("evidence_ids") or record.get("source_ids") or []
    if not evidence_refs:
        evidence_refs = [f"memory:{memory_id}"] if memory_id else ["synthetic:memory"]
    return {
        "memory_id": memory_id,
        "statement": str(record.get("statement") or record.get("text") or ""),
        "kind": record.get("kind"),
        "status": record.get("status"),
        "candidate_ids": [str(item) for item in candidate_ids if item],
        "evidence_refs": [str(item) for item in evidence_refs if item],
        "tags": list(record.get("tags") or []),
    }


def _active_memory_ids(cell: Path) -> set[str]:
    from .mutations import active_charge_ids

    ids = set(active_charge_ids(cell, projection="retrieval"))
    if ids:
        return ids
    return {row["memory_id"] for row in (_memory_row(record) for record in _read_memories(cell)) if row["memory_id"] and row.get("status", "approved") == "approved"}


def _proposal_excluded_ids(proposal: Mapping[str, Any]) -> List[str]:
    ptype = str(proposal.get("proposal_type") or "")
    targets = [str(item) for item in proposal.get("target_ids") or [] if item]
    if ptype in {"deprecate_memory", "forget_memory", "redact_memory", "supersede_memory"}:
        return targets
    if ptype == "replace_memory":
        return targets
    if ptype == "merge_memories":
        return targets[1:]
    return []


def generate_rehearsal_fixtures(cell_path: PathLike) -> List[JsonRecord]:
    cell = Path(cell_path)
    retrieval_by_pack: Dict[str, JsonRecord] = {}
    path = cell / "ledger" / "retrieval_logs.jsonl"
    if path.exists():
        for _, record in read_jsonl(path):
            pack_id = str(record.get("pack_id") or record.get("loadout_id") or "")
            if pack_id:
                retrieval_by_pack[pack_id] = dict(record)
    outcomes_path = cell / "ledger" / "outcomes.jsonl"
    fixtures: List[JsonRecord] = []
    if not outcomes_path.exists():
        return fixtures
    for _, outcome in read_jsonl(outcomes_path):
        pack_id = str(outcome.get("loadout_id") or outcome.get("pack_id") or "")
        retrieval = retrieval_by_pack.get(pack_id, {})
        query = str(retrieval.get("query") or outcome.get("task_id") or "synthetic rehearsal review")
        memory_ids = outcome.get("useful_trace_ids") or outcome.get("useful_charge_ids") or outcome.get("applied_trace_ids") or outcome.get("applied_charge_ids") or []
        for memory_id in [str(item) for item in memory_ids if item]:
            fixtures.append({
                "fixture_id": f"rehearsal-{pack_id or 'no-pack'}-{memory_id}",
                "query": query,
                "expected_memory_id": memory_id,
                "pack_id": pack_id,
                "task_id": str(outcome.get("task_id") or ""),
                "outcome_id": str(outcome.get("outcome_id") or ""),
            })
    fixtures.sort(key=lambda item: (item["fixture_id"], item["expected_memory_id"]))
    return fixtures


def rehearse_cell(cell_path: PathLike, *, append_report: bool = False, top_k: int = 5) -> JsonRecord:
    from .provider.memory import search

    cell = Path(cell_path)
    fixtures = generate_rehearsal_fixtures(cell)
    results: List[JsonRecord] = []
    hits = 0
    for fixture in fixtures:
        query = str(fixture.get("query") or "")
        expected_memory_id = str(fixture.get("expected_memory_id") or "")
        matches = search(cell, query, top_k=top_k)
        matched_ids = [match.memory_id for match in matches]
        matched = expected_memory_id in matched_ids
        if matched:
            hits += 1
        results.append({
            **fixture,
            "matched": matched,
            "matched_memory_ids": matched_ids,
        })
    report = {
        "report_id": new_proposal_id("rehearsal"),
        "status": "ok",
        "read_only": False,
        "fixture_count": len(results),
        "hit_count": hits,
        "hit_rate": round(hits / len(results), 4) if results else 0.0,
        "fixtures": results,
        "created_at": _now(),
    }
    if append_report:
        append_jsonl(cell / "ledger" / "evolution" / "rehearsal_reports.jsonl", report)
    return report


def _ledger_line_counts(cell: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    ledger = cell / "ledger"
    if ledger.exists():
        for path in sorted(ledger.rglob("*.jsonl")):
            counts[str(path.relative_to(cell))] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    for rel in ("traces/approved.jsonl", "charges/approved.jsonl", "memories/approved.jsonl"):
        path = cell / rel
        if path.exists():
            counts[rel] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return counts


def _pack_query_examples(cell: Path) -> List[str]:
    examples: List[str] = []
    path = cell / "ledger" / "retrieval_logs.jsonl"
    if path.exists():
        for _, record in read_jsonl(path):
            query = record.get("query")
            if query:
                examples.append(str(query))
    return examples[:5] or ["synthetic memory evolution review"]


def _dedupe_proposals(proposals: Sequence[JsonRecord]) -> List[JsonRecord]:
    seen: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()
    rows: List[JsonRecord] = []
    for proposal in proposals:
        key = (str(proposal.get("proposal_type")), tuple(sorted(str(x) for x in proposal.get("target_ids") or [])), tuple(sorted(str(x) for x in proposal.get("candidate_ids") or [])))
        if key in seen:
            continue
        seen.add(key)
        rows.append(proposal)
    return rows


def _split_text(text: str, *, max_chars: int, min_child_chars: int) -> List[str]:
    parts = [part.strip() for part in re.split(r"\n\s*\n|(?=^#{1,6}\s)", text, flags=re.MULTILINE) if part.strip()]
    if len(parts) < 2:
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    chunks: List[str] = []
    current = ""
    for part in parts:
        if current and len(current) + len(part) + 1 > max_chars:
            chunks.append(current.strip())
            current = part
        else:
            current = f"{current} {part}".strip()
    if current:
        chunks.append(current.strip())
    merged: List[str] = []
    for chunk in chunks:
        if merged and len(chunk) < min_child_chars:
            merged[-1] = f"{merged[-1]} {chunk}".strip()
        else:
            merged.append(chunk)
    if len(merged) < 2 and len(text) > max_chars:
        midpoint = len(text) // 2
        cut = text.rfind(". ", 0, midpoint)
        if cut == -1:
            cut = midpoint
        merged = [text[:cut + 1].strip(), text[cut + 1:].strip()]
    return [chunk for chunk in merged if chunk]


def _has_topic_shift(text: str) -> bool:
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(paragraphs) < 2:
        return False
    return _token_overlap(paragraphs[0], paragraphs[-1]) < 0.12


def _boundary_label(chunk: str) -> str:
    first = chunk.splitlines()[0].strip()
    if first.startswith("#"):
        return "heading"
    return "paragraph_or_sentence"


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2 and token not in {"the", "and", "for", "with", "this", "that", "from", "into"}}


def _token_overlap(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _consolidated_statement(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    if _normalize(str(left.get("statement") or "")) == _normalize(str(right.get("statement") or "")):
        return str(left.get("statement") or right.get("statement") or "")
    return f"{left.get('statement')} / {right.get('statement')}"


def _kept_distinctions(left: Mapping[str, Any], right: Mapping[str, Any]) -> List[str]:
    distinctions: List[str] = []
    if left.get("kind") != right.get("kind"):
        distinctions.append(f"kind differs: {left.get('kind')} vs {right.get('kind')}")
    return distinctions


def _unique(items: Iterable[Any]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        text = str(item)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _infer_missing_memory_shape(text: str) -> tuple[str, str]:
    lowered = text.lower()
    procedural_markers = ("run ", "before ", "after ", "record ", "verify ", "check ", "use ")
    if any(marker in lowered for marker in procedural_markers):
        return ("procedural", "workflow")
    return ("semantic", "preference")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
