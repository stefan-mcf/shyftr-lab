from __future__ import annotations

import json

from shyftr.layout import init_cell
from shyftr.loadout import LoadoutTaskInput, assemble_loadout
from shyftr.privacy import AccessPolicy, filter_charge_records, redact_charge_projection


def _append_secret_resource_trace(cell_path, trace_id: str = "trace-resource-secret") -> dict:
    record = {
        "trace_id": trace_id,
        "cell_id": "phase7-privacy-cell",
        "statement": "Internal deployment evidence artifact.",
        "source_fragment_ids": ["frag-resource-secret"],
        "status": "approved",
        "kind": "tool_quirk",
        "memory_type": "resource",
        "confidence": 0.82,
        "tags": ["artifact", "secret"],
        "sensitivity": "secret",
        "user_id": "reviewer-1",
        "project_id": "shyftr",
        "runtime_id": "runtime-a",
        "resource_ref": {
            "ref_type": "artifact",
            "locator": "/private/teams/customer-a/deployments/release-42.txt",
            "label": "release verification artifact",
            "content_digest": "sha256:abc123",
            "origin": "pytest",
            "span": {"start_line": 4, "end_line": 9},
        },
        "metadata": {
            "uri": "s3://private-bucket/customer-a/release-42.txt",
            "path": "/private/teams/customer-a/deployments/release-42.txt",
            "safe_display": "release verification artifact",
        },
        "grounding_refs": [trace_id],
        "retention_hint": "durable_reference",
    }
    ledger = cell_path / "traces" / "approved.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def test_redaction_hides_nested_sensitive_resource_metadata_but_keeps_safe_fields() -> None:
    record = {
        "trace_id": "trace-resource-secret",
        "statement": "Internal deployment evidence artifact.",
        "source_fragment_ids": ["frag-resource-secret"],
        "sensitivity": "secret",
        "resource_ref": {
            "ref_type": "artifact",
            "locator": "/private/teams/customer-a/deployments/release-42.txt",
            "label": "release verification artifact",
            "content_digest": "sha256:abc123",
            "origin": "pytest",
            "span": {"start_line": 4, "end_line": 9},
        },
        "metadata": {
            "uri": "s3://private-bucket/customer-a/release-42.txt",
            "path": "/private/teams/customer-a/deployments/release-42.txt",
            "safe_display": "release verification artifact",
        },
        "grounding_refs": ["trace-resource-secret"],
    }

    redacted = redact_charge_projection(record)

    assert redacted["statement"] == "[REDACTED]"
    assert redacted["resource_ref"]["label"] == "release verification artifact"
    assert redacted["resource_ref"]["locator"] == "[REDACTED]"
    assert redacted["resource_ref"]["content_digest"] == "[REDACTED]"
    assert redacted["resource_ref"]["origin"] == "pytest"
    assert redacted["metadata"]["uri"] == "[REDACTED]"
    assert redacted["metadata"]["path"] == "[REDACTED]"
    assert redacted["metadata"]["safe_display"] == "release verification artifact"
    assert redacted["grounding_refs"] == ["trace-resource-secret"]


def test_filter_charge_records_keeps_same_redaction_for_allowed_secret_rows() -> None:
    record = {
        "trace_id": "trace-resource-secret",
        "statement": "Internal deployment evidence artifact.",
        "source_fragment_ids": ["frag-resource-secret"],
        "sensitivity": "secret",
        "user_id": "reviewer-1",
        "project_id": "shyftr",
        "runtime_id": "runtime-a",
        "resource_ref": {
            "ref_type": "artifact",
            "locator": "/private/teams/customer-a/deployments/release-42.txt",
            "label": "release verification artifact",
            "content_digest": "sha256:abc123",
            "origin": "pytest",
        },
        "metadata": {
            "uri": "s3://private-bucket/customer-a/release-42.txt",
            "path": "/private/teams/customer-a/deployments/release-42.txt",
            "safe_display": "release verification artifact",
        },
        "grounding_refs": ["trace-resource-secret"],
    }
    policy = AccessPolicy(
        runtime_id="runtime-a",
        user_id="reviewer-1",
        project_id="shyftr",
        allowed_sensitivity=("public", "internal", "secret"),
    )

    projection = filter_charge_records("/tmp/phase7-privacy-cell", [record], policy)

    assert len(projection["included"]) == 1
    included = projection["included"][0]
    assert included["statement"] == "[REDACTED]"
    assert included["resource_ref"]["locator"] == "[REDACTED]"
    assert included["resource_ref"]["label"] == "release verification artifact"
    assert included["metadata"]["uri"] == "[REDACTED]"
    assert included["metadata"]["safe_display"] == "release verification artifact"


def test_pack_includes_allowed_secret_resource_with_redacted_projection_payload(tmp_path) -> None:
    cell = init_cell(tmp_path, "phase7-privacy-cell")
    _append_secret_resource_trace(cell)

    loadout = assemble_loadout(LoadoutTaskInput(
        cell_path=str(cell),
        query="release verification artifact",
        task_id="phase7-pack-secret",
        max_items=5,
        runtime_id="runtime-a",
        user_id="reviewer-1",
        project_id="shyftr",
        allowed_sensitivity=["public", "internal", "secret"],
    ))

    assert [item.item_id for item in loadout.items] == ["trace-resource-secret"]
    item = loadout.items[0]
    assert item.statement == "[REDACTED]"
    assert item.resource_ref is not None
    assert item.resource_ref["locator"] == "[REDACTED]"
    assert item.resource_ref["label"] == "release verification artifact"
    score_resource_ref = item.score_trace.get("resource_ref")
    assert score_resource_ref is not None
    assert score_resource_ref["locator"] == "[REDACTED]"
    assert score_resource_ref["label"] == "release verification artifact"
