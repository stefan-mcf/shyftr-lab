import pytest

from shyftr.policy import BoundaryPolicyError, check_source_boundary


def test_boundary_policy_accepts_durable_lessons():
    text = "When pytest temp directories fail, check disk headroom before debugging test logic."

    result = check_source_boundary(text, metadata={"origin": "reviewed lesson"})

    assert result.accepted is True
    assert result.status == "accepted"
    assert result.reasons == []


@pytest.mark.parametrize(
    "text",
    [
        "Queue item dmq-123 is in_progress with worker_summary running 1.",
        "Current branch task/foo and worktree /tmp/project/SANDBOX/active/foo are ready.",
        "Use artifact path /example/operator/example-runtime/local-runtime/artifacts/dev_manager_pods/worker-artifacts/x.log as memory.",
        "Completion log: task completed successfully at 12:03; save this closeout.",
        "Tests passed and verification is complete, but no evidence is attached.",
    ],
)
def test_boundary_policy_rejects_operational_pollution(text):
    result = check_source_boundary(text)

    assert result.accepted is False
    assert result.status == "rejected"
    assert result.reasons


def test_boundary_policy_raises_for_rejected_source_when_requested():
    with pytest.raises(BoundaryPolicyError):
        check_source_boundary("Queue status: pending_manager_pickup", raise_on_reject=True)


def test_boundary_policy_checks_metadata_values():
    result = check_source_boundary(
        "A durable lesson may be polluted by metadata.",
        metadata={"artifact_path": "/example/operator/example-runtime/local-runtime/artifacts/file.log"},
    )

    assert result.accepted is False
    assert "artifact_path" in " ".join(result.reasons)
