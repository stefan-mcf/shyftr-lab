"""Tests for ShyftR runtime integration adapter protocols.

Verifies:
- ExternalSourceRef model creation, serialization, and validation.
- SourcePayload model creation, serialization, and embedded refs.
- Round-trip JSON serialization for both models.
- Structural subtyping (duck typing) for SourceAdapter and OutcomeAdapter.
- Error handling for missing required fields.
- Protocol classes are runtime_checkable via isinstance().
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest

from shyftr.integrations import IntegrationAdapterError
from shyftr.integrations.protocols import (
    ExternalSourceRef,
    OutcomeAdapter,
    SourceAdapter,
    SourcePayload,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def assert_round_trips(instance):
    """Verify deterministic dict and JSON round-trip for SerializableModel."""
    as_dict = instance.to_dict()
    assert list(as_dict) == sorted(as_dict)
    restored = type(instance).from_dict(as_dict)
    assert restored == instance
    as_json = instance.to_json()
    assert json.loads(as_json) == as_dict
    assert type(instance).from_json(as_json) == instance


# ── ExternalSourceRef tests ──────────────────────────────────────────────────


class TestExternalSourceRef:
    def test_minimal_ref_is_serializable(self):
        ref = ExternalSourceRef(
            adapter_id="test-adapter",
            external_system="hermes",
            external_scope="worker",
            source_kind="closeout",
        )
        assert ref.adapter_id == "test-adapter"
        assert ref.source_uri is None
        assert ref.source_line_offset is None
        assert ref.external_ids == {}
        assert ref.metadata is None
        assert_round_trips(ref)

    def test_full_ref_with_all_fields(self):
        ref = ExternalSourceRef(
            adapter_id="file-adapter-v1",
            external_system="custom-runtime",
            external_scope="monitor",
            source_kind="log",
            source_uri="/var/log/runtime/worker-1.log",
            source_line_offset=142,
            external_ids={
                "external_run_id": "run-20260424-abc",
                "external_task_id": "task-001",
            },
            metadata={"file_size": 4096, "content_type": "text/plain"},
        )
        assert ref.source_uri == "/var/log/runtime/worker-1.log"
        assert ref.source_line_offset == 142
        assert ref.external_ids["external_run_id"] == "run-20260424-abc"
        assert ref.metadata["file_size"] == 4096
        assert_round_trips(ref)

    def test_required_fields_validation(self):
        with pytest.raises(ValueError, match="adapter_id"):
            ExternalSourceRef(
                adapter_id="",
                external_system="sys",
                external_scope="scope",
                source_kind="kind",
            )
        with pytest.raises(ValueError, match="external_system"):
            ExternalSourceRef(
                adapter_id="id",
                external_system="",
                external_scope="scope",
                source_kind="kind",
            )
        with pytest.raises(ValueError, match="external_scope"):
            ExternalSourceRef(
                adapter_id="id",
                external_system="sys",
                external_scope="",
                source_kind="kind",
            )
        with pytest.raises(ValueError, match="source_kind"):
            ExternalSourceRef(
                adapter_id="id",
                external_system="sys",
                external_scope="scope",
                source_kind="",
            )

    def test_missing_required_field_in_from_dict(self):
        with pytest.raises(ValueError, match="adapter_id"):
            ExternalSourceRef.from_dict({
                "external_system": "sys",
                "external_scope": "scope",
                "source_kind": "kind",
            })

    def test_unknown_field_in_from_dict(self):
        with pytest.raises(ValueError, match="Unknown field"):
            ExternalSourceRef.from_dict({
                "adapter_id": "id",
                "external_system": "sys",
                "external_scope": "scope",
                "source_kind": "kind",
                "nonexistent": True,
            })


# ── SourcePayload tests ──────────────────────────────────────────────────────


class TestSourcePayload:
    def test_minimal_payload_is_serializable(self):
        payload = SourcePayload(
            content_hash="a" * 64,
            kind="text",
        )
        assert payload.content_hash == "a" * 64
        assert payload.kind == "text"
        assert payload.metadata is None
        assert payload.external_refs == []
        assert_round_trips(payload)

    def test_payload_with_external_refs(self):
        ref = ExternalSourceRef(
            adapter_id="test-adapter",
            external_system="hermes",
            external_scope="worker",
            source_kind="closeout",
            source_uri="/tmp/source.md",
            source_line_offset=10,
            external_ids={"external_run_id": "run-001"},
        )
        payload = SourcePayload(
            content_hash="b" * 64,
            kind="markdown",
            metadata={"subject": "task closeout"},
            external_refs=[ref],
        )
        assert len(payload.external_refs) == 1
        assert payload.external_refs[0].adapter_id == "test-adapter"
        assert payload.metadata["subject"] == "task closeout"
        assert_round_trips(payload)

    def test_payload_round_trip_preserves_external_refs(self):
        ref = ExternalSourceRef(
            adapter_id="file-adapter",
            external_system="cli-runtime",
            external_scope="ingest",
            source_kind="jsonl",
            source_uri="/data/outcomes.jsonl",
            source_line_offset=7,
            external_ids={
                "external_run_id": "run-999",
                "external_task_id": "task-888",
            },
        )
        payload = SourcePayload(
            content_hash="c" * 64,
            kind="json",
            external_refs=[ref],
        )
        restored = SourcePayload.from_dict(payload.to_dict())
        assert len(restored.external_refs) == 1
        assert restored.external_refs[0].external_ids == {
            "external_run_id": "run-999",
            "external_task_id": "task-888",
        }

    def test_required_fields_validation(self):
        with pytest.raises(ValueError, match="content_hash"):
            SourcePayload(content_hash="", kind="text")

    def test_missing_required_field_in_from_dict(self):
        with pytest.raises(ValueError, match="content_hash"):
            SourcePayload.from_dict({"kind": "text"})


# ── SourceAdapter protocol tests ─────────────────────────────────────────────


class TestSourceAdapterProtocol:
    def test_concrete_adapter_satisfies_protocol(self):
        """A class implementing SourceAdapter should pass isinstance check."""

        @dataclass
        class ConcreteFileAdapter:
            sources: List[ExternalSourceRef]

            def discover_sources(self) -> List[ExternalSourceRef]:
                return self.sources

            def read_source(self, ref: ExternalSourceRef) -> SourcePayload:
                return SourcePayload(
                    content_hash="d" * 64,
                    kind="text",
                    external_refs=[ref],
                )

            def source_metadata(self, ref: ExternalSourceRef) -> Dict[str, Any]:
                return {"size": 1024, "modified": "2026-04-24T00:00:00Z"}

        ref = ExternalSourceRef(
            adapter_id="concrete",
            external_system="test",
            external_scope="scope",
            source_kind="file",
        )
        adapter = ConcreteFileAdapter(sources=[ref])

        assert isinstance(adapter, SourceAdapter)
        discovered = adapter.discover_sources()
        assert len(discovered) == 1
        assert discovered[0].adapter_id == "concrete"

        payload = adapter.read_source(ref)
        assert payload.content_hash == "d" * 64

        meta = adapter.source_metadata(ref)
        assert meta["size"] == 1024

    def test_incomplete_class_does_not_satisfy_protocol(self):

        class MissingMethods:
            def discover_sources(self) -> List:
                return []

        assert not isinstance(MissingMethods(), SourceAdapter)


# ── OutcomeAdapter protocol tests ────────────────────────────────────────────


class TestOutcomeAdapterProtocol:
    def test_concrete_adapter_satisfies_protocol(self):

        class ConcreteOutcomeReader:
            def discover_outcomes(self) -> List[ExternalSourceRef]:
                ref = ExternalSourceRef(
                    adapter_id="outcome-adapter",
                    external_system="runtime",
                    external_scope="outcomes",
                    source_kind="jsonl",
                    source_uri="/data/outcomes.jsonl",
                )
                return [ref]

            def read_outcome(self, ref: ExternalSourceRef) -> SourcePayload:
                return SourcePayload(
                    content_hash="e" * 64,
                    kind="json",
                    external_refs=[ref],
                )

            def map_outcome(self, payload: SourcePayload) -> Dict[str, Any]:
                return {
                    "verdict": "success",
                    "score": 0.85,
                    "applied_trace_ids": ["trace-001"],
                }

        adapter = ConcreteOutcomeReader()
        assert isinstance(adapter, OutcomeAdapter)

        outcomes = adapter.discover_outcomes()
        assert len(outcomes) == 1
        assert outcomes[0].adapter_id == "outcome-adapter"

        payload = adapter.read_outcome(outcomes[0])
        assert payload.kind == "json"

        mapped = adapter.map_outcome(payload)
        assert mapped["verdict"] == "success"
        assert mapped["score"] == 0.85

    def test_incomplete_class_does_not_satisfy_protocol(self):

        class MissingMapOutcome:
            def discover_outcomes(self) -> List:
                return []

            def read_outcome(self, ref) -> SourcePayload:
                raise NotImplementedError

        assert not isinstance(MissingMapOutcome(), OutcomeAdapter)


# ── IntegrationAdapterError tests ────────────────────────────────────────────


class TestIntegrationAdapterError:
    def test_error_with_message_only(self):
        err = IntegrationAdapterError("source not found")
        assert str(err) == "source not found"
        assert err.details == {}

    def test_error_with_details(self):
        err = IntegrationAdapterError(
            "permission denied",
            details={"path": "/restricted/file", "errno": 13},
        )
        assert err.details["path"] == "/restricted/file"
        assert err.details["errno"] == 13

    def test_is_exception(self):
        assert issubclass(IntegrationAdapterError, Exception)
