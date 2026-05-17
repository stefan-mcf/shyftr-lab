from __future__ import annotations

import json
from pathlib import Path

import pytest

from shyftr.benchmarks.beam_standard import load_beam_standard_json, map_beam_standard_payload
from shyftr.benchmarks.fixture import resolve_benchmark_fixture
from scripts.convert_beam_standard_fixture import convert_beam_standard_file


def _beam_payload(*, contains_private_data: bool = False) -> dict[str, object]:
    return {
        "dataset_version": "local-schema-smoke",
        "split": "beam-standard-smoke",
        "contains_private_data": contains_private_data,
        "cases": [
            {
                "question_id": "beam-q-1",
                "ability": "timeline-reasoning",
                "token_bucket": "small-local",
                "question": "Where is the badge?",
                "answer": "desk drawer",
                "messages": [{"role": "user", "content": "The badge is in the desk drawer."}],
            }
        ],
    }


def test_beam_standard_payload_maps_to_fixture_contract() -> None:
    fixture = map_beam_standard_payload(_beam_payload())
    assert fixture.dataset_name == "beam-standard"
    assert fixture.fixture_id == "beam-standard-smoke"
    assert fixture.contains_private_data is False
    assert fixture.questions[0].question_type == "timeline-reasoning"
    assert fixture.questions[0].temporal_hint == "small-local"
    assert fixture.questions[0].expected_item_ids == ["beam-q-1-m0001"]


def test_beam_standard_loader_rejects_private_by_default(tmp_path: Path) -> None:
    path = tmp_path / "beam.json"
    path.write_text(json.dumps(_beam_payload(contains_private_data=True)), encoding="utf-8")
    with pytest.raises(ValueError, match="contains_private_data=true"):
        load_beam_standard_json(path)
    assert load_beam_standard_json(path, allow_private_data=True).contains_private_data is True


def test_resolver_loads_beam_standard_format_from_explicit_path(tmp_path: Path) -> None:
    path = tmp_path / "beam.json"
    path.write_text(json.dumps(_beam_payload()), encoding="utf-8")
    fixture = resolve_benchmark_fixture(fixture_name="beam-standard", fixture_path=path, fixture_format="beam-standard")
    assert fixture.dataset_name == "beam-standard"


def test_beam_standard_name_requires_explicit_path() -> None:
    with pytest.raises(ValueError, match="requires --fixture-path"):
        resolve_benchmark_fixture(fixture_name="beam-standard")


def test_beam_converter_writes_guarded_public_fixture(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "beam.json"
    output_path = repo_root / "artifacts" / "benchmarks" / "beam.fixture.json"
    input_path.write_text(json.dumps(_beam_payload()), encoding="utf-8")
    written = convert_beam_standard_file(input_path, output_path, repo_root=repo_root, public_output=True)
    payload = json.loads(written.read_text(encoding="utf-8"))
    manifest = json.loads(output_path.with_suffix(output_path.suffix + ".manifest.json").read_text(encoding="utf-8"))
    assert payload["dataset_name"] == "beam-standard"
    assert payload["contains_private_data"] is False
    assert manifest["case_manifest"]["ability_counts"]["timeline-reasoning"] == 1


def test_beam_converter_rejects_private_input_without_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "beam.json"
    output_path = repo_root / "tmp" / "beam.fixture.json"
    input_path.write_text(json.dumps(_beam_payload(contains_private_data=True)), encoding="utf-8")
    with pytest.raises(ValueError, match="allow-private-input"):
        convert_beam_standard_file(input_path, output_path, repo_root=repo_root)


def test_beam_converter_rejects_output_outside_guarded_dirs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    input_path = tmp_path / "beam.json"
    output_path = repo_root / "fixtures" / "beam.fixture.json"
    input_path.write_text(json.dumps(_beam_payload()), encoding="utf-8")
    with pytest.raises(ValueError, match="outside repo-local"):
        convert_beam_standard_file(input_path, output_path, repo_root=repo_root, public_output=True)
