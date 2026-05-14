"""Sparse keyword/BM25 retrieval over approved Traces using SQLite FTS5.

The sparse Mesh is rebuildable acceleration over canonical JSONL ledgers.
It creates an FTS5 virtual table over Trace fields (statement, rationale,
tags) and queries it with BM25 scoring. Deprecated/quarantined Traces are
excluded by default.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

from ..ledger import read_jsonl

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SparseResult:
    """A single retrieval result with provenance and score."""

    trace_id: str
    cell_id: str
    statement: str
    rationale: Optional[str]
    tags: List[str]
    kind: Optional[str]
    confidence: Optional[float]
    bm25_score: float
    label: Optional[str] = None
    status: str = "approved"


# ---------------------------------------------------------------------------
# FTS5 schema
# ---------------------------------------------------------------------------

_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS traces_fts USING fts5(
    trace_id UNINDEXED,
    cell_id UNINDEXED,
    statement,
    rationale,
    tags,
    kind,
    label,
    status UNINDEXED,
    confidence UNINDEXED,
    tokenize='porter unicode61'
);
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def open_sparse_index(db_path: PathLike) -> sqlite3.Connection:
    """Open (or create) a SQLite database with the FTS5 sparse index.

    The database also contains the standard ShyftR metadata tables so that
    rebuild_from_cell and sparse rebuild can share one connection.
    """
    from ..store.sqlite import open_sqlite

    conn = open_sqlite(db_path)
    conn.executescript(_FTS_DDL)
    conn.commit()
    return conn


def rebuild_sparse_index(
    conn: sqlite3.Connection,
    cell_path: PathLike,
    *,
    include_statuses: Optional[Sequence[str]] = None,
) -> int:
    """Rebuild the FTS5 index from a Cell's traces/approved.jsonl.

    By default only approved Traces are indexed. Pass *include_statuses*
    to override (e.g. ``["approved", "deprecated"]`` for debugging).

    Returns the number of Traces indexed.
    """
    cell = Path(cell_path)
    ledger = cell / "traces" / "approved.jsonl"

    cell_id = _read_cell_id(cell)

    # Clear existing FTS rows for this cell
    _clear_fts_for_cell(conn, cell_id)

    if not ledger.exists():
        conn.commit()
        return 0

    count = 0
    for _, record in read_jsonl(ledger):
        status = record.get("status", "approved")

        # Filter by status unless explicitly overridden
        if include_statuses is not None:
            if status not in include_statuses:
                continue
        else:
            # Default: only index approved Traces
            if status != "approved":
                continue

        tags = record.get("tags", [])
        tags_text = json.dumps(tags, sort_keys=True) if isinstance(tags, list) else str(tags)

        resource_ref = record.get("resource_ref")
        label = ""
        if isinstance(resource_ref, dict):
            label = str(resource_ref.get("label") or "")

        conn.execute(
            "INSERT INTO traces_fts "
            "(trace_id, cell_id, statement, rationale, tags, kind, label, status, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("trace_id"),
                record.get("cell_id") or cell_id,
                record.get("statement", ""),
                record.get("rationale") or "",
                tags_text,
                record.get("kind") or "",
                label,
                status,
                record.get("confidence"),
            ),
        )
        count += 1

    conn.commit()
    return count


def query_sparse(
    conn: sqlite3.Connection,
    query: str,
    *,
    cell_id: Optional[str] = None,
    limit: int = 10,
    include_statuses: Optional[Sequence[str]] = None,
) -> List[SparseResult]:
    """Query the sparse FTS5 index with BM25 scoring.

    Returns results ordered by BM25 relevance (highest first).

    Parameters
    ----------
    conn : sqlite3.Connection
        Connection with the FTS5 index populated.
    query : str
        Natural-language or keyword query.
    cell_id : str, optional
        Restrict results to a specific Cell.
    limit : int
        Maximum results to return.
    include_statuses : sequence of str, optional
        If provided, include Traces with these statuses (e.g.
        ``["approved", "deprecated"]``). By default only approved
        Traces are returned (those with status='approved' in the FTS
        index).
    """
    if not query or not query.strip():
        return []

    # Sanitize the query for FTS5: wrap tokens in quotes
    safe_query = _sanitize_fts_query(query)

    # Build the WHERE clause for cell filtering
    cell_filter = ""
    params: list[Any] = [safe_query]
    if cell_id:
        cell_filter = "AND cell_id = ?"
        params.append(cell_id)

    # Build status filter
    status_filter = ""
    if include_statuses is not None:
        placeholders = ", ".join("?" for _ in include_statuses)
        status_filter = f"AND status IN ({placeholders})"
        params.extend(include_statuses)
    else:
        # Default: only approved
        status_filter = "AND status = 'approved'"

    sql = f"""
        SELECT
            trace_id,
            cell_id,
            statement,
            rationale,
            tags,
            kind,
            label,
            status,
            confidence,
            bm25(traces_fts) AS bm25_score
        FROM traces_fts
        WHERE traces_fts MATCH ?
        {cell_filter}
        {status_filter}
        ORDER BY bm25_score ASC
        LIMIT ?
    """
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    results: List[SparseResult] = []
    for row in rows:
        tags_raw = row[4]
        if isinstance(tags_raw, str):
            try:
                tags = json.loads(tags_raw)
            except (json.JSONDecodeError, TypeError):
                tags = [t.strip() for t in tags_raw.split() if t.strip()]
        else:
            tags = tags_raw or []

        results.append(
            SparseResult(
                trace_id=row[0],
                cell_id=row[1],
                statement=row[2],
                rationale=row[3],
                tags=tags,
                kind=row[5],
                label=row[6] if isinstance(row[6], str) and row[6] else None,
                status=row[7] if isinstance(row[7], str) else str(row[7]),
                confidence=row[8],
                bm25_score=row[9],
            )
        )

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_cell_id(cell: Path) -> str:
    """Read cell_id from the Cell manifest."""
    manifest_path = cell / "config" / "cell_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Cell manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cell_id = manifest.get("cell_id")
    if not cell_id:
        raise ValueError("Cell manifest is missing cell_id")
    return str(cell_id)


def _clear_fts_for_cell(conn: sqlite3.Connection, cell_id: str) -> None:
    """Remove all FTS rows belonging to a cell."""
    conn.execute(
        "DELETE FROM traces_fts WHERE cell_id = ?",
        (cell_id,),
    )


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a user query for FTS5 MATCH.

    Normal word tokens are left unquoted so the porter stemmer can match
    inflected forms (e.g. "exception" matches "exceptions"). Tokens
    containing FTS5 special characters are quoted to avoid syntax errors.
    Tokens are joined with AND for implicit AND semantics.
    """
    # FTS5 special characters that need quoting
    _FTS5_SPECIAL = set('+-*():"^')
    tokens = query.split()
    if not tokens:
        return '""'
    sanitized: list[str] = []
    for token in tokens:
        if any(c in _FTS5_SPECIAL for c in token):
            sanitized.append(f'"{token}"')
        else:
            sanitized.append(token)
    return " AND ".join(sanitized)
