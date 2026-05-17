from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType

import pytest

from shyftr.episodes import append_episode, get_latest_episode, list_episode_rows
from shyftr.layout import init_cell
from shyftr.models import Episode
from shyftr.mcp_server import create_mcp_server, shyftr_episode_capture_bridge, shyftr_episode_search_bridge


def test_mcp_episode_capture_defaults_to_dry_run(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    result = shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-1",
            "title": "MCP dry run",
            "summary": "MCP previewed an episode.",
            "actor": "mcp-test",
            "action": "capture_episode",
            "live_context_entry_ids": ["live-1"],
        }
    )

    assert result["tool"] == "shyftr_episode_capture"
    assert result["status"] == "dry_run"
    assert result["write"] is False
    assert list_episode_rows(cell) == []


def test_mcp_episode_capture_allows_minimal_proposed_episode(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    result = shyftr_episode_capture_bridge({"cell_path": str(cell), "episode_id": "episode-mcp-minimal", "confidence": None, "write": True})

    assert result["status"] == "ok"
    episode = list_episode_rows(cell)[0]
    assert episode.episode_id == "episode-mcp-minimal"
    assert episode.status == "proposed"
    assert episode.title is None
    assert episode.confidence is None


def test_mcp_episode_capture_write_and_search_returns_capsule(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    write_result = shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-2",
            "episode_kind": "incident",
            "title": "MCP incident",
            "summary": "MCP wrote a searchable approved episode.",
            "actor": "mcp-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "live_context_entry_ids": ["live-2"],
            "write": True,
        }
    )

    assert write_result["status"] == "ok"
    assert write_result["write"] is True
    search_result = shyftr_episode_search_bridge({"cell_path": str(cell), "query": "incident?", "limit": 5})
    assert search_result["results"][0]["episode_id"] == "episode-mcp-2"
    assert search_result["results"][0]["summary"] == "MCP wrote a searchable approved episode."


def test_mcp_episode_search_redacts_private_capsule_prose(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-private",
            "episode_kind": "incident",
            "title": "Private incident title",
            "summary": "Secretprivateprose.",
            "actor": "mcp-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "sensitivity": "private",
            "live_context_entry_ids": ["live-private"],
            "write": True,
        }
    )

    search_result = shyftr_episode_search_bridge({"cell_path": str(cell), "query": "episode-mcp-private", "include_private": True})
    hidden_probe = shyftr_episode_search_bridge({"cell_path": str(cell), "query": "Secretprivateprose", "include_private": True})

    assert search_result["results"][0]["episode_id"] == "episode-mcp-private"
    assert search_result["results"][0]["title"] == "Private incident title"
    assert search_result["results"][0]["summary"] == "Secretprivateprose."
    assert hidden_probe["results"] == []


def test_mcp_episode_search_keeps_archived_and_redacted_episodes_inspectable(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    archived_base = Episode(
        episode_id="episode-mcp-lifecycle-archived",
        cell_id="memory",
        episode_kind="incident",
        title="Lifecycle incident",
        summary="Lifecycle archive remains inspectable.",
        started_at="2026-05-16T00:00:00+00:00",
        ended_at="2026-05-16T00:10:00+00:00",
        actor="mcp-test",
        action="capture_episode",
        outcome="success",
        status="approved",
        confidence=0.8,
        sensitivity="internal",
        created_at="2026-05-16T00:11:00+00:00",
        live_context_entry_ids=["live-lifecycle"],
    )
    redacted_base = Episode.from_dict({**archived_base.to_dict(), "episode_id": "episode-mcp-lifecycle-redacted", "summary": "Secretmcpprose"})
    append_episode(cell, archived_base)
    append_episode(cell, Episode.from_dict({**archived_base.to_dict(), "status": "archived", "created_at": "2026-05-16T00:12:00+00:00"}))

    archived = shyftr_episode_search_bridge({"cell_path": str(cell), "query": "archived episode-mcp-lifecycle-archived"})

    assert archived["results"][0]["status"] == "archived"
    append_episode(cell, redacted_base)
    append_episode(cell, Episode.from_dict({**redacted_base.to_dict(), "status": "redacted", "created_at": "2026-05-16T00:13:00+00:00"}))
    redacted = shyftr_episode_search_bridge({"cell_path": str(cell), "query": "redacted episode-mcp-lifecycle-redacted"})
    assert redacted["results"][0]["status"] == "redacted"
    assert redacted["results"][0]["title"] is None
    assert redacted["results"][0]["anchors"]["live_context_entry_ids"] == ["live-lifecycle"]
    hidden_prose_probe = shyftr_episode_search_bridge({"cell_path": str(cell), "query": "Secretmcpprose"})
    assert hidden_prose_probe["results"] == []


def test_mcp_episode_capture_allows_resource_ref_as_only_approved_anchor(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    result = shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-resource",
            "episode_kind": "incident",
            "title": "Resource anchored incident",
            "summary": "Approved episode anchored to a resource reference.",
            "actor": "mcp-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "resource_refs": [{"ref_type": "artifact", "locator": "artifact://proof", "label": "proof"}],
            "write": True,
        }
    )

    assert result["status"] == "ok"
    episode = list_episode_rows(cell)[0]
    assert episode.resource_refs[0].locator == "artifact://proof"


def test_mcp_episode_capture_can_promote_existing_proposal_with_review_fields(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-promote",
            "episode_kind": "incident",
            "title": "Promoted incident",
            "summary": "Proposal fields should survive approval.",
            "actor": "mcp-test",
            "action": "capture_episode",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "live_context_entry_ids": ["live-promote"],
            "write": True,
        }
    )

    shyftr_episode_capture_bridge({"cell_path": str(cell), "episode_id": "episode-mcp-promote", "status": "approved", "outcome": "success", "write": True})

    latest = get_latest_episode(cell, "episode-mcp-promote")
    assert latest is not None
    assert latest.status == "approved"
    assert latest.title == "Promoted incident"
    assert latest.live_context_entry_ids == ["live-promote"]


def test_mcp_episode_capture_preserves_existing_fields_on_lifecycle_transition(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-transition",
            "episode_kind": "incident",
            "title": "Transition incident",
            "summary": "Original transition summary.",
            "actor": "mcp-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "live_context_entry_ids": ["live-transition"],
            "write": True,
        }
    )

    shyftr_episode_capture_bridge({"cell_path": str(cell), "episode_id": "episode-mcp-transition", "status": "archived", "write": True})

    latest = get_latest_episode(cell, "episode-mcp-transition")
    assert latest is not None
    assert latest.status == "archived"
    assert latest.title == "Transition incident"
    assert latest.live_context_entry_ids == ["live-transition"]


def test_mcp_episode_capture_redaction_transition_clears_prose_fields(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-redact-transition",
            "episode_kind": "incident",
            "title": "Sensitive transition title",
            "summary": "Sensitive transition summary.",
            "actor": "mcp-test",
            "action": "capture_episode",
            "outcome": "success",
            "status": "approved",
            "started_at": "2026-05-16T00:00:00+00:00",
            "ended_at": "2026-05-16T00:10:00+00:00",
            "live_context_entry_ids": ["live-transition"],
            "write": True,
        }
    )

    shyftr_episode_capture_bridge({"cell_path": str(cell), "episode_id": "episode-mcp-redact-transition", "status": "redacted", "write": True})

    latest = get_latest_episode(cell, "episode-mcp-redact-transition")
    assert latest is not None
    assert latest.status == "redacted"
    assert latest.title is None
    assert latest.summary is None
    assert latest.live_context_entry_ids == ["live-transition"]


def test_mcp_episode_capture_first_write_redacted_requires_approved_predecessor(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    with pytest.raises(ValueError, match="without an approved predecessor"):
        shyftr_episode_capture_bridge(
            {
                "cell_path": str(cell),
                "episode_id": "episode-mcp-redacted-first",
                "episode_kind": "incident",
                "title": "Sensitive first title",
                "summary": "Sensitive first summary.",
                "status": "redacted",
                "write": True,
            }
        )


def test_mcp_episode_capture_can_clear_explicit_anchor_fields(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")
    shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-clear-anchors",
            "actor": "mcp-test",
            "action": "draft",
            "outcome": "unknown",
            "live_context_entry_ids": ["live-old"],
            "metadata": {"review": "needed"},
            "write": True,
        }
    )

    shyftr_episode_capture_bridge(
        {
            "cell_path": str(cell),
            "episode_id": "episode-mcp-clear-anchors",
            "live_context_entry_ids": [],
            "metadata": {},
            "write": True,
        }
    )

    latest = get_latest_episode(cell, "episode-mcp-clear-anchors")
    assert latest is not None
    assert latest.live_context_entry_ids == []
    assert latest.metadata == {}


def test_mcp_episode_capture_rejects_mapping_for_string_anchor_fields(tmp_path: Path) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    with pytest.raises(ValueError):
        shyftr_episode_capture_bridge(
            {
                "cell_path": str(cell),
                "episode_id": "episode-mcp-bad-anchor",
                "episode_kind": "incident",
                "title": "Bad anchor incident",
                "summary": "String-list anchor fields must reject mapping payloads.",
                "actor": "mcp-test",
                "action": "capture_episode",
                "outcome": "success",
                "status": "approved",
                "started_at": "2026-05-16T00:00:00+00:00",
                "ended_at": "2026-05-16T00:10:00+00:00",
                "live_context_entry_ids": {"id": "live-1"},
                "write": True,
            }
        )


def test_mcp_fastmcp_episode_capture_forwards_supported_fields(tmp_path: Path, monkeypatch) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    class FakeFastMCP:
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools = {}

        def tool(self, *, name: str):
            def decorator(func):
                self.tools[name] = func
                return func

            return decorator

    mcp_module = ModuleType("mcp")
    server_module = ModuleType("mcp.server")
    fastmcp_module = ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeFastMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)

    server = create_mcp_server()
    result = server.tools["shyftr_episode_capture"](
        cell_path=str(cell),
        episode_id="episode-mcp-wrapper",
        episode_kind="incident",
        title="MCP wrapper incident",
        summary="MCP wrapper captured all supported optional fields.",
        actor="mcp-test",
        action="capture_episode",
        outcome="success",
        status="approved",
        started_at="2026-05-16T00:00:00+00:00",
        ended_at="2026-05-16T00:10:00+00:00",
        runtime_id="runtime-1",
        session_id="session-1",
        task_id="task-1",
        memory_ids=["memory-1"],
        feedback_ids=["feedback-1"],
        resource_refs=["artifact://wrapper-proof"],
        grounding_refs=["grounding-1"],
        artifact_refs=["artifact-1"],
        metadata={"source": "fastmcp-wrapper"},
        write=True,
    )

    assert result["status"] == "ok"
    episode = list_episode_rows(cell)[0]
    assert episode.memory_ids == ["memory-1"]
    assert episode.feedback_ids == ["feedback-1"]
    assert episode.resource_refs[0].locator == "artifact://wrapper-proof"
    assert episode.runtime_id == "runtime-1"
    assert episode.session_id == "session-1"
    assert episode.task_id == "task-1"
    assert episode.started_at == "2026-05-16T00:00:00+00:00"
    assert episode.ended_at == "2026-05-16T00:10:00+00:00"
    assert episode.metadata == {"source": "fastmcp-wrapper"}


def test_mcp_fastmcp_episode_capture_preserves_explicit_default_resets(tmp_path: Path, monkeypatch) -> None:
    cell = init_cell(tmp_path, "memory", cell_type="memory")

    class FakeFastMCP:
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools = {}

        def tool(self, *, name: str):
            def decorator(func):
                self.tools[name] = func
                return func

            return decorator

    mcp_module = ModuleType("mcp")
    server_module = ModuleType("mcp.server")
    fastmcp_module = ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeFastMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)

    server = create_mcp_server()
    server.tools["shyftr_episode_capture"](
        cell_path=str(cell),
        episode_id="episode-mcp-default-reset",
        episode_kind="incident",
        title="Resettable incident",
        summary="Explicit default resets must survive wrapper forwarding.",
        actor="mcp-test",
        action="capture_episode",
        outcome="failure",
        status="approved",
        started_at="2026-05-16T00:00:00+00:00",
        ended_at="2026-05-16T00:10:00+00:00",
        live_context_entry_ids=["live-reset"],
        sensitivity="private",
        confidence=0.91,
        write=True,
    )

    server.tools["shyftr_episode_capture"](
        cell_path=str(cell),
        episode_id="episode-mcp-default-reset",
        episode_kind="session",
        outcome="unknown",
        status="approved",
        sensitivity="internal",
        confidence=0.8,
        write=True,
    )

    latest = get_latest_episode(cell, "episode-mcp-default-reset")
    assert latest is not None
    assert latest.episode_kind == "session"
    assert latest.outcome == "unknown"
    assert latest.sensitivity == "internal"
    assert latest.confidence == 0.8
