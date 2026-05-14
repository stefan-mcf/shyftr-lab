"""Tests for the Challenger audit loop module."""

from __future__ import annotations

import importlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shyftr.audit.challenger import (
    ChallengerFinding,
    ChallengerReport,
    _rank_score,
    rank_targets,
    _collect_counter_evidence,
    _classify_evidence,
    _finding_spark_key,
    _existing_open_challenge_keys,
    run_challenge,
)
from shyftr.sweep import TraceMetrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cell_with_ledger() -> Path:
    """Create a temporary Cell directory with minimal ledger structure."""
    tmp = Path(tempfile.mkdtemp())
    (tmp / "config").mkdir(parents=True)
    (tmp / "ledger").mkdir()
    (tmp / "charges").mkdir()

    # Cell manifest
    manifest = {"cell_id": "test-cell-01"}
    (tmp / "config" / "cell_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Empty outcome ledger
    (tmp / "ledger" / "outcomes.jsonl").write_text("", encoding="utf-8")

    # Empty sources ledger
    (tmp / "ledger" / "sources.jsonl").write_text("", encoding="utf-8")

    # Empty audit sparks
    (tmp / "ledger" / "audit_sparks.jsonl").write_text("", encoding="utf-8")

    return tmp


@pytest.fixture
def sample_metrics_dict() -> dict:
    """Sample TraceMetrics dict for ranking tests."""
    return {
        "trace-a": TraceMetrics(
            trace_id="trace-a",
            trace_kind="charge",
            trace_status="approved",
            retrieval_count=15,
            application_count=5,
            useful_count=3,
            harmful_count=1,
            miss_count=2,
            application_rate=0.33,
            useful_rate=0.20,
            harmful_rate=0.07,
            miss_rate=0.13,
        ),
        "trace-b": TraceMetrics(
            trace_id="trace-b",
            trace_kind="charge",
            trace_status="approved",
            retrieval_count=100,
            application_count=20,
            useful_count=15,
            harmful_count=0,
            miss_count=60,
            application_rate=0.20,
            useful_rate=0.15,
            harmful_rate=0.0,
            miss_rate=0.60,
        ),
        "trace-c": TraceMetrics(
            trace_id="trace-c",
            trace_kind="charge",
            trace_status="approved",
            retrieval_count=0,
            application_count=0,
            useful_count=0,
            harmful_count=0,
            miss_count=0,
        ),
    }


# ---------------------------------------------------------------------------
# ChallengerFinding
# ---------------------------------------------------------------------------


class TestChallengerFinding:
    def test_valid_classification(self):
        f = ChallengerFinding(
            trace_id="t1",
            classification="direct_contradiction",
            rationale="test",
        )
        assert f.trace_id == "t1"
        assert f.classification == "direct_contradiction"

    def test_invalid_classification(self):
        with pytest.raises(ValueError, match="Invalid classification"):
            ChallengerFinding(
                trace_id="t1",
                classification="bogus_class",
                rationale="test",
            )

    def test_to_dict_omits_optionals(self):
        f = ChallengerFinding(
            trace_id="t1",
            classification="supersession",
            rationale="test",
        )
        d = f.to_dict()
        assert "supporting_data" not in d
        assert "fragment_id" not in d
        assert "target_status" not in d
        assert "target_confidence" not in d
        assert "rank_score" not in d

    def test_to_dict_includes_provided_optionals(self):
        f = ChallengerFinding(
            trace_id="t1",
            classification="supersession",
            rationale="test",
            signal_strength=0.8,
            rank_score=0.75,
            fragment_id="frag-1",
        )
        d = f.to_dict()
        assert d["rank_score"] == 0.75
        assert d["candidate_id"] == "frag-1"
        assert d["signal_strength"] == 0.8


# ---------------------------------------------------------------------------
# ChallengerReport
# ---------------------------------------------------------------------------


class TestChallengerReport:
    def test_package_import_exposes_flat_audit_helpers_and_submodule(self):
        audit_pkg = importlib.import_module("shyftr.audit")
        challenger_mod = importlib.import_module("shyftr.audit.challenger")

        assert hasattr(audit_pkg, "append_audit_row")
        assert hasattr(audit_pkg, "append_audit_spark")
        assert challenger_mod.run_challenge is run_challenge

    def test_to_dict(self):
        findings = [
            ChallengerFinding(trace_id="t1", classification="direct_contradiction", rationale="r1"),
        ]
        report = ChallengerReport(
            cell_id="cell-1",
            scanned_at="2025-01-01T00:00:00",
            dry_run=True,
            target_count=10,
            findings=findings,
            written_spark_ids=[],
            skipped_spark_ids=[],
            summary={"total_findings": 1},
        )
        d = report.to_dict()
        assert d["cell_id"] == "cell-1"
        assert d["finding_count"] == 1
        assert d["dry_run"] is True
        assert d["findings"][0]["trace_id"] == "t1"


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


class TestRankScore:
    def test_zero_metrics_score_zero(self):
        m = TraceMetrics(trace_id="t1")
        score = _rank_score(m)
        assert score == 0.0

    def test_high_retrieval_and_applications(self):
        m = TraceMetrics(
            trace_id="t1",
            retrieval_count=100,
            application_count=20,
            useful_count=10,
        )
        score = _rank_score(m)
        assert score > 0.3
        assert score <= 1.0

    def test_harmful_adds_weight(self):
        m_clean = TraceMetrics(trace_id="t1", retrieval_count=10, useful_count=1)
        m_harmful = TraceMetrics(trace_id="t2", retrieval_count=10, useful_count=1, harmful_count=3)
        clean_score = _rank_score(m_clean)
        harmful_score = _rank_score(m_harmful)
        assert harmful_score > clean_score

    def test_high_miss_rate_with_retrieval_gap(self):
        m = TraceMetrics(
            trace_id="t1",
            retrieval_count=10,
            miss_rate=0.5,
        )
        # High retrieval + high miss rate = confidence gap bonus
        score = _rank_score(m)
        assert score > 0.15  # miss component + gap

    def test_low_retrieval_no_gap(self):
        m = TraceMetrics(
            trace_id="t1",
            retrieval_count=2,
            miss_rate=0.5,
        )
        score = _rank_score(m)
        # Low retrieval means no confidence gap bonus
        assert score < 0.3


class TestRankTargets:
    def test_returns_sorted_by_score_desc(self, sample_metrics_dict):
        ranked = rank_targets(sample_metrics_dict)
        assert len(ranked) >= 2
        # Check descending order
        for i in range(len(ranked) - 1):
            assert ranked[i][2] >= ranked[i + 1][2]

    def test_top_n(self, sample_metrics_dict):
        ranked = rank_targets(sample_metrics_dict, top_n=1)
        assert len(ranked) == 1

    def test_min_score_filter(self, sample_metrics_dict):
        # trace-c has all zeros — score should be 0
        ranked = rank_targets(sample_metrics_dict, min_score=0.01)
        ids = [r[0] for r in ranked]
        assert "trace-c" not in ids

    def test_empty_metrics(self):
        ranked = rank_targets({})
        assert ranked == []


# ---------------------------------------------------------------------------
# Counter-evidence
# ---------------------------------------------------------------------------


class TestCollectCounterEvidence:
    def test_empty_cell_returns_empty(self, cell_with_ledger):
        evidence = _collect_counter_evidence(cell_with_ledger, "trace-a")
        assert evidence == []

    def test_harmful_outcome_detected(self, cell_with_ledger):
        outcomes = [
            {
                "outcome_id": "oc-1",
                "verdict": "harmful",
                "trace_ids": ["trace-a"],
                "metadata": {"harmful_trace_ids": ["trace-a"]},
                "recorded_at": "2025-01-01T00:00:00",
            }
        ]
        (cell_with_ledger / "ledger" / "outcomes.jsonl").write_text(
            "\n".join(json.dumps(o) for o in outcomes), encoding="utf-8"
        )
        evidence = _collect_counter_evidence(cell_with_ledger, "trace-a")
        assert len(evidence) >= 1
        assert evidence[0]["direction"] == "contradiction"

    def test_pack_miss_detected(self, cell_with_ledger):
        outcomes = [
            {
                "outcome_id": "oc-2",
                "verdict": "miss",
                "trace_ids": [],
                "metadata": {},
                "pack_miss_details": [
                    {
                        "charge_id": "trace-a",
                        "miss_type": "contradicted",
                        "reason": "Directly contradicts current policy",
                    }
                ],
                "recorded_at": "2025-01-01T00:00:00",
            }
        ]
        (cell_with_ledger / "ledger" / "outcomes.jsonl").write_text(
            "\n".join(json.dumps(o) for o in outcomes), encoding="utf-8"
        )
        evidence = _collect_counter_evidence(cell_with_ledger, "trace-a")
        assert len(evidence) >= 1
        assert evidence[0]["direction"] == "contradiction"

    def test_legacy_pack_misses_fallback_is_detected(self, cell_with_ledger):
        outcomes = [
            {
                "outcome_id": "oc-legacy",
                "verdict": "miss",
                "trace_ids": [],
                "metadata": {},
                "pack_misses": ["trace-a"],
                "recorded_at": "2025-01-01T00:00:00",
            }
        ]
        (cell_with_ledger / "ledger" / "outcomes.jsonl").write_text(
            "\n".join(json.dumps(o) for o in outcomes), encoding="utf-8"
        )
        evidence = _collect_counter_evidence(cell_with_ledger, "trace-a")
        assert any(item["source"] == "ledger/outcomes.jsonl:oc-legacy" for item in evidence)
        assert any(item["direction"] == "ambiguous" for item in evidence)

    def test_existing_audit_spark_is_not_reused_as_new_counter_evidence(self, cell_with_ledger):
        sparks = [
            {
                "spark_id": "spark-1",
                "trace_id": "trace-a",
                "classification": "direct_contradiction",
                "rationale": "flagged earlier",
                "proposed_at": "2025-01-02T00:00:00",
            }
        ]
        (cell_with_ledger / "ledger" / "audit_sparks.jsonl").write_text(
            "\n".join(json.dumps(s) for s in sparks), encoding="utf-8"
        )
        evidence = _collect_counter_evidence(cell_with_ledger, "trace-a")
        assert not any(item["source"].endswith("spark-1") for item in evidence)

    def test_closed_audit_spark_is_ignored_as_evidence(self, cell_with_ledger):
        spark = {
            "spark_id": "spark-closed",
            "trace_id": "trace-a",
            "classification": "direct_contradiction",
            "rationale": "already reviewed",
            "proposed_at": "2025-01-02T00:00:00",
        }
        review = {
            "review_id": "review-closed",
            "cell_id": "test-cell-01",
            "spark_id": "spark-closed",
            "decision": "resolved",
            "reviewer": "regulator",
            "reviewed_at": "2025-01-03T00:00:00",
            "rationale": "handled",
        }
        (cell_with_ledger / "ledger" / "audit_sparks.jsonl").write_text(
            json.dumps(spark) + "\n",
            encoding="utf-8",
        )
        (cell_with_ledger / "ledger" / "audit_reviews.jsonl").write_text(
            json.dumps(review) + "\n",
            encoding="utf-8",
        )
        evidence = _collect_counter_evidence(cell_with_ledger, "trace-a")
        assert not any(item["source"].endswith("spark-closed") for item in evidence)

    def test_legacy_non_challenger_spark_is_ignored_as_evidence(self, cell_with_ledger):
        legacy_spark = {
            "spark_id": "legacy-1",
            "trace_id": "trace-a",
            "action": "challenge",
            "rationale": "legacy spark without challenger classification",
            "proposed_at": "2025-01-02T00:00:00",
        }
        (cell_with_ledger / "ledger" / "audit_sparks.jsonl").write_text(
            json.dumps(legacy_spark) + "\n",
            encoding="utf-8",
        )
        evidence = _collect_counter_evidence(cell_with_ledger, "trace-a")
        assert not any(item["source"].endswith("legacy-1") for item in evidence)

    def test_legacy_traces_deprecated_row_is_supersession_evidence(self, cell_with_ledger):
        legacy_trace = {
            "trace_id": "trace-a",
            "source_fragment_ids": ["frag-a"],
        }
        (cell_with_ledger / "traces").mkdir(exist_ok=True)
        (cell_with_ledger / "traces" / "deprecated.jsonl").write_text(
            json.dumps(legacy_trace) + "\n",
            encoding="utf-8",
        )
        metrics = TraceMetrics(trace_id="trace-a", source_fragment_ids=("frag-a",))
        evidence = _collect_counter_evidence(
            cell_with_ledger,
            "trace-a",
            target_metrics=metrics,
        )
        assert any(item["source"] == "traces/deprecated.jsonl:trace-a" for item in evidence)
        assert any(item["direction"] == "supersession" for item in evidence)

    def test_related_spark_row_is_used_as_counter_evidence(self, cell_with_ledger):
        spark_rows = [
            {
                "fragment_id": "frag-a",
                "kind": "failure_signature",
                "source_id": "pulse-9",
                "text": "New Spark indicates this recovery no longer applies in the current runtime.",
                "metadata": {"trace_ids": ["trace-a"]},
            }
        ]
        (cell_with_ledger / "ledger" / "sparks.jsonl").write_text(
            "\n".join(json.dumps(row) for row in spark_rows),
            encoding="utf-8",
        )
        evidence = _collect_counter_evidence(
            cell_with_ledger,
            "trace-a",
            target_metrics=TraceMetrics(trace_id="trace-a", source_fragment_ids=("frag-a",)),
        )
        assert any(item["source"] == "ledger/sparks.jsonl:frag-a" for item in evidence)
        assert any(item["direction"] == "ambiguous" for item in evidence)

    def test_isolated_rows_are_scope_evidence(self, cell_with_ledger):
        isolated = {
            "charge_id": "trace-a",
            "source_fragment_ids": ["frag-a"],
        }
        (cell_with_ledger / "charges" / "isolated.jsonl").write_text(
            json.dumps(isolated) + "\n",
            encoding="utf-8",
        )
        evidence = _collect_counter_evidence(
            cell_with_ledger,
            "trace-a",
            target_metrics=TraceMetrics(trace_id="trace-a", source_fragment_ids=("frag-a",)),
        )
        assert any(item["source"] == "charges/isolated.jsonl:trace-a" for item in evidence)
        assert any(item["direction"] == "scope" for item in evidence)

    def test_unrelated_deprecated_charge_is_ignored(self, cell_with_ledger):
        deprecated = [
            {
                "charge_id": "trace-b",
                "source_fragment_ids": ["frag-b"],
            }
        ]
        (cell_with_ledger / "charges" / "deprecated.jsonl").write_text(
            "\n".join(json.dumps(row) for row in deprecated), encoding="utf-8"
        )
        metrics = TraceMetrics(trace_id="trace-a", source_fragment_ids=("frag-a",))
        evidence = _collect_counter_evidence(
            cell_with_ledger,
            "trace-a",
            target_metrics=metrics,
        )
        assert not any(item["direction"] == "supersession" for item in evidence)

    def test_unrelated_update_pulse_is_ignored(self, cell_with_ledger):
        pulses = [
            {
                "source_id": "pulse-1",
                "kind": "update",
                "metadata": {"trace_ids": ["trace-b"], "source_fragment_ids": ["frag-b"]},
                "recorded_at": "2025-01-04T00:00:00",
            }
        ]
        (cell_with_ledger / "ledger" / "sources.jsonl").write_text(
            "\n".join(json.dumps(row) for row in pulses), encoding="utf-8"
        )
        metrics = TraceMetrics(trace_id="trace-a", source_fragment_ids=("frag-a",))
        evidence = _collect_counter_evidence(
            cell_with_ledger,
            "trace-a",
            target_metrics=metrics,
        )
        assert not any(item["direction"] == "temporal" for item in evidence)

    def test_related_update_pulse_is_temporal_evidence(self, cell_with_ledger):
        pulses = [
            {
                "source_id": "pulse-2",
                "kind": "update",
                "metadata": {"trace_ids": ["trace-a"]},
                "recorded_at": "2025-01-05T00:00:00",
            }
        ]
        (cell_with_ledger / "ledger" / "sources.jsonl").write_text(
            "\n".join(json.dumps(row) for row in pulses), encoding="utf-8"
        )
        evidence = _collect_counter_evidence(
            cell_with_ledger,
            "trace-a",
            target_metrics=TraceMetrics(trace_id="trace-a", source_fragment_ids=("frag-a",)),
        )
        assert any(item["direction"] == "temporal" for item in evidence)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassifyEvidence:
    def test_direct_contradiction(self):
        evidence = [
            {
                "source": "ledger/outcomes.jsonl:oc-1",
                "direction": "contradiction",
                "evidence": "flagged as harmful",
                "created_at": "2025-01-01",
            }
        ]
        findings = _classify_evidence("trace-a", None, evidence)
        classifications = {f.classification for f in findings}
        assert "direct_contradiction" in classifications

    def test_supersession(self):
        evidence = [
            {
                "source": "charges/deprecated.jsonl:charge-b",
                "direction": "supersession",
                "evidence": "charge-b is deprecated",
                "created_at": "",
            }
        ]
        findings = _classify_evidence("trace-a", None, evidence)
        classifications = {f.classification for f in findings}
        assert "supersession" in classifications

    def test_scope_exception_requires_usage_signal(self):
        metrics = TraceMetrics(
            trace_id="trace-a",
            trace_status="approved",
            retrieval_count=0,
            application_count=0,
        )
        findings = _classify_evidence("trace-a", metrics, [])
        classifications = {f.classification for f in findings}
        assert "scope_exception" not in classifications

    def test_scope_exception_infers_from_retrieved_but_never_applied_trace(self):
        metrics = TraceMetrics(
            trace_id="trace-a",
            trace_status="approved",
            retrieval_count=3,
            application_count=0,
        )
        findings = _classify_evidence("trace-a", metrics, [])
        classifications = {f.classification for f in findings}
        assert "scope_exception" in classifications

    def test_scope_exception_skips_non_approved_status(self):
        metrics = TraceMetrics(
            trace_id="trace-a",
            trace_status="deprecated",
            retrieval_count=0,
            application_count=0,
        )
        findings = _classify_evidence("trace-a", metrics, [])
        classifications = {f.classification for f in findings}
        assert "scope_exception" not in classifications

    def test_temporal_update(self):
        evidence = [
            {
                "source": "ledger/sources.jsonl:pulse-1",
                "direction": "temporal",
                "evidence": "newer Pulse exists",
                "created_at": "2025-06-01",
            }
        ]
        findings = _classify_evidence("trace-a", None, evidence)
        classifications = {f.classification for f in findings}
        assert "temporal_update" in classifications

    def test_ambiguous_counterevidence(self):
        evidence = [
            {
                "source": "ledger/outcomes.jsonl:oc-1",
                "direction": "ambiguous",
                "evidence": "unknown miss type",
                "created_at": "",
            }
        ]
        findings = _classify_evidence("trace-a", None, evidence)
        classifications = {f.classification for f in findings}
        assert "ambiguous_counterevidence" in classifications

    def test_scope_direction_produces_scope_exception(self):
        evidence = [
            {
                "source": "ledger/audit_sparks.jsonl:spark-scope",
                "direction": "scope",
                "evidence": "prior scope review flagged this target",
                "created_at": "2025-01-01",
            }
        ]
        findings = _classify_evidence("trace-a", None, evidence)
        classifications = {f.classification for f in findings}
        assert "scope_exception" in classifications

    def test_isolation_scope_evidence_classifies_as_scope_exception(self):
        evidence = [
            {
                "source": "charges/isolated.jsonl:trace-a",
                "direction": "scope",
                "evidence": "trace-a is isolated pending review",
                "created_at": "2025-01-01",
            }
        ]
        findings = _classify_evidence("trace-a", None, evidence)
        classifications = {f.classification for f in findings}
        assert "scope_exception" in classifications
        assert "supersession" not in classifications
        assert "direct_contradiction" not in classifications


# ---------------------------------------------------------------------------
# Dedup keys
# ---------------------------------------------------------------------------


class TestSparkKey:
    def test_deterministic_for_same_inputs(self):
        f1 = ChallengerFinding(
            trace_id="t1", classification="direct_contradiction",
            rationale="r1", counter_evidence_source="src:1",
        )
        f2 = ChallengerFinding(
            trace_id="t1", classification="direct_contradiction",
            rationale="r2", counter_evidence_source="src:1",
        )
        key1 = _finding_spark_key("cell-1", f1)
        key2 = _finding_spark_key("cell-1", f2)
        # Same cell_id, trace_id, classification, source => same key (despite different rationale)
        assert key1 == key2

    def test_different_cell_different_key(self):
        f = ChallengerFinding(
            trace_id="t1", classification="direct_contradiction",
            rationale="r1", counter_evidence_source="src:1",
        )
        key1 = _finding_spark_key("cell-a", f)
        key2 = _finding_spark_key("cell-b", f)
        assert key1 != key2

    def test_different_classification_different_key(self):
        f1 = ChallengerFinding(
            trace_id="t1", classification="direct_contradiction",
            rationale="r1", counter_evidence_source="src:1",
        )
        f2 = ChallengerFinding(
            trace_id="t1", classification="supersession",
            rationale="r1", counter_evidence_source="src:1",
        )
        key1 = _finding_spark_key("cell-1", f1)
        key2 = _finding_spark_key("cell-1", f2)
        assert key1 != key2

    def test_key_format(self):
        f = ChallengerFinding(
            trace_id="trace-a", classification="direct_contradiction",
            rationale="r", counter_evidence_source="src:1",
        )
        key = _finding_spark_key("cell-1", f)
        assert key.startswith("challenge:")
        assert "cell-1" in key
        assert "trace-a" in key

    def test_existing_open_keys_ignores_closed_reviews(self, cell_with_ledger):
        spark = {
            "spark_id": "spark-1",
            "cell_id": "test-cell-01",
            "trace_id": "trace-a",
            "classification": "direct_contradiction",
            "rationale": "flagged earlier",
            "counter_evidence_source": "ledger/outcomes.jsonl:oc-1",
        }
        (cell_with_ledger / "ledger" / "audit_sparks.jsonl").write_text(
            json.dumps(spark) + "\n",
            encoding="utf-8",
        )
        review = {
            "review_id": "review-1",
            "cell_id": "test-cell-01",
            "spark_id": "spark-1",
            "decision": "accepted",
            "reviewer": "regulator",
            "reviewed_at": "2025-01-03T00:00:00",
            "rationale": "handled",
        }
        (cell_with_ledger / "ledger" / "audit_reviews.jsonl").write_text(
            json.dumps(review) + "\n",
            encoding="utf-8",
        )
        assert _existing_open_challenge_keys(cell_with_ledger) == set()

    def test_existing_open_keys_use_manifest_cell_id_for_legacy_sparks(self, cell_with_ledger):
        spark = {
            "spark_id": "spark-legacy",
            "trace_id": "trace-a",
            "classification": "direct_contradiction",
            "rationale": "legacy open spark missing cell_id",
            "counter_evidence_source": "ledger/outcomes.jsonl:oc-1",
        }
        (cell_with_ledger / "ledger" / "audit_sparks.jsonl").write_text(
            json.dumps(spark) + "\n",
            encoding="utf-8",
        )
        expected_key = _finding_spark_key(
            "test-cell-01",
            ChallengerFinding(
                trace_id="trace-a",
                classification="direct_contradiction",
                rationale="legacy open spark missing cell_id",
                counter_evidence_source="ledger/outcomes.jsonl:oc-1",
            ),
        )
        assert _existing_open_challenge_keys(cell_with_ledger) == {expected_key}

    def test_existing_open_keys_ignore_legacy_non_challenger_sparks(self, cell_with_ledger):
        legacy_spark = {
            "spark_id": "legacy-1",
            "cell_id": "test-cell-01",
            "fragment_id": "fragment-1",
            "action": "challenge",
            "rationale": "legacy spark without challenger classification",
        }
        (cell_with_ledger / "ledger" / "audit_sparks.jsonl").write_text(
            json.dumps(legacy_spark) + "\n",
            encoding="utf-8",
        )
        assert _existing_open_challenge_keys(cell_with_ledger) == set()


# ---------------------------------------------------------------------------
# run_challenge integration
# ---------------------------------------------------------------------------


class TestRunChallenge:
    def test_dry_run_on_empty_cell(self, cell_with_ledger):
        """A dry run on an empty Cell should still produce a valid report."""
        report = run_challenge(cell_with_ledger, dry_run=True)
        assert isinstance(report, ChallengerReport)
        assert report.cell_id == "test-cell-01"
        assert report.dry_run is True
        assert report.findings == []

    def test_raises_for_missing_manifest(self):
        with pytest.raises(ValueError, match="Cell manifest not found"):
            run_challenge("/tmp/nonexistent-path-12345")

    def test_top_n_limits_findings(self, cell_with_ledger, sample_metrics_dict):
        # We patch compute_trace_metrics to return controlled data
        with patch("shyftr.audit.challenger.compute_trace_metrics") as mock_compute:
            mock_compute.return_value = sample_metrics_dict
            report = run_challenge(cell_with_ledger, dry_run=True, top_n=1)
            # top_n=1 means at most 1 target ranked, but findings depend on evidence
            assert report.target_count == 3

    def test_zero_usage_approved_trace_is_not_challenged_without_evidence(self, cell_with_ledger):
        metrics = {
            "trace-a": TraceMetrics(
                trace_id="trace-a",
                trace_status="approved",
                retrieval_count=0,
                application_count=0,
            )
        }
        with patch("shyftr.audit.challenger.compute_trace_metrics") as mock_compute:
            mock_compute.return_value = metrics
            report = run_challenge(cell_with_ledger, dry_run=True)
        assert report.findings == []

    def test_charge_id_filtering(self, cell_with_ledger, sample_metrics_dict):
        with patch("shyftr.audit.challenger.compute_trace_metrics") as mock_compute:
            mock_compute.return_value = sample_metrics_dict
            report = run_challenge(cell_with_ledger, dry_run=True, charge_id="trace-a")
            assert report.target_count == 1

    def test_charge_id_raises_for_missing(self, cell_with_ledger, sample_metrics_dict):
        with patch("shyftr.audit.challenger.compute_trace_metrics") as mock_compute:
            mock_compute.return_value = sample_metrics_dict
            with pytest.raises(ValueError, match="not found"):
                run_challenge(cell_with_ledger, dry_run=True, charge_id="nonexistent")

    def test_output_path_writes_file(self, cell_with_ledger):
        output = cell_with_ledger / "challenger_report.json"
        report = run_challenge(cell_with_ledger, dry_run=True, output_path=output)
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["cell_id"] == "test-cell-01"

    def test_propose_with_dry_run_false_no_ledger(self, cell_with_ledger):
        """propose=True, dry_run=False should attempt spark writing.
        With empty metrics, no sparks are written."""
        with patch("shyftr.audit.challenger.compute_trace_metrics") as mock_compute:
            mock_compute.return_value = {}
            report = run_challenge(cell_with_ledger, dry_run=False, propose=True)
            assert report.written_spark_ids == []

    def test_propose_repeat_runs_do_not_append_duplicate_open_sparks(self, cell_with_ledger):
        outcomes = [
            {
                "outcome_id": "oc-repeat",
                "verdict": "harmful",
                "trace_ids": ["trace-a"],
                "metadata": {"harmful_trace_ids": ["trace-a"]},
                "recorded_at": "2025-01-01T00:00:00",
            }
        ]
        (cell_with_ledger / "ledger" / "outcomes.jsonl").write_text(
            "\n".join(json.dumps(o) for o in outcomes),
            encoding="utf-8",
        )
        metrics = {
            "trace-a": TraceMetrics(
                trace_id="trace-a",
                trace_status="approved",
                retrieval_count=2,
                application_count=1,
                harmful_count=1,
            )
        }
        with patch("shyftr.audit.challenger.compute_trace_metrics") as mock_compute:
            mock_compute.return_value = metrics
            first = run_challenge(cell_with_ledger, dry_run=False, propose=True)
            second = run_challenge(cell_with_ledger, dry_run=False, propose=True)
        assert len(first.written_spark_ids) == 1
        assert second.written_spark_ids == []
        audit_sparks = [json.loads(line) for line in (cell_with_ledger / "ledger" / "audit_sparks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(audit_sparks) == 1
