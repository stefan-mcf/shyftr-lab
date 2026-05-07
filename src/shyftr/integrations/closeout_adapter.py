"""Closeout artifact adapter for integration adapters track public-safe integrations.

External runtimes can write closeout artifacts first, then ask ShyftR to ingest
those artifacts through this SourceAdapter. The adapter never edits the source
artifact, so ingestion failure cannot corrupt closeout completion state.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from shyftr.integrations import IntegrationAdapterError
from shyftr.integrations.protocols import ExternalSourceRef, SourcePayload

_CLOSEOUT_ADAPTER_VERSION = "1.0.0"
_DEFAULT_PATTERNS = ("*.md", "*.markdown", "*.json")


class CloseoutArtifactAdapter:
    """Discover Markdown/JSON closeout artifacts in a local directory."""

    adapter_id = "closeout-artifact"
    version = _CLOSEOUT_ADAPTER_VERSION

    def __init__(
        self,
        closeout_root: str | Path,
        *,
        adapter_id: str = "closeout-artifact",
        external_system: str = "generic-closeout",
        external_scope: str = "default",
        patterns: Sequence[str] = _DEFAULT_PATTERNS,
        recursive: bool = False,
    ) -> None:
        self.closeout_root = Path(closeout_root).expanduser()
        if not self.closeout_root.exists():
            raise IntegrationAdapterError("closeout_root does not exist", details={"closeout_root": str(self.closeout_root)})
        if not self.closeout_root.is_dir():
            raise IntegrationAdapterError("closeout_root must be a directory", details={"closeout_root": str(self.closeout_root)})
        self.adapter_id = adapter_id
        self.external_system = external_system
        self.external_scope = external_scope
        self.patterns = tuple(patterns)
        self.recursive = recursive

    def discover_sources(self) -> List[ExternalSourceRef]:
        paths: list[Path] = []
        for pattern in self.patterns:
            paths.extend(self.closeout_root.rglob(pattern) if self.recursive else self.closeout_root.glob(pattern))
        refs: list[ExternalSourceRef] = []
        for path in sorted({p.resolve() for p in paths if p.is_file()}):
            refs.append(
                ExternalSourceRef(
                    adapter_id=self.adapter_id,
                    external_system=self.external_system,
                    external_scope=self.external_scope,
                    source_kind="task_closeout",
                    source_uri=str(path),
                    external_ids={"closeout_artifact": path.name},
                    metadata={
                        "adapter_version": self.version,
                        "content_type": _guess_content_type(path),
                        "relative_path": str(path.relative_to(self.closeout_root.resolve())),
                    },
                )
            )
        return refs

    def read_source(self, ref: ExternalSourceRef) -> SourcePayload:
        if not ref.source_uri:
            raise IntegrationAdapterError("source_uri is required", details={"ref": ref.to_dict()})
        path = Path(ref.source_uri)
        if not path.exists():
            raise IntegrationAdapterError("closeout artifact does not exist", details={"source_uri": ref.source_uri})
        text = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return SourcePayload(
            content_hash=digest,
            kind=ref.source_kind,
            metadata={
                "adapter_id": self.adapter_id,
                "adapter_version": self.version,
                "size_bytes": len(text.encode("utf-8")),
                "content_type": _guess_content_type(path),
                **(ref.metadata or {}),
            },
            external_refs=[ref],
        )

    def source_metadata(self, ref: ExternalSourceRef) -> Dict[str, Any]:
        if not ref.source_uri:
            return {"error": "source_uri is required", "ref": ref.to_dict()}
        path = Path(ref.source_uri)
        if not path.exists():
            return {"error": f"closeout artifact does not exist: {ref.source_uri}"}
        stat = path.stat()
        return {
            "adapter_id": self.adapter_id,
            "source_kind": ref.source_kind,
            "size_bytes": stat.st_size,
            "modified_epoch": int(stat.st_mtime),
            "content_type": _guess_content_type(path),
            "external_refs": [ref.to_dict()],
        }


def closeout_adapter_metadata() -> Dict[str, Any]:
    """Return plugin metadata for the built-in closeout artifact adapter."""

    return {
        "name": "closeout-artifact",
        "version": _CLOSEOUT_ADAPTER_VERSION,
        "description": "Built-in SourceAdapter for public-safe task/domain closeout artifacts.",
        "supported_input_kinds": ["task_closeout"],
        "capabilities": ["discover", "read", "metadata", "idempotent"],
        "adapter_sdk_version": "1.0.0",
        "config_schema_version": "1.0.0",
        "entry_point_group": "builtin",
        "adapter_class": "shyftr.integrations.closeout_adapter.CloseoutArtifactAdapter",
        "builtin": True,
    }


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    if suffix == ".json":
        return "application/json"
    return "text/plain"


__all__ = ["CloseoutArtifactAdapter", "closeout_adapter_metadata"]
