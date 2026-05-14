from __future__ import annotations

from shyftr.privacy import redact_charge_projection


def test_redaction_preserves_safe_resource_label_but_hides_sensitive_locator() -> None:
    record = {
        "trace_id": "trace-resource-secret",
        "statement": "Internal deployment evidence artifact.",
        "source_fragment_ids": ["frag-resource-secret"],
        "sensitivity": "secret",
        "resource_ref": {
            "ref_type": "artifact",
            "locator": "/private/teams/customer-a/deployments/release-42.txt",
            "label": "release verification artifact",
        },
        "grounding_refs": ["trace-resource-secret"],
    }

    redacted = redact_charge_projection(record)

    assert redacted["statement"] == "[REDACTED]"
    assert redacted["resource_ref"]["label"] == "release verification artifact"
    assert redacted["resource_ref"]["locator"] == "[REDACTED]"
    assert redacted["grounding_refs"] == ["trace-resource-secret"]
