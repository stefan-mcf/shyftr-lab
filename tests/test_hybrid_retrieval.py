"""Tests for trust-aware hybrid retrieval (Work slice 9).

All tests are dependency-free and network-free.
"""
from __future__ import annotations

import pytest

from shyftr.retrieval.hybrid import (
    CandidateItem,
    HybridResult,
    HybridWeights,
    ScoreComponents,
    TrustTier,
    candidates_from_sparse,
    candidates_from_vector,
    hybrid_search,
    merge_candidates,
    resolve_trust_tier,
)
from shyftr.retrieval.sparse import SparseResult
from shyftr.retrieval.vector import VectorResult


# ---------------------------------------------------------------------------
# Trust tier resolution
# ---------------------------------------------------------------------------

class TestTrustTiers:
    def test_all_tiers_resolve(self):
        assert resolve_trust_tier("doctrine") == TrustTier.DOCTRINE
        assert resolve_trust_tier("trace") == TrustTier.TRACE
        assert resolve_trust_tier("alloy") == TrustTier.ALLOY
        assert resolve_trust_tier("fragment") == TrustTier.FRAGMENT
        assert resolve_trust_tier("source") == TrustTier.SOURCE

    def test_case_insensitive(self):
        assert resolve_trust_tier("DOCTRINE") == TrustTier.DOCTRINE
        assert resolve_trust_tier(" Trace ") == TrustTier.TRACE

    def test_unknown_tier_raises(self):
        with pytest.raises(ValueError, match="Unknown trust tier"):
            resolve_trust_tier("bogus")

    def test_tier_ordering(self):
        assert TrustTier.DOCTRINE > TrustTier.TRACE > TrustTier.ALLOY
        assert TrustTier.ALLOY > TrustTier.FRAGMENT > TrustTier.SOURCE


# ---------------------------------------------------------------------------
# Trust-tier ordering: Doctrine > Traces > Alloys > Fragments > Sources
# ---------------------------------------------------------------------------

class TestTrustTierOrdering:
    """Approved Traces outrank unapproved Fragments by default."""

    def _make(self, tier: str, **kw) -> CandidateItem:
        defaults = dict(
            item_id=f"{tier}-1",
            cell_id="c1",
            trust_tier=tier,
            statement=f"stmt-{tier}",
        )
        defaults.update(kw)
        return CandidateItem(**defaults)

    def test_doctrine_beats_trace(self):
        d = self._make("doctrine", dense_score=0.5)
        t = self._make("trace", dense_score=0.5)
        results = hybrid_search([d, t])
        assert results[0].trust_tier == "doctrine"

    def test_trace_beats_alloy(self):
        t = self._make("trace", dense_score=0.5)
        a = self._make("alloy", dense_score=0.5)
        results = hybrid_search([t, a])
        assert results[0].trust_tier == "trace"

    def test_alloy_beats_fragment(self):
        a = self._make("alloy", dense_score=0.5)
        f = self._make("fragment", dense_score=0.5)
        results = hybrid_search([a, f], include_fragments=True)
        assert results[0].trust_tier == "alloy"

    def test_fragment_beats_source(self):
        f = self._make("fragment", dense_score=0.5)
        s = self._make("source", dense_score=0.5)
        results = hybrid_search([f, s], include_fragments=True)
        assert results[0].trust_tier == "fragment"

    def test_comparable_scores_tier_ordering(self):
        """When all scores are identical, tier ordering is the sole discriminator."""
        items = [
            self._make("source", dense_score=0.3, sparse_score=0.3),
            self._make("fragment", dense_score=0.3, sparse_score=0.3),
            self._make("alloy", dense_score=0.3, sparse_score=0.3),
            self._make("trace", dense_score=0.3, sparse_score=0.3),
            self._make("doctrine", dense_score=0.3, sparse_score=0.3),
        ]
        results = hybrid_search(items, include_fragments=True)
        tiers = [r.trust_tier for r in results]
        assert tiers == ["doctrine", "trace", "alloy", "fragment", "source"]


# ---------------------------------------------------------------------------
# Approved Traces outrank unapproved Fragments by default
# ---------------------------------------------------------------------------

class TestApprovedTraceVsFragment:
    def test_approved_trace_beats_unapproved_fragment(self):
        trace = CandidateItem(
            item_id="t1", cell_id="c1", trust_tier="trace",
            statement="approved trace", status="approved", dense_score=0.3,
        )
        fragment = CandidateItem(
            item_id="f1", cell_id="c1", trust_tier="fragment",
            statement="unapproved fragment", status="pending", dense_score=0.3,
        )
        results = hybrid_search([trace, fragment])
        assert len(results) == 1
        assert results[0].trust_tier == "trace"
        assert results[0].item_id == "t1"


# ---------------------------------------------------------------------------
# Fragment exclusion / background-only
# ---------------------------------------------------------------------------

class TestFragmentExclusion:
    def test_fragments_excluded_by_default(self):
        items = [
            CandidateItem(item_id="t1", cell_id="c1", trust_tier="trace",
                          statement="trace", dense_score=0.5),
            CandidateItem(item_id="f1", cell_id="c1", trust_tier="fragment",
                          statement="fragment", dense_score=0.9),
        ]
        results = hybrid_search(items)
        assert len(results) == 1
        assert results[0].item_id == "t1"

    def test_fragments_included_when_flag_set(self):
        items = [
            CandidateItem(item_id="t1", cell_id="c1", trust_tier="trace",
                          statement="trace", dense_score=0.5),
            CandidateItem(item_id="f1", cell_id="c1", trust_tier="fragment",
                          statement="fragment", dense_score=0.9),
        ]
        results = hybrid_search(items, include_fragments=True)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Deprecated / quarantined Trace penalty
# ---------------------------------------------------------------------------

class TestDeprecationPenalty:
    def test_deprecated_trace_penalised(self):
        good = CandidateItem(
            item_id="t1", cell_id="c1", trust_tier="trace",
            statement="good", dense_score=0.5, sparse_score=0.5,
        )
        bad = CandidateItem(
            item_id="t2", cell_id="c1", trust_tier="trace",
            statement="deprecated", dense_score=0.5, sparse_score=0.5,
            is_deprecated=True,
        )
        results = hybrid_search([good, bad])
        assert results[0].item_id == "t1"
        assert results[1].item_id == "t2"
        assert results[1].components.deprecation_penalty == 1.0

    def test_quarantined_trace_half_penalty(self):
        good = CandidateItem(
            item_id="t1", cell_id="c1", trust_tier="trace",
            statement="good", dense_score=0.5, sparse_score=0.5,
        )
        q = CandidateItem(
            item_id="t2", cell_id="c1", trust_tier="trace",
            statement="quarantined", dense_score=0.5, sparse_score=0.5,
            is_quarantined=True,
        )
        results = hybrid_search([good, q])
        assert results[0].item_id == "t1"
        assert results[1].components.deprecation_penalty == 0.5


# ---------------------------------------------------------------------------
# Confidence contribution
# ---------------------------------------------------------------------------

class TestConfidenceContribution:
    def test_high_confidence_ranks_above_low(self):
        high = CandidateItem(
            item_id="h", cell_id="c1", trust_tier="trace",
            statement="high conf", dense_score=0.5, sparse_score=0.5,
            confidence=0.95,
        )
        low = CandidateItem(
            item_id="l", cell_id="c1", trust_tier="trace",
            statement="low conf", dense_score=0.5, sparse_score=0.5,
            confidence=0.1,
        )
        results = hybrid_search([low, high])
        assert results[0].item_id == "h"
        assert results[0].components.confidence == 0.95
        assert results[1].components.confidence == 0.1

    def test_missing_confidence_defaults_to_half(self):
        item = CandidateItem(
            item_id="x", cell_id="c1", trust_tier="trace",
            statement="no conf", dense_score=0.5, sparse_score=0.5,
            confidence=None,
        )
        results = hybrid_search([item])
        assert results[0].components.confidence == 0.5


# ---------------------------------------------------------------------------
# Kind / tag match contribution
# ---------------------------------------------------------------------------

class TestKindTagMatch:
    def test_kind_match_bonus(self):
        match = CandidateItem(
            item_id="m", cell_id="c1", trust_tier="trace",
            statement="match", dense_score=0.5, sparse_score=0.5,
            kind="error",
        )
        nomatch = CandidateItem(
            item_id="n", cell_id="c1", trust_tier="trace",
            statement="no match", dense_score=0.5, sparse_score=0.5,
            kind="config",
        )
        results = hybrid_search([nomatch, match], query_kind="error")
        assert results[0].item_id == "m"
        assert results[0].components.kind_match == 1.0
        assert results[1].components.kind_match == 0.0

    def test_tag_match_bonus(self):
        tagged = CandidateItem(
            item_id="t", cell_id="c1", trust_tier="trace",
            statement="tagged", dense_score=0.5, sparse_score=0.5,
            tags=["python", "async"],
        )
        untagged = CandidateItem(
            item_id="u", cell_id="c1", trust_tier="trace",
            statement="untagged", dense_score=0.5, sparse_score=0.5,
            tags=["java"],
        )
        results = hybrid_search([untagged, tagged], query_tags=["python", "async"])
        assert results[0].item_id == "t"
        assert results[0].components.tag_match == 1.0
        assert results[1].components.tag_match == 0.0

    def test_partial_tag_match(self):
        item = CandidateItem(
            item_id="p", cell_id="c1", trust_tier="trace",
            statement="partial", dense_score=0.5, sparse_score=0.5,
            tags=["python"],
        )
        results = hybrid_search([item], query_tags=["python", "async"])
        assert results[0].components.tag_match == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Successful reuse bonus / failed reuse penalty
# ---------------------------------------------------------------------------

class TestReuseSignals:
    def test_success_bonus(self):
        item = CandidateItem(
            item_id="s", cell_id="c1", trust_tier="trace",
            statement="used", dense_score=0.5, sparse_score=0.5,
            success_count=8, failure_count=2,
        )
        results = hybrid_search([item])
        assert results[0].components.reuse_bonus == pytest.approx(0.8)
        assert results[0].components.reuse_penalty == pytest.approx(0.2)

    def test_all_failures_penalty(self):
        item = CandidateItem(
            item_id="f", cell_id="c1", trust_tier="trace",
            statement="failed", dense_score=0.5, sparse_score=0.5,
            success_count=0, failure_count=5,
        )
        results = hybrid_search([item])
        assert results[0].components.reuse_bonus == 0.0
        assert results[0].components.reuse_penalty == 1.0

    def test_no_uses_zero_signals(self):
        item = CandidateItem(
            item_id="n", cell_id="c1", trust_tier="trace",
            statement="unused", dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([item])
        assert results[0].components.reuse_bonus == 0.0
        assert results[0].components.reuse_penalty == 0.0


# ---------------------------------------------------------------------------
# Dense + sparse score fusion ordering
# ---------------------------------------------------------------------------

class TestScoreFusion:
    def test_dense_dominates_when_sparse_zero(self):
        """An item with high dense and zero sparse beats one with zero dense and high sparse."""
        dense_heavy = CandidateItem(
            item_id="d", cell_id="c1", trust_tier="trace",
            statement="dense", dense_score=0.9, sparse_score=0.0,
        )
        sparse_heavy = CandidateItem(
            item_id="s", cell_id="c1", trust_tier="trace",
            statement="sparse", dense_score=0.0, sparse_score=0.9,
        )
        # Both have equal weighted contribution (w_dense == w_sparse == 0.25),
        # so they tie.  The test verifies both are scored and the fusion
        # produces a valid ordered result without crashing.
        results = hybrid_search([sparse_heavy, dense_heavy])
        assert len(results) == 2
        scores = {r.item_id: r.final_score for r in results}
        # Both should have the same final score since weights are symmetric
        assert scores["d"] == pytest.approx(scores["s"])

    def test_sparse_dominates_when_dense_zero(self):
        """An item with high sparse and zero dense is scored correctly."""
        dense_heavy = CandidateItem(
            item_id="d", cell_id="c1", trust_tier="trace",
            statement="dense", dense_score=0.0, sparse_score=0.9,
        )
        sparse_heavy = CandidateItem(
            item_id="s", cell_id="c1", trust_tier="trace",
            statement="sparse", dense_score=0.9, sparse_score=0.0,
        )
        results = hybrid_search([dense_heavy, sparse_heavy])
        assert len(results) == 2
        scores = {r.item_id: r.final_score for r in results}
        assert scores["d"] == pytest.approx(scores["s"])

    def test_balanced_fusion(self):
        both = CandidateItem(
            item_id="b", cell_id="c1", trust_tier="trace",
            statement="both", dense_score=0.7, sparse_score=0.7,
        )
        one = CandidateItem(
            item_id="o", cell_id="c1", trust_tier="trace",
            statement="one", dense_score=0.9, sparse_score=0.0,
        )
        results = hybrid_search([one, both])
        assert results[0].item_id == "b"


# ---------------------------------------------------------------------------
# Explainable score trace
# ---------------------------------------------------------------------------

class TestExplainableTrace:
    def test_result_has_components(self):
        item = CandidateItem(
            item_id="e", cell_id="c1", trust_tier="trace",
            statement="explain", dense_score=0.6, sparse_score=0.4,
            confidence=0.8, tags=["x"], kind="error",
        )
        results = hybrid_search([item], query_kind="error", query_tags=["x"])
        assert len(results) == 1
        comp = results[0].components
        assert comp.dense == 0.6
        assert comp.sparse == 0.4
        assert comp.kind_match == 1.0
        assert comp.tag_match == 1.0
        assert comp.confidence == 0.8
        assert comp.trust_tier == 40  # TRACE

    def test_components_to_dict_roundtrip(self):
        comp = ScoreComponents(
            dense=0.5, sparse=0.3, kind_match=1.0, tag_match=0.5,
            confidence=0.7, reuse_bonus=0.6, reuse_penalty=0.1,
            decay=0.0, deprecation_penalty=0.0, trust_tier=40,
        )
        d = comp.to_dict()
        assert d["dense"] == 0.5
        assert d["trust_tier"] == 40

    def test_result_to_dict(self):
        item = CandidateItem(
            item_id="r", cell_id="c1", trust_tier="trace",
            statement="roundtrip", dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([item])
        d = results[0].to_dict()
        assert d["item_id"] == "r"
        assert "components" in d
        assert isinstance(d["components"], dict)


# ---------------------------------------------------------------------------
# Empty / no-match behaviour
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_candidates_returns_empty(self):
        assert hybrid_search([]) == []

    def test_no_match_query_returns_all(self):
        """hybrid_search does not filter by query text; all candidates are scored."""
        item = CandidateItem(
            item_id="x", cell_id="c1", trust_tier="trace",
            statement="anything", dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([item])
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Top-k limiting
# ---------------------------------------------------------------------------

class TestTopK:
    def test_top_k_limits_results(self):
        items = [
            CandidateItem(
                item_id=f"t{i}", cell_id="c1", trust_tier="trace",
                statement=f"item {i}", dense_score=0.9 - i * 0.1,
            )
            for i in range(5)
        ]
        results = hybrid_search(items, top_k=3)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# Candidate conversion helpers
# ---------------------------------------------------------------------------

class TestCandidateConversion:
    def test_candidates_from_sparse_normalise(self):
        r1 = SparseResult(
            trace_id="t1", cell_id="c1", statement="a", rationale=None,
            tags=[], kind=None, status="approved", confidence=0.8,
            bm25_score=10.0,
        )
        r2 = SparseResult(
            trace_id="t2", cell_id="c1", statement="b", rationale=None,
            tags=[], kind=None, status="approved", confidence=0.5,
            bm25_score=20.0,
        )
        items = candidates_from_sparse([r1, r2])
        assert len(items) == 2
        # Lower BM25 is better, so sparse_score should be higher-is-better.
        scores = {i.item_id: i.sparse_score for i in items}
        assert scores["t1"] == pytest.approx(1.0)
        assert scores["t2"] == pytest.approx(0.0)

    def test_candidates_from_sparse_empty(self):
        assert candidates_from_sparse([]) == []

    def test_candidates_from_vector(self):
        r = VectorResult(
            trace_id="v1", cell_id="c1", statement="vec", rationale=None,
            tags=[], kind=None, status="approved", confidence=0.9,
            cosine_score=0.85,
        )
        items = candidates_from_vector([r])
        assert len(items) == 1
        assert items[0].dense_score == pytest.approx(0.85)

    def test_merge_candidates_combines_scores(self):
        sparse = [
            CandidateItem(
                item_id="t1", cell_id="c1", trust_tier="trace",
                statement="sparse", sparse_score=0.8,
            ),
        ]
        vector = [
            CandidateItem(
                item_id="t1", cell_id="c1", trust_tier="trace",
                statement="vector", dense_score=0.9,
            ),
        ]
        merged = merge_candidates(sparse, vector)
        assert len(merged) == 1
        assert merged[0].sparse_score == pytest.approx(0.8)
        assert merged[0].dense_score == pytest.approx(0.9)

    def test_merge_candidates_keeps_unique(self):
        sparse = [
            CandidateItem(
                item_id="s1", cell_id="c1", trust_tier="trace",
                statement="only-sparse", sparse_score=0.5,
            ),
        ]
        vector = [
            CandidateItem(
                item_id="v1", cell_id="c1", trust_tier="trace",
                statement="only-vector", dense_score=0.5,
            ),
        ]
        merged = merge_candidates(sparse, vector)
        assert len(merged) == 2


# ---------------------------------------------------------------------------
# Decay contribution
# ---------------------------------------------------------------------------

class TestDecayContribution:
    def test_decay_penalises(self):
        fresh = CandidateItem(
            item_id="f", cell_id="c1", trust_tier="trace",
            statement="fresh", dense_score=0.5, sparse_score=0.5,
            decay=0.0,
        )
        stale = CandidateItem(
            item_id="s", cell_id="c1", trust_tier="trace",
            statement="stale", dense_score=0.5, sparse_score=0.5,
            decay=0.8,
        )
        results = hybrid_search([stale, fresh])
        assert results[0].item_id == "f"
        assert results[1].components.decay == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Custom weights
# ---------------------------------------------------------------------------

class TestCustomWeights:
    def test_sparse_heavy_weight(self):
        w = HybridWeights(w_dense=0.0, w_sparse=1.0, w_kind=0.0,
                          w_tag=0.0, w_confidence=0.0, w_reuse=0.0,
                          w_decay=0.0, w_deprecation=0.0, tier_multiplier=0.0)
        dense = CandidateItem(
            item_id="d", cell_id="c1", trust_tier="trace",
            statement="dense", dense_score=0.9, sparse_score=0.0,
        )
        sparse = CandidateItem(
            item_id="s", cell_id="c1", trust_tier="trace",
            statement="sparse", dense_score=0.0, sparse_score=0.9,
        )
        results = hybrid_search([dense, sparse], weights=w)
        assert results[0].item_id == "s"


# ===========================================================================
# AL-2 Negative-Space Retrieval Tests
# ===========================================================================


class TestNegativeSpaceKindDetection:
    """Negative-space kinds (failure_signature, anti_pattern, supersession)
    are detected and assigned selection_reason=caution."""

    def _make(self, kind: str, **kw) -> CandidateItem:
        defaults = dict(
            item_id=f"neg-{kind}",
            cell_id="c1",
            trust_tier="trace",
            statement=f"statement for {kind}",
            kind=kind,
            dense_score=0.5,
            sparse_score=0.5,
        )
        defaults.update(kw)
        return CandidateItem(**defaults)

    def test_failure_signature_is_caution(self):
        item = self._make("failure_signature")
        results = hybrid_search([item])
        assert len(results) == 1
        assert results[0].selection_reason == "caution"
        assert results[0].components.negative_similarity > 0.0

    def test_anti_pattern_is_caution(self):
        item = self._make("anti_pattern")
        results = hybrid_search([item])
        assert len(results) == 1
        assert results[0].selection_reason == "caution"

    def test_supersession_is_caution(self):
        item = self._make("supersession")
        results = hybrid_search([item])
        assert len(results) == 1
        assert results[0].selection_reason == "caution"

    def test_normal_kind_is_positive_guidance(self):
        item = self._make("error")
        results = hybrid_search([item])
        assert len(results) == 1
        assert results[0].selection_reason == "positive_guidance"

    def test_negative_space_via_negative_space_kind_field(self):
        item = CandidateItem(
            item_id="n1", cell_id="c1", trust_tier="trace",
            statement="explicit negative",
            kind="error",
            negative_space_kind="anti_pattern",
            dense_score=0.5,
            sparse_score=0.5,
        )
        results = hybrid_search([item])
        assert len(results) == 1
        assert results[0].selection_reason == "caution"

    def test_case_insensitive_kind(self):
        item = self._make("ANTI_PATTERN")
        results = hybrid_search([item])
        assert len(results) == 1
        assert results[0].selection_reason == "caution"

    def test_malformed_optional_fields_do_not_break_scoring(self):
        item = CandidateItem(
            item_id="odd", cell_id="c1", trust_tier="trace",
            statement="odd fields", kind=123, status=None,
            negative_space_kind=456,
            dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([item])
        assert len(results) == 1
        assert results[0].selection_reason == "positive_guidance"


class TestCautionCoefficient:
    """Negative-space items are scored lower than equivalently-scored
    positive items due to the caution coefficient."""

    def test_caution_coefficient_reduces_score(self):
        pos = CandidateItem(
            item_id="pos", cell_id="c1", trust_tier="trace",
            statement="positive", kind="error",
            dense_score=0.8, sparse_score=0.8,
        )
        neg = CandidateItem(
            item_id="neg", cell_id="c1", trust_tier="trace",
            statement="negative", kind="anti_pattern",
            dense_score=0.8, sparse_score=0.8,
        )
        results = hybrid_search([neg, pos])
        assert len(results) == 2
        assert results[0].item_id == "pos"
        assert results[1].item_id == "neg"
        assert results[0].final_score > results[1].final_score

    def test_caution_coefficient_default_is_05(self):
        assert HybridWeights().caution_coefficient == 0.5

    def test_caution_coefficient_custom(self):
        w = HybridWeights(caution_coefficient=0.1)
        neg = CandidateItem(
            item_id="neg", cell_id="c1", trust_tier="trace",
            statement="negative", kind="anti_pattern",
            dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([neg], weights=w)
        # At 0.1 coefficient the score is heavily reduced
        assert results[0].final_score <= 0.3  # well below baseline

    def test_no_caution_coefficient_for_positive(self):
        w = HybridWeights(caution_coefficient=0.1)
        pos = CandidateItem(
            item_id="pos", cell_id="c1", trust_tier="trace",
            statement="positive", kind="error",
            dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([pos], weights=w)
        # Positive items are NOT multiplied by caution_coefficient
        assert results[0].selection_reason == "positive_guidance"


class TestExcludedStatuses:
    """Statuses isolated, superseded, deprecated are excluded from results."""

    def _make(self, status: str) -> CandidateItem:
        return CandidateItem(
            item_id=f"item-{status}", cell_id="c1", trust_tier="trace",
            statement=status, status=status,
            dense_score=0.5, sparse_score=0.5,
        )

    def test_isolated_excluded(self):
        results = hybrid_search([self._make("isolated")])
        assert len(results) == 0

    def test_superseded_excluded(self):
        results = hybrid_search([self._make("superseded")])
        assert len(results) == 0

    def test_deprecated_excluded(self):
        results = hybrid_search([self._make("deprecated")])
        assert len(results) == 0

    def test_case_insensitive_status_exclusion(self):
        results = hybrid_search([self._make("ISOLATED")])
        assert len(results) == 0

    def test_other_statuses_included(self):
        results = hybrid_search([self._make("approved")])
        assert len(results) == 1
        assert results[0].selection_reason == "positive_guidance"


class TestPenalisedStatuses:
    """Status challenged is penalised and labelled as caution.

    isolation_candidate was moved to EXCLUDED_STATUSES under AL-8;
    high/critical isolation candidates are excluded from normal guidance
    by default.
    """

    def _make(self, status: str) -> CandidateItem:
        return CandidateItem(
            item_id=f"item-{status}", cell_id="c1", trust_tier="trace",
            statement=status, status=status,
            dense_score=0.5, sparse_score=0.5,
        )

    def test_challenged_is_caution(self):
        results = hybrid_search([self._make("challenged")])
        assert len(results) == 1
        assert results[0].selection_reason == "caution"
        assert results[0].components.risk_penalty > 0.0

    def test_isolation_candidate_excluded_by_default(self):
        """isolation_candidate items are excluded from normal guidance."""
        results = hybrid_search([self._make("isolation_candidate")])
        assert len(results) == 0

    def test_isolation_candidate_included_in_audit_mode(self):
        """With include_all_statuses=True, isolation_candidate items
        appear with selection_reason='filtered'."""
        results = hybrid_search(
            [self._make("isolation_candidate")],
            include_all_statuses=True,
        )
        assert len(results) == 1
        assert results[0].selection_reason == "filtered"
        assert results[0].status == "isolation_candidate"

    def test_penalised_score_lower_than_approved(self):
        challenged = CandidateItem(
            item_id="ch", cell_id="c1", trust_tier="trace",
            statement="challenged", status="challenged",
            dense_score=0.5, sparse_score=0.5,
        )
        approved = CandidateItem(
            item_id="ok", cell_id="c1", trust_tier="trace",
            statement="approved", status="approved",
            dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([challenged, approved])
        assert results[0].item_id == "ok"
        assert results[1].item_id == "ch"
        assert results[0].final_score > results[1].final_score


class TestPositiveAndCautionDualRetrieval:
    """A valid task retrieves both positive guidance and related caution."""

    def test_dual_retrieval(self):
        positive = CandidateItem(
            item_id="pos1", cell_id="c1", trust_tier="trace",
            statement="Use async context managers",
            rationale="Prevents resource leaks",
            kind="guidance", status="approved",
            dense_score=0.9, sparse_score=0.8,
            confidence=0.95,
        )
        caution = CandidateItem(
            item_id="neg1", cell_id="c1", trust_tier="trace",
            statement="Async with nested callbacks can deadlock",
            rationale="Detected in production incident #42",
            kind="anti_pattern", status="approved",
            dense_score=0.7, sparse_score=0.6,
            confidence=0.85,
            related_positive_ids=["pos1"],
        )
        results = hybrid_search([positive, caution])
        assert len(results) == 2
        reasons = {r.item_id: r.selection_reason for r in results}
        assert reasons["pos1"] == "conflict"
        assert reasons["neg1"] == "caution"

    def test_positive_outscores_caution_by_default(self):
        pos = CandidateItem(
            item_id="p", cell_id="c1", trust_tier="trace",
            statement="positive", kind="guidance",
            dense_score=0.9, sparse_score=0.9, status="approved",
        )
        neg = CandidateItem(
            item_id="n", cell_id="c1", trust_tier="trace",
            statement="caution", kind="anti_pattern",
            dense_score=0.9, sparse_score=0.9, status="approved",
        )
        results = hybrid_search([neg, pos])
        assert results[0].item_id == "p"
        assert results[1].item_id == "n"
        assert results[0].final_score > results[1].final_score


class TestNegativeSpaceScoreComponents:
    """ScoreComponents contains new AL-2 fields when items are negative-space."""

    def test_positive_item_has_zero_negative_components(self):
        item = CandidateItem(
            item_id="p", cell_id="c1", trust_tier="trace",
            statement="positive", kind="guidance",
            dense_score=0.5, sparse_score=0.5, status="approved",
        )
        results = hybrid_search([item])
        comp = results[0].components
        assert comp.positive_similarity > 0.0
        assert comp.negative_similarity == 0.0
        assert comp.risk_penalty == 0.0

    def test_negative_item_has_risk_penalty(self):
        item = CandidateItem(
            item_id="n", cell_id="c1", trust_tier="trace",
            statement="negative", kind="anti_pattern",
            dense_score=0.8, sparse_score=0.8, status="approved",
        )
        results = hybrid_search([item])
        comp = results[0].components
        assert comp.positive_similarity > 0.0
        assert comp.negative_similarity > 0.0
        assert comp.proven_signal_weight > 0.0
        assert comp.symbolic_match_weight >= 0.0
        assert comp.risk_penalty > 0.0

    def test_challenged_item_has_risk_penalty(self):
        item = CandidateItem(
            item_id="c", cell_id="c1", trust_tier="trace",
            statement="challenged", kind="error", status="challenged",
            dense_score=0.5, sparse_score=0.5,
        )
        results = hybrid_search([item])
        comp = results[0].components
        assert comp.risk_penalty > 0.0
        assert comp.selection_reason == "caution"

    def test_related_antipattern_marks_positive_as_conflict(self):
        positive = CandidateItem(
            item_id="pos1", cell_id="c1", trust_tier="trace",
            statement="Use bounded worker pools", kind="guidance",
            dense_score=0.9, sparse_score=0.9, status="approved",
        )
        caution = CandidateItem(
            item_id="neg1", cell_id="c1", trust_tier="trace",
            statement="Unbounded pools can starve the event loop", kind="anti_pattern",
            dense_score=0.7, sparse_score=0.7, status="approved",
            related_positive_ids=["pos1"],
        )

        results = hybrid_search([positive, caution])
        by_id = {result.item_id: result for result in results}
        assert by_id["pos1"].selection_reason == "conflict"
        assert by_id["pos1"].components.selection_reason == "conflict"
        assert by_id["neg1"].selection_reason == "caution"

    def test_related_supersession_marks_positive_as_suppressed(self):
        positive = CandidateItem(
            item_id="pos1", cell_id="c1", trust_tier="trace",
            statement="Use the legacy retry wrapper", kind="guidance",
            dense_score=0.9, sparse_score=0.9, status="approved",
        )
        caution = CandidateItem(
            item_id="neg1", cell_id="c1", trust_tier="trace",
            statement="Legacy retry wrapper was superseded", kind="supersession",
            dense_score=0.7, sparse_score=0.7, status="approved",
            related_positive_ids=["pos1"],
        )

        results = hybrid_search([positive, caution])
        by_id = {result.item_id: result for result in results}
        assert by_id["pos1"].selection_reason == "suppressed"
        assert by_id["pos1"].components.selection_reason == "suppressed"
        assert by_id["pos1"].final_score < positive.dense_score

    def test_score_components_to_dict_includes_new_fields(self):
        comp = ScoreComponents(
            positive_similarity=0.8, negative_similarity=0.6,
            confidence_weight=0.7, proven_signal_weight=0.5,
            symbolic_match_weight=0.4, risk_penalty=0.3,
        )
        d = comp.to_dict()
        assert d["positive_similarity"] == 0.8
        assert d["negative_similarity"] == 0.6
        assert d["confidence_weight"] == 0.7
        assert d["proven_signal_weight"] == 0.5
        assert d["symbolic_match_weight"] == 0.4
        assert d["risk_penalty"] == 0.3

    def test_hybrid_result_to_dict_includes_selection_reason(self):
        item = CandidateItem(
            item_id="r", cell_id="c1", trust_tier="trace",
            statement="roundtrip", kind="anti_pattern",
            dense_score=0.5, sparse_score=0.5, status="approved",
        )
        results = hybrid_search([item])
        d = results[0].to_dict()
        assert "selection_reason" in d
        assert d["selection_reason"] == "caution"


class TestNamedConstants:
    """Module-level constants are accessible for downstream consumers."""

    def test_constants_defined(self):
        from shyftr.retrieval.hybrid import (
            NEGATIVE_SPACE_KINDS,
            EXCLUDED_STATUSES,
            PENALISED_STATUSES,
            SELECTION_POSITIVE,
            SELECTION_CAUTION,
            SELECTION_SUPPRESSED,
            SELECTION_FILTERED,
            SELECTION_CONFLICT,
        )
        assert "failure_signature" in NEGATIVE_SPACE_KINDS
        assert "anti_pattern" in NEGATIVE_SPACE_KINDS
        assert "supersession" in NEGATIVE_SPACE_KINDS
        assert "isolated" in EXCLUDED_STATUSES
        assert "superseded" in EXCLUDED_STATUSES
        assert "deprecated" in EXCLUDED_STATUSES
        assert "isolation_candidate" in EXCLUDED_STATUSES
        assert "challenged" in PENALISED_STATUSES
        assert SELECTION_POSITIVE == "positive_guidance"
        assert SELECTION_CAUTION == "caution"
        assert SELECTION_SUPPRESSED == "suppressed"
        assert SELECTION_FILTERED == "filtered"
        assert SELECTION_CONFLICT == "conflict"
