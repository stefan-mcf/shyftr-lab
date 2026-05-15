from __future__ import annotations

from shyftr.privacy import redact_charge_projection


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
