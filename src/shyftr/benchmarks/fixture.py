from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .types import BenchmarkConversation, BenchmarkMessage, BenchmarkQuestion


FIXTURE_SCHEMA_VERSION = "shyftr-memory-benchmark-fixture/v0"


@dataclass(frozen=True)
class BenchmarkFixture:
    schema_version: str
    fixture_id: str
    dataset_name: str
    dataset_version: str
    contains_private_data: bool
    conversations: List[BenchmarkConversation] = field(default_factory=list)
    questions: List[BenchmarkQuestion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        def _msg_to_dict(msg):
            return {
                "message_id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at,
                "metadata": dict(msg.metadata),
            }

        def _conv_to_dict(conv: BenchmarkConversation):
            return {
                "conversation_id": conv.conversation_id,
                "session_id": conv.session_id,
                "started_at": conv.started_at,
                "messages": [_msg_to_dict(m) for m in conv.messages],
                "metadata": dict(conv.metadata),
            }

        def _q_to_dict(q: BenchmarkQuestion):
            return {
                "question_id": q.question_id,
                "query": q.query,
                "expected_answer": q.expected_answer,
                "expected_item_ids": list(q.expected_item_ids) if q.expected_item_ids is not None else None,
                "question_type": q.question_type,
                "temporal_hint": q.temporal_hint,
                "evaluation_notes": q.evaluation_notes,
            }

        return {
            "schema_version": self.schema_version,
            "fixture_id": self.fixture_id,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "contains_private_data": bool(self.contains_private_data),
            "conversations": [_conv_to_dict(c) for c in self.conversations],
            "questions": [_q_to_dict(q) for q in self.questions],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BenchmarkFixture":
        schema_version = str(payload.get("schema_version") or "")
        if schema_version != FIXTURE_SCHEMA_VERSION:
            raise ValueError(f"unsupported fixture schema_version: {schema_version}")

        conversations: List[BenchmarkConversation] = []
        for conv in payload.get("conversations") or []:
            messages = []
            for msg in conv.get("messages") or []:
                messages.append(
                    {
                        "message_id": str(msg.get("message_id") or ""),
                        "role": str(msg.get("role") or ""),
                        "content": str(msg.get("content") or ""),
                        "created_at": msg.get("created_at"),
                        "metadata": dict(msg.get("metadata") or {}),
                    }
                )
            conversations.append(
                BenchmarkConversation(
                    conversation_id=str(conv.get("conversation_id") or ""),
                    session_id=conv.get("session_id"),
                    started_at=conv.get("started_at"),
                    messages=[BenchmarkMessage(**m) for m in messages],
                    metadata=dict(conv.get("metadata") or {}),
                )
            )

        questions: List[BenchmarkQuestion] = []
        for q in payload.get("questions") or []:
            questions.append(
                BenchmarkQuestion(
                    question_id=str(q.get("question_id") or ""),
                    query=str(q.get("query") or ""),
                    expected_answer=q.get("expected_answer"),
                    expected_item_ids=list(q.get("expected_item_ids")) if q.get("expected_item_ids") is not None else None,
                    question_type=q.get("question_type"),
                    temporal_hint=q.get("temporal_hint"),
                    evaluation_notes=q.get("evaluation_notes"),
                )
            )

        return cls(
            schema_version=schema_version,
            fixture_id=str(payload.get("fixture_id") or ""),
            dataset_name=str(payload.get("dataset_name") or ""),
            dataset_version=str(payload.get("dataset_version") or ""),
            contains_private_data=bool(payload.get("contains_private_data") or False),
            conversations=conversations,
            questions=questions,
        )


def synthetic_mini_fixture() -> BenchmarkFixture:
    """Return a deterministic, public-safe synthetic fixture.

    This fixture is tiny by design. It is only meant to validate the adapter and
    report contract (P11-1) and should not be used for broad benchmark claims.
    """

    from .types import BenchmarkMessage

    conv1 = BenchmarkConversation(
        conversation_id="conv-001",
        session_id="session-a",
        started_at="2026-01-01T00:00:00Z",
        messages=[
            BenchmarkMessage(message_id="m-001", role="user", content="My favorite color is teal."),
            BenchmarkMessage(message_id="m-002", role="assistant", content="Noted: teal."),
        ],
        metadata={"topic": "preferences"},
    )

    conv2 = BenchmarkConversation(
        conversation_id="conv-002",
        session_id="session-b",
        started_at="2026-01-02T00:00:00Z",
        messages=[
            BenchmarkMessage(message_id="m-003", role="user", content="My project codename is LANTERN."),
            BenchmarkMessage(message_id="m-004", role="assistant", content="Understood."),
        ],
        metadata={"topic": "project"},
    )

    questions = [
        BenchmarkQuestion(
            question_id="q-001",
            query="What is my favorite color?",
            expected_answer="teal",
            expected_item_ids=["m-001"],
            question_type="factual",
        ),
        BenchmarkQuestion(
            question_id="q-002",
            query="What is the project codename?",
            expected_answer="LANTERN",
            expected_item_ids=["m-003"],
            question_type="factual",
        ),
        BenchmarkQuestion(
            question_id="q-003",
            query="In session-a, what color did I say I like?",
            expected_answer="teal",
            expected_item_ids=["m-001"],
            question_type="temporal",
            temporal_hint="session-a",
        ),
    ]

    return BenchmarkFixture(
        schema_version=FIXTURE_SCHEMA_VERSION,
        fixture_id="synthetic-mini-001",
        dataset_name="synthetic-mini",
        dataset_version="v0",
        contains_private_data=False,
        conversations=[conv1, conv2],
        questions=questions,
    )


__all__ = ["BenchmarkFixture", "FIXTURE_SCHEMA_VERSION", "synthetic_mini_fixture"]
