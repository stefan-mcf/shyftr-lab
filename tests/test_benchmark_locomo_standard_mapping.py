from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.benchmarks.fixture import resolve_benchmark_fixture
from shyftr.benchmarks.locomo_standard import load_locomo_standard_json, map_locomo_standard_payload
from scripts.convert_locomo_standard_fixture import convert_locomo_standard_file


def _locomo_standard_payload(*, contains_private_data: bool = False) -> dict[str, object]:
    return {
        "dataset_version": "local-schema-smoke",
        "split": "locomo-standard-smoke",
        "contains_private_data": contains_private_data,
        "conversations": [
            {
                "session_id": "session-1",
                "started_at": "2026-01-01T00:00:00Z",
                "messages": [
                    {
                        "turn_id": "turn-1",
                        "speaker": "user",
                        "text": "I keep the blue notebook on the kitchen shelf.",
                        "timestamp": "2026-01-01T00:01:00Z",
                    },
                    {
                        "turn_id": "turn-2",
                        "speaker": "assistant",
                        "text": "Noted.",
                    },
                ],
            }
        ],
        "questions": [
            {
                "qa_id": "qa-1",
                "question": "Where is the blue notebook?",
                "answer": "on the kitchen shelf",
                "evidence_message_ids": ["turn-1"],
                "category": "single-hop",
                "session_id": "session-1",
            }
        ],
    }


def test_locomo_standard_payload_maps_to_fixture_contract() -> None:
    fixture = map_locomo_standard_payload(_locomo_standard_payload())

    assert fixture.dataset_name == "locomo-standard"
    assert fixture.dataset_version == "local-schema-smoke"
    assert fixture.fixture_id == "locomo-standard-smoke"
    assert fixture.contains_private_data is False
    assert fixture.conversations[0].conversation_id == "session-1"
    assert fixture.conversations[0].messages[0].message_id == "turn-1"
    assert fixture.conversations[0].messages[0].role == "user"
    assert fixture.questions[0].question_id == "qa-1"
    assert fixture.questions[0].expected_item_ids == ["turn-1"]
    assert fixture.questions[0].question_type == "single-hop"


def test_locomo_standard_loader_rejects_private_by_default(tmp_path: Path) -> None:
    path = tmp_path / "locomo-standard.json"
    path.write_text(json.dumps(_locomo_standard_payload(contains_private_data=True)), encoding="utf-8")

    with pytest.raises(ValueError, match="contains_private_data=true"):
        load_locomo_standard_json(path)

    fixture = load_locomo_standard_json(path, allow_private_data=True)
    assert fixture.contains_private_data is True


def test_resolver_loads_locomo_standard_format_from_explicit_path(tmp_path: Path) -> None:
    path = tmp_path / "locomo-standard.json"
    path.write_text(json.dumps(_locomo_standard_payload()), encoding="utf-8")

    fixture = resolve_benchmark_fixture(
        fixture_name="locomo-standard",
        fixture_path=path,
        fixture_format="locomo-standard",
    )

    assert fixture.dataset_name == "locomo-standard"
    assert fixture.questions[0].expected_answer == "on the kitchen shelf"


def test_locomo_standard_name_requires_explicit_path() -> None:
    with pytest.raises(ValueError, match="requires --fixture-path"):
        resolve_benchmark_fixture(fixture_name="locomo-standard")


def test_converter_writes_guarded_public_fixture(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "locomo-standard.json"
    output_path = repo_root / "artifacts" / "benchmarks" / "converted.fixture.json"
    input_path.write_text(json.dumps(_locomo_standard_payload()), encoding="utf-8")

    written = convert_locomo_standard_file(input_path, output_path, repo_root=repo_root, public_output=True)
    payload = json.loads(written.read_text(encoding="utf-8"))

    assert written == output_path.resolve()
    assert payload["schema_version"] == "shyftr-memory-benchmark-fixture/v0"
    assert payload["dataset_name"] == "locomo-standard"
    assert payload["contains_private_data"] is False
    assert payload["questions"][0]["expected_item_ids"] == ["turn-1"]


def test_converter_rejects_private_input_without_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "locomo-standard.json"
    output_path = repo_root / "tmp" / "converted.fixture.json"
    input_path.write_text(json.dumps(_locomo_standard_payload(contains_private_data=True)), encoding="utf-8")

    with pytest.raises(ValueError, match="allow-private-input"):
        convert_locomo_standard_file(input_path, output_path, repo_root=repo_root)

    written = convert_locomo_standard_file(input_path, output_path, repo_root=repo_root, allow_private_input=True)
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["contains_private_data"] is True


def test_converter_rejects_output_outside_guarded_dirs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "locomo-standard.json"
    output_path = repo_root / "fixtures" / "converted.fixture.json"
    input_path.write_text(json.dumps(_locomo_standard_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match="outside repo-local"):
        convert_locomo_standard_file(input_path, output_path, repo_root=repo_root, public_output=True)
