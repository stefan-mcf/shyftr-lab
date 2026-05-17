from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List

from shyftr.benchmarks.adapters.no_memory import NoMemoryBackendAdapter
from shyftr.benchmarks.fixture import FIXTURE_SCHEMA_VERSION, BenchmarkFixture, resolve_benchmark_fixture
from shyftr.benchmarks.runner import run_fixture_benchmark
from shyftr.benchmarks.types import BenchmarkConversation, BenchmarkMessage, BenchmarkQuestion, RetrievalItem, SearchOutput


class RecordingBackend(NoMemoryBackendAdapter):
    def __init__(self) -> None:
        super().__init__(backend_name="recording")
        self.reset_calls: List[str] = []
        self.ingested_by_reset: dict[str, list[str]] = {}
        self.search_calls: list[str] = []

    def reset_run(self, run_id: str) -> None:
        super().reset_run(run_id)
        self.reset_calls.append(run_id)
        self.ingested_by_reset.setdefault(run_id, [])

    def ingest_conversation(self, conversation: BenchmarkConversation) -> None:
        self.ingested_by_reset.setdefault(self._run_id, []).append(conversation.conversation_id)

    def search(self, *, query_id: str, query: str, top_k: int) -> SearchOutput:  # noqa: ARG002
        self.search_calls.append(query_id)
        items = [
            RetrievalItem(
                item_id=f"{query_id}-m1",
                text=f"answer for {query_id}",
                provenance={"query_id": query_id},
            )
        ]
        return SearchOutput(backend_name=self.backend_name, run_id=self._run_id, query_id=query_id, items=items, latency_ms=0.0)


def _repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "artifacts" / "benchmarks").mkdir(parents=True)
    (root / "reports" / "benchmarks").mkdir(parents=True)
    (root / "tmp").mkdir(parents=True)
    return root


def _case_fixture(*, with_groups: bool = True) -> BenchmarkFixture:
    conversations = []
    questions = []
    for case_id in ["case-a", "case-b", "case-c"]:
        metadata = {"isolation_group": case_id} if with_groups else {}
        conversations.append(
            BenchmarkConversation(
                conversation_id=f"{case_id}-conversation",
                session_id=f"{case_id}-session",
                messages=[BenchmarkMessage(message_id=f"{case_id}-m1", role="user", content=f"answer for {case_id}", metadata=metadata)],
                metadata=metadata,
            )
        )
        notes = f"isolation_group={case_id}" if with_groups else None
        questions.append(
            BenchmarkQuestion(
                question_id=case_id,
                query=f"question for {case_id}",
                expected_answer=f"answer for {case_id}",
                expected_item_ids=[f"{case_id}-m1"],
                question_type="factual",
                evaluation_notes=notes,
            )
        )
    return BenchmarkFixture(
        schema_version=FIXTURE_SCHEMA_VERSION,
        fixture_id="phase13-cases",
        dataset_name="phase13-synthetic",
        dataset_version="v0",
        contains_private_data=False,
        conversations=conversations,
        questions=questions,
    )


def test_limit_questions_runs_bounded_subset_and_reports_limit(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    backend = RecordingBackend()
    output = repo_root / "artifacts" / "benchmarks" / "limit.json"
    run_fixture_benchmark(
        fixture=_case_fixture(),
        adapters=[backend],
        run_id="limit",
        output_path=output,
        repo_root=repo_root,
        limit_questions=2,
        include_retrieval_details=False,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert backend.search_calls == ["case-a", "case-b"]
    assert payload["fairness"]["limit_questions"] == 2
    assert payload["fairness"]["original_question_count"] == 3
    assert payload["fairness"]["limited_question_count"] == 2
    assert payload["dataset"]["question_count"] == 2


def test_isolate_per_case_resets_backend_before_each_question(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    backend = RecordingBackend()
    output = repo_root / "artifacts" / "benchmarks" / "isolated.json"
    run_fixture_benchmark(
        fixture=_case_fixture(),
        adapters=[backend],
        run_id="isolated",
        output_path=output,
        repo_root=repo_root,
        limit_questions=2,
        isolate_per_case=True,
        include_retrieval_details=False,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert backend.reset_calls == ["isolated:case-a", "isolated:case-b"]
    assert payload["fairness"]["isolate_per_case"] is True
    result = payload["backend_results"][0]
    assert result["ingest"]["reset_count"] == 2
    assert result["search"]["operation_count"] == 2


def test_isolate_per_case_ingests_only_matching_case_conversations(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    backend = RecordingBackend()
    output = repo_root / "artifacts" / "benchmarks" / "isolated_ingest.json"
    run_fixture_benchmark(
        fixture=_case_fixture(),
        adapters=[backend],
        run_id="isolated-ingest",
        output_path=output,
        repo_root=repo_root,
        limit_questions=2,
        isolate_per_case=True,
        include_retrieval_details=False,
    )
    assert backend.ingested_by_reset["isolated-ingest:case-a"] == ["case-a-conversation"]
    assert backend.ingested_by_reset["isolated-ingest:case-b"] == ["case-b-conversation"]


def test_isolate_per_case_fails_when_case_group_is_missing(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    output = repo_root / "artifacts" / "benchmarks" / "missing_group.json"
    run_fixture_benchmark(
        fixture=_case_fixture(with_groups=False),
        adapters=[RecordingBackend()],
        run_id="missing-group",
        output_path=output,
        repo_root=repo_root,
        isolate_per_case=True,
        include_retrieval_details=False,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    result = payload["backend_results"][0]
    assert result["status"] == "failed"
    assert "isolate_per_case requires case grouping metadata" in result["status_reason"]


def test_cli_help_includes_beam_standard_and_phase13_flags() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_memory_benchmark.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "beam-standard" in completed.stdout
    assert "--limit-questions" in completed.stdout
    assert "--isolate-per-case" in completed.stdout


def test_explicit_beam_standard_path_resolves_without_download(tmp_path: Path) -> None:
    payload = {
        "dataset_version": "local",
        "split": "beam-smoke",
        "contains_private_data": False,
        "cases": [
            {
                "case_id": "beam-1",
                "ability": "Information Extraction",
                "question": "What was saved?",
                "answer": "a receipt",
                "messages": [{"role": "user", "content": "I saved a receipt."}],
            }
        ],
    }
    source = tmp_path / "beam.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    fixture = resolve_benchmark_fixture(
        fixture_path=source,
        fixture_format="beam-standard",
        allow_private_data=False,
    )
    assert fixture.dataset_name == "beam-standard"
    assert fixture.questions[0].question_type == "Information Extraction"


def test_defaults_preserve_phase12_shared_fixture_behavior(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    backend = RecordingBackend()
    output = repo_root / "artifacts" / "benchmarks" / "default.json"
    run_fixture_benchmark(
        fixture=_case_fixture(),
        adapters=[backend],
        run_id="default",
        output_path=output,
        repo_root=repo_root,
        include_retrieval_details=False,
    )
    assert backend.reset_calls == ["default"]
    assert backend.search_calls == ["case-a", "case-b", "case-c"]
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["fairness"]["isolate_per_case"] is False
    assert payload["fairness"]["limit_questions"] is None


def test_answer_eval_still_runs_with_limit_questions(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    output = repo_root / "artifacts" / "benchmarks" / "answer_eval_limited.json"
    run_fixture_benchmark(
        fixture=_case_fixture(),
        adapters=[RecordingBackend()],
        run_id="answer-eval-limited",
        output_path=output,
        repo_root=repo_root,
        limit_questions=2,
        include_retrieval_details=False,
        enable_answer_eval=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    answer_eval = payload["backend_results"][0]["metrics"]["answer_eval"]
    assert answer_eval["enabled"] is True
    assert answer_eval["question_count"] == 2
