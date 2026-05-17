from __future__ import annotations

import pytest

from shyftr.models import Episode, ResourceRef


def _make_episode_all_fields(*, status: str = "approved", memory_type: str = "episodic", **overrides) -> Episode:
    payload = dict(
        episode_id="ep_001",
        cell_id="cell_001",
        episode_kind="task",
        title="Fix retrieval regression",
        summary="Investigated failing tests, identified root cause, and patched implementation.",
        started_at="2026-05-16T08:00:00Z",
        ended_at="2026-05-16T08:15:00Z",
        actor="runtime",
        action="run pytest and patch models",
        outcome="success",
        status=status,
        memory_type=memory_type,
        authority="review_gated",
        retention="event_history",
        confidence=0.9,
        sensitivity="internal",
        created_at="2026-05-16T08:16:00Z",
        runtime_id="rt_123",
        session_id="sess_123",
        task_id="task_123",
        tool_name="pytest",
        tool_action="run",
        key_points=["repro", "patch", "verify"],
        failure_signature=None,
        recovery_summary=None,
        parent_episode_id=None,
        related_episode_ids=["ep_000"],
        derived_memory_ids=["mem_01"],
        supersedes_episode_id=None,
        superseded_by_episode_id=None,
        valid_until=None,
        retention_hint=None,
        metadata={"note": "unit-test"},
        live_context_entry_ids=["lc_1"],
        memory_ids=[],
        feedback_ids=[],
        resource_refs=[ResourceRef(ref_type="artifact", locator="file://artifact.txt", label="artifact")],
        grounding_refs=["gr_1"],
        artifact_refs=["art_1"],
    )
    payload.update(overrides)
    return Episode.from_dict(payload)


def test_episode_round_trip_to_dict_from_dict_with_required_fields() -> None:
    episode = _make_episode_all_fields()
    payload = episode.to_dict()
    restored = Episode.from_dict(payload)
    assert restored == episode


def test_episode_rejects_non_episodic_memory_type() -> None:
    with pytest.raises(ValueError):
        _make_episode_all_fields(memory_type="semantic")


def test_episode_rejects_approved_without_any_anchors() -> None:
    with pytest.raises(ValueError):
        Episode(
            episode_id="ep_002",
            cell_id="cell_001",
            episode_kind="task",
            title="No anchors",
            summary="This should not validate.",
            started_at="2026-05-16T08:00:00Z",
            ended_at="2026-05-16T08:10:00Z",
            actor="runtime",
            action="attempt",
            outcome="success",
            status="approved",
            memory_type="episodic",
            confidence=0.5,
            sensitivity="internal",
            created_at="2026-05-16T08:11:00Z",
            live_context_entry_ids=[],
            memory_ids=[],
            feedback_ids=[],
            resource_refs=[],
            grounding_refs=[],
            artifact_refs=[],
        )


def test_episode_rejects_invalid_status() -> None:
    with pytest.raises(ValueError):
        _make_episode_all_fields(status="invalid")


def test_episode_preserves_sensitivity_and_relationship_fields() -> None:
    episode = _make_episode_all_fields()
    restored = Episode.from_dict(episode.to_dict())
    assert restored.sensitivity == "internal"
    assert restored.related_episode_ids == ["ep_000"]
    assert restored.derived_memory_ids == ["mem_01"]


def test_episode_rejects_whitespace_only_approved_required_fields() -> None:
    with pytest.raises(ValueError, match="title is required"):
        _make_episode_all_fields(title="   ")


def test_episode_rejects_invalid_outcome_or_kind() -> None:
    with pytest.raises(ValueError):
        Episode(
            episode_id="ep_003",
            cell_id="cell_001",
            episode_kind="not_a_kind",
            status="proposed",
            memory_type="episodic",
            created_at="2026-05-16T08:16:00Z",
        )

    with pytest.raises(ValueError):
        Episode(
            episode_id="ep_004",
            cell_id="cell_001",
            episode_kind="task",
            status="approved",
            memory_type="episodic",
            created_at="2026-05-16T08:16:00Z",
            title="Bad outcome",
            summary="",
            started_at="2026-05-16T08:00:00Z",
            ended_at="2026-05-16T08:10:00Z",
            actor="runtime",
            action="attempt",
            outcome="not_an_outcome",
            confidence=0.5,
            sensitivity="internal",
            live_context_entry_ids=["lc"],
        )
