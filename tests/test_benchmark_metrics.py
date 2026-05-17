from __future__ import annotations

from shyftr.benchmarks.runner import _compute_retrieval_metrics
from shyftr.benchmarks.types import RetrievalItem, SearchOutput


def test_retrieval_metrics_include_ndcg_and_support_coverage() -> None:
    outputs = [SearchOutput(backend_name="b", run_id="r", query_id="q", items=[RetrievalItem("m1", "a"), RetrievalItem("m2", "b")])]
    metrics = _compute_retrieval_metrics(outputs, {"q": ["m2"]}, k=2)
    assert metrics["recall_at_k"] == 1.0
    assert metrics["ndcg_at_k"] is not None
    assert 0 < metrics["ndcg_at_k"] < 1
    assert metrics["answer_support_coverage"] == 1.0
    assert metrics["conflict_retrieval_rate"] == "not_supported"
