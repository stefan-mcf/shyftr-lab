"""Trust-aware hybrid retrieval combining sparse, vector, symbolic, confidence, outcome, and negative-space signals.

The hybrid Mesh merges results from sparse (BM25) and vector (cosine)
retrieval, applies trust-tier weighting, and returns explainable score
traces so downstream consumers can understand why each item was selected.

Trust tiers (highest to lowest):
  Doctrine > approved Traces > Alloys > Fragments > Sources

Fragments are background-only unless explicitly included via
``include_fragments=True``.

AL-2 Negative-Space Retrieval:
  Adds caution-coefficient scoring for negative-space kinds
  (failure_signature, anti_pattern, supersession) and status-based
  filtering/penalisation (challenged, isolation_candidate, isolated,
  superseded, deprecated).  Each result carries a ``selection_reason``
  code explaining why it was included.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, FrozenSet, List, Optional, Sequence


from .sparse import SparseResult
from .vector import VectorResult


# ---------------------------------------------------------------------------
# AL-2 constants
# ---------------------------------------------------------------------------

# Negative-space kinds — these Trace/Charge kinds carry caution semantics.
NEGATIVE_SPACE_KINDS: FrozenSet[str] = frozenset(
    {"failure_signature", "anti_pattern", "supersession"}
)

# Statuses that cause items to be excluded from normal guidance output.
# AL-8: isolation_candidate is excluded by default; audit/debug mode via
# ``include_all_statuses`` can re-include these for review purposes.
EXCLUDED_STATUSES: FrozenSet[str] = frozenset(
    {"isolated", "superseded", "deprecated", "isolation_candidate"}
)

# Statuses that trigger a risk penalty and caution labelling.
PENALISED_STATUSES: FrozenSet[str] = frozenset(
    {"challenged"}
)

# Selection reason codes (returned in ``HybridResult.selection_reason``).
SELECTION_POSITIVE: str = "positive_guidance"
SELECTION_CAUTION: str = "caution"
SELECTION_SUPPRESSED: str = "suppressed"
SELECTION_FILTERED: str = "filtered"
SELECTION_CONFLICT: str = "conflict"


def _norm(value: Any) -> str:
    """Return a safe lower-case string for optional ledger fields."""
    return str(value or "").strip().lower()


# ---------------------------------------------------------------------------
# Trust tiers
# ---------------------------------------------------------------------------

class TrustTier(IntEnum):
    """Trust tiers ordered from highest to lowest authority."""

    DOCTRINE = 50
    TRACE = 40
    ALLOY = 30
    FRAGMENT = 20
    SOURCE = 10


_TIER_MAP: Dict[str, TrustTier] = {
    "doctrine": TrustTier.DOCTRINE,
    "trace": TrustTier.TRACE,
    "alloy": TrustTier.ALLOY,
    "fragment": TrustTier.FRAGMENT,
    "source": TrustTier.SOURCE,
}


def resolve_trust_tier(tier_label: str) -> TrustTier:
    """Resolve a string tier label to a TrustTier enum value."""
    key = tier_label.strip().lower()
    if key not in _TIER_MAP:
        raise ValueError(f"Unknown trust tier: {tier_label!r}")
    return _TIER_MAP[key]


# ---------------------------------------------------------------------------
# Score components
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoreComponents:
    """Breakdown of every signal contributing to a hybrid score.

    All components are 0.0-1.0 normalised where applicable, except
    ``trust_tier`` which is the raw integer tier value.

    AL-2 negative-space fields (positive_similarity through risk_penalty)
    are zero for standard positive-guidance items.
    """

    dense: float = 0.0
    sparse: float = 0.0
    kind_match: float = 0.0
    tag_match: float = 0.0
    confidence: float = 0.0
    reuse_bonus: float = 0.0
    reuse_penalty: float = 0.0
    decay: float = 0.0
    deprecation_penalty: float = 0.0
    trust_tier: int = 0
    # --- AL-2 negative-space components ---
    positive_similarity: float = 0.0
    negative_similarity: float = 0.0
    confidence_weight: float = 0.0
    proven_signal_weight: float = 0.0
    symbolic_match_weight: float = 0.0
    risk_penalty: float = 0.0
    selection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "dense": self.dense,
            "sparse": self.sparse,
            "kind_match": self.kind_match,
            "tag_match": self.tag_match,
            "confidence": self.confidence,
            "reuse_bonus": self.reuse_bonus,
            "reuse_penalty": self.reuse_penalty,
            "decay": self.decay,
            "deprecation_penalty": self.deprecation_penalty,
            "trust_tier": self.trust_tier,
            "positive_similarity": self.positive_similarity,
            "negative_similarity": self.negative_similarity,
            "confidence_weight": self.confidence_weight,
            "proven_signal_weight": self.proven_signal_weight,
            "symbolic_match_weight": self.symbolic_match_weight,
            "risk_penalty": self.risk_penalty,
            "selection_reason": self.selection_reason,
        }


# ---------------------------------------------------------------------------
# Hybrid result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HybridResult:
    """A single hybrid retrieval result with full score trace.

    ``selection_reason`` explains why this item was selected (AL-2):
      - positive_guidance : standard item, no caution flags
      - caution           : negative-space kind or penalised status
      - suppressed        : item whose score was heavily reduced by a
                            related negative-space item
      - filtered          : item excluded from results entirely
      - conflict          : item whose signal conflicts with a caution item
    """

    item_id: str
    cell_id: str
    trust_tier: str
    statement: str
    rationale: Optional[str]
    tags: List[str]
    kind: Optional[str]
    memory_type: Optional[str]
    status: str = "approved"
    confidence: Optional[float] = None
    final_score: float = 0.0
    components: ScoreComponents = field(default_factory=ScoreComponents)
    resource_ref: Optional[Dict[str, Any]] = None
    grounding_refs: List[str] = field(default_factory=list)
    sensitivity: Optional[str] = None
    retention_hint: Optional[str] = None
    selection_reason: str = SELECTION_POSITIVE

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "item_id": self.item_id,
            "cell_id": self.cell_id,
            "trust_tier": self.trust_tier,
            "statement": self.statement,
            "rationale": self.rationale,
            "tags": self.tags,
            "kind": self.kind,
            "memory_type": self.memory_type,
            "resource_ref": self.resource_ref,
            "grounding_refs": list(self.grounding_refs),
            "sensitivity": self.sensitivity,
            "retention_hint": self.retention_hint,
            "status": self.status,
            "confidence": self.confidence,
            "final_score": self.final_score,
            "components": self.components.to_dict(),
            "selection_reason": self.selection_reason,
        }


# ---------------------------------------------------------------------------
# Candidate items for hybrid scoring
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CandidateItem:
    """A pre-scored candidate item ready for hybrid fusion.

    Callers build these from sparse/vector results or from direct ledger
    reads and pass them to :func:`hybrid_search`.

    AL-2 additions:
      ``negative_space_kind`` — set to ``failure_signature``,
        ``anti_pattern``, or ``supersession`` when the item represents a
        caution/negative-space concept.
      ``related_positive_ids`` — links this negative-space item to related
        positive guidance items for conflict and suppression analysis.
    """

    item_id: str
    cell_id: str
    trust_tier: str
    statement: str
    rationale: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    kind: Optional[str] = None
    memory_type: Optional[str] = None
    resource_ref: Optional[Dict[str, Any]] = None
    grounding_refs: List[str] = field(default_factory=list)
    sensitivity: Optional[str] = None
    retention_hint: Optional[str] = None
    status: str = "approved"
    confidence: Optional[float] = None
    # Score inputs (0.0-1.0 normalised)
    dense_score: float = 0.0
    sparse_score: float = 0.0
    # Outcome signals
    success_count: int = 0
    failure_count: int = 0
    # Decay / deprecation
    decay: float = 0.0
    is_deprecated: bool = False
    is_quarantined: bool = False
    # --- AL-2 negative-space fields ---
    negative_space_kind: Optional[str] = None
    related_positive_ids: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default weights
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HybridWeights:
    """Configurable weights for hybrid score fusion.

    ``caution_coefficient`` (AL-2) is multiplied against the raw score
    of negative-space items so they rank lower than equivalently-scored
    positive guidance by default.
    """

    w_dense: float = 0.25
    w_sparse: float = 0.25
    w_kind: float = 0.10
    w_tag: float = 0.10
    w_confidence: float = 0.15
    w_reuse: float = 0.10
    w_decay: float = 0.05
    w_deprecation: float = 0.05
    # Trust-tier multiplier (applied on top of weighted sum)
    tier_multiplier: float = 0.15
    # --- AL-2 ---
    caution_coefficient: float = 0.5


DEFAULT_WEIGHTS = HybridWeights()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_negative_space(item: CandidateItem) -> bool:
    """Return True if *item* is a negative-space candidate.

    Checks ``negative_space_kind`` first, then falls back to ``kind``.
    """
    if item.negative_space_kind and _norm(item.negative_space_kind) in NEGATIVE_SPACE_KINDS:
        return True
    if item.kind and _norm(item.kind) in NEGATIVE_SPACE_KINDS:
        return True
    return False


def _compute_selection_reason(
    item: CandidateItem,
    is_neg: bool,
    is_penalised: bool,
    *,
    include_all_statuses: bool = False,
) -> str:
    """Determine the selection reason for a result item.

    When *include_all_statuses* is True (audit/debug mode), items with
    excluded statuses are still labelled ``filtered`` but are NOT filtered
    out of results — downstream consumers can decide how to handle them.
    """
    if _norm(item.status) in EXCLUDED_STATUSES:
        return SELECTION_FILTERED
    if is_neg:
        return SELECTION_CAUTION
    if is_penalised:
        return SELECTION_CAUTION
    return SELECTION_POSITIVE


def _related_positive_map(candidates: Sequence[CandidateItem]) -> Dict[str, List[CandidateItem]]:
    """Return negative-space items keyed by related positive item id."""
    related: Dict[str, List[CandidateItem]] = {}
    for item in candidates:
        if not _is_negative_space(item):
            continue
        for positive_id in item.related_positive_ids:
            related.setdefault(str(positive_id), []).append(item)
    return related


def _related_positive_reason(negative_items: Sequence[CandidateItem]) -> str:
    """Resolve suppression semantics for positives linked to negative-space items."""
    for item in negative_items:
        if _norm(item.negative_space_kind or item.kind) == "supersession":
            return SELECTION_SUPPRESSED
        if _norm(item.status) in {"superseded", "deprecated"}:
            return SELECTION_SUPPRESSED
    return SELECTION_CONFLICT


def _apply_related_positive_semantics(
    results: Sequence[HybridResult],
    related_map: Dict[str, List[CandidateItem]],
) -> List[HybridResult]:
    """Apply conflict/suppression semantics to linked positive guidance items."""
    adjusted: List[HybridResult] = []
    for result in results:
        related_negative_items = related_map.get(result.item_id, [])
        if not related_negative_items or result.selection_reason != SELECTION_POSITIVE:
            adjusted.append(result)
            continue

        adjusted_reason = _related_positive_reason(related_negative_items)
        score_factor = 0.75 if adjusted_reason == SELECTION_SUPPRESSED else 0.85
        adjusted_components = ScoreComponents(
            dense=result.components.dense,
            sparse=result.components.sparse,
            kind_match=result.components.kind_match,
            tag_match=result.components.tag_match,
            confidence=result.components.confidence,
            reuse_bonus=result.components.reuse_bonus,
            reuse_penalty=result.components.reuse_penalty,
            decay=result.components.decay,
            deprecation_penalty=result.components.deprecation_penalty,
            trust_tier=result.components.trust_tier,
            positive_similarity=result.components.positive_similarity,
            negative_similarity=result.components.negative_similarity,
            confidence_weight=result.components.confidence_weight,
            proven_signal_weight=result.components.proven_signal_weight,
            symbolic_match_weight=result.components.symbolic_match_weight,
            risk_penalty=result.components.risk_penalty,
            selection_reason=adjusted_reason,
        )
        adjusted.append(
            HybridResult(
                item_id=result.item_id,
                cell_id=result.cell_id,
                trust_tier=result.trust_tier,
                statement=result.statement,
                rationale=result.rationale,
                tags=result.tags,
                kind=result.kind,
                memory_type=result.memory_type,
                status=result.status,
                confidence=result.confidence,
                final_score=result.final_score * score_factor,
                components=adjusted_components,
                selection_reason=adjusted_reason,
            )
        )
    return adjusted


# ---------------------------------------------------------------------------
# Core hybrid search
# ---------------------------------------------------------------------------

def hybrid_search(
    candidates: Sequence[CandidateItem],
    *,
    query_kind: Optional[str] = None,
    query_tags: Optional[Sequence[str]] = None,
    include_fragments: bool = False,
    include_all_statuses: bool = False,
    weights: HybridWeights = DEFAULT_WEIGHTS,
    top_k: int = 10,
) -> List[HybridResult]:
    """Score and rank candidates through trust-aware hybrid fusion.

    Parameters
    ----------
    candidates : sequence of CandidateItem
        Pre-scored candidate items from sparse/vector/direct sources.
    query_kind : str, optional
        Expected kind for kind-match scoring.
    query_tags : sequence of str, optional
        Expected tags for tag-match scoring.
    include_fragments : bool
        If False (default), Fragment-tier items are excluded.
    include_all_statuses : bool
        If True (audit/debug mode), items with excluded statuses
        (isolated, superseded, deprecated, isolation_candidate) are
        included with ``selection_reason = \"filtered\"`` rather than
        being omitted from results.  Default False.
    weights : HybridWeights
        Fusion weights, including ``caution_coefficient``.
    top_k : int
        Maximum results to return.

    Returns
    -------
    list of HybridResult
        Results sorted by final_score descending, with explainable traces
        and AL-2 selection_reason codes.
    """
    results: List[HybridResult] = []

    for item in candidates:
        # --- Fragment exclusion ---
        tier = resolve_trust_tier(item.trust_tier)
        if tier == TrustTier.FRAGMENT and not include_fragments:
            continue

        # --- AL-2 status pre-filter (excluded statuses) ---
        if _norm(item.status) in EXCLUDED_STATUSES and not include_all_statuses:
            # Excluded items are omitted from normal guidance output.
            # In audit/debug mode (include_all_statuses=True) they are
            # still included with ``selection_reason = "filtered"``.
            continue

        # --- AL-2 negative-space detection ---
        is_negative = _is_negative_space(item)
        is_penalised = _norm(item.status) in PENALISED_STATUSES

        # --- Deprecation / quarantine penalty ---
        dep_penalty = 0.0
        if item.is_deprecated:
            dep_penalty = 1.0
        elif item.is_quarantined:
            dep_penalty = 0.5

        # --- Kind match ---
        kind_match = 0.0
        if query_kind and item.kind:
            if item.kind.lower() == query_kind.lower():
                kind_match = 1.0

        # --- Tag match ---
        tag_match = 0.0
        if query_tags and item.tags:
            query_set = {t.lower() for t in query_tags}
            item_set = {t.lower() for t in item.tags}
            overlap = query_set & item_set
            if overlap:
                tag_match = len(overlap) / max(len(query_set), 1)

        # --- Confidence ---
        conf = item.confidence if item.confidence is not None else 0.5

        # --- Reuse signals ---
        total_uses = item.success_count + item.failure_count
        reuse_bonus = 0.0
        reuse_penalty = 0.0
        if total_uses > 0:
            reuse_bonus = min(item.success_count / total_uses, 1.0)
            reuse_penalty = min(item.failure_count / total_uses, 1.0)

        # --- AL-2 negative-space scoring components ---
        # Positive similarity: aggregate of dense + sparse signal
        positive_similarity = (item.dense_score + item.sparse_score) / 2.0

        # Negative similarity: for negative-space items, how much the
        # negative signal matches (proxied by the same dense+sparse score)
        negative_similarity = positive_similarity if is_negative else 0.0

        # Confidence weight: confidence value scaled by w_confidence
        confidence_weight = conf

        # Proven signal weight: success rate with Laplace smoothing
        proven_total = item.success_count + item.failure_count
        if proven_total > 0:
            proven_signal_weight = (item.success_count + 1) / (proven_total + 2)
        else:
            proven_signal_weight = 0.5

        # Symbolic match weight: average of kind + tag match
        symbolic_match_weight = (kind_match + tag_match) / 2.0

        # Risk penalty: penalise challenged / isolation_candidate items
        risk_penalty = 0.0
        if is_penalised or is_negative:
            risk_penalty = weights.w_deprecation * 0.5
            if is_negative:
                risk_penalty += 0.1 * max(0.0, negative_similarity)

        # --- Weighted sum ---
        utility_signal = proven_signal_weight - 0.5
        raw_score = (
            weights.w_dense * item.dense_score
            + weights.w_sparse * item.sparse_score
            + weights.w_kind * kind_match
            + weights.w_tag * tag_match
            + weights.w_confidence * conf
            + weights.w_reuse * (reuse_bonus - reuse_penalty)
            + (weights.w_reuse * 0.25) * utility_signal
            - weights.w_decay * item.decay
            - weights.w_deprecation * dep_penalty
        )

        # --- Trust-tier boost ---
        tier_boost = weights.tier_multiplier * (tier.value / 50.0)
        base_score = raw_score + tier_boost

        # --- AL-2 caution coefficient for negative-space items ---
        if is_negative:
            final_score = base_score * weights.caution_coefficient
        else:
            final_score = base_score

        # Subtract risk penalty
        final_score = max(0.0, final_score - risk_penalty)

        # --- Selection reason ---
        selection_reason = _compute_selection_reason(item, is_negative, is_penalised, include_all_statuses=include_all_statuses)

        components = ScoreComponents(
            dense=item.dense_score,
            sparse=item.sparse_score,
            kind_match=kind_match,
            tag_match=tag_match,
            confidence=conf,
            reuse_bonus=reuse_bonus,
            reuse_penalty=reuse_penalty,
            decay=item.decay,
            deprecation_penalty=dep_penalty,
            trust_tier=tier.value,
            positive_similarity=positive_similarity,
            negative_similarity=negative_similarity,
            confidence_weight=confidence_weight,
            proven_signal_weight=proven_signal_weight,
            symbolic_match_weight=symbolic_match_weight,
            risk_penalty=risk_penalty,
            selection_reason=selection_reason,
        )

        results.append(
            HybridResult(
                item_id=item.item_id,
                cell_id=item.cell_id,
                trust_tier=item.trust_tier,
                statement=item.statement,
                rationale=item.rationale,
                tags=item.tags,
                kind=item.kind,
                memory_type=item.memory_type,
                resource_ref=item.resource_ref,
                grounding_refs=list(item.grounding_refs),
                sensitivity=item.sensitivity,
                retention_hint=item.retention_hint,
                status=item.status,
                confidence=item.confidence,
                final_score=final_score,
                components=components,
                selection_reason=selection_reason,
            )
        )

    # --- Phase 4 related caution handling ---
    related_map = _related_positive_map(candidates)
    if related_map:
        results = _apply_related_positive_semantics(results, related_map)

    # Sort by final_score descending, break ties by trust tier descending
    results.sort(key=lambda r: (r.final_score, r.components.trust_tier, r.item_id), reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Convenience: build candidates from sparse + vector results
# ---------------------------------------------------------------------------

def candidates_from_sparse(
    results: Sequence[SparseResult],
    *,
    trust_tier: str = "trace",
) -> List[CandidateItem]:
    """Convert SparseResult objects into CandidateItems.

    BM25 scores are min-max normalised across the result set.
    """
    if not results:
        return []

    scores = [r.bm25_score for r in results]
    min_s, max_s = min(scores), max(scores)
    span = max_s - min_s if max_s != min_s else 1.0

    return [
        CandidateItem(
            item_id=r.trace_id,
            cell_id=r.cell_id,
            trust_tier=trust_tier,
            statement=r.statement,
            rationale=(r.rationale or r.label),
            tags=r.tags,
            kind=r.kind,
            resource_ref={"label": r.label} if r.label else None,
            status=r.status,
            confidence=r.confidence,
            sparse_score=(max_s - r.bm25_score) / span,
        )
        for r in results
    ]


def candidates_from_vector(
    results: Sequence[VectorResult],
    *,
    trust_tier: str = "trace",
) -> List[CandidateItem]:
    """Convert VectorResult objects into CandidateItems.

    Cosine scores are already 0-1 so no additional normalisation is needed.
    """
    return [
        CandidateItem(
            item_id=r.trace_id,
            cell_id=r.cell_id,
            trust_tier=trust_tier,
            statement=r.statement,
            rationale=r.rationale,
            tags=r.tags,
            kind=r.kind,
            status=r.status,
            confidence=r.confidence,
            dense_score=max(r.cosine_score, 0.0),
        )
        for r in results
    ]


def merge_candidates(
    sparse_items: Sequence[CandidateItem],
    vector_items: Sequence[CandidateItem],
) -> List[CandidateItem]:
    """Merge sparse and vector candidates, combining scores for shared item_ids.

    When the same item appears in both lists, the scores are combined
    (dense from vector, sparse from sparse).  Unique items are kept as-is.
    """
    by_id: Dict[str, CandidateItem] = {}

    for item in sparse_items:
        by_id[item.item_id] = item

    for item in vector_items:
        if item.item_id in by_id:
            existing = by_id[item.item_id]
            # Combine: keep sparse score from sparse, dense score from vector
            merged = CandidateItem(
                item_id=existing.item_id,
                cell_id=existing.cell_id,
                trust_tier=existing.trust_tier,
                statement=existing.statement or item.statement,
                rationale=existing.rationale or item.rationale,
                tags=existing.tags or item.tags,
                kind=existing.kind or item.kind,
                memory_type=existing.memory_type or item.memory_type,
                resource_ref=existing.resource_ref or item.resource_ref,
                grounding_refs=existing.grounding_refs or item.grounding_refs,
                sensitivity=existing.sensitivity or item.sensitivity,
                retention_hint=existing.retention_hint or item.retention_hint,
                status=existing.status,
                confidence=existing.confidence or item.confidence,
                dense_score=max(existing.dense_score, item.dense_score),
                sparse_score=max(existing.sparse_score, item.sparse_score),
                success_count=max(existing.success_count, item.success_count),
                failure_count=max(existing.failure_count, item.failure_count),
                decay=min(existing.decay, item.decay),
                is_deprecated=existing.is_deprecated or item.is_deprecated,
                is_quarantined=existing.is_quarantined or item.is_quarantined,
                negative_space_kind=existing.negative_space_kind or item.negative_space_kind,
                related_positive_ids=list(
                    set(existing.related_positive_ids) | set(item.related_positive_ids)
                ),
            )
            by_id[item.item_id] = merged
        else:
            by_id[item.item_id] = item

    return list(by_id.values())
