from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from shyftr.benchmarks.fixture import FIXTURE_SCHEMA_VERSION, BenchmarkFixture
from shyftr.benchmarks.types import BenchmarkConversation, BenchmarkMessage, BenchmarkQuestion

BEAM_STANDARD_FORMAT = "beam-standard/v0"

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

def _rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [_as_dict(item) for item in payload]
    data = _as_dict(payload)
    return [_as_dict(item) for item in _as_list(_first_present(data, ["cases", "questions", "data", "rows"], []))]

def map_beam_standard_payload(payload: Any) -> BenchmarkFixture:
    data = _as_dict(payload)
    dataset_version = str(_first_present(data, ["dataset_version", "version"], "unknown"))
    split = str(_first_present(data, ["split", "fixture_id"], "beam-standard-local"))
    contains_private_data = bool(_first_present(data, ["contains_private_data"], True))
    conversations: List[BenchmarkConversation] = []
    questions: List[BenchmarkQuestion] = []
    for index, case in enumerate(_rows(payload), start=1):
        case_id = str(_first_present(case, ["case_id", "question_id", "id", "qid"], f"beam-case-{index:04d}"))
        ability = _string_or_none(_first_present(case, ["ability", "ability_type", "question_type", "type"], "beam-local"))
        raw_messages = _as_list(_first_present(case, ["messages", "context", "haystack", "turns"], []))
        messages: List[BenchmarkMessage] = []
        for msg_index, raw_msg in enumerate(raw_messages, start=1):
            msg = _as_dict(raw_msg)
            messages.append(BenchmarkMessage(
                message_id=str(_first_present(msg, ["message_id", "id", "turn_id"], f"{case_id}-m{msg_index:04d}")),
                role=str(_first_present(msg, ["role", "speaker"], "user")).lower(),
                content=str(_first_present(msg, ["content", "text", "utterance", "message"], raw_msg if isinstance(raw_msg, str) else "")),
                created_at=_string_or_none(_first_present(msg, ["created_at", "date", "timestamp"])),
                metadata={**_as_dict(msg.get("metadata")), "beam_case_id": case_id, "beam_ability": ability},
            ))
        if not messages and case.get("context_text"):
            messages.append(BenchmarkMessage(message_id=f"{case_id}-m0001", role="user", content=str(case["context_text"]), metadata={"beam_case_id": case_id, "beam_ability": ability}))
        conversations.append(BenchmarkConversation(
            conversation_id=str(_first_present(case, ["conversation_id", "session_id"], f"{case_id}-conversation")),
            session_id=_string_or_none(_first_present(case, ["session_id"], case_id)),
            started_at=_string_or_none(_first_present(case, ["date", "started_at", "timestamp"])),
            messages=messages,
            metadata={**_as_dict(case.get("metadata")), "beam_case_id": case_id, "beam_ability": ability, "token_bucket": _string_or_none(case.get("token_bucket"))},
        ))
        explicit_expected = _first_present(case, ["expected_item_ids", "evidence_message_ids", "answer_message_ids"], None)
        if explicit_expected is None:
            expected = [messages[0].message_id] if messages else None
        else:
            expected = [str(item) for item in _as_list(explicit_expected)]
        questions.append(BenchmarkQuestion(
            question_id=str(_first_present(case, ["question_id", "qid", "id"], case_id)),
            query=str(_first_present(case, ["question", "query", "prompt"], "")),
            expected_answer=_first_present(case, ["answer", "expected_answer", "target"], None),
            expected_item_ids=expected,
            question_type=ability,
            temporal_hint=_string_or_none(_first_present(case, ["token_bucket", "date"])),
            evaluation_notes=json.dumps({"beam_case_id": case_id, "ability": ability, "token_bucket": _string_or_none(case.get("token_bucket"))}, sort_keys=True),
        ))
    return BenchmarkFixture(FIXTURE_SCHEMA_VERSION, split, "beam-standard", dataset_version, contains_private_data, conversations, questions)

def build_beam_case_manifest(*, input_sha256: Optional[str], output_sha256: Optional[str], fixture: BenchmarkFixture, public_output: bool, allow_private_input: bool) -> Dict[str, Any]:
    ability_counts: Dict[str, int] = {}
    token_buckets: Dict[str, int] = {}
    message_count = sum(len(c.messages) for c in fixture.conversations)
    for q in fixture.questions:
        ability_counts[q.question_type or "unknown"] = ability_counts.get(q.question_type or "unknown", 0) + 1
        if q.temporal_hint:
            token_buckets[q.temporal_hint] = token_buckets.get(q.temporal_hint, 0) + 1
    return {
        "schema_version": "shyftr-beam-case-manifest/v0",
        "dataset_name": fixture.dataset_name,
        "dataset_version": fixture.dataset_version,
        "fixture_id": fixture.fixture_id,
        "case_count": len(fixture.questions),
        "session_count": len(fixture.conversations),
        "message_count": message_count,
        "ability_counts": dict(sorted(ability_counts.items())),
        "token_bucket_counts": dict(sorted(token_buckets.items())),
        "input_sha256": input_sha256,
        "output_sha256": output_sha256,
        "contains_private_data": fixture.contains_private_data,
        "public_output": public_output,
        "allow_private_input": allow_private_input,
        "claim_limit": "mapping and conversion metadata only; not a full BEAM run or performance claim",
    }

def load_beam_standard_json(path: Path, *, allow_private_data: bool = False) -> BenchmarkFixture:
    payload = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    fixture = map_beam_standard_payload(payload)
    if fixture.contains_private_data and not allow_private_data:
        raise ValueError("Refusing to load BEAM-standard input marked or defaulted contains_private_data=true (pass allow_private_data=true only for local, non-public runs)")
    return fixture

__all__ = ["BEAM_STANDARD_FORMAT", "build_beam_case_manifest", "load_beam_standard_json", "map_beam_standard_payload"]
