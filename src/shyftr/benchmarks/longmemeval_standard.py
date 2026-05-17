from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from shyftr.benchmarks.fixture import FIXTURE_SCHEMA_VERSION, BenchmarkFixture
from shyftr.benchmarks.types import BenchmarkConversation, BenchmarkMessage, BenchmarkQuestion


LONGMEMEVAL_STANDARD_FORMAT = "longmemeval-standard/v0"


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


def _case_rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [_as_dict(item) for item in payload]
    data = _as_dict(payload)
    return [_as_dict(item) for item in _as_list(_first_present(data, ["cases", "questions", "data"], []))]


def map_longmemeval_standard_payload(payload: Any) -> BenchmarkFixture:
    """Map a normalized local LongMemEval-style payload into the benchmark fixture contract.

    The mapper is deliberately local-path and dependency-free. It accepts either
    a top-level list of cases or an object with cases/questions/data. It does not
    download, vendor, or run LongMemEval.
    """

    data = _as_dict(payload)
    dataset_version = str(_first_present(data, ["dataset_version", "version"], "unknown"))
    split = str(_first_present(data, ["split", "fixture_id"], "longmemeval-standard-local"))
    contains_private_data = bool(_first_present(data, ["contains_private_data"], True))

    conversations: List[BenchmarkConversation] = []
    questions: List[BenchmarkQuestion] = []
    for case_index, case in enumerate(_case_rows(payload), start=1):
        case_id = str(_first_present(case, ["case_id", "question_id", "id", "qid"], f"longmemeval-case-{case_index:04d}"))
        question_id = str(_first_present(case, ["question_id", "qid", "id"], case_id))
        question_type = _string_or_none(_first_present(case, ["question_type", "type", "category"]))
        question_date = _string_or_none(_first_present(case, ["question_date", "query_date", "date"]))
        haystack_session_ids = [str(v) for v in _as_list(_first_present(case, ["haystack_session_ids", "session_ids"], []))]
        haystack_dates = [str(v) for v in _as_list(_first_present(case, ["haystack_dates", "session_dates"], []))]
        expected_item_ids: List[str] = []

        raw_sessions = _as_list(_first_present(case, ["haystack_sessions", "sessions", "haystack"], []))
        for session_index, raw_session in enumerate(raw_sessions, start=1):
            if isinstance(raw_session, list):
                session_payload: Dict[str, Any] = {"messages": raw_session}
            else:
                session_payload = _as_dict(raw_session)
            session_id = str(_first_present(session_payload, ["session_id", "id"], haystack_session_ids[session_index - 1] if session_index - 1 < len(haystack_session_ids) else f"{case_id}-session-{session_index:04d}"))
            started_at = _string_or_none(_first_present(session_payload, ["started_at", "date", "timestamp"], haystack_dates[session_index - 1] if session_index - 1 < len(haystack_dates) else None))
            conversation_id = str(_first_present(session_payload, ["conversation_id", "dialogue_id"], session_id))
            metadata = _as_dict(session_payload.get("metadata"))
            metadata.update({"longmemeval_case_id": case_id, "isolation_group": case_id})
            messages: List[BenchmarkMessage] = []
            for message_index, raw_msg in enumerate(_as_list(_first_present(session_payload, ["messages", "turns", "dialogue"], [])), start=1):
                msg = _as_dict(raw_msg)
                message_id = str(_first_present(msg, ["message_id", "turn_id", "id"], f"{session_id}-m-{message_index:04d}"))
                if message_index == 1 and not _as_list(_first_present(case, ["expected_item_ids", "evidence_message_ids", "answer_message_ids"], [])):
                    expected_item_ids.append(message_id)
                messages.append(
                    BenchmarkMessage(
                        message_id=message_id,
                        role=str(_first_present(msg, ["role", "speaker"], "user")).lower(),
                        content=str(_first_present(msg, ["content", "text", "utterance", "message"], "")),
                        created_at=_string_or_none(_first_present(msg, ["created_at", "timestamp", "date", "time"], started_at)),
                        metadata={**_as_dict(msg.get("metadata")), "longmemeval_case_id": case_id, "isolation_group": case_id},
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

        explicit_expected = _first_present(case, ["expected_item_ids", "evidence_message_ids", "answer_message_ids"], None)
        if explicit_expected is not None:
            expected_item_ids = [str(item) for item in _as_list(explicit_expected)]
        eval_notes = (
            f"longmemeval_case_id={case_id}; question_date={question_date}; "
            f"haystack_session_ids={','.join(haystack_session_ids)}; "
            f"haystack_dates={','.join(haystack_dates)}; isolation_group={case_id}"
        )
        questions.append(
            BenchmarkQuestion(
                question_id=question_id,
                query=str(_first_present(case, ["question", "query"], "")),
                expected_answer=_first_present(case, ["answer", "expected_answer", "target"], None),
                expected_item_ids=expected_item_ids or None,
                question_type=question_type,
                temporal_hint=question_date,
                evaluation_notes=eval_notes,
            )
        )

    return BenchmarkFixture(
        schema_version=FIXTURE_SCHEMA_VERSION,
        fixture_id=split,
        dataset_name="longmemeval-standard",
        dataset_version=dataset_version,
        contains_private_data=contains_private_data,
        conversations=conversations,
        questions=questions,
    )


def build_longmemeval_case_manifest(
    *,
    input_sha256: Optional[str],
    output_sha256: Optional[str],
    fixture: BenchmarkFixture,
    public_output: bool,
    allow_private_input: bool,
) -> Dict[str, Any]:
    question_type_counts: Dict[str, int] = {}
    message_count = 0
    isolation_groups = set()
    for question in fixture.questions:
        label = question.question_type or "unknown"
        question_type_counts[label] = question_type_counts.get(label, 0) + 1
        try:
            notes = json.loads(question.evaluation_notes or "{}")
            if notes.get("isolation_group"):
                isolation_groups.add(str(notes["isolation_group"]))
        except Exception:
            pass
    for conv in fixture.conversations:
        message_count += len(conv.messages)
        if conv.metadata.get("isolation_group"):
            isolation_groups.add(str(conv.metadata["isolation_group"]))
    return {
        "schema_version": "shyftr-longmemeval-case-manifest/v0",
        "dataset_name": fixture.dataset_name,
        "dataset_version": fixture.dataset_version,
        "fixture_id": fixture.fixture_id,
        "case_count": len(fixture.questions),
        "session_count": len(fixture.conversations),
        "message_count": message_count,
        "question_type_counts": dict(sorted(question_type_counts.items())),
        "isolation_group_count": len(isolation_groups),
        "input_sha256": input_sha256,
        "output_sha256": output_sha256,
        "contains_private_data": bool(fixture.contains_private_data),
        "public_output": bool(public_output),
        "allow_private_input": bool(allow_private_input),
        "claim_limit": "mapping and conversion metadata only; not a full LongMemEval run or performance claim",
        "runner_contract": "future full runs must reset backend state per case unless an experiment explicitly declares shared warm memory",
    }


def load_longmemeval_standard_json(path: Path, *, allow_private_data: bool = False) -> BenchmarkFixture:
    payload = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    fixture = map_longmemeval_standard_payload(payload)
    if fixture.contains_private_data and not allow_private_data:
        raise ValueError(
            "Refusing to load LongMemEval-standard input marked or defaulted contains_private_data=true "
            "(pass allow_private_data=true only for local, non-public runs)"
        )
    return fixture


__all__ = [
    "LONGMEMEVAL_STANDARD_FORMAT",
    "build_longmemeval_case_manifest",
    "load_longmemeval_standard_json",
    "map_longmemeval_standard_payload",
]
