"""Tests for the Runtime Loadout API contract (RI-5).

All tests are dependency-free and network-free.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from shyftr.integrations.loadout_api import (
    RuntimeLoadoutRequest,
    RuntimeLoadoutResponse,
    process_runtime_loadout_request,
    _categorize_item,
    _detect_risk_flags,
    _item_to_dict,
)
from shyftr.layout import init_cell
from shyftr.ledger import append_jsonl
from shyftr.loadout import (
    LoadoutItem,
    LoadoutTaskInput,
    assemble_loadout,
    estimate_tokens,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cell(tmp: Path, cell_id: str = "test-cell") -> Path:
    return init_cell(tmp, cell_id)


def _seed_traces(cell_path: Path, traces: list[dict]) -> None:
    ledger = cell_path / "traces" / "approved.jsonl"
    for t in traces:
        append_jsonl(ledger, t)


def _make_trace(trace_id: str = "t1", **overrides) -> dict:
    base = {
        "trace_id": trace_id,
        "cell_id": "test-cell",
        "statement": f"Statement for {trace_id}",
        "rationale": f"Rationale for {trace_id}",
        "source_fragment_ids": ["f1"],
        "status": "approved",
        "confidence": 0.8,
        "tags": ["python"],
        "kind": "guidance",
        "use_count": 0,
        "success_count": 0,
        "failure_count": 0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# RuntimeLoadoutRequest
# ---------------------------------------------------------------------------


class TestRuntimeLoadoutRequest:
    def test_minimal_request(self):
        req = RuntimeLoadoutRequest(
            cell_path_or_id="/tmp/cell",
            query="test query",
        )
        assert req.cell_path_or_id == "/tmp/cell"
        assert req.query == "test query"
        assert req.max_items == 20
        assert req.max_tokens == 4000
        assert req.external_system == "unknown"
        assert req.include_fragments is False

    def test_full_request(self):
        req = RuntimeLoadoutRequest(
            cell_path_or_id="/tmp/cell",
            query="debug KeyError",
            task_kind="debug",
            external_system="example-runtime",
            external_scope="worker-runtime",
            external_task_id="wt-123",
            tags=["python", "errors"],
            max_items=10,
            max_tokens=2000,
            requested_trust_tiers=["doctrine", "trace"],
            include_fragments=True,
        )
        assert req.task_kind == "debug"
        assert req.external_system == "example-runtime"
        assert req.external_scope == "worker-runtime"
        assert req.external_task_id == "wt-123"
        assert req.tags == ["python", "errors"]
        assert req.max_items == 10
        assert req.max_tokens == 2000
        assert req.requested_trust_tiers == ["doctrine", "trace"]
        assert req.include_fragments is True

    def test_to_dict_roundtrip(self):
        req = RuntimeLoadoutRequest(
            cell_path_or_id="/tmp/cell",
            query="test",
            task_kind="debug",
            external_system="example-runtime",
            external_task_id="wt-123",
        )
        d = req.to_dict()
        req2 = RuntimeLoadoutRequest.from_dict(d)
        assert req2.cell_path_or_id == req.cell_path_or_id
        assert req2.query == req.query
        assert req2.task_kind == req.task_kind
        assert req2.external_system == req.external_system
        assert req2.external_task_id == req.external_task_id

    def test_from_json_roundtrip(self):
        req = RuntimeLoadoutRequest(
            cell_path_or_id="/tmp/cell",
            query="test",
            task_kind="code",
            external_system="example-runtime",
            tags=["python"],
        )
        json_str = json.dumps(req.to_dict())
        req2 = RuntimeLoadoutRequest.from_json(json_str)
        assert req2.cell_path_or_id == req.cell_path_or_id
        assert req2.query == req.query
        assert req2.task_kind == req.task_kind
        assert req2.tags == req.tags

    def test_to_from_json_string(self):
        req = RuntimeLoadoutRequest(cell_path_or_id="/cell", query="test")
        # to_json doesn't exist on request, but from_dict/from_json with serialization works
        d = req.to_dict()
        req2 = RuntimeLoadoutRequest.from_dict(d)
        assert req2.to_dict() == d


# ---------------------------------------------------------------------------
# RuntimeLoadoutResponse
# ---------------------------------------------------------------------------


class TestRuntimeLoadoutResponse:
    def test_empty_response(self):
        req = RuntimeLoadoutRequest(cell_path_or_id="/cell", query="test")
        resp = RuntimeLoadoutResponse(
            loadout_id="lo-test123",
            request=req,
        )
        assert resp.loadout_id == "lo-test123"
        assert resp.total_items == 0
        assert resp.guidance_items == []

    def test_to_dict_roundtrip(self):
        req = RuntimeLoadoutRequest(cell_path_or_id="/cell", query="test")
        resp = RuntimeLoadoutResponse(
            loadout_id="lo-test123",
            request=req,
            guidance_items=[{"item_id": "t1", "statement": "test"}],
            selected_ids=["t1"],
            score_traces={"t1": {"score": 0.9}},
            total_items=1,
            total_tokens=10,
            generated_at="2026-01-01T00:00:00",
        )
        d = resp.to_dict()
        assert d["pack_id"] == "lo-test123"
        assert d["loadout_id"] == "lo-test123"
        assert d["logged_at"] == "2026-01-01T00:00:00"
        resp2 = RuntimeLoadoutResponse.from_dict(d)
        assert resp2.pack_id == resp.pack_id
        assert resp2.loadout_id == resp.loadout_id
        assert resp2.guidance_items == resp.guidance_items
        assert resp2.selected_ids == resp.selected_ids
        assert resp2.total_items == resp.total_items

    def test_to_json_roundtrip(self):
        req = RuntimeLoadoutRequest(cell_path_or_id="/cell", query="test")
        resp = RuntimeLoadoutResponse(
            loadout_id="lo-test123",
            request=req,
            guidance_items=[{"item_id": "t1", "statement": "test guidance"}],
        )
        json_str = resp.to_json()
        resp2 = RuntimeLoadoutResponse.from_json(json_str)
        assert resp2.loadout_id == resp.loadout_id
        assert resp2.guidance_items == resp.guidance_items


# ---------------------------------------------------------------------------
# Item categorization
# ---------------------------------------------------------------------------


class TestItemCategorization:
    def test_guidance_by_kind(self):
        item = LoadoutItem(
            item_id="g1",
            trust_tier="trace",
            statement="Always use async context managers",
            rationale=None,
            tags=[],
            kind="guidance",
            confidence=0.9,
            score=0.95,
            score_trace={},
        )
        assert _categorize_item(item) == "guidance"

    def test_guidance_by_doctrine_tier(self):
        item = LoadoutItem(
            item_id="d1",
            trust_tier="doctrine",
            statement="Stateless functions are preferred",
            rationale=None,
            tags=[],
            kind=None,
            confidence=None,
            score=1.0,
            score_trace={},
        )
        assert _categorize_item(item) == "guidance"

    def test_caution(self):
        item = LoadoutItem(
            item_id="c1",
            trust_tier="trace",
            statement="Avoid mutable defaults in function signatures",
            rationale=None,
            tags=[],
            kind="caution",
            confidence=0.7,
            score=0.8,
            score_trace={},
        )
        assert _categorize_item(item) == "caution"

    def test_warning_as_caution(self):
        item = LoadoutItem(
            item_id="w1",
            trust_tier="trace",
            statement="Beware of circular imports",
            rationale=None,
            tags=[],
            kind="warning",
            confidence=0.6,
            score=0.7,
            score_trace={},
        )
        assert _categorize_item(item) == "caution"

    def test_conflict(self):
        item = LoadoutItem(
            item_id="x1",
            trust_tier="alloy",
            statement="Some approaches differ by context",
            rationale=None,
            tags=[],
            kind="conflict",
            confidence=0.5,
            score=0.5,
            score_trace={},
        )
        assert _categorize_item(item) == "conflict"

    def test_background_default(self):
        item = LoadoutItem(
            item_id="b1",
            trust_tier="trace",
            statement="Python 3.11 introduced exception groups",
            rationale=None,
            tags=[],
            kind="observation",
            confidence=0.8,
            score=0.9,
            score_trace={},
        )
        assert _categorize_item(item) == "background"

    def test_anti_pattern_is_caution(self):
        item = LoadoutItem(
            item_id="a1",
            trust_tier="trace",
            statement="Global state causes test pollution",
            rationale=None,
            tags=[],
            kind="anti-pattern",
            confidence=0.8,
            score=0.85,
            score_trace={},
        )
        assert _categorize_item(item) == "caution"


# ---------------------------------------------------------------------------
# Risk flags
# ---------------------------------------------------------------------------


class TestRiskFlags:
    def test_no_caution_no_conflict(self):
        items = [{"item_id": "t1", "confidence": 0.8}]
        flags = _detect_risk_flags(items)
        assert flags["has_caution"] is False
        assert flags["has_conflict"] is False
        assert flags["empty_loadout"] is False
        assert flags["low_confidence_items"] is False

    def test_empty_loadout(self):
        flags = _detect_risk_flags([])
        assert flags["empty_loadout"] is True

    def test_low_confidence_detected(self):
        items = [{"item_id": "t1", "confidence": 0.3}]
        flags = _detect_risk_flags(items)
        assert flags["low_confidence_items"] is True


# ---------------------------------------------------------------------------
# Integration: process_runtime_loadout_request (needs real Cell)
# ---------------------------------------------------------------------------


class TestProcessRequest:
    def test_minimal_request_returns_response(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        req = RuntimeLoadoutRequest(
            cell_path_or_id=str(cell),
            query="test",
            external_system="test-runtime",
        )
        resp = process_runtime_loadout_request(req)

        assert resp.loadout_id.startswith("lo-")
        assert resp.request.external_system == "test-runtime"
        assert resp.total_items >= 0
        assert isinstance(resp.risk_flags, dict)
        assert "has_caution" in resp.risk_flags

    def test_response_includes_categorization(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [
            _make_trace("t1", kind="guidance", statement="Use async patterns"),
            _make_trace("t2", kind="caution", statement="Avoid blocking calls"),
        ])

        req = RuntimeLoadoutRequest(
            cell_path_or_id=str(cell),
            query="async patterns",
            max_items=10,
        )
        resp = process_runtime_loadout_request(req)

        # At least guidance and caution should be categorized
        all_items = resp.guidance_items + resp.caution_items + resp.background_items + resp.conflict_items
        assert len(all_items) > 0

        guidance_ids = {i["item_id"] for i in resp.guidance_items}
        caution_ids = {i["item_id"] for i in resp.caution_items}
        assert "t1" in guidance_ids or "t1" in {i["item_id"] for i in all_items}
        assert any(i["item_id"] == "t2" for i in resp.caution_items)

    def test_selected_ids_match_items(self, tmp_path):
        cell = _make_cell(tmp_path)
        _seed_traces(cell, [_make_trace("t1")])

        req = RuntimeLoadoutRequest(
            cell_path_or_id=str(cell),
            query="test",
        )
        resp = process_runtime_loadout_request(req)

        # Every selected_id should have a score_trace entry
        for sid in resp.selected_ids:
            assert sid in resp.score_traces

    def test_external_identity_preserved(self, tmp_path):
        cell = _make_cell(tmp_path)

        req = RuntimeLoadoutRequest(
            cell_path_or_id=str(cell),
            query="test",
            external_system="my-runtime",
            external_scope="scope-42",
            external_task_id="task-99",
        )
        resp = process_runtime_loadout_request(req)
        assert resp.request.external_system == "my-runtime"
        assert resp.request.external_scope == "scope-42"
        assert resp.request.external_task_id == "task-99"


# ---------------------------------------------------------------------------
# Item to dict serialization
# ---------------------------------------------------------------------------


class TestItemToDict:
    def test_serializes_all_fields(self):
        item = LoadoutItem(
            item_id="i1",
            trust_tier="trace",
            statement="Test statement",
            rationale="Test rationale",
            tags=["python", "async"],
            kind="guidance",
            confidence=0.85,
            score=0.92,
            score_trace={},
        )
        d = _item_to_dict(item)
        assert d["item_id"] == "i1"
        assert d["trust_tier"] == "trace"
        assert d["statement"] == "Test statement"
        assert d["rationale"] == "Test rationale"
        assert d["tags"] == ["python", "async"]
        assert d["kind"] == "guidance"
        assert d["confidence"] == 0.85
        assert d["score"] == 0.92


# ---------------------------------------------------------------------------
# JSON round-trip tests
# ---------------------------------------------------------------------------


class TestJSONRoundTrip:
    def test_request_json_roundtrip(self):
        req = RuntimeLoadoutRequest(
            cell_path_or_id="/cell",
            query="debug memory leak",
            task_kind="debug",
            external_system="example-runtime",
            tags=["python", "memory"],
            max_items=15,
        )
        # Serialize to JSON, parse back
        json_str = json.dumps(req.to_dict(), sort_keys=True)
        parsed = json.loads(json_str)
        req2 = RuntimeLoadoutRequest.from_dict(parsed)
        assert req2.cell_path_or_id == req.cell_path_or_id
        assert req2.query == req.query
        assert req2.task_kind == req.task_kind
        assert req2.external_system == req.external_system
        assert req2.max_items == req.max_items
        assert req2.tags == req.tags

    def test_request_from_json_file_roundtrip(self, tmp_path):
        """Simulate reading from a --request-json file."""
        req = RuntimeLoadoutRequest(
            cell_path_or_id="/cell",
            query="test",
            external_system="test-system",
            tags=["tag1"],
        )
        json_path = tmp_path / "test-request.json"
        json_path.write_text(json.dumps(req.to_dict()), encoding="utf-8")

        # Simulate CLI reading
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        req2 = RuntimeLoadoutRequest.from_dict(raw)
        assert req2.query == "test"
        assert req2.external_system == "test-system"

    def test_response_json_roundtrip(self):
        req = RuntimeLoadoutRequest(cell_path_or_id="/cell", query="test")
        resp = RuntimeLoadoutResponse(
            loadout_id="lo-abc123",
            request=req,
            guidance_items=[
                {"item_id": "t1", "trust_tier": "trace", "statement": "Use async", "confidence": 0.9}
            ],
            risk_flags={"has_caution": False, "has_conflict": False, "low_confidence_items": False, "empty_loadout": False},
            selected_ids=["t1"],
            score_traces={"t1": {"semantic_score": 0.8, "kind_score": 0.1}},
            total_items=1,
            total_tokens=5,
            generated_at="2026-04-24T22:00:00",
        )
        json_str = resp.to_json()
        resp2 = RuntimeLoadoutResponse.from_json(json_str)
        assert resp2.loadout_id == resp.loadout_id
        assert resp2.total_items == resp.total_items
        assert resp2.selected_ids == resp.selected_ids
        assert resp2.guidance_items == resp.guidance_items
