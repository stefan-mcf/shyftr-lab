from __future__ import annotations

import json
from pathlib import Path

from shyftr.benchmarks.adapters.no_memory import NoMemoryBackendAdapter
from shyftr.benchmarks.answerer import ExtractiveAnswerer, FixedLabelAnswerer
from shyftr.benchmarks.fixture import resolve_benchmark_fixture
from shyftr.benchmarks.judge import DeterministicCompositeJudge, token_f1
from shyftr.benchmarks.runner import run_fixture_benchmark
from shyftr.benchmarks.types import BenchmarkQuestion, RetrievalItem, SearchOutput

class PerfectBackend(NoMemoryBackendAdapter):
    def __init__(self) -> None:
        super().__init__(backend_name="perfect")
        self._items = {
            "lc-q001": [RetrievalItem(item_id="lc1-m001", text="The basil is my favorite herb so far.")],
            "lc-q002": [RetrievalItem(item_id="lc1-m003", text="The watering schedule is every Monday and Thursday.")],
            "lc-q003": [RetrievalItem(item_id="lc2-m001", text="For the demo tomorrow, the passphrase is ORIGAMI-PINE.")],
        }

    def search(self, *, query_id: str, query: str, top_k: int) -> SearchOutput:  # noqa: ARG002
        return SearchOutput(backend_name=self.backend_name, run_id=self._run_id, query_id=query_id, items=list(self._items.get(query_id, [])), latency_ms=0.0)


def test_deterministic_answerer_extracts_expected_answer() -> None:
    question = BenchmarkQuestion(question_id="q", query="Where is the notebook?", expected_answer="kitchen shelf")
    item = RetrievalItem(item_id="m", text="The notebook is on the kitchen shelf.")
    answer = ExtractiveAnswerer().answer(question=question, retrieved_items=[item])
    judged = DeterministicCompositeJudge().judge(question=question, answer=answer)
    assert answer.answer_state == "answered"
    assert answer.answer_text == "kitchen shelf"
    assert answer.supporting_item_ids == ["m"]
    assert judged.verdict == "correct"


def test_fixed_label_answerer_is_marked_debug_oracle() -> None:
    question = BenchmarkQuestion(question_id="q", query="What?", expected_answer="gold")
    answer = FixedLabelAnswerer().answer(question=question, retrieved_items=[])
    assert answer.answer_text == "gold"
    assert answer.notes["debug_oracle"] is True
    assert answer.notes["comparable"] is False


def test_token_f1_partial_match_is_deterministic() -> None:
    assert token_f1("blue notebook shelf", "notebook shelf") > 0.7


def test_runner_answer_eval_writes_fixture_level_metrics(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "artifacts" / "benchmarks").mkdir(parents=True)
    (repo_root / "tmp").mkdir(parents=True)
    fixture = resolve_benchmark_fixture(fixture_name="locomo-mini")
    output = repo_root / "artifacts" / "benchmarks" / "answer_eval.json"
    run_fixture_benchmark(
        fixture=fixture,
        adapters=[PerfectBackend()],
        run_id="answer-eval",
        output_path=output,
        repo_root=repo_root,
        top_k_values=[1, 3],
        include_retrieval_details=False,
        enable_answer_eval=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    result = payload["backend_results"][0]
    answer_eval = result["metrics"]["answer_eval"]
    assert payload["models"]["answerer"]["name"] == "deterministic-extractive"
    assert answer_eval["enabled"] is True
    assert answer_eval["question_count"] == len(fixture.questions)
    assert answer_eval["correctness"] > 0
    assert "by_question_type" in answer_eval
