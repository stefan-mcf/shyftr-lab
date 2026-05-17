from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.benchmarks.fixture import resolve_benchmark_fixture
from shyftr.benchmarks.longmemeval_standard import load_longmemeval_standard_json, map_longmemeval_standard_payload
from scripts.convert_longmemeval_standard_fixture import convert_longmemeval_standard_file


def _longmemeval_standard_payload(*, contains_private_data: bool = False) -> dict[str, object]:
    return {
        "dataset_version": "local-schema-smoke",
        "split": "longmemeval-standard-smoke",
        "contains_private_data": contains_private_data,
        "cases": [
            {
                "question_id": "q-1",
                "question_type": "single-session-user",
                "question": "Where did the user put the blue notebook?",
                "answer": "on the kitchen shelf",
                "question_date": "2026-01-02",
                "haystack_session_ids": ["session-1"],
                "haystack_dates": ["2026-01-01"],
                "haystack_sessions": [
                    [
                        {"role": "user", "content": "I keep the blue notebook on the kitchen shelf.", "date": "2026-01-01"},
                        {"role": "assistant", "content": "Noted.", "date": "2026-01-01"},
                    ]
                ],
            }
        ],
    }


def test_longmemeval_standard_payload_maps_to_fixture_contract() -> None:
    fixture = map_longmemeval_standard_payload(_longmemeval_standard_payload())

    assert fixture.dataset_name == "longmemeval-standard"
    assert fixture.dataset_version == "local-schema-smoke"
    assert fixture.fixture_id == "longmemeval-standard-smoke"
    assert fixture.contains_private_data is False
    assert fixture.conversations[0].conversation_id == "session-1"
    assert fixture.conversations[0].messages[0].message_id == "session-1-m-0001"
    assert fixture.conversations[0].messages[0].role == "user"
    assert fixture.questions[0].question_id == "q-1"
    assert fixture.questions[0].expected_answer == "on the kitchen shelf"
    assert fixture.questions[0].question_type == "single-session-user"
    assert "question_date=2026-01-02" in str(fixture.questions[0].evaluation_notes)


def test_longmemeval_standard_loader_rejects_private_by_default(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval-standard.json"
    path.write_text(json.dumps(_longmemeval_standard_payload(contains_private_data=True)), encoding="utf-8")

    with pytest.raises(ValueError, match="contains_private_data=true"):
        load_longmemeval_standard_json(path)

    fixture = load_longmemeval_standard_json(path, allow_private_data=True)
    assert fixture.contains_private_data is True


def test_resolver_loads_longmemeval_standard_format_from_explicit_path(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval-standard.json"
    path.write_text(json.dumps(_longmemeval_standard_payload()), encoding="utf-8")

    fixture = resolve_benchmark_fixture(
        fixture_name="longmemeval-standard",
        fixture_path=path,
        fixture_format="longmemeval-standard",
    )

    assert fixture.dataset_name == "longmemeval-standard"
    assert fixture.questions[0].expected_answer == "on the kitchen shelf"


def test_longmemeval_standard_name_requires_explicit_path() -> None:
    with pytest.raises(ValueError, match="requires --fixture-path"):
        resolve_benchmark_fixture(fixture_name="longmemeval-standard")


def test_converter_writes_guarded_public_fixture(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "longmemeval-standard.json"
    output_path = repo_root / "artifacts" / "benchmarks" / "converted.fixture.json"
    input_path.write_text(json.dumps(_longmemeval_standard_payload()), encoding="utf-8")

    written = convert_longmemeval_standard_file(input_path, output_path, repo_root=repo_root, public_output=True)
    payload = json.loads(written.read_text(encoding="utf-8"))

    assert written == output_path.resolve()
    assert payload["schema_version"] == "shyftr-memory-benchmark-fixture/v0"
    assert payload["dataset_name"] == "longmemeval-standard"
    assert payload["contains_private_data"] is False
    manifest = json.loads(output_path.with_suffix(output_path.suffix + ".manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "shyftr-memory-benchmark-conversion-manifest/v0"
    assert manifest["output_sha256"]
    assert manifest["dataset_name"] == "longmemeval-standard"
    assert manifest["conversation_count"] == 1
    assert manifest["question_count"] == 1


def test_converter_rejects_private_input_without_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "longmemeval-standard.json"
    output_path = repo_root / "tmp" / "converted.fixture.json"
    input_path.write_text(json.dumps(_longmemeval_standard_payload(contains_private_data=True)), encoding="utf-8")

    with pytest.raises(ValueError, match="allow-private-input"):
        convert_longmemeval_standard_file(input_path, output_path, repo_root=repo_root)

    written = convert_longmemeval_standard_file(input_path, output_path, repo_root=repo_root, allow_private_input=True)
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["contains_private_data"] is True


def test_converter_rejects_output_outside_guarded_dirs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "longmemeval-standard.json"
    output_path = repo_root / "fixtures" / "converted.fixture.json"
    input_path.write_text(json.dumps(_longmemeval_standard_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match="outside repo-local"):
        convert_longmemeval_standard_file(input_path, output_path, repo_root=repo_root, public_output=True)
