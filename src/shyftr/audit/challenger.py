"""Challenger audit loop for ShyftR Cell ledgers.

The Challenger is a deterministic analysis pass that:

- Ranks Traces/Charges by impact and confidence-reliability gap
- Searches counter-evidence across Pulses, Sparks, Signal, audit
  records, and deprecated/superseded Traces/Charges
- Classifies findings into 8 defined types
- Emits low-authority audit sparks (ledger/audit_sparks.jsonl)
- Never directly mutates Trace/Charge lifecycle ledgers

Key design constraints (AL-7):
- Isolation and deprecation remain review-gated (no direct mutation)
- Persistence/retrieval state changes are review-gated
- Output is append-only audit sparks with deterministic dedup keys
"""
from __future__ import annotations

import hashlib
import json as _json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from shyftr.audit import (
    CHALLENGER_FINDING_CLASSIFICATIONS,
    append_audit_spark,
    read_audit_sparks,
)
from shyftr.ledger import read_audit_reviews, read_jsonl
from shyftr.sweep import TraceMetrics, compute_trace_metrics

PathLike = Union[str, Path]
JsonRecord = Dict[str, Any]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChallengerFinding:
    """A single finding from the Challenger audit loop.

    Parameters
    ----------
    trace_id : the Trace/Charge being challenged
    classification : one of the 8 CHALLENGER_FINDING_CLASSIFICATIONS
    rationale : human-readable explanation
    signal_strength : evidence weight (0.0-1.0)
    counter_evidence_source : where counter-evidence was found
    supporting_data : optional additional context
    fragment_id : optional source fragment id
    target_status : optional current status of the target trace
    target_confidence : optional current confidence of the target trace
    rank_score : optional impact rank score computed by the challenger
    """

    trace_id: str
    classification: str
    rationale: str
    signal_strength: float = 0.5
    counter_evidence_source: str = ""
    supporting_data: Optional[Dict[str, Any]] = None
    fragment_id: str = ""
    target_status: Optional[str] = None
    target_confidence: Optional[float] = None
    rank_score: Optional[float] = None

    def __post_init__(self) -> None:
        if self.classification not in CHALLENGER_FINDING_CLASSIFICATIONS:
            raise ValueError(
                f"Invalid classification '{self.classification}'. "
                f"Must be one of: {sorted(CHALLENGER_FINDING_CLASSIFICATIONS)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "trace_id": self.trace_id,
            "classification": self.classification,
            "rationale": self.rationale,
            "signal_strength": self.signal_strength,
            "counter_evidence_source": self.counter_evidence_source,
        }
        if self.supporting_data:
            d["supporting_data"] = self.supporting_data
        if self.fragment_id:
            d["fragment_id"] = self.fragment_id
            d["candidate_id"] = self.fragment_id
        if self.target_status:
            d["target_status"] = self.target_status
        if self.target_confidence is not None:
            d["target_confidence"] = self.target_confidence
        if self.rank_score is not None:
            d["rank_score"] = self.rank_score
        return d


@dataclass(frozen=True)
class ChallengerReport:
    """Complete report from a Challenger audit pass."""

    cell_id: str
    scanned_at: str
    dry_run: bool
    target_count: int
    findings: List[ChallengerFinding] = field(default_factory=list)
    written_spark_ids: List[str] = field(default_factory=list)
    skipped_spark_ids: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "scanned_at": self.scanned_at,
            "dry_run": self.dry_run,
            "target_count": self.target_count,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "written_spark_ids": list(self.written_spark_ids),
            "skipped_spark_ids": list(self.skipped_spark_ids),
            "summary": dict(self.summary),
        }


# ---------------------------------------------------------------------------
# Ranking: rank Traces/Charges by impact and gap
# ---------------------------------------------------------------------------


def _rank_score(
    metrics: TraceMetrics,
    *,
    weight_retrieval: float = 0.15,
    weight_application: float = 0.20,
    weight_useful: float = 0.15,
    weight_harmful: float = 0.25,
    weight_miss: float = 0.15,
    weight_confidence_gap: float = 0.10,
) -> float:
    """Compute a single rank score for a TraceMetric.

    Higher scores indicate higher priority for challenger scrutiny.
    The scoring favours:

    - **High miss rate** — traces that are frequently retrieved but miss
      are costing time and may contain stale/contradictory information.
    - **Harmful signal** — traces that have ever been flagged harmful
      need immediate review.
    - **Applied count** — heavily used traces that go wrong have wide
      blast radius.
    - **Confidence gap** — a mismatch between how often the trace is
      retrieved and how often it is actually useful suggests it is
      over-confident in retrieval rankings.
    """
    score = 0.0

    # Retrieval: traces retrieved more often are more impactful
    r = metrics.retrieval_count
    score += min(r, 20) / 20 * weight_retrieval

    # Applications: applied traces matter more
    a = metrics.application_count
    score += min(a, 10) / 10 * weight_application

    # Useful: positive signals are non-zero weight
    u = metrics.useful_count
    score += min(u, 5) / 5 * weight_useful

    # Harmful: heavy weight — any harmful signal is a red flag
    h = metrics.harmful_count
    score += min(h, 5) / 5 * weight_harmful

    # Miss rate: the more misses the more concerning
    mr = metrics.miss_rate or 0.0
    score += mr * weight_miss

    # Confidence gap: trace retrieved often but with a high miss rate
    # indicates a discrepancy between retrieval priority and relevance
    if metrics.retrieval_count > 3 and mr > 0.3:
        gap = min(mr, 0.9)
        score += gap * weight_confidence_gap

    return round(min(score, 1.0), 4)


def rank_targets(
    metrics: Dict[str, TraceMetrics],
    *,
    top_n: Optional[int] = None,
    min_score: float = 0.0,
) -> List[Tuple[str, TraceMetrics, float]]:
    """Rank traces by challenger priority score.

    Parameters
    ----------
    metrics : dict from compute_trace_metrics
    top_n : if set, return only the top N scores
    min_score : minimum score threshold (0.0 = no filter)

    Returns
    -------
    List of (trace_id, metrics, score) sorted descending by score.
    """
    scored: List[Tuple[str, TraceMetrics, float]] = []
    for tid, m in metrics.items():
        s = _rank_score(m)
        if s >= min_score:
            scored.append((tid, m, s))
    scored.sort(key=lambda x: (-x[2], x[0]))
    if top_n is not None:
        scored = scored[:top_n]
    return scored


# ---------------------------------------------------------------------------
# Counter-evidence search
# ---------------------------------------------------------------------------


def _read_signal_ledger(cell_path: Path) -> List[JsonRecord]:
    """Read ledger/outcomes.jsonl (Signal records)."""
    path = cell_path / "ledger" / "outcomes.jsonl"
    if not path.exists():
        return []
    return [record for _, record in read_jsonl(path)]


def _read_pulses(cell_path: Path) -> List[JsonRecord]:
    """Read ledger/sources.jsonl (Pulse records)."""
    path = cell_path / "ledger" / "sources.jsonl"
    if not path.exists():
        return []
    return [record for _, record in read_jsonl(path)]


def _read_sparks(cell_path: Path) -> List[JsonRecord]:
    """Read ledger/sparks.jsonl (Sparks/Fragments)."""
    path = cell_path / "ledger" / "sparks.jsonl"
    if not path.exists():
        return []
    return [record for _, record in read_jsonl(path)]


def _read_status_rows(cell_path: Path, status: str) -> List[Tuple[str, JsonRecord]]:
    """Read preferred charges/ and legacy traces/ status ledgers.

    Returns tuples of (relative_source_path, record) in deterministic order.
    """
    rows: List[Tuple[str, JsonRecord]] = []
    for directory_name in ("charges", "traces"):
        path = cell_path / directory_name / f"{status}.jsonl"
        if not path.exists():
            continue
        relative_source = f"{directory_name}/{status}.jsonl"
        rows.extend((relative_source, record) for _, record in read_jsonl(path))
    return rows


def _collect_counter_evidence(
    cell_path: Path,
    target_trace_id: str,
    *,
    target_metrics: Optional[TraceMetrics] = None,
    max_candidates: int = 50,
) -> List[Dict[str, Any]]:
    """Collect counter-evidence records from all relevant ledger sources.

    Searches across:
    - ledger/outcomes.jsonl (Signal) — harmful outcomes and pack misses
    - ledger/audit_sparks.jsonl — existing challenger findings
    - ledger/audit.jsonl — audit rows for deprecation/contradiction
    - charges/deprecated.jsonl — superseded/contradicted charges
    - charges/isolated.jsonl — isolated charges
    - ledger/sources.jsonl (Pulses) — for temporal updates
    - ledger/sparks.jsonl (Sparks) — for context

    Returns a list of dicts with keys:
    - source (str): e.g. 'ledger/outcomes.jsonl:oc-a'
    - direction (str): 'contradiction', 'supersession', 'scope',
      'temporal', 'environment', 'ambiguous', 'policy', 'drift'
    - evidence (str): short snippet of the relevant data
    - created_at (str): ISO timestamp if available
    """
    evidence: List[Dict[str, Any]] = []
    target = target_trace_id

    # 1. Signal outcomes — harmful entries and pack misses for the target
    outcomes = _read_signal_ledger(cell_path)
    for outcome in outcomes:
        outcome_id = outcome.get("outcome_id", "?")
        verdict = outcome.get("verdict", "")
        applied = outcome.get("trace_ids", [])
        meta = outcome.get("metadata", {})
        harmful = meta.get("harmful_trace_ids", [])
        miss_details = outcome.get("pack_miss_details") or []
        legacy_pack_misses = outcome.get("pack_misses") or []

        if target in harmful:
            evidence.append({
                "source": f"ledger/outcomes.jsonl:{outcome_id}",
                "direction": "contradiction",
                "evidence": f"Outcome {outcome_id} ({verdict}) flagged {target} as harmful",
                "created_at": outcome.get("recorded_at", ""),
            })

        for md in miss_details:
            if md.get("charge_id") == target:
                miss_type = md.get("miss_type", "unknown")
                if miss_type == "contradicted":
                    direction = "contradiction"
                else:
                    direction = "ambiguous"
                evidence.append({
                    "source": f"ledger/outcomes.jsonl:{outcome_id}",
                    "direction": direction,
                    "evidence": f"Pack miss for {target}: {miss_type} — {md.get('reason', 'no reason')}",
                    "created_at": outcome.get("recorded_at", ""),
                })

        for legacy_charge_id in legacy_pack_misses:
            if str(legacy_charge_id) != target:
                continue
            evidence.append({
                "source": f"ledger/outcomes.jsonl:{outcome_id}",
                "direction": "ambiguous",
                "evidence": f"Legacy pack miss recorded for {target}",
                "created_at": outcome.get("recorded_at", ""),
            })

        if len(evidence) >= max_candidates:
            break

    # 2. Existing audit sparks are intentionally not recycled as fresh
    # counter-evidence here. They are derivative challenger outputs rather
    # than primary evidence, and feeding them back into new findings makes
    # repeated propose runs non-idempotent.

    # 3. Audit rows — deprecation/contradiction/isolation actions
    audit_path = cell_path / "ledger" / "audit.jsonl"
    audit_action_to_direction = {
        "deprecate": "supersession",
        "propose_deprecation": "supersession",
        "contradict": "contradiction",
        "isolate": "scope",
    }
    if audit_path.exists():
        for _, record in read_jsonl(audit_path):
            action = str(record.get("action", ""))
            if record.get("target_id") == target and action in audit_action_to_direction:
                evidence.append({
                    "source": f"ledger/audit.jsonl:{record.get('audit_id', '?')}",
                    "direction": audit_action_to_direction[action],
                    "evidence": record.get("rationale", ""),
                    "created_at": record.get("recorded_at", ""),
                })
                if len(evidence) >= max_candidates:
                    break

    # 4. Deprecated/isolated traces/charges that reference the same fragment.
    # Isolation remains a review-gated risk/scope signal rather than being
    # collapsed into supersession or contradiction semantics.
    target_fragments = set(target_metrics.source_fragment_ids) if target_metrics else set()
    for status_name in ("deprecated", "isolated"):
        status_rows = _read_status_rows(cell_path, status_name)
        for relative_source, record in status_rows:
            record_sources = set(record.get("source_fragment_ids") or record.get("source_ids") or [])
            record_id = record.get("charge_id") or record.get("trace_id") or ""
            same_target = bool(record_id) and record_id == target
            shares_fragment = bool(target_fragments and record_sources and target_fragments & record_sources)
            if same_target or shares_fragment:
                evidence.append({
                    "source": f"{relative_source}:{record_id}",
                    "direction": "scope" if status_name == "isolated" else "supersession",
                    "evidence": f"Record {record_id} is {status_name} and shares lineage with {target}",
                    "created_at": "",
                })
                if len(evidence) >= max_candidates:
                    break

    # 5. Sparks — bounded context/counter-evidence linked to the same trace or lineage.
    sparks = _read_sparks(cell_path)
    for spark in sparks:
        metadata = spark.get("metadata") or {}
        related_trace_ids = set(metadata.get("trace_ids") or metadata.get("related_trace_ids") or [])
        related_fragments = set(
            metadata.get("source_fragment_ids")
            or metadata.get("fragment_ids")
            or []
        )
        spark_fragment_id = str(spark.get("fragment_id") or "")
        spark_source = spark_fragment_id or str(spark.get("spark_id") or spark.get("source_id") or "?")
        spark_text = str(spark.get("text") or spark.get("statement") or spark.get("source_excerpt") or "").strip()
        if not spark_text:
            continue
        if not (
            target in related_trace_ids
            or (target_fragments and spark_fragment_id and spark_fragment_id in target_fragments)
            or (target_fragments and related_fragments and target_fragments & related_fragments)
        ):
            continue
        lowered = spark_text.lower()
        policy_markers = (
            "ignore previous instructions",
            "ignore prior instructions",
            "disregard previous",
            "system prompt",
            "reveal secret",
            "exfiltrate",
            "override safety",
            "export all secrets",
        )
        direction = "policy" if any(m in lowered for m in policy_markers) else "ambiguous"
        evidence.append({
            "source": f"ledger/sparks.jsonl:{spark_source}",
            "direction": direction,
            "evidence": spark_text,
            "created_at": spark.get("recorded_at", "") or spark.get("captured_at", ""),
        })
        if len(evidence) >= max_candidates:
            break

    # 6. Pulses — check for temporal updates (newer pulses on similar topics)
    pulses = _read_pulses(cell_path)
    target_fragments = set(target_metrics.source_fragment_ids) if target_metrics else set()
    for pulse in pulses:
        pulse_id = pulse.get("source_id", "")
        pulse_kind = pulse.get("kind", "")
        metadata = pulse.get("metadata") or {}
        related_trace_ids = set(metadata.get("trace_ids") or metadata.get("related_trace_ids") or [])
        related_fragments = set(metadata.get("source_fragment_ids") or metadata.get("fragment_ids") or [])
        if pulse_kind in ("update", "revision", "correction") and (
            target in related_trace_ids or (target_fragments and related_fragments and target_fragments & related_fragments)
        ):
            evidence.append({
                "source": f"ledger/sources.jsonl:{pulse_id}",
                "direction": "temporal",
                "evidence": f"Pulse {pulse_id} is a {pulse_kind} linked to {target} — may supersede earlier knowledge",
                "created_at": pulse.get("recorded_at", ""),
            })
            if len(evidence) >= max_candidates:
                break

    return evidence


# ---------------------------------------------------------------------------
# Finding classification
# ---------------------------------------------------------------------------


def _classify_evidence(
    target_trace_id: str,
    target_metrics: Optional[TraceMetrics],
    evidence_items: Sequence[Dict[str, Any]],
) -> List[ChallengerFinding]:
    """Analyze collected counter-evidence and produce classified findings.

    Classification rules:
    - **direct_contradiction**: an outcome explicitly flagged the trace as
      harmful, OR a pack miss recorded 'contradicted', OR an audit row
      contains 'contradict' action.
    - **supersession**: a deprecated charge exists related to the target,
      or an audit row has deprecate/propose_deprecation action.
    - **scope_exception**: the trace was retrieved but never or rarely
      applied, suggesting it may be out of scope for the Cell; isolated
      audit/status evidence is also treated as scope review input.
    - **environment_specific**: evidence references a specific environment
      (e.g. {'env': 'staging'}) in its supporting data.
    - **temporal_update**: a newer Pulse with kind=update/revision/correction
      exists in the Cell.
    - **ambiguous_counterevidence**: pack miss type is not 'contradicted'
      but not 'not_relevant' either (e.g. duplicative, unknown).
    - **policy_conflict**: reserved for future policy-based classification.
    - **implementation_drift**: reserved for future implementation-drift
      detection.
    """
    findings: List[ChallengerFinding] = []
    seen_classifications: set[str] = set()

    direct_contradictions: List[Dict[str, Any]] = []
    supersessions: List[Dict[str, Any]] = []
    temporal_items: List[Dict[str, Any]] = []
    ambiguous_items: List[Dict[str, Any]] = []
    scope_items: List[Dict[str, Any]] = []

    for item in evidence_items:
        direction = item.get("direction", "")
        if direction == "contradiction":
            direct_contradictions.append(item)
        elif direction == "supersession":
            supersessions.append(item)
        elif direction == "temporal":
            temporal_items.append(item)
        elif direction == "ambiguous":
            ambiguous_items.append(item)
        elif direction == "scope":
            scope_items.append(item)

    # 1. Direct contradiction
    if direct_contradictions:
        sources = [e["source"] for e in direct_contradictions[:3]]
        seen_classifications.add("direct_contradiction")
        findings.append(ChallengerFinding(
            trace_id=target_trace_id,
            classification="direct_contradiction",
            rationale=(
                f"Found {len(direct_contradictions)} direct contradiction signal(s) "
                f"for {target_trace_id}: {direct_contradictions[0].get('evidence', '')}"
            ),
            signal_strength=round(min(0.6 + 0.1 * len(direct_contradictions), 0.95), 4),
            counter_evidence_source="; ".join(sources),
            target_status=target_metrics.trace_status if target_metrics else None,
            target_confidence=target_metrics.confidence if target_metrics else None,
        ))

    # 2. Supersession
    if supersessions:
        sources = [e["source"] for e in supersessions[:3]]
        seen_classifications.add("supersession")
        findings.append(ChallengerFinding(
            trace_id=target_trace_id,
            classification="supersession",
            rationale=(
                f"Found {len(supersessions)} supersession candidate(s) "
                f"related to {target_trace_id}"
            ),
            signal_strength=round(min(0.5 + 0.05 * len(supersessions), 0.9), 4),
            counter_evidence_source="; ".join(sources),
            target_status=target_metrics.trace_status if target_metrics else None,
            target_confidence=target_metrics.confidence if target_metrics else None,
        ))

    # 3. Scope exception — preserve existing open scope evidence and also
    # infer it for approved/current charges that are repeatedly retrieved
    # but never applied, which is a stronger out-of-scope signal than
    # brand-new zero-usage charges.
    inferred_scope = (
        target_metrics
        and target_metrics.trace_status in {None, "approved", "current"}
        and target_metrics.retrieval_count > 0
        and target_metrics.application_count == 0
    )
    if scope_items or inferred_scope:
        sources = [e["source"] for e in scope_items[:3]]
        seen_classifications.add("scope_exception")
        findings.append(ChallengerFinding(
            trace_id=target_trace_id,
            classification="scope_exception",
            rationale=(
                f"Trace {target_trace_id} appears out of scope for this Cell"
                if scope_items
                else (
                    f"Trace {target_trace_id} was retrieved {target_metrics.retrieval_count} time(s) "
                    f"but never applied (status: {target_metrics.trace_status or 'unknown'}) — "
                    f"may be out of scope for this Cell"
                )
            ),
            signal_strength=0.35 if scope_items else 0.3,
            counter_evidence_source=(
                "; ".join(sources)
                if scope_items
                else "metrics: retrieved_without_application"
            ),
            target_status=target_metrics.trace_status if target_metrics else None,
            target_confidence=target_metrics.confidence if target_metrics else None,
        ))

    # 4. Temporal update
    if temporal_items:
        sources = [e["source"] for e in temporal_items[:3]]
        seen_classifications.add("temporal_update")
        findings.append(ChallengerFinding(
            trace_id=target_trace_id,
            classification="temporal_update",
            rationale=(
                f"Found {len(temporal_items)} newer Pulse(s) of type "
                f"update/revision/correction — knowledge may be outdated"
            ),
            signal_strength=0.4,
            counter_evidence_source="; ".join(sources),
            target_status=target_metrics.trace_status if target_metrics else None,
            target_confidence=target_metrics.confidence if target_metrics else None,
        ))

    # 5. Policy conflict (prompt-injection / policy-violating instructions)
    # This is a conservative, local-only heuristic that never mutates state.
    policy_items = [e for e in evidence_items if e.get("direction") == "policy"]
    if policy_items:
        sources = [e["source"] for e in policy_items[:3]]
        seen_classifications.add("policy_conflict")
        findings.append(ChallengerFinding(
            trace_id=target_trace_id,
            classification="policy_conflict",
            rationale=(
                f"Found {len(policy_items)} policy-conflict signal(s) linked to {target_trace_id} "
                f"(e.g. prompt-injection-like instruction in evidence)"
            ),
            signal_strength=0.45,
            counter_evidence_source="; ".join(sources),
            target_status=target_metrics.trace_status if target_metrics else None,
            target_confidence=target_metrics.confidence if target_metrics else None,
            supporting_data={"policy_signal": "prompt_injection_like"},
        ))

    # 6. Ambiguous counter-evidence
    if ambiguous_items:
        sources = [e["source"] for e in ambiguous_items[:3]]
        seen_classifications.add("ambiguous_counterevidence")
        findings.append(ChallengerFinding(
            trace_id=target_trace_id,
            classification="ambiguous_counterevidence",
            rationale=(
                f"Found {len(ambiguous_items)} ambiguous pack miss record(s) "
                f"for {target_trace_id}"
            ),
            signal_strength=0.3,
            counter_evidence_source="; ".join(sources),
            target_status=target_metrics.trace_status if target_metrics else None,
            target_confidence=target_metrics.confidence if target_metrics else None,
        ))

    return findings


# ---------------------------------------------------------------------------
# Dedup for audit sparks
# ---------------------------------------------------------------------------


def _finding_spark_key(
    cell_id: str,
    finding: ChallengerFinding,
) -> str:
    """Deterministic dedup key for a challenger finding.

    Two findings for the same trace with the same classification and
    evidence source produce the same key, preventing duplicate sparks.
    """
    payload = {
        "cell_id": cell_id,
        "trace_id": finding.trace_id,
        "classification": finding.classification,
        "counter_evidence_source": finding.counter_evidence_source,
    }
    digest = hashlib.sha256(
        _json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"challenge:{cell_id}:{finding.trace_id}:{finding.classification}:{digest}"


def _existing_open_challenge_keys(cell: Path) -> set[str]:
    """Read existing audit sparks to find active challenge keys.

    Only open/pending sparks are considered; closed/resolved/accepted
    sparks are skipped so the same finding can be re-raised if it
    re-emerges after resolution.
    """
    closed_decisions = {"accepted", "rejected", "resolved", "closed", "dismissed"}
    reviews_path = cell / "ledger" / "audit_reviews.jsonl"
    manifest_path = cell / "config" / "cell_manifest.json"
    manifest_cell_id = ""
    if manifest_path.exists():
        manifest_cell_id = str(_json.loads(manifest_path.read_text(encoding="utf-8")).get("cell_id", ""))
    closed_spark_ids = set()
    if reviews_path.exists():
        closed_spark_ids = {
            str(record.get("spark_id"))
            for _, record in read_audit_reviews(cell)
            if str(record.get("decision", "")).lower() in closed_decisions and record.get("spark_id")
        }

    open_keys: set[str] = set()
    for spark in read_audit_sparks(cell):
        spark_id = spark.get("spark_id")
        if spark_id in closed_spark_ids:
            continue
        classification = str(spark.get("classification", ""))
        if classification not in CHALLENGER_FINDING_CLASSIFICATIONS:
            continue
        spark_cell_id = str(spark.get("cell_id") or manifest_cell_id)
        if not spark_cell_id:
            continue
        open_keys.add(
            _finding_spark_key(
                spark_cell_id,
                ChallengerFinding(
                    trace_id=spark.get("trace_id", ""),
                    classification=classification,
                    rationale=spark.get("rationale", ""),
                    counter_evidence_source=spark.get("counter_evidence_source", ""),
                ),
            )
        )
    return open_keys


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_challenge(
    cell_path: PathLike,
    *,
    dry_run: bool = True,
    propose: bool = False,
    top_n: Optional[int] = None,
    min_rank_score: float = 0.0,
    charge_id: Optional[str] = None,
    output_path: Optional[PathLike] = None,
) -> ChallengerReport:
    """Run a Challenger audit loop pass on a Cell.

    Parameters
    ----------
    cell_path : path to the Cell directory
    dry_run : if True (default), no ledger records are written
    propose : when True and dry_run is False, append audit sparks to
        ledger/audit_sparks.jsonl
    top_n : if set, only challenge the top N highest-scored targets
    min_rank_score : minimum rank score threshold (0.0 = no filter)
    charge_id : if set, challenge only this specific charge/trace
    output_path : optional path to write report JSON

    Returns
    -------
    ChallengerReport with findings.
    """
    from datetime import datetime, timezone

    cell = Path(cell_path)

    # Read cell manifest
    manifest_path = cell / "config" / "cell_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Cell manifest not found: {manifest_path}")
    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    cell_id = str(manifest.get("cell_id", ""))

    scanned_at = datetime.now(timezone.utc).isoformat()

    # 1. Compute metrics
    trace_metrics = compute_trace_metrics(cell)

    # 2. Filter to specific charge if requested
    if charge_id:
        filtered = {k: v for k, v in trace_metrics.items() if k == charge_id}
        if not filtered:
            raise ValueError(f"Charge {charge_id} not found in Cell {cell_id}")
        trace_metrics = filtered

    # 3. Rank targets
    ranked = rank_targets(
        trace_metrics,
        top_n=top_n,
        min_score=min_rank_score,
    )

    # 4. For each ranked target, collect and classify evidence
    findings: List[ChallengerFinding] = []
    for target_tid, target_m, score in ranked:
        evidence_items = _collect_counter_evidence(
            cell,
            target_tid,
            target_metrics=target_m,
        )
        target_findings = _classify_evidence(target_tid, target_m, evidence_items)
        for f in target_findings:
            findings.append(ChallengerFinding(
                trace_id=f.trace_id,
                classification=f.classification,
                rationale=f.rationale,
                signal_strength=f.signal_strength,
                counter_evidence_source=f.counter_evidence_source,
                supporting_data={
                    **(f.supporting_data or {}),
                    "rank_score": score,
                },
                fragment_id=target_m.source_fragment_ids[0] if target_m.source_fragment_ids else "",
                target_status=f.target_status,
                target_confidence=f.target_confidence,
                rank_score=score,
            ))

    # 5. Sort findings deterministically
    findings.sort(key=lambda f: (f.classification, f.trace_id, f.rationale))

    # 6. Compute summary
    classification_counts: Dict[str, int] = {}
    for f in findings:
        classification_counts[f.classification] = classification_counts.get(f.classification, 0) + 1

    summary = {
        "total_targets_scanned": len(trace_metrics),
        "targets_ranked": len(ranked),
        "total_findings": len(findings),
        "findings_by_classification": dict(
            sorted(classification_counts.items(), key=lambda x: -x[1])
        ),
    }

    # 7. Write audit sparks if propose and not dry_run
    written_spark_ids: List[str] = []
    skipped_spark_ids: List[str] = []
    if propose and not dry_run:
        existing_keys = _existing_open_challenge_keys(cell)
        for finding in findings:
            key = _finding_spark_key(cell_id, finding)
            if key in existing_keys:
                skipped_spark_ids.append(key)
                continue
            record = append_audit_spark(
                cell,
                trace_id=finding.trace_id,
                classification=finding.classification,
                challenger="challenger-bot",
                rationale=finding.rationale,
                counter_evidence_source=finding.counter_evidence_source,
                cell_id=cell_id,
                fragment_id=finding.fragment_id,
                spark_id=key,
                proposed_at=scanned_at,
            )
            written_spark_ids.append(key)
            existing_keys.add(key)
        summary = {
            **summary,
            "sparks_written": len(written_spark_ids),
            "sparks_skipped": len(skipped_spark_ids),
        }

    # 8. Build report
    report = ChallengerReport(
        cell_id=cell_id,
        scanned_at=scanned_at,
        dry_run=dry_run,
        target_count=len(trace_metrics),
        findings=findings,
        written_spark_ids=written_spark_ids,
        skipped_spark_ids=skipped_spark_ids,
        summary=summary,
    )

    # 9. Write output if requested
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            _json.dumps(report.to_dict(), sort_keys=True, indent=2, default=str),
            encoding="utf-8",
        )

    return report
