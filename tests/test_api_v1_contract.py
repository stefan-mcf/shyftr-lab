"""Phase 8 v1 API contract smoke checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from shyftr.server import _get_app


def test_v1_health_alias_and_version_headers() -> None:
    client = TestClient(_get_app())
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-ShyftR-API-Version"] == "v1"
    assert "Deprecation" not in response.headers


def test_unversioned_routes_remain_deprecated_alpha_aliases() -> None:
    client = TestClient(_get_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["Deprecation"] == "true"
    assert response.headers["X-ShyftR-API-Version"] == "v1"


def test_v1_discovery_endpoint_lists_stable_surface() -> None:
    client = TestClient(_get_app())
    payload = client.get("/v1").json()
    assert payload["api_versions"] == ["v1"]
    assert payload["latest"] == "v1"
    assert payload["schema_version"] == "1.0.0"
    assert payload["posture"] == "stable local-first release"


def test_committed_openapi_v1_spec_contains_only_v1_paths() -> None:
    spec_path = Path("docs/openapi-v1.json")
    assert spec_path.exists()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec["info"]["x-shyftr-api-version"] == "v1"
    assert spec["paths"]
    assert all(path.startswith("/v1") for path in spec["paths"])
    assert "/v1/health" in spec["paths"]
