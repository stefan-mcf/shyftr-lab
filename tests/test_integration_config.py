"""Tests for ShyftR runtime adapter config schema and validation.

Verifies:
- InputDefinition model creation and field validation.
- RuntimeAdapterConfig model creation and field validation.
- Config loading from JSON (stdlib path).
- Config loading from YAML (only if PyYAML is available).
- Config validation: input kinds, source kind mappings, identity
  mappings, ingest options, path constraints.
- Error cases: missing fields, invalid values, path escape.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from shyftr.integrations import IntegrationAdapterError
from shyftr.integrations.config import (
    ALLOWED_INPUT_KINDS,
    ConfigValidationError,
    InputDefinition,
    RuntimeAdapterConfig,
    VALID_EXTERNAL_ID_FIELDS,
    VALID_INGEST_OPTIONS,
    VALID_SOURCE_KINDS,
    load_config,
    validate_config,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_json_config(data: Dict[str, Any], suffix: str = ".json") -> str:
    """Write a temporary config file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False
    )
    json.dump(data, tmp)
    tmp.close()
    return tmp.name


def _make_minimal_config(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    config = {
        "adapter_id": "test-adapter",
        "cell_id": "cell-main",
        "external_system": "generic-runtime",
        "external_scope": "execution-scope",
        "source_root": "/tmp/shyftr-sources",
        "inputs": [
            {
                "kind": "glob",
                "path": "*.md",
                "source_kind": "closeout",
            },
        ],
    }
    if overrides:
        config.update(overrides)
    return config


# ── InputDefinition tests ─────────────────────────────────────────────────────


class TestInputDefinition:
    def test_minimal_input(self):
        inp = InputDefinition(kind="file", path="output.json", source_kind="log")
        assert inp.kind == "file"
        assert inp.path == "output.json"
        assert inp.source_kind == "log"
        assert inp.identity_mapping == {}

    def test_input_with_identity_mapping(self):
        inp = InputDefinition(
            kind="jsonl",
            path="outcomes.jsonl",
            source_kind="outcome",
            identity_mapping={"external_run_id": "run_id"},
        )
        assert inp.identity_mapping["external_run_id"] == "run_id"

    def test_input_accepts_all_valid_kinds(self):
        for kind in ("file", "glob", "jsonl", "directory"):
            inp = InputDefinition(kind=kind, path="x", source_kind="log")
            assert inp.kind == kind

    def test_input_fields_are_immutable(self):
        inp = InputDefinition(kind="file", path="x", source_kind="log")
        with pytest.raises(Exception):  # frozen dataclass
            inp.kind = "glob"  # type: ignore[misc]


# ── RuntimeAdapterConfig tests ────────────────────────────────────────────────


class TestRuntimeAdapterConfig:
    def test_minimal_config(self):
        inp = InputDefinition(kind="glob", path="*.md", source_kind="closeout")
        config = RuntimeAdapterConfig(
            adapter_id="a1",
            cell_id="c1",
            external_system="generic-runtime",
            external_scope="execution-scope",
            source_root="/data/sources",
            inputs=[inp],
        )
        assert config.adapter_id == "a1"
        assert config.cell_id == "c1"
        assert config.identity_mapping == {}
        assert config.ingest_options == {}

    def test_config_with_all_fields(self):
        inp = InputDefinition(
            kind="jsonl",
            path="events.jsonl",
            source_kind="log",
            identity_mapping={"external_run_id": "trace_id"},
        )
        config = RuntimeAdapterConfig(
            adapter_id="full-adapter",
            cell_id="cell-alpha",
            external_system="custom-runtime",
            external_scope="monitor",
            source_root="/opt/runtime/data",
            inputs=[inp],
            identity_mapping={
                "external_system": "system_name",
                "external_task_id": "task_id",
            },
            ingest_options={
                "deduplicate": True,
                "max_sources": 1000,
                "recursive": True,
            },
        )
        assert config.adapter_id == "full-adapter"
        assert config.ingest_options["max_sources"] == 1000
        assert len(config.inputs) == 1

    def test_config_multiple_inputs(self):
        inputs = [
            InputDefinition(kind="file", path="output.md", source_kind="closeout"),
            InputDefinition(kind="glob", path="logs/*.log", source_kind="log"),
            InputDefinition(
                kind="jsonl", path="outcomes.jsonl", source_kind="outcome"
            ),
            InputDefinition(
                kind="directory", path="artifacts/", source_kind="artifact"
            ),
        ]
        config = RuntimeAdapterConfig(
            adapter_id="multi",
            cell_id="c1",
            external_system="test",
            external_scope="scope",
            source_root="/tmp",
            inputs=inputs,
        )
        assert len(config.inputs) == 4
        assert config.inputs[1].kind == "glob"

    def test_config_fields_are_immutable(self):
        inp = InputDefinition(kind="file", path="x", source_kind="log")
        config = RuntimeAdapterConfig(
            adapter_id="a",
            cell_id="c",
            external_system="s",
            external_scope="sc",
            source_root="/r",
            inputs=[inp],
        )
        with pytest.raises(Exception):
            config.adapter_id = "new"  # type: ignore[misc]


# ── Config loading (JSON) ─────────────────────────────────────────────────────


class TestLoadConfig:
    def test_load_minimal_json(self):
        data = _make_minimal_config()
        path = _write_json_config(data)
        try:
            config = load_config(path)
            assert config.adapter_id == "test-adapter"
            assert config.external_system == "generic-runtime"
            assert len(config.inputs) == 1
            assert config.inputs[0].kind == "glob"
        finally:
            os.unlink(path)

    def test_load_full_json(self):
        data = _make_minimal_config({
            "identity_mapping": {
                "external_system": "system_name",
                "external_run_id": "run_id",
            },
            "ingest_options": {
                "deduplicate": True,
                "max_sources": 500,
            },
        })
        path = _write_json_config(data)
        try:
            config = load_config(path)
            assert config.identity_mapping["external_system"] == "system_name"
            assert config.ingest_options["max_sources"] == 500
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("/tmp/nonexistent-config-12345.json")

    def test_load_not_a_dict(self):
        data = ["not", "a", "dict"]
        path = _write_json_config(data)
        try:
            with pytest.raises(ConfigValidationError, match="mapping"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_load_missing_required_top_level_field(self):
        data = _make_minimal_config({"adapter_id": None})
        del data["adapter_id"]
        path = _write_json_config(data)
        try:
            with pytest.raises(ConfigValidationError, match="adapter_id"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_load_empty_inputs_list(self):
        data = _make_minimal_config({"inputs": []})
        path = _write_json_config(data)
        try:
            with pytest.raises(
                ConfigValidationError, match="At least one input"
            ):
                load_config(path)
        finally:
            os.unlink(path)

    def test_load_inputs_not_a_list(self):
        data = _make_minimal_config({"inputs": "not-a-list"})
        path = _write_json_config(data)
        try:
            with pytest.raises(ConfigValidationError, match="inputs.*list"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_load_input_missing_fields(self):
        data = _make_minimal_config({
            "inputs": [{"kind": "file"}]  # missing path, source_kind
        })
        path = _write_json_config(data)
        try:
            with pytest.raises(ConfigValidationError, match="missing required"):
                load_config(path)
        finally:
            os.unlink(path)


# ── Config validation ─────────────────────────────────────────────────────────


class TestValidateConfig:
    def test_valid_config_passes(self):
        inp = InputDefinition(kind="file", path="x.md", source_kind="closeout")
        config = RuntimeAdapterConfig(
            adapter_id="a",
            cell_id="c",
            external_system="s",
            external_scope="sc",
            source_root="/tmp",
            inputs=[inp],
        )
        validate_config(config)  # should not raise

    def test_invalid_input_kind(self):
        inp = InputDefinition(kind="badger", path="x", source_kind="log")
        config = _base_config(inputs=[inp])
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("badger" in e for e in errors)
        assert any("file" in e or "glob" in e for e in errors)

    def test_input_source_kind_unrecognised(self):
        inp = InputDefinition(
            kind="file", path="x.md", source_kind="invalid_kind_xyz"
        )
        config = _base_config(inputs=[inp])
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("invalid_kind_xyz" in e for e in errors)

    def test_input_source_kind_recognised_values(self):
        for kind in VALID_SOURCE_KINDS:
            inp = InputDefinition(kind="file", path="x", source_kind=kind)
            config = _base_config(inputs=[inp])
            validate_config(config)  # should not raise

    def test_empty_source_kind(self):
        inp = InputDefinition(kind="file", path="x", source_kind="   ")
        config = _base_config(inputs=[inp])
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("source_kind" in e for e in errors)

    def test_identity_mapping_unknown_key(self):
        inp = InputDefinition(kind="file", path="x", source_kind="log")
        config = RuntimeAdapterConfig(
            adapter_id="a",
            cell_id="c",
            external_system="s",
            external_scope="sc",
            source_root="/tmp",
            inputs=[inp],
            identity_mapping={"unknown_field": "value"},
        )
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("unknown_field" in e for e in errors)

    def test_identity_mapping_per_input_unknown_key(self):
        inp = InputDefinition(
            kind="file",
            path="x",
            source_kind="log",
            identity_mapping={"bad_key": "val"},
        )
        config = _base_config(inputs=[inp])
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("bad_key" in e for e in errors)

    def test_valid_identity_mapping_keys(self):
        inp = InputDefinition(kind="file", path="x", source_kind="log")
        config = RuntimeAdapterConfig(
            adapter_id="a",
            cell_id="c",
            external_system="s",
            external_scope="sc",
            source_root="/tmp",
            inputs=[inp],
            identity_mapping={
                "external_system": "sys",
                "external_scope": "scope",
                "external_run_id": "run_id",
                "external_task_id": "task_id",
                "external_trace_id": "trace_id",
                "external_session_id": "session_id",
            },
        )
        validate_config(config)  # should not raise

    def test_ingest_options_unknown_key(self):
        inp = InputDefinition(kind="file", path="x", source_kind="log")
        config = RuntimeAdapterConfig(
            adapter_id="a",
            cell_id="c",
            external_system="s",
            external_scope="sc",
            source_root="/tmp",
            inputs=[inp],
            ingest_options={"nonexistent_option": True},
        )
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("nonexistent_option" in e for e in errors)

    def test_ingest_options_known_keys(self):
        inp = InputDefinition(kind="file", path="x", source_kind="log")
        config = RuntimeAdapterConfig(
            adapter_id="a",
            cell_id="c",
            external_system="s",
            external_scope="sc",
            source_root="/tmp",
            inputs=[inp],
            ingest_options={
                "deduplicate": True,
                "dry_run": False,
                "max_sources": 100,
                "include_hidden": False,
                "recursive": True,
            },
        )
        validate_config(config)  # should not raise


# ── Path validation ───────────────────────────────────────────────────────────


class TestPathValidation:
    def test_relative_path_is_allowed(self):
        inp = InputDefinition(kind="file", path="relative/path.md", source_kind="log")
        config = _base_config(source_root="/tmp", inputs=[inp])
        validate_config(config)

    def test_absolute_path_under_source_root_is_allowed(self):
        under = os.path.join("/tmp", "shyftr-test-subdir")
        try:
            os.makedirs(under, exist_ok=True)
            inp = InputDefinition(
                kind="file",
                path=under,
                source_kind="log",
            )
            config = _base_config(
                source_root="/tmp", inputs=[inp]
            )
            validate_config(config)
        finally:
            if os.path.isdir(under):
                os.rmdir(under)

    def test_absolute_path_outside_source_root_blocked(self):
        inp = InputDefinition(
            kind="file", path="/etc/passwd", source_kind="log"
        )
        config = _base_config(source_root="/tmp", inputs=[inp])
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("outside allowed roots" in e for e in errors)
        assert any("/etc/passwd" in e for e in errors)

    def test_absolute_path_allowed_explicit_allowed_root(self):
        inp = InputDefinition(
            kind="file", path="/opt/external/data/log.md", source_kind="log"
        )
        config = RuntimeAdapterConfig(
            adapter_id="a",
            cell_id="c",
            external_system="s",
            external_scope="sc",
            source_root="/tmp",
            inputs=[inp],
            ingest_options={"allowed_roots": ["/opt/external/data"]},
        )
        validate_config(config)

    def test_multiple_inputs_some_blocked(self):
        good = InputDefinition(kind="file", path="relative/log.md", source_kind="log")
        bad = InputDefinition(kind="file", path="/etc/shadow", source_kind="log")
        config = _base_config(source_root="/tmp", inputs=[good, bad])
        with pytest.raises(ConfigValidationError) as exc:
            validate_config(config)
        errors = exc.value.details["errors"]
        assert any("/etc/shadow" in e for e in errors)


# ── ConfigValidationError ─────────────────────────────────────────────────────


class TestConfigValidationError:
    def test_is_integration_adapter_error(self):
        assert issubclass(ConfigValidationError, IntegrationAdapterError)

    def test_error_with_message(self):
        err = ConfigValidationError("bad config")
        assert str(err) == "bad config"

    def test_error_with_details(self):
        err = ConfigValidationError(
            "validation failed",
            details={"errors": ["path blocked", "bad kind"]},
        )
        assert "path blocked" in str(err.details["errors"])

    def test_default_details(self):
        err = ConfigValidationError("oops")
        assert err.details == {}


# ── Constants and module exports ──────────────────────────────────────────────


class TestConstants:
    def test_allowed_input_kinds(self):
        assert sorted(ALLOWED_INPUT_KINDS) == ["directory", "file", "glob", "jsonl"]

    def test_valid_source_kinds(self):
        assert "closeout" in VALID_SOURCE_KINDS
        assert "log" in VALID_SOURCE_KINDS
        assert "outcome" in VALID_SOURCE_KINDS
        assert "artifact" in VALID_SOURCE_KINDS

    def test_valid_external_id_fields(self):
        assert "external_run_id" in VALID_EXTERNAL_ID_FIELDS
        assert "external_task_id" in VALID_EXTERNAL_ID_FIELDS
        assert "external_system" in VALID_EXTERNAL_ID_FIELDS

    def test_valid_ingest_options(self):
        assert "deduplicate" in VALID_INGEST_OPTIONS
        assert "max_sources" in VALID_INGEST_OPTIONS
        assert "recursive" in VALID_INGEST_OPTIONS


# ── Private helpers ───────────────────────────────────────────────────────────


def _base_config(
    adapter_id: str = "test",
    cell_id: str = "c1",
    external_system: str = "test-runtime",
    external_scope: str = "scope",
    source_root: str = "/tmp",
    inputs=None,
) -> RuntimeAdapterConfig:
    if inputs is None:
        inputs = [
            InputDefinition(kind="file", path="x.md", source_kind="closeout")
        ]
    return RuntimeAdapterConfig(
        adapter_id=adapter_id,
        cell_id=cell_id,
        external_system=external_system,
        external_scope=external_scope,
        source_root=source_root,
        inputs=inputs,
    )
