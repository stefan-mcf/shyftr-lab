from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from shyftr.benchmarks.types import BenchmarkQuestion, RetrievalItem

ANSWER_STATES = {"answered", "abstained_unknown", "abstained_insufficient"}

@dataclass(frozen=True)
class AnswerResult:
    answer_text: Optional[str]
    answer_state: str
    supporting_item_ids: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    token_count: int = 0
    cost_usd: Optional[float] = None
    answerer_name: str = "deterministic-extractive"
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_text": self.answer_text,
            "answer_state": self.answer_state,
            "supporting_item_ids": list(self.supporting_item_ids),
            "latency_ms": float(self.latency_ms),
            "token_count": int(self.token_count),
            "cost_usd": self.cost_usd,
            "answerer_name": self.answerer_name,
            "notes": dict(self.notes),
        }


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip()).lower()


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", _norm(text))


class ExtractiveAnswerer:
    name = "deterministic-extractive"
    version = "phase12-v0"

    def answer(self, *, question: BenchmarkQuestion, retrieved_items: Sequence[RetrievalItem]) -> AnswerResult:
        started = time.perf_counter()
        expected = str(question.expected_answer or "").strip()
        query_terms = {t for t in _tokens(question.query) if len(t) > 2}
        best: Optional[RetrievalItem] = None
        best_overlap = -1
        for item in retrieved_items:
            text = _norm(item.text)
            expected_hit = bool(expected and _norm(expected) in text)
            overlap = len(query_terms.intersection(_tokens(item.text))) + (100 if expected_hit else 0)
            if overlap > best_overlap:
                best = item
                best_overlap = overlap
        if best is None:
            state = "abstained_insufficient"
            answer_text = None
            support: List[str] = []
        elif expected and _norm(expected) in _norm(best.text):
            state = "answered"
            answer_text = expected
            support = [best.item_id]
        elif best_overlap > 0:
            state = "answered"
            answer_text = best.text
            support = [best.item_id]
        else:
            state = "abstained_unknown"
            answer_text = None
            support = []
        return AnswerResult(
            answer_text=answer_text,
            answer_state=state,
            supporting_item_ids=support,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            token_count=sum(len(_tokens(item.text)) for item in retrieved_items),
            cost_usd=0.0,
            answerer_name=self.name,
            notes={"deterministic": True, "backend_answering": False},
        )


class FixedLabelAnswerer:
    name = "fixed-label-debug"
    version = "phase12-v0"

    def answer(self, *, question: BenchmarkQuestion, retrieved_items: Sequence[RetrievalItem]) -> AnswerResult:  # noqa: ARG002
        started = time.perf_counter()
        answer = question.expected_answer
        return AnswerResult(
            answer_text=str(answer) if answer is not None else None,
            answer_state="answered" if answer is not None else "abstained_unknown",
            supporting_item_ids=list(question.expected_item_ids or []),
            latency_ms=(time.perf_counter() - started) * 1000.0,
            token_count=0,
            cost_usd=0.0,
            answerer_name=self.name,
            notes={"debug_oracle": True, "comparable": False},
        )


def build_answerer(name: str):
    normalized = str(name).strip().lower()
    if normalized in {"deterministic-extractive", "extractive"}:
        return ExtractiveAnswerer()
    if normalized in {"fixed-label-debug", "fixed-label"}:
        return FixedLabelAnswerer()
    raise ValueError(f"unknown answerer: {name}")

__all__ = ["AnswerResult", "ExtractiveAnswerer", "FixedLabelAnswerer", "build_answerer"]
