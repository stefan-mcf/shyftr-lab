from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.benchmarks.adapters.no_memory import NoMemoryBackendAdapter
from shyftr.benchmarks.fixture import synthetic_mini_fixture
from shyftr.benchmarks.llm_judge import LLMJudgeConfig, evaluate_optional_llm_judge, safe_llm_judge_output_path
from shyftr.benchmarks.runner import run_fixture_benchmark


class FakeJudgeProvider:
    def __init__(self, verdict: str = "correct") -> None:
        self.verdict = verdict
        self.prompts: list[str] = []

    def judge_case(self, *, prompt: str, config: LLMJudgeConfig, case: dict) -> dict:  # noqa: ARG002
        self.prompts.append(prompt)
        return {
            "verdict": self.verdict,
            "score": 1.0 if self.verdict == "correct" else 0.0,
            "rationale": "mocked judge response",
            "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
        }


def _repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "artifacts" / "benchmarks").mkdir(parents=True)
    (root / "reports" / "benchmarks").mkdir(parents=True)
    (root / "tmp").mkdir(parents=True)
    return root


def _deterministic_answer_eval() -> dict:
    return {
        "enabled": True,
        "results": [
            {
                "query_id": "q-001",
                "answer": {"answer_text": "teal", "answer_state": "answered"},
                "judge": {"verdict": "correct", "score": 1.0},
            }
        ],
    }


def test_llm_judge_provider_none_makes_no_import_or_network_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail_find_spec(name: str):  # noqa: ANN001
        raise AssertionError(f"provider=none must not inspect optional dependency: {name}")

    monkeypatch.setattr("importlib.util.find_spec", fail_find_spec)
    result = evaluate_optional_llm_judge(
        config=LLMJudgeConfig(provider="none"),
        fixture_questions=synthetic_mini_fixture().questions,
        deterministic_answer_eval=_deterministic_answer_eval(),
        repo_root=_repo_root(tmp_path),
    )
    assert result is None


def test_llm_judge_requested_without_dependency_reports_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("P13_FAKE_KEY", "secret-test-key")
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    result = evaluate_optional_llm_judge(
        config=LLMJudgeConfig(provider="openai-compatible", model="judge-model", api_key_env="P13_FAKE_KEY"),
        fixture_questions=synthetic_mini_fixture().questions,
        deterministic_answer_eval=_deterministic_answer_eval(),
        repo_root=_repo_root(tmp_path),
    )
    assert result is not None
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "missing_openai_dependency"


def test_llm_judge_requested_without_credentials_reports_skipped(tmp_path: Path) -> None:
    result = evaluate_optional_llm_judge(
        config=LLMJudgeConfig(provider="openai-compatible", model="judge-model", api_key_env="P13_MISSING_KEY"),
        fixture_questions=synthetic_mini_fixture().questions,
        deterministic_answer_eval=_deterministic_answer_eval(),
        repo_root=_repo_root(tmp_path),
    )
    assert result is not None
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "missing_api_key"


def test_llm_judge_refuses_to_serialize_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret = "very-secret-p13-key"
    monkeypatch.setenv("P13_SECRET_KEY", secret)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    result = evaluate_optional_llm_judge(
        config=LLMJudgeConfig(provider="openai-compatible", model="judge-model", api_key_env="P13_SECRET_KEY"),
        fixture_questions=synthetic_mini_fixture().questions,
        deterministic_answer_eval=_deterministic_answer_eval(),
        repo_root=_repo_root(tmp_path),
    )
    assert secret not in json.dumps(result)
    assert "P13_SECRET_KEY" in json.dumps(result)


def test_llm_judge_requires_guarded_output_path_for_raw_jsonl(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    safe = safe_llm_judge_output_path(repo_root / "artifacts" / "benchmarks" / "judge.jsonl", repo_root=repo_root)
    assert safe.name == "judge.jsonl"
    with pytest.raises(ValueError, match="outside repo-local"):
        safe_llm_judge_output_path(tmp_path / "outside.jsonl", repo_root=repo_root)
    with pytest.raises(ValueError, match="must be a .jsonl"):
        safe_llm_judge_output_path(repo_root / "artifacts" / "benchmarks" / "judge.json", repo_root=repo_root)


def test_deterministic_judge_remains_primary_when_llm_judge_is_enabled(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    output = repo_root / "artifacts" / "benchmarks" / "missing-key.json"
    run_fixture_benchmark(
        fixture=synthetic_mini_fixture(),
        adapters=[NoMemoryBackendAdapter()],
        run_id="missing-key",
        output_path=output,
        repo_root=repo_root,
        enable_answer_eval=True,
        llm_judge_provider="openai-compatible",
        llm_judge_model="judge-model",
        llm_judge_api_key_env="P13_MISSING_KEY",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    metrics = payload["backend_results"][0]["metrics"]
    assert metrics["answer_eval"]["enabled"] is True
    assert metrics["llm_judge"]["status"] == "skipped"
    assert metrics["llm_judge"]["skip_reason"] == "missing_api_key"
    assert payload["models"]["judge"]["name"] == "deterministic-composite"


def test_llm_judge_records_model_prompt_temperature_and_skip_reason(tmp_path: Path) -> None:
    result = evaluate_optional_llm_judge(
        config=LLMJudgeConfig(provider="local-openai-compatible", model="judge-model", base_url="http://127.0.0.1:8000/v1"),
        fixture_questions=synthetic_mini_fixture().questions,
        deterministic_answer_eval=_deterministic_answer_eval(),
        repo_root=_repo_root(tmp_path),
    )
    assert result is not None
    assert result["status"] == "skipped"
    assert result["skip_reason"] == "missing_api_key"
    assert result["config"]["model"] == "judge-model"
    assert result["config"]["temperature"] == 0.0
    assert result["config"]["prompt_template_version"] == "phase13-llm-judge-v0"
    assert result["config"]["prompt_template_sha256"]


def test_llm_judge_agreement_metric_is_reported_when_mock_provider_returns_labels(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("P13_FAKE_KEY", "fake-key")
    output = _repo_root(tmp_path) / "artifacts" / "benchmarks" / "judge.jsonl"
    result = evaluate_optional_llm_judge(
        config=LLMJudgeConfig(
            provider="openai-compatible",
            model="judge-model",
            api_key_env="P13_FAKE_KEY",
            output_jsonl=output,
        ),
        fixture_questions=synthetic_mini_fixture().questions,
        deterministic_answer_eval=_deterministic_answer_eval(),
        repo_root=output.parents[2],
        provider_client=FakeJudgeProvider(verdict="correct"),
    )
    assert result is not None
    assert result["status"] == "ok"
    assert result["agreement_rate"] == 1.0
    assert result["results"][0]["agreement"] is True
    assert result["usage_summary"]["cost_estimate_usd"] == "unknown"
    assert output.exists()
    assert "fake-key" not in output.read_text(encoding="utf-8")
