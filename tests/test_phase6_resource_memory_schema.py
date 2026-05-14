from __future__ import annotations

from shyftr.models import Trace, ResourceRef, ResourceSpan


def test_trace_round_trips_typed_resource_ref_and_grounding_refs():
    trace = Trace.from_dict(
        {
            "trace_id": "trace-resource-1",
            "cell_id": "cell-alpha",
            "statement": "Release closeout is grounded in the canonical handoff artifact.",
            "source_fragment_ids": ["frag-1"],
            "kind": "tool_quirk",
            "memory_type": "resource",
            "resource_ref": {
                "ref_type": "file",
                "locator": "/synthetic/artifacts/closeout.md",
                "label": "Phase closeout markdown",
                "span": {"start_line": 10, "end_line": 24},
                "content_digest": "sha256:abc123",
                "captured_at": "2026-05-15T08:00:00+00:00",
                "origin": "pytest",
                "mime_type": "text/markdown",
                "size_bytes": 512,
            },
            "grounding_refs": ["trace-supporting-1", "file:/synthetic/support.md"],
            "sensitivity": "internal",
            "retention_hint": "durable_reference",
        }
    )

    assert isinstance(trace.resource_ref, ResourceRef)
    assert trace.resource_ref.ref_type == "file"
    assert trace.resource_ref.locator == "/synthetic/artifacts/closeout.md"
    assert trace.resource_ref.label == "Phase closeout markdown"
    assert trace.resource_ref.span == ResourceSpan(start_line=10, end_line=24)
    assert trace.grounding_refs == ["trace-supporting-1", "file:/synthetic/support.md"]
    assert trace.sensitivity == "internal"
    assert trace.retention_hint == "durable_reference"
    assert Trace.from_dict(trace.to_dict()) == trace


def test_trace_accepts_grounding_refs_without_resource_ref_for_semantic_memory():
    trace = Trace.from_dict(
        {
            "trace_id": "trace-grounded-semantic",
            "cell_id": "cell-alpha",
            "statement": "Deployment checklist references the canonical runbook.",
            "source_fragment_ids": ["frag-2"],
            "kind": "preference",
            "grounding_refs": ["trace-resource-1"],
        }
    )

    assert trace.memory_type == "semantic"
    assert trace.resource_ref is None
    assert trace.grounding_refs == ["trace-resource-1"]
    assert Trace.from_dict(trace.to_dict()) == trace


def test_trace_rejects_resource_memory_without_locator_backed_ref():
    try:
        Trace.from_dict(
            {
                "trace_id": "trace-invalid-resource",
                "cell_id": "cell-alpha",
                "statement": "Blob-like content with no stable handle.",
                "source_fragment_ids": ["frag-3"],
                "kind": "tool_quirk",
                "memory_type": "resource",
                "resource_ref": {"ref_type": "file", "label": "Missing locator"},
            }
        )
    except ValueError as exc:
        assert "locator" in str(exc)
    else:
        raise AssertionError("resource Trace should reject resource_ref without locator")
