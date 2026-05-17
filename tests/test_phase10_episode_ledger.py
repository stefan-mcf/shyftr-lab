from __future__ import annotations

from typing import Any

import pytest

from shyftr.episodes import (
    append_episode,
    approve_episode,
    episodes_ledger_path,
    get_latest_episode,
    list_episode_rows,
    list_latest_episodes,
    propose_episode,
)
from shyftr.layout import init_cell
from shyftr.models import Episode


def _episode(episode_id: str = "ep_1", *, status: str = "proposed", title: str | None = None) -> Episode:
    kwargs: dict[str, Any] = {
        "episode_id": episode_id,
        "cell_id": "cell",
        "episode_kind": "task",
        "status": status,
        "memory_type": "episodic",
        "created_at": "2026-05-16T08:00:00Z",
    }
    if status == "approved":
        kwargs.update(
            {
                "title": title or "Approved task episode",
                "summary": "A bounded task completed with evidence.",
                "started_at": "2026-05-16T07:00:00Z",
                "ended_at": "2026-05-16T08:00:00Z",
                "actor": "runtime",
                "action": "execute tranche",
                "outcome": "success",
                "confidence": 0.8,
                "sensitivity": "internal",
                "live_context_entry_ids": ["lc_1"],
            }
        )
    return Episode(**kwargs)


def test_proposing_episode_appends_without_retrieval_approval(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    proposed = _episode(status="proposed")

    propose_episode(cell, proposed)

    assert episodes_ledger_path(cell).exists()
    rows = list_episode_rows(cell)
    assert rows == [proposed]
    assert list_latest_episodes(cell)[0].status == "proposed"


def test_approving_anchored_episode_appends_approved_row(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    approved = _episode(status="approved")

    approve_episode(cell, approved)

    assert get_latest_episode(cell, "ep_1") == approved
    assert list_latest_episodes(cell)[0].status == "approved"


def test_approving_anchorless_episode_fails_before_append(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")

    with pytest.raises(ValueError):
        approve_episode(
            cell,
            Episode(
                episode_id="ep_bad",
                cell_id="cell",
                episode_kind="task",
                title="No anchors",
                summary="Should fail.",
                started_at="2026-05-16T07:00:00Z",
                ended_at="2026-05-16T08:00:00Z",
                actor="runtime",
                action="execute",
                outcome="success",
                status="approved",
                memory_type="episodic",
                confidence=0.8,
                sensitivity="internal",
                created_at="2026-05-16T08:00:00Z",
            ),
        )

    assert list_episode_rows(cell) == []


def test_latest_row_wins_for_archive_and_redaction(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    propose_episode(cell, _episode(status="proposed"))
    approved = _episode(status="approved", title="Approved v1")
    approve_episode(cell, approved)
    archived = Episode.from_dict({**approved.to_dict(), "status": "archived", "created_at": "2026-05-16T09:00:00Z"})

    # Archive/redaction transitions are still append-only Episode rows.
    append_episode(cell, archived)

    assert len(list_episode_rows(cell)) == 3
    assert get_latest_episode(cell, "ep_1") == archived
    assert list_latest_episodes(cell)[0].status == "archived"


def test_legacy_cells_without_episode_ledgers_read_cleanly(tmp_path) -> None:
    cell = tmp_path / "legacy-cell"
    (cell / "ledger").mkdir(parents=True)

    assert list_episode_rows(cell) == []
    assert list_latest_episodes(cell) == []
    assert get_latest_episode(cell, "missing") is None


def test_append_episode_rejects_cross_cell_rows(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    foreign = Episode.from_dict({**_episode(status="approved").to_dict(), "cell_id": "other-cell"})

    with pytest.raises(ValueError, match="does not match target cell"):
        append_episode(cell, foreign)


def test_append_episode_rejects_non_memory_cells(tmp_path) -> None:
    live_cell = init_cell(tmp_path, "live", cell_type="live_context")
    episode = Episode.from_dict({**_episode(status="approved").to_dict(), "cell_id": "live"})

    with pytest.raises(ValueError, match="only be written to memory cells"):
        append_episode(live_cell, episode)


def test_append_episode_rejects_lifecycle_regressions_after_approval(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    approved = _episode(status="approved")
    approve_episode(cell, approved)

    with pytest.raises(ValueError, match="cannot regress episode"):
        append_episode(cell, Episode.from_dict({**approved.to_dict(), "status": "proposed", "created_at": "2026-05-16T09:00:00Z"}))


def test_append_episode_rejects_post_approval_status_without_predecessor(tmp_path) -> None:
    cell = init_cell(tmp_path, "cell", cell_type="memory")
    approved_payload = _episode(status="approved").to_dict()

    with pytest.raises(ValueError, match="without an approved predecessor"):
        append_episode(cell, Episode.from_dict({**approved_payload, "status": "archived"}))
