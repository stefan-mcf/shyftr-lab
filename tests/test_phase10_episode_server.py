from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from shyftr.episodes import list_episode_rows
from shyftr.layout import init_cell
from shyftr.server import _get_app


def test_http_episode_capture_defaults_to_dry_run(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    client = TestClient(_get_app())

    response = client.post(
        "/episode/capture",
        json={
            "cell_path": str(cell),
            "episode_id": "episode-http-1",
            "title": "HTTP dry run",
            "summary": "HTTP previewed an episode.",
            "actor": "http-test",
            "action": "capture_episode",
            "live_context_entry_ids": ["live-1"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dry_run"
    assert payload["write"] is False
    assert list_episode_rows(cell) == []


def test_http_episode_capture_rejects_missing_episode_id(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    client = TestClient(_get_app())

    response = client.post(
        "/episode/capture",
        json={
            "cell_path": str(cell),
            "title": "HTTP missing episode id",
            "summary": "HTTP should reject missing identity before writing.",
            "actor": "http-test",
            "action": "capture_episode",
            "write": True,
        },
    )

    assert response.status_code == 422
    assert "episode_id" in response.json()["message"]
    assert list_episode_rows(cell) == []


def test_http_episode_capture_rejects_blank_optional_text_fields(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    client = TestClient(_get_app())

    response = client.post(
        "/episode/capture",
        json={
            "cell_path": str(cell),
            "episode_id": "episode-http-bad",
            "title": "",
            "summary": " ",
            "actor": "",
            "action": " ",
            "write": True,
        },
    )

    assert response.status_code == 422
    message = response.json()["message"]
    assert "title" in message
    assert "summary" in message
    assert "actor" in message
    assert "action" in message
    assert list_episode_rows(cell) == []


def test_http_episode_capture_rejects_uninitialized_cell_path_even_for_dry_run(tmp_path: Path) -> None:
    client = TestClient(_get_app())
    uninitialized = tmp_path / "not-a-cell"
    uninitialized.mkdir()

    response = client.post(
        "/episode/capture",
        json={"cell_path": str(uninitialized), "episode_id": "episode-http-bad-cell"},
    )

    assert response.status_code == 422
    assert "initialized ShyftR cell" in response.json()["message"]


def test_http_episode_capture_writes_proposed_episode_with_required_text(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    client = TestClient(_get_app())

    response = client.post(
        "/episode/capture",
        json={
            "cell_path": str(cell),
            "episode_id": "episode-http-minimal",
            "title": "HTTP proposed",
            "summary": "HTTP wrote a proposed episode with required text.",
            "actor": "http-test",
            "action": "capture_episode",
            "write": True,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"
    episode = list_episode_rows(cell)[0]
    assert episode.episode_id == "episode-http-minimal"
    assert episode.status == "proposed"
    assert episode.title == "HTTP proposed"


def test_http_episode_capture_allows_lifecycle_only_update(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    client = TestClient(_get_app())

    create_response = client.post(
        "/episode/capture",
        json={
            "cell_path": str(cell),
            "episode_id": "episode-http-lifecycle",
            "title": "HTTP lifecycle",
            "summary": "HTTP wrote a lifecycle episode.",
            "actor": "http-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "confidence": 0.9,
            "sensitivity": "internal",
            "live_context_entry_ids": ["live-http-lifecycle"],
            "write": True,
        },
    )
    assert create_response.status_code == 200, create_response.text

    archive_response = client.post(
        "/episode/capture",
        json={"cell_path": str(cell), "episode_id": "episode-http-lifecycle", "status": "archived", "write": True},
    )

    assert archive_response.status_code == 200, archive_response.text
    rows = list_episode_rows(cell)
    assert rows[-1].status == "archived"
    assert rows[-1].title == "HTTP lifecycle"


def test_http_episode_capture_preserves_scalar_anchor_as_single_value(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    client = TestClient(_get_app())

    response = client.post(
        "/episode/capture",
        json={
            "cell_path": str(cell),
            "episode_id": "episode-http-scalar-anchor",
            "title": "Scalar anchor episode",
            "summary": "HTTP preserves scalar anchors as a single value.",
            "actor": "http-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "live_context_entry_ids": "live-1",
            "write": True,
        },
    )

    assert response.status_code == 200, response.text
    episode = list_episode_rows(cell)[0]
    assert episode.live_context_entry_ids == ["live-1"]


def test_http_episode_capture_write_and_search_are_capsule_safe(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    client = TestClient(_get_app())

    write_response = client.post(
        "/episode/capture",
        json={
            "cell_path": str(cell),
            "episode_id": "episode-http-2",
            "episode_kind": "incident",
            "title": "HTTP incident",
            "summary": "HTTP wrote a searchable approved episode.",
            "actor": "http-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "live_context_entry_ids": ["live-2"],
            "write": True,
        },
    )
    assert write_response.status_code == 200, write_response.text
    assert write_response.json()["status"] == "ok"

    search_response = client.get("/episode/search", params={"cell_path": str(cell), "query": "incident"})
    assert search_response.status_code == 200, search_response.text
    result = search_response.json()["results"][0]
    assert result["episode_id"] == "episode-http-2"
    assert result["anchors"]["live_context_entry_ids"] == ["live-2"]


def test_http_episode_search_rejects_uninitialized_cell_path(tmp_path: Path) -> None:
    client = TestClient(_get_app())
    uninitialized = tmp_path / "not-a-cell"
    uninitialized.mkdir()

    response = client.get("/episode/search", params={"cell_path": str(uninitialized), "query": "incident"})

    assert response.status_code == 422
    assert "initialized ShyftR cell" in response.json()["message"]
