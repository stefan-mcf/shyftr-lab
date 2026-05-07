from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from .ledger import append_jsonl, file_sha256, read_jsonl
from .models import Source
from .policy import check_source_boundary

PathLike = Union[str, Path]


def ingest_sources_from_adapter(
    cell_path: PathLike,
    adapter: Any,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ingest sources into a Cell from any SourceAdapter implementation.

    This integration adapters track adapter path reuses the same ledger-first safety rules as the
    config-backed file adapter: deterministic adapter source keys, boundary
    checks before append, and Source ledger truth with external provenance in
    metadata. Dry-run mode discovers and reads sources but never writes ledgers.
    """
    cell = Path(cell_path)
    sources_ledger = cell / "ledger" / "sources.jsonl"
    if not sources_ledger.exists():
        raise ValueError(f"sources ledger does not exist for Cell: {sources_ledger}")

    cell_id = _read_cell_id(cell)
    refs = adapter.discover_sources()
    existing_keys = _existing_adapter_source_keys(sources_ledger)
    ingested = 0
    skipped = 0
    errors: List[str] = []
    source_ids: List[str] = []
    skipped_keys: List[str] = []

    for ref in refs:
        try:
            payload = adapter.read_source(ref)
            source_key = _adapter_source_key(payload.content_hash, ref.to_dict())
            if source_key in existing_keys:
                skipped += 1
                skipped_keys.append(source_key)
                continue

            source_text = _adapter_source_text(ref)
            check_source_boundary(source_text, metadata=_boundary_metadata(payload.metadata), raise_on_reject=True)

            if dry_run:
                ingested += 1
                continue

            record = Source(
                source_id=f"src-{uuid4().hex}",
                cell_id=cell_id,
                kind=payload.kind or ref.source_kind,
                uri=ref.source_uri,
                sha256=payload.content_hash,
                captured_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "adapter_id": ref.adapter_id,
                    "external_system": ref.external_system,
                    "external_scope": ref.external_scope,
                    "external_refs": [r.to_dict() for r in payload.external_refs],
                    "adapter_source_key": source_key,
                    **(payload.metadata or {}),
                },
            )
            append_jsonl(sources_ledger, record.to_dict())
            existing_keys.add(source_key)
            ingested += 1
            source_ids.append(record.source_id)
        except Exception as exc:
            errors.append(f"Failed to ingest {getattr(ref, 'source_uri', None)}: {exc}")

    return {
        "sources_ingested": ingested,
        "sources_skipped": skipped,
        "source_ids": source_ids,
        "skipped_keys": skipped_keys,
        "errors": errors,
        "discovery_summary": {
            "adapter_id": getattr(adapter, "adapter_id", "unknown"),
            "total_sources": len(refs),
            "total_ingested": ingested,
            "total_skipped": skipped,
            "dry_run": bool(dry_run),
        },
    }


def ingest_source(
    cell_path: PathLike,
    source_path: PathLike,
    kind: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Source:
    """Capture raw evidence as an append-only Source ledger record."""
    cell = Path(cell_path)
    source = Path(source_path)
    sources_ledger = cell / "ledger" / "sources.jsonl"
    if not sources_ledger.exists():
        raise ValueError(f"sources ledger does not exist for Cell: {sources_ledger}")
    if not kind:
        raise ValueError("kind is required")

    text = source.read_text(encoding="utf-8")
    check_source_boundary(text, metadata=metadata, raise_on_reject=True)

    digest = file_sha256(source)
    existing = _find_existing_source(sources_ledger, digest)
    if existing is not None:
        return existing

    record = Source(
        source_id=f"src-{uuid4().hex}",
        cell_id=_read_cell_id(cell),
        kind=kind,
        uri=str(source),
        sha256=digest,
        captured_at=datetime.now(timezone.utc).isoformat(),
        metadata=metadata or {},
    )
    append_jsonl(sources_ledger, record.to_dict())
    return record


def ingest_from_adapter(
    cell_path: PathLike,
    adapter_config_or_path: Any,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ingest sources into a Cell using a runtime adapter configuration.

    Discovers Sources from a RI-2 RuntimeAdapterConfig, reads each source via
    the generic file adapter, and appends new Source rows to the Cell ledger.
    Dry-run mode returns deterministic discovery counts without ledger writes.
    """
    from shyftr.integrations.config import RuntimeAdapterConfig, load_config
    from shyftr.integrations.file_adapter import FileSourceAdapter

    cell = Path(cell_path)
    sources_ledger = cell / "ledger" / "sources.jsonl"
    if not sources_ledger.exists():
        raise ValueError(f"sources ledger does not exist for Cell: {sources_ledger}")

    if isinstance(adapter_config_or_path, RuntimeAdapterConfig):
        config = adapter_config_or_path
    else:
        config = load_config(str(adapter_config_or_path))

    adapter = FileSourceAdapter(config)

    if dry_run:
        summary = adapter.dry_run_discovery()
        return {
            "sources_ingested": 0,
            "sources_skipped": 0,
            "errors": list(summary.errors),
            "discovery_summary": {
                "adapter_id": summary.adapter_id,
                "total_sources": summary.total_sources,
                "by_kind": dict(summary.by_kind),
                "by_input_kind": dict(summary.by_input_kind),
                "inputs_processed": summary.inputs_processed,
            },
        }

    refs = adapter.discover_sources()
    existing_keys = _existing_adapter_source_keys(sources_ledger)
    ingested = 0
    skipped = 0
    errors: List[str] = []

    for ref in refs:
        try:
            payload = adapter.read_source(ref)
            source_key = _adapter_source_key(payload.content_hash, ref.to_dict())
            if source_key in existing_keys:
                skipped += 1
                continue

            source_text = _adapter_source_text(ref)
            check_source_boundary(source_text, metadata=_boundary_metadata(payload.metadata), raise_on_reject=True)

            record = Source(
                source_id=f"src-{uuid4().hex}",
                cell_id=config.cell_id,
                kind=ref.source_kind,
                uri=ref.source_uri,
                sha256=payload.content_hash,
                captured_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "adapter_id": config.adapter_id,
                    "external_system": config.external_system,
                    "external_scope": config.external_scope,
                    "external_refs": [r.to_dict() for r in payload.external_refs],
                    "adapter_source_key": source_key,
                    **(payload.metadata or {}),
                },
            )
            append_jsonl(sources_ledger, record.to_dict())
            existing_keys.add(source_key)
            ingested += 1
        except Exception as exc:
            errors.append(f"Failed to ingest {ref.source_uri}: {exc}")

    return {
        "sources_ingested": ingested,
        "sources_skipped": skipped,
        "errors": errors,
        "discovery_summary": {
            "adapter_id": config.adapter_id,
            "total_sources": len(refs),
            "total_ingested": ingested,
            "total_skipped": skipped,
        },
    }


def sync_from_adapter(
    cell_path: PathLike,
    adapter_config_or_path: Any,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Incrementally ingest append-only JSONL adapter inputs.

    The Cell ledger remains append-only truth. The sync-state file records the
    last byte offset, physical line number, content hash, and sync timestamp for
    each JSONL source path so repeated syncs skip already-seen rows and detect
    truncation/rotation before appending new Sources.
    """
    from shyftr.integrations.config import RuntimeAdapterConfig, load_config
    from shyftr.integrations.file_adapter import FileSourceAdapter
    from shyftr.integrations.protocols import ExternalSourceRef
    from shyftr.integrations.sync_state import (
        SyncStateEntry,
        SyncStateStore,
        build_file_content_hash,
        check_file_truncation,
        new_sync_entry,
    )

    cell = Path(cell_path)
    sources_ledger = cell / "ledger" / "sources.jsonl"
    if not sources_ledger.exists():
        raise ValueError(f"sources ledger does not exist for Cell: {sources_ledger}")

    if isinstance(adapter_config_or_path, RuntimeAdapterConfig):
        config = adapter_config_or_path
    else:
        config = load_config(str(adapter_config_or_path))

    adapter = FileSourceAdapter(config)
    store = SyncStateStore.load(cell)
    existing_keys = _existing_adapter_source_keys(sources_ledger)

    ingested = 0
    skipped = 0
    errors: List[str] = []
    synced_files: List[Dict[str, Any]] = []

    for inp in config.inputs:
        if inp.kind != "jsonl":
            continue
        path = adapter.resolve_source_path(inp.path)
        source_path = str(path)
        entry = store.get_entry(source_path)
        if entry is not None:
            check_file_truncation(path, entry)
            start_line = entry.last_line_number
        else:
            start_line = 0

        file_ingested = 0
        file_skipped = 0
        last_seen_line = start_line
        if path.exists() and path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                for line_number, raw in enumerate(handle, start=1):
                    last_seen_line = max(last_seen_line, line_number)
                    if line_number <= start_line:
                        continue
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    ref = ExternalSourceRef(
                        adapter_id=config.adapter_id,
                        external_system=config.external_system,
                        external_scope=config.external_scope,
                        source_kind=inp.source_kind,
                        source_uri=source_path,
                        source_line_offset=line_number,
                        external_ids=adapter.external_ids_for_input(inp, stripped),
                        metadata={
                            "row_hash": _text_sha256(stripped),
                            "input_path": inp.path,
                            "input_kind": "jsonl",
                            "sync_state_incremental": True,
                        },
                    )
                    try:
                        payload = adapter.read_source(ref)
                        source_key = _adapter_source_key(payload.content_hash, ref.to_dict())
                        if source_key in existing_keys:
                            skipped += 1
                            file_skipped += 1
                            continue
                        source_text = _adapter_source_text(ref)
                        check_source_boundary(source_text, metadata=payload.metadata, raise_on_reject=True)
                        record = Source(
                            source_id=f"src-{uuid4().hex}",
                            cell_id=config.cell_id,
                            kind=ref.source_kind,
                            uri=ref.source_uri,
                            sha256=payload.content_hash,
                            captured_at=datetime.now(timezone.utc).isoformat(),
                            metadata={
                                "adapter_id": config.adapter_id,
                                "external_system": config.external_system,
                                "external_scope": config.external_scope,
                                "external_refs": [r.to_dict() for r in payload.external_refs],
                                "adapter_source_key": source_key,
                                "sync_state_path": str(cell / "indexes" / "adapter_sync_state.json"),
                                **(payload.metadata or {}),
                            },
                        )
                        if not dry_run:
                            append_jsonl(sources_ledger, record.to_dict())
                            existing_keys.add(source_key)
                        ingested += 1
                        file_ingested += 1
                    except Exception as exc:
                        errors.append(f"Failed to sync {source_path}:{line_number}: {exc}")
        if path.exists() and path.is_file():
            new_entry = new_sync_entry(
                adapter_id=config.adapter_id,
                source_path=source_path,
                file_size=path.stat().st_size,
                line_count=last_seen_line,
                content_hash=build_file_content_hash(path),
            )
            if not dry_run:
                store.upsert_entry(new_entry)
            synced_files.append({
                "source_path": source_path,
                "start_line": start_line,
                "last_line_number": last_seen_line,
                "sources_ingested": file_ingested,
                "sources_skipped": file_skipped,
            })
    if not dry_run:
        store.save()
    return {
        "sources_ingested": ingested,
        "sources_skipped": skipped,
        "errors": errors,
        "sync_state_path": str(cell / "indexes" / "adapter_sync_state.json"),
        "synced_files": synced_files,
    }


def _boundary_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return user-content metadata for boundary checks, excluding provenance labels.

    Adapter ids, source kinds, file names, and content types are provenance, not
    durable memory text. Checking them verbatim would reject legitimate integration adapters track
    closeout/evidence adapters because their adapter names contain words the
    boundary policy correctly rejects in memory content.
    """
    if not metadata:
        return None
    provenance_keys = {
        "adapter_id",
        "adapter_version",
        "content_type",
        "document_index",
        "external_refs",
        "materialized",
        "relative_path",
        "size_bytes",
        "title",
    }
    return {key: value for key, value in metadata.items() if key not in provenance_keys}


def _text_sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _adapter_source_key(content_hash: str, ref_payload: Dict[str, Any]) -> str:
    stable_ref = json.dumps(ref_payload, sort_keys=True, separators=(",", ":"))
    return f"{content_hash}:{stable_ref}"


def _existing_adapter_source_keys(sources_ledger: Path) -> set[str]:
    keys: set[str] = set()
    for _, record in read_jsonl(sources_ledger):
        metadata = record.get("metadata") or {}
        source_key = metadata.get("adapter_source_key")
        if isinstance(source_key, str):
            keys.add(source_key)
            continue
        external_refs = metadata.get("external_refs") or []
        if record.get("sha256") and external_refs:
            for ref in external_refs:
                if isinstance(ref, dict):
                    keys.add(_adapter_source_key(str(record["sha256"]), ref))
    return keys


def _adapter_source_text(ref: Any) -> str:
    if not ref.source_uri:
        return ""
    path = Path(ref.source_uri)
    if ref.source_line_offset is None:
        return path.read_text(encoding="utf-8")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line_number == ref.source_line_offset:
                return line.strip()
            if line_number > ref.source_line_offset:
                break
    return ""


def _find_existing_source(sources_ledger: Path, digest: str) -> Optional[Source]:
    for _, record in read_jsonl(sources_ledger):
        if record.get("sha256") == digest:
            return Source.from_dict(record)
    return None


def _read_cell_id(cell_path: Path) -> str:
    manifest_path = cell_path / "config" / "cell_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Cell manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cell_id = manifest.get("cell_id")
    if not cell_id:
        raise ValueError("Cell manifest is missing cell_id")
    return str(cell_id)
