"""productization track adapter SDK harness and template checks."""

from __future__ import annotations

from pathlib import Path

from shyftr.integrations.plugins import builtin_file_adapter
from shyftr.integrations.template_adapter import MarkdownFolderTemplateAdapter
from shyftr.integrations.test_harness import AdapterTestHarness


def test_builtin_adapter_metadata_includes_capabilities_and_sdk_version() -> None:
    meta = builtin_file_adapter()
    payload = meta.to_dict()
    assert payload["adapter_sdk_version"] == "1.0.0"
    assert "dry_run" in payload["capabilities"]
    assert "idempotent" in payload["capabilities"]


def test_template_adapter_passes_public_contract_harness(tmp_path: Path) -> None:
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "one.md").write_text("# One\n\nSynthetic note.\n", encoding="utf-8")
    adapter = MarkdownFolderTemplateAdapter(tmp_path)
    result = AdapterTestHarness(adapter).run(require_sources=True)
    assert result.status == "ok", result.to_dict()
    assert result.refs_checked == 1
