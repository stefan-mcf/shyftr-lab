from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from shyftr.benchmarks.fixture import FIXTURE_SCHEMA_VERSION, BenchmarkFixture
from shyftr.benchmarks.types import BenchmarkConversation, BenchmarkMessage, BenchmarkQuestion


LOCOMO_STANDARD_FORMAT = "locomo-standard/v0"


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _first_present(payload: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return default


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def map_locomo_standard_payload(payload: Dict[str, Any]) -> BenchmarkFixture:
    """Map a LOCOMO-standard-like payload into the Phase 11 benchmark fixture contract.

    This mapper is intentionally conservative and dependency-free. It accepts a
    normalized local JSON shape that mirrors LOCOMO-style multi-session data,
    but it does not download or vendor the public dataset.
    """

    dataset_version = str(_first_present(payload, ["dataset_version", "version"], "unknown"))
    split = str(_first_present(payload, ["split", "fixture_id"], "locomo-standard-local"))
    contains_private_data = bool(_first_present(payload, ["contains_private_data"], True))

    conversations: List[BenchmarkConversation] = []
    for conv_index, raw_conv in enumerate(_as_list(_first_present(payload, ["conversations", "sessions", "dialogues"], [])), start=1):
        conv = _as_dict(raw_conv)
        conversation_id = str(_first_present(conv, ["conversation_id", "session_id", "dialogue_id", "id"], f"locomo-conv-{conv_index:04d}"))
        session_id = _string_or_none(_first_present(conv, ["session_id", "conversation_id", "dialogue_id"]))
        started_at = _string_or_none(_first_present(conv, ["started_at", "timestamp", "date"]))
        metadata = _as_dict(conv.get("metadata"))
        if "locomo_user_id" not in metadata and conv.get("user_id") is not None:
            metadata["locomo_user_id"] = str(conv.get("user_id"))

        messages: List[BenchmarkMessage] = []
        raw_messages = _as_list(_first_present(conv, ["messages", "turns", "dialogue"], []))
        for msg_index, raw_msg in enumerate(raw_messages, start=1):
            msg = _as_dict(raw_msg)
            message_id = str(_first_present(msg, ["message_id", "turn_id", "id"], f"{conversation_id}-m-{msg_index:04d}"))
            role = str(_first_present(msg, ["role", "speaker"], "user")).lower()
            content = str(_first_present(msg, ["content", "text", "utterance", "message"], ""))
            created_at = _string_or_none(_first_present(msg, ["created_at", "timestamp", "date", "time"]))
            messages.append(
                BenchmarkMessage(
                    message_id=message_id,
                    role=role,
                    content=content,
                    created_at=created_at,
                    metadata=_as_dict(msg.get("metadata")),
                )
            )

        conversations.append(
            BenchmarkConversation(
                conversation_id=conversation_id,
                session_id=session_id,
                started_at=started_at,
                messages=messages,
                metadata=metadata,
            )
        )

    questions: List[BenchmarkQuestion] = []
    for q_index, raw_q in enumerate(_as_list(_first_present(payload, ["questions", "qa", "qas"], [])), start=1):
        q = _as_dict(raw_q)
        question_id = str(_first_present(q, ["question_id", "qa_id", "id"], f"locomo-q-{q_index:04d}"))
        expected_item_ids = _first_present(q, ["expected_item_ids", "evidence_message_ids", "answer_message_ids"], None)
        questions.append(
            BenchmarkQuestion(
                question_id=question_id,
                query=str(_first_present(q, ["query", "question"], "")),
                expected_answer=_first_present(q, ["expected_answer", "answer"], None),
                expected_item_ids=[str(item) for item in _as_list(expected_item_ids)] if expected_item_ids is not None else None,
                question_type=_string_or_none(_first_present(q, ["question_type", "category", "type"])),
                temporal_hint=_string_or_none(_first_present(q, ["temporal_hint", "session_id", "time_hint"])),
                evaluation_notes=_string_or_none(_first_present(q, ["evaluation_notes", "notes"])),
            )
        )

    return BenchmarkFixture(
        schema_version=FIXTURE_SCHEMA_VERSION,
        fixture_id=split,
        dataset_name="locomo-standard",
        dataset_version=dataset_version,
        contains_private_data=contains_private_data,
        conversations=conversations,
        questions=questions,
    )


def load_locomo_standard_json(path: Path, *, allow_private_data: bool = False) -> BenchmarkFixture:
    payload = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    fixture = map_locomo_standard_payload(_as_dict(payload))
    if fixture.contains_private_data and not allow_private_data:
        raise ValueError(
            "Refusing to load LOCOMO-standard input marked or defaulted contains_private_data=true "
            "(pass allow_private_data=true only for local, non-public runs)"
        )
    return fixture


__all__ = ["LOCOMO_STANDARD_FORMAT", "load_locomo_standard_json", "map_locomo_standard_payload"]
