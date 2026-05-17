from __future__ import annotations

import json

from shyftr.episodes import append_episode, approve_episode, propose_episode
from shyftr.layout import init_cell
from shyftr.models import Episode, ResourceRef
from shyftr.store.sqlite import open_sqlite, rebuild_from_cell


def _approved(created_at: str = "2026-05-16T08:00:00Z", *, status: str = "approved") -> Episode:
    return Episode(
        episode_id="ep_sqlite",
        cell_id="cell",
        episode_kind="incident",
        title="Incident handled",
        summary="A deterministic incident fixture was handled.",
        started_at="2026-05-16T07:00:00Z",
        ended_at="2026-05-16T08:00:00Z",
        actor="runtime",
        action="diagnose incident",
        outcome="partial",
        status=status,
        memory_type="episodic",
        confidence=0.7,
        sensitivity="internal",
        created_at=created_at,
        live_context_entry_ids=["lc_1"],
        memory_ids=["mem_1"],
        feedback_ids=["fb_1"],
        resource_refs=[ResourceRef(ref_type="artifact", locator="file://incident.md")],
        grounding_refs=["gr_1"],
        artifact_refs=["art_1"],
        related_episode_ids=["ep_parent"],
        derived_memory_ids=["mem_derived"],
        key_points=["diagnosed", "contained"],
    )


def test_rebuild_creates_episodes_projection_table(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    conn = open_sqlite(tmp_path / "grid" / "cell.sqlite")

    rebuild_from_cell(conn, cell)

    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='episodes'").fetchone()
    assert row == ("episodes",)


def test_episode_projection_stores_capsule_and_json_fields(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    approve_episode(cell, _approved())
    conn = open_sqlite(tmp_path / "grid" / "cell.sqlite")

    rebuild_from_cell(conn, cell)

    row = conn.execute("SELECT * FROM episodes WHERE episode_id = 'ep_sqlite'").fetchone()
    columns = [description[0] for description in conn.execute("SELECT * FROM episodes LIMIT 0").description]
    payload = dict(zip(columns, row))
    assert payload["title"] == "Incident handled"
    assert payload["status"] == "approved"
    assert payload["memory_type"] == "episodic"
    anchors = json.loads(payload["anchors_json"])
    assert anchors["live_context_entry_ids"] == ["lc_1"]
    assert anchors["resource_refs"][0]["locator"] == "file://incident.md"
    relationships = json.loads(payload["relationships_json"])
    assert relationships["related_episode_ids"] == ["ep_parent"]
    capsule = json.loads(payload["capsule_json"])
    assert capsule["key_points"] == ["diagnosed", "contained"]


def test_episode_projection_uses_latest_row_wins(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    propose_episode(cell, Episode(episode_id="ep_sqlite", cell_id="cell", episode_kind="incident", created_at="2026-05-16T06:00:00Z"))
    approve_episode(cell, _approved("2026-05-16T08:00:00Z"))
    append_episode(cell, Episode.from_dict({**_approved("2026-05-16T08:00:00Z").to_dict(), "status": "redacted", "summary": "REDACTED", "created_at": "2026-05-16T09:00:00Z"}))
    conn = open_sqlite(tmp_path / "grid" / "cell.sqlite")

    rebuild_from_cell(conn, cell)

    rows = conn.execute("SELECT episode_id, status, summary, updated_at FROM episodes").fetchall()
    assert rows == [("ep_sqlite", "redacted", None, "2026-05-16T09:00:00Z")]


def test_older_cells_without_episode_ledger_rebuild_cleanly(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    (cell / "ledger" / "episodes.jsonl").unlink()
    conn = open_sqlite(tmp_path / "grid" / "cell.sqlite")

    rebuild_from_cell(conn, cell)

    assert conn.execute("SELECT count(*) FROM episodes").fetchone() == (0,)


def test_episode_projection_keys_latest_rows_by_cell_and_episode_id(tmp_path) -> None:
    cell_a = init_cell(tmp_path, "cell-a", cell_type="memory")
    cell_b = init_cell(tmp_path, "cell-b", cell_type="memory")
    approve_episode(cell_a, Episode.from_dict({**_approved().to_dict(), "cell_id": "cell-a", "summary": "Cell A episode."}))
    approve_episode(cell_b, Episode.from_dict({**_approved().to_dict(), "cell_id": "cell-b", "summary": "Cell B episode."}))
    conn = open_sqlite(tmp_path / "grid" / "cells.sqlite")

    rebuild_from_cell(conn, cell_a)
    rebuild_from_cell(conn, cell_b)

    rows = conn.execute("SELECT cell_id, episode_id, summary FROM episodes ORDER BY cell_id").fetchall()
    assert rows == [("cell-a", "ep_sqlite", "Cell A episode."), ("cell-b", "ep_sqlite", "Cell B episode.")]
