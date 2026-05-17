from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Set

from shyftr.benchmarks.answerer import AnswerResult
from shyftr.benchmarks.types import BenchmarkQuestion

@dataclass(frozen=True)
class JudgeResult:
    score: float
    verdict: str
    evaluation_type: str
    notes: Dict[str, Any] = field(default_factory=dict)
    token_f1: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": float(self.score),
            "verdict": self.verdict,
            "evaluation_type": self.evaluation_type,
            "notes": dict(self.notes),
            "token_f1": self.token_f1,
        }


def normalize_answer(text: Optional[str]) -> str:
    value = "" if text is None else str(text).lower()
    value = re.sub(r"\b(a|an|the)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def token_f1(predicted: Optional[str], expected: Optional[str]) -> Optional[float]:
    if expected is None:
        return None
    p = normalize_answer(predicted).split()
    g = normalize_answer(expected).split()
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    common = 0
    used = [False] * len(g)
    for token in p:
        for idx, gold in enumerate(g):
            if not used[idx] and token == gold:
                used[idx] = True
                common += 1
                break
    if common == 0:
        return 0.0
    precision = common / len(p)
    recall = common / len(g)
    return 2 * precision * recall / (precision + recall)


class DeterministicCompositeJudge:
    name = "deterministic-composite"
    version = "phase12-v0"

    def judge(self, *, question: BenchmarkQuestion, answer: AnswerResult) -> JudgeResult:
        expected = question.expected_answer
        if answer.answer_state.startswith("abstained"):
            if expected is None:
                return JudgeResult(1.0, "correct_abstention", self.name, {"abstained": True}, token_f1=None)
            return JudgeResult(0.0, "missed_answer", self.name, {"abstained": True}, token_f1=0.0)
        exact = normalize_answer(answer.answer_text) == normalize_answer(expected)
        f1 = token_f1(answer.answer_text, expected)
        if exact:
            return JudgeResult(1.0, "correct", self.name, {"exact_match": True}, token_f1=1.0)
        if f1 is not None and f1 >= 0.75:
            return JudgeResult(float(f1), "partially_correct", self.name, {"exact_match": False}, token_f1=float(f1))
        if not answer.supporting_item_ids:
            return JudgeResult(float(f1 or 0.0), "unsupported_answer", self.name, {"exact_match": False}, token_f1=f1)
        return JudgeResult(float(f1 or 0.0), "incorrect", self.name, {"exact_match": False}, token_f1=f1)


def build_judge(name: str):
    normalized = str(name).strip().lower()
    if normalized in {"deterministic-composite", "composite"}:
        return DeterministicCompositeJudge()
    raise ValueError(f"unknown judge: {name}")

__all__ = ["JudgeResult", "DeterministicCompositeJudge", "build_judge", "normalize_answer", "token_f1"]
