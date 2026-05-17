from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from shyftr.episodes import get_latest_episode, list_episode_rows
from shyftr.layout import init_cell


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}"
    return subprocess.run([sys.executable, "-m", "shyftr.cli", *args], text=True, capture_output=True, env=env, check=False)


def test_episode_cli_capture_is_dry_run_by_default(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    result = _cli(
        "episode",
        "capture",
        str(cell),
        "--episode-id",
        "episode-cli-1",
        "--title",
        "CLI dry run",
        "--summary",
        "CLI captured an episode preview.",
        "--actor",
        "cli-test",
        "--action",
        "capture_episode",
        "--anchor-live-entry",
        "live-1",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry_run"
    assert payload["write"] is False
    assert list_episode_rows(cell) == []


def test_episode_cli_capture_writes_when_explicitly_requested(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    result = _cli(
        "episode",
        "capture",
        str(cell),
        "--episode-id",
        "episode-cli-2",
        "--episode-kind",
        "incident",
        "--title",
        "CLI write",
        "--summary",
        "CLI wrote an approved anchored episode.",
        "--actor",
        "cli-test",
        "--action",
        "capture_episode",
        "--outcome",
        "success",
        "--status",
        "approved",
        "--started-at",
        "2026-05-16T00:00:00+00:00",
        "--ended-at",
        "2026-05-16T00:10:00+00:00",
        "--sensitivity",
        "internal",
        "--anchor-live-entry",
        "live-2",
        "--write",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["write"] is True
    assert [episode.episode_id for episode in list_episode_rows(cell)] == ["episode-cli-2"]


def test_episode_cli_capture_writes_minimal_proposed_episode(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    result = _cli("episode", "capture", str(cell), "--episode-id", "episode-cli-minimal", "--write")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    episode = list_episode_rows(cell)[0]
    assert episode.episode_id == "episode-cli-minimal"
    assert episode.status == "proposed"
    assert episode.title is None


def test_episode_cli_capture_preserves_explicit_default_resets(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    first = _cli(
        "episode",
        "capture",
        str(cell),
        "--episode-id",
        "episode-cli-reset",
        "--episode-kind",
        "incident",
        "--title",
        "CLI reset incident",
        "--summary",
        "CLI default reset behavior.",
        "--actor",
        "cli-test",
        "--action",
        "capture_episode",
        "--outcome",
        "failure",
        "--status",
        "approved",
        "--started-at",
        "2026-05-16T00:00:00+00:00",
        "--ended-at",
        "2026-05-16T00:10:00+00:00",
        "--sensitivity",
        "private",
        "--confidence",
        "0.91",
        "--anchor-live-entry",
        "live-reset",
        "--write",
    )
    assert first.returncode == 0, first.stderr

    second = _cli(
        "episode",
        "capture",
        str(cell),
        "--episode-id",
        "episode-cli-reset",
        "--episode-kind",
        "session",
        "--outcome",
        "unknown",
        "--status",
        "approved",
        "--sensitivity",
        "internal",
        "--confidence",
        "0.8",
        "--write",
    )
    assert second.returncode == 0, second.stderr

    latest = get_latest_episode(cell, "episode-cli-reset")
    assert latest is not None
    assert latest.episode_kind == "session"
    assert latest.outcome == "unknown"
    assert latest.sensitivity == "internal"
    assert latest.confidence == 0.8


def test_episode_cli_search_returns_public_capsules(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    write_result = _cli(
        "episode",
        "capture",
        str(cell),
        "--episode-id",
        "episode-cli-3",
        "--title",
        "Importer history",
        "--summary",
        "Importer failed and then recovered.",
        "--actor",
        "cli-test",
        "--action",
        "capture_episode",
        "--outcome",
        "partial",
        "--status",
        "approved",
        "--started-at",
        "2026-05-16T00:00:00+00:00",
        "--ended-at",
        "2026-05-16T00:10:00+00:00",
        "--anchor-live-entry",
        "live-3",
        "--write",
    )
    assert write_result.returncode == 0, write_result.stderr

    result = _cli("episode", "search", str(cell), "importer")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["results"][0]["episode_id"] == "episode-cli-3"
    assert payload["results"][0]["anchors"]["live_context_entry_ids"] == ["live-3"]
