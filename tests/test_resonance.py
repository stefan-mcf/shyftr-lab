from __future__ import annotations

from shyftr.models import Alloy, Fragment, Outcome, Trace
from shyftr.resonance import (
    ResonanceScore,
    _jaccard,
    _tokenize,
    compute_resonance,
    detect_similar_alloys,
    detect_similar_fragments,
    detect_similar_traces,
    get_high_resonance_alloys,
)


def _fragment(fragment_id: str, cell_id: str, text: str) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        source_id=f"source-{fragment_id}",
        cell_id=cell_id,
        kind="note",
        text=text,
    )


def _trace(
    trace_id: str,
    cell_id: str,
    statement: str,
    *,
    confidence: float | None = None,
    source_fragment_ids: list[str] | None = None,
) -> Trace:
    return Trace(
        trace_id=trace_id,
        cell_id=cell_id,
        statement=statement,
        source_fragment_ids=source_fragment_ids or [f"fragment-{trace_id}"],
        status="approved",
        confidence=confidence,
        tags=["review"],
    )


def _alloy(
    alloy_id: str,
    cell_id: str,
    summary: str,
    source_trace_ids: list[str],
    *,
    confidence: float | None = None,
) -> Alloy:
    return Alloy(
        alloy_id=alloy_id,
        cell_id=cell_id,
        theme="review",
        summary=summary,
        source_trace_ids=source_trace_ids,
        confidence=confidence,
    )


def _outcome(outcome_id: str, trace_ids: list[str], verdict: str = "success") -> Outcome:
    return Outcome(
        outcome_id=outcome_id,
        cell_id="cell-a",
        loadout_id="loadout-1",
        task_id="task-1",
        verdict=verdict,
        trace_ids=trace_ids,
        score=0.9 if verdict == "success" else 0.2,
    )


def test_tokenization_and_jaccard_are_deterministic() -> None:
    assert _tokenize("Cross-Cell resonance!") == {"crosscell", "resonance"}
    assert _jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert _jaccard(set(), set()) == 0.0


def test_detects_similar_fragments_only_across_cells() -> None:
    fragments = [
        _fragment("f1", "cell-a", "review memory fragments before promotion"),
        _fragment("f2", "cell-b", "review memory before promotion"),
        _fragment("f3", "cell-a", "review memory fragments before promotion"),
    ]

    matches = detect_similar_fragments(fragments, threshold=0.40)

    assert ("f1", "f2", "cell-a", "cell-b") in [match[:4] for match in matches]
    assert ("f1", "f3", "cell-a", "cell-a") not in [match[:4] for match in matches]
    assert all(left_cell != right_cell for *_ids, left_cell, right_cell, _score in matches)


def test_detects_similar_traces_and_alloys_across_cells() -> None:
    traces = [
        _trace("t1", "cell-a", "always review memory before promotion"),
        _trace("t2", "cell-b", "review memory before promotion always"),
        _trace("t3", "cell-a", "always review memory before promotion"),
    ]
    alloys = [
        _alloy("a1", "cell-a", "Alloy: review memory before promotion", ["t1"]),
        _alloy("a2", "cell-b", "Alloy: memory review before promotion", ["t2"]),
        _alloy("a3", "cell-a", "Alloy: review memory before promotion", ["t3"]),
    ]

    trace_matches = detect_similar_traces(traces, threshold=0.50)
    alloy_matches = detect_similar_alloys(alloys, threshold=0.50)

    assert ("t1", "t2", "cell-a", "cell-b", 1.0) in trace_matches
    assert all(left_cell != right_cell for *_ids, left_cell, right_cell, _score in trace_matches)
    assert {match[0:2] for match in alloy_matches} == {("a1", "a2"), ("a2", "a3")}


def test_compute_resonance_scores_recurrence_diversity_confidence_and_success() -> None:
    traces = [
        _trace("t1", "cell-a", "always review memory before promotion", confidence=0.9),
        _trace("t2", "cell-b", "review memory before promotion always", confidence=0.8),
    ]
    alloys = [
        _alloy("a1", "cell-a", "Alloy: review memory before promotion", ["t1"], confidence=0.9),
        _alloy("a2", "cell-b", "Alloy: memory review before promotion", ["t2"], confidence=0.7),
    ]
    outcomes = [_outcome("o1", ["t1"]), _outcome("o2", ["t2"])]

    scores = compute_resonance(
        traces,
        alloys,
        outcomes=outcomes,
        trace_threshold=0.50,
        alloy_threshold=0.40,
    )

    assert [score.alloy_id for score in scores] == ["a1", "a2"]
    assert all(score.cell_diversity == 2 for score in scores)
    assert all(score.recurrence_count >= 2 for score in scores)
    assert scores[0].avg_confidence is not None
    assert scores[0].success_ratio == 1.0
    assert 0.0 <= scores[0].score <= 1.0


def test_fragment_resonance_uses_trace_fragment_provenance() -> None:
    fragments = [
        _fragment("f1", "cell-a", "validate sources before trace promotion"),
        _fragment("f2", "cell-b", "validate sources before promotion"),
    ]
    traces = [
        _trace(
            "t1",
            "cell-a",
            "local unique wording",
            source_fragment_ids=["f1"],
            confidence=0.8,
        )
    ]
    alloys = [_alloy("a1", "cell-a", "unique local alloy", ["t1"], confidence=0.8)]

    scores = compute_resonance(
        traces,
        alloys,
        fragments=fragments,
        trace_threshold=1.0,
        alloy_threshold=1.0,
        fragment_threshold=0.50,
    )

    assert len(scores) == 1
    assert scores[0].alloy_id == "a1"
    assert scores[0].cell_diversity == 2


def test_no_cross_cell_match_produces_no_score_by_default() -> None:
    scores = compute_resonance(
        [_trace("t1", "cell-a", "one two three")],
        [_alloy("a1", "cell-a", "one two", ["t1"])],
    )
    assert scores == []


def test_high_resonance_filter_is_threshold_based() -> None:
    scores = [
        ResonanceScore("a1", recurrence_count=3, cell_diversity=2, score=0.75),
        ResonanceScore("a2", recurrence_count=1, cell_diversity=1, score=0.25),
    ]

    assert get_high_resonance_alloys(scores, threshold=0.50) == [scores[0]]
