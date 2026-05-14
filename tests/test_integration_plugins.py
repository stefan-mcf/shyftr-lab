"""Tests for runtime adapter plugin discovery."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pytest

from shyftr.integrations.plugins import (
    ADAPTER_ENTRY_POINT_GROUP,
    AdapterPluginMeta,
    adapter_plugins_payload,
    builtin_adapters,
    builtin_file_adapter,
    discover_adapter_plugins,
    list_adapter_plugins,
)


@dataclass(frozen=True)
class FakeEntryPoint:
    name: str
    loaded: Any
    group: str = ADAPTER_ENTRY_POINT_GROUP

    def load(self) -> Any:
        return self.loaded


class FakeSelectableEntryPoints(list):
    def select(self, *, group: str) -> list[FakeEntryPoint]:
        return [entry_point for entry_point in self if entry_point.group == group]


def fake_provider(entry_points: Iterable[FakeEntryPoint]):
    def _provider() -> FakeSelectableEntryPoints:
        return FakeSelectableEntryPoints(entry_points)

    return _provider


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "shyftr.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_builtin_file_adapter_metadata_is_available_without_plugins() -> None:
    meta = builtin_file_adapter()
    assert meta.name == "file"
    assert meta.builtin is True
    assert meta.entry_point_group == "builtin"
    assert meta.config_schema_version == "1.0.0"
    assert set(meta.supported_input_kinds) == {"file", "glob", "jsonl", "directory"}
    assert meta.adapter_class == "shyftr.integrations.file_adapter.FileSourceAdapter"


def test_builtin_adapters_returns_fresh_list() -> None:
    first = builtin_adapters()
    first.append(
        AdapterPluginMeta(
            name="external",
            version="1.0.0",
            supported_input_kinds=("file",),
        )
    )
    assert [plugin.name for plugin in builtin_adapters()] == ["file", "generic-evidence", "closeout-artifact"]


def test_discover_adapter_plugins_loads_fake_entry_point_metadata() -> None:
    third_party = AdapterPluginMeta(
        name="runtime-alpha",
        version="2.3.4",
        description="Runtime alpha adapter",
        supported_input_kinds=("jsonl",),
        config_schema_version="1.0.0",
        adapter_class="runtime_alpha.Adapter",
    )

    plugins = discover_adapter_plugins(
        entry_point_provider=fake_provider([FakeEntryPoint("runtime-alpha", lambda: third_party)])
    )

    assert plugins == [third_party]


def test_discover_adapter_plugins_accepts_dict_metadata() -> None:
    plugins = discover_adapter_plugins(
        entry_point_provider=fake_provider(
            [
                FakeEntryPoint(
                    "runtime-beta",
                    lambda: {
                        "name": "runtime-beta",
                        "version": "0.5.0",
                        "description": "Runtime beta adapter",
                        "supported_input_kinds": ["file", "jsonl"],
                        "config_schema_version": "1.0.0",
                    },
                )
            ]
        )
    )

    assert len(plugins) == 1
    assert plugins[0].name == "runtime-beta"
    assert plugins[0].supported_input_kinds == ("file", "jsonl")


def test_discover_adapter_plugins_handles_single_meta_entry_point_and_list_entry_point() -> None:
    single = AdapterPluginMeta(name="single", version="1.0.0", supported_input_kinds=("file",))
    multiple = [
        AdapterPluginMeta(name="multi-a", version="1.0.0", supported_input_kinds=("jsonl",)),
        AdapterPluginMeta(name="multi-b", version="1.0.0", supported_input_kinds=("directory",)),
    ]

    plugins = discover_adapter_plugins(
        entry_point_provider=fake_provider(
            [
                FakeEntryPoint("single", single),
                FakeEntryPoint("multiple", lambda: multiple),
            ]
        )
    )

    assert [plugin.name for plugin in plugins] == ["single", "multi-a", "multi-b"]


def test_list_adapter_plugins_includes_builtins_and_third_party_plugins() -> None:
    plugin = AdapterPluginMeta(name="runtime-alpha", version="1.0.0", supported_input_kinds=("jsonl",))

    plugins = list_adapter_plugins(entry_point_provider=fake_provider([FakeEntryPoint("runtime-alpha", plugin)]))

    assert [plugin.name for plugin in plugins] == ["file", "generic-evidence", "closeout-artifact", "runtime-alpha"]


def test_list_adapter_plugins_deduplicates_builtin_entry_point_metadata() -> None:
    plugins = list_adapter_plugins(
        entry_point_provider=fake_provider([FakeEntryPoint("file", builtin_file_adapter)])
    )

    assert [plugin.name for plugin in plugins] == ["file", "generic-evidence", "closeout-artifact"]
    assert plugins[0].supported_input_kinds == ("file", "glob", "jsonl", "directory")


def test_adapter_plugins_payload_is_json_ready() -> None:
    payload = adapter_plugins_payload(entry_point_provider=fake_provider([]))

    assert payload["status"] == "ok"
    assert payload["entry_point_group"] == "shyftr.adapters"
    assert payload["builtin_count"] == 3
    assert payload["plugin_count"] == 0
    assert payload["total"] == 3
    assert [plugin["name"] for plugin in payload["plugins"]] == ["file", "generic-evidence", "closeout-artifact"]
    json.dumps(payload)


def test_failed_plugin_metadata_load_is_ignored() -> None:
    def broken() -> AdapterPluginMeta:
        raise RuntimeError("plugin unavailable")

    plugins = discover_adapter_plugins(entry_point_provider=fake_provider([FakeEntryPoint("broken", broken)]))

    assert plugins == []


def test_cli_adapter_list_outputs_builtin_metadata() -> None:
    result = _cli("adapter", "list", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["entry_point_group"] == "shyftr.adapters"
    assert payload["builtin_count"] >= 1
    names = {plugin["name"] for plugin in payload["plugins"]}
    assert "file" in names
