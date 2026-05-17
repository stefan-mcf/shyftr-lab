from __future__ import annotations

from pathlib import Path

from shyftr.episodes import append_episode, approve_episode, search_episode_capsules
from shyftr.layout import init_cell
from shyftr.models import Episode
from shyftr.pack import LoadoutTaskInput, assemble_pack
from shyftr.provider.memory import remember, search


def _episode(
    *,
    episode_id: str = "episode-1",
    status: str = "approved",
    sensitivity: str = "internal",
    title: str = "Previous importer failure",
    summary: str = "The previous importer attempt failed, recovered with a bounded retry, and produced artifact evidence.",
) -> Episode:
    return Episode(
        episode_id=episode_id,
        cell_id="core",
        episode_kind="incident",
        title=title,
        summary=summary,
        started_at="2026-05-16T00:00:00+00:00",
        ended_at="2026-05-16T00:10:00+00:00",
        actor="runtime-test",
        action="run_importer",
        outcome="partial",
        status=status,
        confidence=0.86,
        sensitivity=sensitivity,
        created_at="2026-05-16T00:11:00+00:00",
        live_context_entry_ids=["live-1"],
        grounding_refs=["grounding-1"],
        artifact_refs=["artifact-1"],
    )


def _cell(tmp_path: Path) -> Path:
    return init_cell(tmp_path, "core", cell_type="memory")


def test_provider_search_explicit_episodic_returns_approved_anchored_episode(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode())

    results = search(cell, "importer", memory_types=["episodic"])

    assert [result.memory_id for result in results] == ["episode-1"]
    assert results[0].memory_type == "episodic"
    assert results[0].selection_rationale == "explicit_episodic"
    assert results[0].provenance["episode_id"] == "episode-1"
    assert results[0].provenance["anchors"]["live_context_entry_ids"] == ["live-1"]


def test_provider_search_explicit_episodic_filters_unrelated_episode(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode(episode_id="episode-importer"))
    approve_episode(
        cell,
        _episode(
            episode_id="episode-billing",
            title="Previous billing review",
            summary="The previous billing review completed with invoice evidence.",
        ),
    )

    results = search(cell, "importer", memory_types=["episodic"], top_k=5)

    assert [result.memory_id for result in results] == ["episode-importer"]


def test_provider_search_does_not_include_episodes_for_normal_semantic_query(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode())
    semantic = remember(cell, "User prefers local-first importer summaries.", "preference")

    results = search(cell, "importer summaries", memory_types=["semantic"])

    assert [result.memory_id for result in results] == [semantic.memory_id]
    assert all(result.memory_id != "episode-1" for result in results)


def test_provider_search_respects_explicit_non_episode_filters_on_history_query(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode())
    semantic = remember(cell, "User prefers local-first importer failure summaries.", "preference")

    semantic_results = search(cell, "previous importer failure", memory_types=["semantic"])
    kind_results = search(cell, "previous importer failure", kinds=["preference"])

    assert [result.memory_id for result in semantic_results] == [semantic.memory_id]
    assert [result.memory_id for result in kind_results] == [semantic.memory_id]


def test_provider_search_does_not_backfill_episodes_for_unrelated_explicit_kind(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode())

    results = search(cell, "previous importer failure", kinds=["preference"])

    assert results == []


def test_provider_search_respects_non_episode_memory_type_even_with_episode_kind_filter(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode())

    results = search(cell, "previous importer failure", memory_types=["semantic"], kinds=["incident"])

    assert results == []


def test_provider_search_keeps_archived_and_redacted_episodes_inspectable(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    archived_base = _episode(episode_id="episode-lifecycle-archived", title="Lifecycle incident", summary="Archivedprose")
    redacted_base = _episode(episode_id="episode-lifecycle-redacted", title="Lifecycle incident", summary="Secretprose")
    approve_episode(cell, archived_base)
    append_episode(cell, Episode.from_dict({**archived_base.to_dict(), "status": "archived", "created_at": "2026-05-16T00:12:00+00:00"}))

    archived = search(cell, "archived episode-lifecycle-archived", memory_types=["episodic"])

    assert archived[0].memory_id == "episode-lifecycle-archived"
    assert archived[0].lifecycle_status == "archived"
    approve_episode(cell, redacted_base)
    append_episode(cell, Episode.from_dict({**redacted_base.to_dict(), "status": "redacted", "created_at": "2026-05-16T00:13:00+00:00"}))
    redacted = search(cell, "redacted episode-lifecycle-redacted", memory_types=["episodic"])
    hidden_probe = search(cell, "Secretprose", memory_types=["episodic"])
    assert redacted[0].lifecycle_status == "redacted"
    assert "Secretprose" not in redacted[0].statement
    assert hidden_probe == []


def test_provider_search_suppresses_superseded_episodes(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    base = _episode(episode_id="episode-superseded", title="Superseded incident", summary="Superseded importer failure.")
    approve_episode(cell, base)
    append_episode(cell, Episode.from_dict({**base.to_dict(), "status": "superseded", "created_at": "2026-05-16T00:12:00+00:00"}))

    results = search(cell, "superseded importer failure", memory_types=["episodic"])
    capsules = search_episode_capsules(cell, "episode-superseded")
    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="superseded importer failure",
            task_id="task-1",
            memory_types=["episodic"],
            dry_run=True,
        )
    )

    assert results == []
    assert capsules == []
    assert all(item.item_id != "episode-superseded" for item in assembled.items)


def test_history_query_can_include_episode_capsule(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode())

    results = search(cell, "what happened last time importer failure")

    assert any(result.memory_id == "episode-1" for result in results)
    episode_result = [result for result in results if result.memory_id == "episode-1"][0]
    assert episode_result.selection_rationale == "episode_history"
    assert "artifact evidence" in episode_result.statement


def test_pack_keeps_episode_background_below_rule_guidance(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode(summary="The previous retry attempt happened after a retry failure."))

    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="what happened last time retry failure focused tests",
            task_id="task-1",
            memory_types=["episodic"],
            dry_run=True,
            max_items=5,
        )
    )

    episode_items = [item for item in assembled.items if item.item_id == "episode-1"]
    assert episode_items
    assert episode_items[0].memory_type == "episodic"
    assert episode_items[0].loadout_role == "background"
    assert episode_items[0].trust_tier == "trace"


def test_pack_keeps_archived_episode_background_inspectable(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    base = _episode(episode_id="episode-archived-pack", summary="Archived retry failure remained useful.")
    approve_episode(cell, base)
    append_episode(cell, Episode.from_dict({**base.to_dict(), "status": "archived", "created_at": "2026-05-16T00:12:00+00:00"}))

    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="retry failure",
            task_id="task-1",
            memory_types=["episodic"],
            dry_run=True,
            max_items=5,
        )
    )

    episode_items = [item for item in assembled.items if item.item_id == "episode-archived-pack"]
    assert episode_items


def test_pack_downranks_archived_episode_below_current_episode(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    archived = _episode(episode_id="episode-archived-prior", title="Retry history", summary="Importer retry failure history.")
    current = _episode(episode_id="episode-current", title="Retry history", summary="Importer retry failure history.")
    approve_episode(cell, archived)
    append_episode(cell, Episode.from_dict({**archived.to_dict(), "status": "archived", "created_at": "2026-05-16T00:12:00+00:00"}))
    approve_episode(cell, current)

    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="importer retry failure history",
            task_id="task-1",
            memory_types=["episodic"],
            dry_run=True,
            max_items=1,
        )
    )

    assert [item.item_id for item in assembled.items] == ["episode-current"]


def test_pack_redacts_redacted_episode_prose(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    base = _episode(episode_id="episode-redacted-pack", title="Sensitive title", summary="Secretpackprose")
    approve_episode(cell, base)
    append_episode(cell, Episode.from_dict({**base.to_dict(), "status": "redacted", "created_at": "2026-05-16T00:12:00+00:00"}))

    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="episode-redacted-pack redacted",
            task_id="task-1",
            memory_types=["episodic"],
            dry_run=True,
            max_items=5,
        )
    )

    episode_items = [item for item in assembled.items if item.item_id == "episode-redacted-pack"]
    assert episode_items
    assert "Sensitive title" not in episode_items[0].statement
    assert "Secretpackprose" not in episode_items[0].statement


def test_private_episodes_are_filtered_from_default_search_and_pack(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode(episode_id="episode-private", sensitivity="private", summary="Private previous failure details."))

    assert search(cell, "previous failure", memory_types=["episodic"]) == []
    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="previous failure",
            task_id="task-1",
            memory_types=["episodic"],
            dry_run=True,
        )
    )
    assert assembled.items == []


def test_pack_can_include_private_episodes_when_allowed(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode(episode_id="episode-private-allowed", sensitivity="private", summary="Private authorized retry detail."))

    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="episode-private-allowed",
            task_id="task-1",
            memory_types=["episodic"],
            allowed_sensitivity=["public", "internal", "private"],
            dry_run=True,
        )
    )

    assert [item.item_id for item in assembled.items] == ["episode-private-allowed"]
    assert "Private authorized retry detail" not in assembled.items[0].statement


def test_pack_filters_internal_episodes_from_public_only_loadout(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    approve_episode(cell, _episode(episode_id="episode-internal", sensitivity="internal", summary="Internal retry failure details."))

    assembled = assemble_pack(
        LoadoutTaskInput(
            cell_path=str(cell),
            query="retry failure",
            task_id="task-1",
            memory_types=["episodic"],
            allowed_sensitivity=["public"],
            dry_run=True,
        )
    )

    assert all(item.item_id != "episode-internal" for item in assembled.items)


def test_legacy_generic_episodic_memory_rows_remain_distinct_from_first_class_episodes(tmp_path: Path) -> None:
    cell = _cell(tmp_path)
    generic = remember(cell, "Legacy episodic row about importer history.", "preference", memory_type="episodic")
    approve_episode(cell, _episode())

    results = search(cell, "importer history", memory_types=["episodic"])
    result_by_id = {result.memory_id: result for result in results}

    assert generic.memory_id in result_by_id
    assert "episode-1" in result_by_id
    assert result_by_id[generic.memory_id].provenance.get("episode_id") is None
    assert result_by_id["episode-1"].provenance["episode_id"] == "episode-1"
