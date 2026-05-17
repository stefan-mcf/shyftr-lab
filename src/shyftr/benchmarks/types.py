from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class BenchmarkMessage:
    message_id: str
    role: str
    content: str
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkConversation:
    conversation_id: str
    session_id: Optional[str] = None
    started_at: Optional[str] = None
    messages: List[BenchmarkMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkQuestion:
    question_id: str
    query: str
    expected_answer: Optional[str] = None
    expected_item_ids: Optional[List[str]] = None
    question_type: Optional[str] = None
    temporal_hint: Optional[str] = None
    evaluation_notes: Optional[str] = None


@dataclass(frozen=True)
class RetrievalItem:
    item_id: str
    text: str
    score: Optional[float] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    sensitivity: Optional[str] = None
    review_status: Optional[str] = None


@dataclass(frozen=True)
class SearchOutput:
    backend_name: str
    run_id: str
    query_id: str
    items: List[RetrievalItem] = field(default_factory=list)
    latency_ms: Optional[float] = None


__all__ = [
    "BenchmarkMessage",
    "BenchmarkConversation",
    "BenchmarkQuestion",
    "RetrievalItem",
    "SearchOutput",
]
