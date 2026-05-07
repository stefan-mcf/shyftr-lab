#!/usr/bin/env python3
"""Public-safe smoke for ShyftR live-context plus carry/continuity flow."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from shyftr.continuity import ContinuityPackRequest, assemble_continuity_pack, continuity_status
from shyftr.layout import init_cell
from shyftr.live_context import (
    LiveContextCaptureRequest,
    LiveContextPackRequest,
    SessionHarvestRequest,
    build_live_context_pack,
    capture_live_context,
    harvest_session,
    live_context_status,
)
from shyftr.provider.memory import MemoryProvider


def _temp_cells() -> tuple[Path, Path, Path, tempfile.TemporaryDirectory[str]]:
    tmp = tempfile.TemporaryDirectory(prefix="shyftr-runtime-context-smoke-")
    base = Path(tmp.name)
    return (
        init_cell(base, "memory", cell_type="memory"),
        init_cell(base, "continuity", cell_type="continuity"),
        init_cell(base, "live-context", cell_type="live_context"),
        tmp,
    )


def _approved_memory_count(memory_cell: Path) -> int:
    path = memory_cell / "ledger" / "memories" / "approved.jsonl"
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _seed_memory(memory_cell: Path) -> None:
    provider = MemoryProvider(memory_cell)
    provider.remember(
        "Runtime compaction remains runtime-owned; ShyftR supplies advisory carry packs and review-gated feedback.",
        "workflow",
        metadata={"origin_ref": "synthetic:runtime-context-smoke"},
    )
    provider.remember(
        "Session-close harvest should produce proposals instead of silently mutating durable memory.",
        "constraint",
        metadata={"origin_ref": "synthetic:runtime-context-smoke"},
    )


def run_smoke(
    *,
    memory_cell: Path | None = None,
    continuity_cell: Path | None = None,
    live_cell: Path | None = None,
    runtime_id: str = "synthetic-runtime-smoke",
    session_id: str = "synthetic-session-smoke",
    write: bool = True,
) -> dict[str, Any]:
    tmp: tempfile.TemporaryDirectory[str] | None = None
    if memory_cell is None or continuity_cell is None or live_cell is None:
        memory_cell, continuity_cell, live_cell, tmp = _temp_cells()

    _seed_memory(memory_cell)
    before_memory_count = _approved_memory_count(memory_cell)
    before_live = live_context_status(live_cell)["counts"]
    before_continuity = continuity_status(continuity_cell)["counts"]

    rows = [
        ("active_goal", "Verify carry and live context are attached to context compaction.", "session"),
        ("constraint", "Direct durable-memory writes remain disabled unless policy explicitly allows them.", "candidate"),
        ("failure", "A missing carry pack after compaction should become continuity feedback.", "session"),
        ("verification", "Post-restart smoke must prove pack, harvest, and advisory-only behavior.", "durable"),
    ]
    for kind, content, retention in rows:
        capture_live_context(
            LiveContextCaptureRequest(
                cell_path=str(live_cell),
                runtime_id=runtime_id,
                session_id=session_id,
                task_id="runtime-context-smoke",
                entry_kind=kind,
                content=content,
                source_ref="synthetic:runtime-context-smoke",
                retention_hint=retention,
                sensitivity_hint="public",
                write=True,
            )
        )

    live_pack = build_live_context_pack(
        LiveContextPackRequest(
            cell_path=str(live_cell),
            runtime_id=runtime_id,
            session_id=session_id,
            query="carry context compaction harvest proposal advisory",
            max_items=4,
            max_tokens=220,
            current_prompt_excerpts=["Verify carry and live context are attached to context compaction."],
            write=write,
            metadata={"provider_api": "smoke:on_pre_compress"},
        )
    )
    carry_pack = assemble_continuity_pack(
        ContinuityPackRequest(
            memory_cell_path=str(memory_cell),
            continuity_cell_path=str(continuity_cell),
            runtime_id=runtime_id,
            session_id=session_id,
            compaction_id=f"smoke-compaction-{session_id}",
            query="runtime-owned compaction advisory carry review-gated feedback",
            trigger="synthetic_context_compaction_smoke",
            mode="advisory",
            max_items=4,
            max_tokens=360,
            write=write,
        )
    )
    harvest = harvest_session(
        SessionHarvestRequest(
            live_cell_path=str(live_cell),
            continuity_cell_path=str(continuity_cell),
            memory_cell_path=str(memory_cell),
            runtime_id=runtime_id,
            session_id=session_id,
            write=write,
            allow_direct_durable_memory=False,
            metadata={"provider_api": "smoke:on_session_end"},
        )
    )

    after_memory_count = _approved_memory_count(memory_cell)
    after_live = live_context_status(live_cell)["counts"]
    after_continuity = continuity_status(continuity_cell)["counts"]
    result = {
        "status": "ok",
        "runtime_id": runtime_id,
        "session_id": session_id,
        "write_pack_and_harvest_ledgers": write,
        "setup_captures_written": True,
        "cells": {"memory": str(memory_cell), "continuity": str(continuity_cell), "live_context": str(live_cell)},
        "before": {"live_context": before_live, "continuity": before_continuity, "approved_memory_count": before_memory_count},
        "after": {"live_context": after_live, "continuity": after_continuity, "approved_memory_count": after_memory_count},
        "live_pack": {"pack_id": live_pack.pack_id, "items": live_pack.total_items, "advisory_only": live_pack.advisory_only},
        "carry_pack": {"pack_id": carry_pack.continuity_pack_id, "items": carry_pack.total_items, "mode": carry_pack.mode},
        "harvest": harvest.to_dict(),
        "checks": {
            "live_pack_generated": live_pack.total_items > 0,
            "carry_pack_generated": carry_pack.total_items > 0,
            "harvest_written_or_dry_run": harvest.status in {"ok", "dry_run"},
            "review_gated": harvest.review_gated is True,
            "no_direct_durable_memory_write": harvest.direct_durable_memory_writes == 0,
            "approved_memory_ledger_unchanged_by_harvest": after_memory_count == before_memory_count,
        },
    }
    failed = [key for key, passed in result["checks"].items() if not passed]
    if failed:
        result["status"] = "failed"
        result["failed_checks"] = failed
    if tmp:
        tmp.cleanup()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-cell", type=Path)
    parser.add_argument("--continuity-cell", type=Path)
    parser.add_argument("--live-cell", type=Path)
    parser.add_argument("--runtime-id", default="synthetic-runtime-smoke")
    parser.add_argument("--session-id", default="synthetic-session-smoke")
    parser.add_argument("--dry-run", action="store_true", help="Do not write pack or harvest ledgers; setup captures are still written so packs have material to retrieve.")
    args = parser.parse_args()
    result = run_smoke(
        memory_cell=args.memory_cell,
        continuity_cell=args.continuity_cell,
        live_cell=args.live_cell,
        runtime_id=args.runtime_id,
        session_id=args.session_id,
        write=not args.dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
