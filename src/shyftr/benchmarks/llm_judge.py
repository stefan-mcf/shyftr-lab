from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence

from shyftr.benchmarks.types import BenchmarkQuestion

PROMPT_TEMPLATE_VERSION = "phase13-llm-judge-v0"
_ALLOWED_OUTPUT_DIRS = ("artifacts", "reports", "tmp")


def _prompt_template() -> str:
    return """You are a strict benchmark judge. Decide whether the proposed answer is correct for the question.
Question type: {question_type}
Question: {question}
Expected answer: {expected_answer}
Proposed answer: {answer_text}
Answer state: {answer_state}

Return compact JSON only with fields: verdict, score, rationale. verdict must be one of correct, partially_correct, incorrect, missed_answer, unsupported_answer, correct_abstention.
"""


def prompt_template_hash() -> str:
    return hashlib.sha256(_prompt_template().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LLMJudgeConfig:
    provider: str = "none"
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    api_key_file: Optional[str] = None
    max_retries: int = 0
    output_jsonl: Optional[Path] = None
    temperature: float = 0.0

    def provider_normalized(self) -> str:
        return str(self.provider or "none").strip().lower()

    def public_summary(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_normalized(),
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "api_key_env": self.api_key_env,
            "api_key_file_configured": bool(self.api_key_file),
            "max_retries": int(self.max_retries),
            "output_jsonl": str(self.output_jsonl) if self.output_jsonl else None,
            "temperature": float(self.temperature),
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "prompt_template_sha256": prompt_template_hash(),
        }


@dataclass(frozen=True)
class LLMJudgeCaseResult:
    query_id: str
    verdict: str
    score: float
    deterministic_verdict: Optional[str] = None
    agreement: Optional[bool] = None
    rationale: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "verdict": self.verdict,
            "score": float(self.score),
            "deterministic_verdict": self.deterministic_verdict,
            "agreement": self.agreement,
            "rationale": self.rationale,
            "usage": dict(self.usage),
            "latency_ms": float(self.latency_ms),
        }


class LLMJudgeProvider(Protocol):
    def judge_case(self, *, prompt: str, config: LLMJudgeConfig, case: Dict[str, Any]) -> Dict[str, Any]:
        ...


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_llm_judge_output_path(output_path: Path, *, repo_root: Path) -> Path:
    resolved = Path(output_path).expanduser().resolve()
    allowed_roots = [(repo_root / name).resolve() for name in _ALLOWED_OUTPUT_DIRS]
    if not any(_is_relative_to(resolved, allowed_root) for allowed_root in allowed_roots):
        allowed = ", ".join(_ALLOWED_OUTPUT_DIRS)
        raise ValueError(f"Refusing to write raw LLM judge JSONL outside repo-local {allowed}/ directories: {resolved}")
    if resolved.suffix != ".jsonl":
        raise ValueError(f"Raw LLM judge output must be a .jsonl file: {resolved}")
    return resolved


def _resolve_api_key(config: LLMJudgeConfig) -> Optional[str]:
    if config.api_key_env:
        value = os.environ.get(str(config.api_key_env))
        if value:
            return value
    if config.api_key_file:
        path = Path(config.api_key_file).expanduser()
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    return None


def _estimate_tokens(text: str) -> int:
    return max(1, len(str(text).split()))


def build_judge_prompt(*, question: BenchmarkQuestion, answer: Dict[str, Any]) -> str:
    return _prompt_template().format(
        question_type=question.question_type or "unknown",
        question=question.query,
        expected_answer=question.expected_answer,
        answer_text=answer.get("answer_text"),
        answer_state=answer.get("answer_state"),
    )


class OpenAICompatibleJudgeProvider:
    """OpenAI-compatible provider loaded only when explicitly requested."""

    def judge_case(self, *, prompt: str, config: LLMJudgeConfig, case: Dict[str, Any]) -> Dict[str, Any]:
        # This import is deliberately inside the explicit provider path. The
        # default `provider=none` path never imports SDKs and never creates a
        # network-capable client.
        from openai import OpenAI  # type: ignore

        api_key = _resolve_api_key(config)
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=str(config.model),
            temperature=float(config.temperature),
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"verdict": "incorrect", "score": 0.0, "rationale": "provider returned non-JSON content"}
        usage = getattr(response, "usage", None)
        if usage is not None:
            parsed["usage"] = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }
        parsed["raw_provider"] = case.get("provider")
        return parsed


def _skip(reason: str, *, config: LLMJudgeConfig, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "enabled": True,
        "status": "skipped",
        "skip_reason": reason,
        "config": config.public_summary(),
        "results": [],
        "agreement_rate": None,
        "cost_estimate_usd": "unknown",
        "details": dict(details or {}),
        "claim_limit": "supplementary optional LLM judge only; deterministic judge remains primary",
    }


def evaluate_optional_llm_judge(
    *,
    config: LLMJudgeConfig,
    fixture_questions: Sequence[BenchmarkQuestion],
    deterministic_answer_eval: Dict[str, Any],
    repo_root: Path,
    provider_client: Optional[LLMJudgeProvider] = None,
) -> Optional[Dict[str, Any]]:
    provider_name = config.provider_normalized()
    if provider_name == "none":
        return None
    if provider_name not in {"openai-compatible", "local-openai-compatible"}:
        return _skip("unsupported_provider", config=config, details={"provider": provider_name})
    if not deterministic_answer_eval.get("enabled"):
        return _skip("deterministic_answer_eval_required", config=config)
    if not config.model:
        return _skip("missing_model", config=config)
    if provider_name == "local-openai-compatible" and not config.base_url:
        return _skip("missing_base_url", config=config)
    if config.output_jsonl is not None:
        safe_llm_judge_output_path(config.output_jsonl, repo_root=repo_root)
    api_key = _resolve_api_key(config)
    if not api_key:
        return _skip("missing_api_key", config=config)
    if provider_client is None:
        if importlib.util.find_spec("openai") is None:
            return _skip("missing_openai_dependency", config=config)
        provider_client = OpenAICompatibleJudgeProvider()

    by_question = {q.question_id: q for q in fixture_questions}
    case_rows = list(deterministic_answer_eval.get("results") or [])
    raw_rows: List[Dict[str, Any]] = []
    results: List[LLMJudgeCaseResult] = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for row in case_rows:
        query_id = str(row.get("query_id") or "")
        question = by_question.get(query_id)
        if question is None:
            continue
        answer = dict(row.get("answer") or {})
        deterministic = dict(row.get("judge") or {})
        prompt = build_judge_prompt(question=question, answer=answer)
        total_prompt_tokens += _estimate_tokens(prompt)
        started = time.perf_counter()
        provider_payload = provider_client.judge_case(
            prompt=prompt,
            config=config,
            case={"query_id": query_id, "provider": provider_name},
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        verdict = str(provider_payload.get("verdict") or "incorrect")
        score = float(provider_payload.get("score", 1.0 if verdict == "correct" else 0.0))
        usage = dict(provider_payload.get("usage") or {})
        if usage.get("prompt_tokens") is None:
            usage["prompt_tokens"] = _estimate_tokens(prompt)
        if usage.get("completion_tokens") is None:
            usage["completion_tokens"] = _estimate_tokens(str(provider_payload.get("rationale") or verdict))
        usage["cost_estimate_usd"] = "unknown"
        total_completion_tokens += int(usage.get("completion_tokens") or 0)
        deterministic_verdict = deterministic.get("verdict")
        agreement = bool(deterministic_verdict == verdict) if deterministic_verdict else None
        result = LLMJudgeCaseResult(
            query_id=query_id,
            verdict=verdict,
            score=score,
            deterministic_verdict=deterministic_verdict,
            agreement=agreement,
            rationale=provider_payload.get("rationale"),
            usage=usage,
            latency_ms=latency_ms,
        )
        results.append(result)
        raw_rows.append({"query_id": query_id, "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), "result": result.to_dict()})

    if config.output_jsonl is not None:
        safe_path = safe_llm_judge_output_path(config.output_jsonl, repo_root=repo_root)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with safe_path.open("w", encoding="utf-8") as handle:
            for row in raw_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    agreement_values = [r.agreement for r in results if r.agreement is not None]
    return {
        "enabled": True,
        "status": "ok",
        "skip_reason": None,
        "config": config.public_summary(),
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "prompt_template_sha256": prompt_template_hash(),
        "temperature": float(config.temperature),
        "question_count": len(results),
        "agreement_rate": (sum(1 for value in agreement_values if value) / len(agreement_values)) if agreement_values else None,
        "results": [r.to_dict() for r in results],
        "usage_summary": {
            "prompt_tokens_estimated": total_prompt_tokens,
            "completion_tokens_estimated": total_completion_tokens,
            "cost_estimate_usd": "unknown",
        },
        "claim_limit": "supplementary optional LLM judge only; deterministic judge remains primary",
    }


__all__ = [
    "LLMJudgeCaseResult",
    "LLMJudgeConfig",
    "LLMJudgeProvider",
    "OpenAICompatibleJudgeProvider",
    "PROMPT_TEMPLATE_VERSION",
    "build_judge_prompt",
    "evaluate_optional_llm_judge",
    "prompt_template_hash",
    "safe_llm_judge_output_path",
]
