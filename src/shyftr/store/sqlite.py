"""Rebuildable SQLite metadata and audit views over ShyftR JSONL ledgers.

SQLite is acceleration/materialization only. JSONL ledgers remain canonical
truth. The entire SQLite database can be deleted and rebuilt deterministically
from the Cell's JSONL files.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..ledger import (
    read_audit_reviews,
    read_audit_sparks,
    read_confidence_events,
    read_jsonl,
    read_retrieval_affinity_events,
)

from ..memory_classes import resolve_memory_type

PathLike = Union[str, Path]


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


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_TABLES_DDL = """
CREATE TABLE IF NOT EXISTS sources (
    source_id   TEXT PRIMARY KEY,
    cell_id     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    uri         TEXT,
    metadata    TEXT
);

CREATE TABLE IF NOT EXISTS fragments (
    fragment_id     TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    cell_id         TEXT NOT NULL,
    kind            TEXT NOT NULL,
    text            TEXT NOT NULL,
    source_excerpt  TEXT,
    boundary_status TEXT NOT NULL DEFAULT 'pending',
    review_status   TEXT NOT NULL DEFAULT 'pending',
    confidence      REAL,
    tags            TEXT
);

CREATE TABLE IF NOT EXISTS traces (
    trace_id              TEXT PRIMARY KEY,
    cell_id               TEXT NOT NULL,
    statement             TEXT NOT NULL,
    source_fragment_ids   TEXT NOT NULL,
    memory_type           TEXT,
    rationale             TEXT,
    status                TEXT NOT NULL DEFAULT 'proposed',
    confidence            REAL,
    tags                  TEXT,
    use_count             INTEGER NOT NULL DEFAULT 0,
    success_count         INTEGER NOT NULL DEFAULT 0,
    failure_count         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id       TEXT PRIMARY KEY,
    fragment_id     TEXT NOT NULL,
    review_action   TEXT NOT NULL,
    review_status   TEXT NOT NULL,
    reviewed_at     TEXT NOT NULL,
    reviewer        TEXT NOT NULL,
    rationale       TEXT NOT NULL,
    metadata        TEXT,
    review_sequence INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS promotions (
    promotion_id         TEXT PRIMARY KEY,
    fragment_id          TEXT NOT NULL,
    trace_id             TEXT NOT NULL,
    source_id            TEXT,
    source_fragment_ids  TEXT,
    promoted_at          TEXT NOT NULL,
    promoter             TEXT NOT NULL,
    review_id            TEXT
);

CREATE TABLE IF NOT EXISTS retrieval_logs (
    retrieval_id  TEXT PRIMARY KEY,
    cell_id       TEXT NOT NULL,
    query         TEXT,
    selected_ids  TEXT,
    score_traces  TEXT,
    logged_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id   TEXT PRIMARY KEY,
    cell_id      TEXT NOT NULL,
    loadout_id   TEXT NOT NULL,
    task_id      TEXT NOT NULL,
    verdict      TEXT NOT NULL,
    trace_ids    TEXT,
    score        REAL,
    observed_at  TEXT,
    metadata     TEXT
);

CREATE TABLE IF NOT EXISTS confidence_events (
    confidence_event_id TEXT PRIMARY KEY,
    cell_id             TEXT NOT NULL,
    fragment_id         TEXT,
    confidence          REAL,
    reason              TEXT,
    observed_at         TEXT
);

CREATE TABLE IF NOT EXISTS retrieval_affinity_events (
    affinity_event_id TEXT PRIMARY KEY,
    cell_id           TEXT NOT NULL,
    query             TEXT,
    result_id         TEXT,
    score             REAL,
    observed_at       TEXT
);

CREATE TABLE IF NOT EXISTS audit_sparks (
    spark_id    TEXT PRIMARY KEY,
    cell_id     TEXT NOT NULL,
    fragment_id TEXT,
    action      TEXT,
    rationale   TEXT,
    observed_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_reviews (
    review_id     TEXT PRIMARY KEY,
    cell_id       TEXT NOT NULL,
    spark_id      TEXT,
    decision      TEXT,
    reviewer      TEXT,
    reviewed_at   TEXT,
    rationale     TEXT
);

CREATE TABLE IF NOT EXISTS lifecycle_events (
    event_id              TEXT PRIMARY KEY,
    cell_id               TEXT NOT NULL,
    charge_id             TEXT NOT NULL,
    action                TEXT NOT NULL,
    status                TEXT,
    replacement_charge_id TEXT,
    related_charge_ids    TEXT,
    actor                 TEXT,
    reason                TEXT,
    created_at            TEXT NOT NULL,
    ledger_name           TEXT NOT NULL,
    event_sequence        INTEGER NOT NULL,
    event_json            TEXT NOT NULL
);
"""

_VIEWS_DDL = """
DROP VIEW IF EXISTS v_latest_fragment_review;
DROP VIEW IF EXISTS v_trace_lifecycle;
DROP VIEW IF EXISTS v_latest_charge_lifecycle_event;

CREATE VIEW v_latest_fragment_review AS
SELECT
    ranked.fragment_id,
    ranked.review_action,
    ranked.review_status,
    ranked.reviewer,
    ranked.rationale,
    ranked.reviewed_at,
    ranked.review_sequence
FROM (
    SELECT
        r.fragment_id,
        r.review_action,
        r.review_status,
        r.reviewer,
        r.rationale,
        r.reviewed_at,
        r.review_sequence,
        ROW_NUMBER() OVER (
            PARTITION BY r.fragment_id
            ORDER BY r.reviewed_at DESC, r.review_sequence DESC
        ) AS review_rank
    FROM reviews r
) ranked
WHERE ranked.review_rank = 1;

CREATE VIEW v_latest_charge_lifecycle_event AS
SELECT
    ranked.charge_id,
    ranked.action,
    ranked.status,
    ranked.replacement_charge_id,
    ranked.actor,
    ranked.reason,
    ranked.created_at,
    ranked.event_id,
    ranked.ledger_name,
    ranked.event_sequence
FROM (
    SELECT
        le.*,
        ROW_NUMBER() OVER (
            PARTITION BY le.charge_id
            ORDER BY le.created_at DESC, le.event_sequence DESC, le.event_id DESC
        ) AS lifecycle_rank
    FROM lifecycle_events le
    WHERE le.action IN ('forget', 'replace', 'deprecate', 'isolate', 'redact')
       OR le.status IN ('forgotten', 'superseded', 'deprecated', 'isolated', 'redacted')
) ranked
WHERE ranked.lifecycle_rank = 1;

CREATE VIEW v_trace_lifecycle AS
SELECT
    t.trace_id,
    t.cell_id,
    t.statement,
    t.status,
    t.confidence,
    t.use_count,
    t.success_count,
    t.failure_count,
    COALESCE(
        CASE
            WHEN le.action = 'forget' THEN 'forgotten'
            WHEN le.action = 'replace' THEN 'superseded'
            WHEN le.action = 'deprecate' THEN 'deprecated'
            WHEN le.action = 'isolate' THEN 'isolated'
            WHEN le.action = 'redact' THEN 'redacted'
            ELSE le.status
        END,
        CASE
            WHEN t.status = 'approved' THEN 'current'
            WHEN t.status = 'deprecated' THEN 'deprecated'
            ELSE 'pending'
        END
    ) AS lifecycle_state,
    CASE
        WHEN COALESCE(le.action, le.status) IN ('forget', 'forgotten', 'replace', 'superseded', 'deprecate', 'deprecated', 'isolate', 'isolated', 'redact', 'redacted') THEN 0
        ELSE 1
    END AS include_in_retrieval,
    CASE
        WHEN COALESCE(le.action, le.status) IN ('forget', 'forgotten', 'replace', 'superseded', 'deprecate', 'deprecated', 'isolate', 'isolated', 'redact', 'redacted') THEN 0
        ELSE 1
    END AS include_in_profile,
    CASE
        WHEN COALESCE(le.action, le.status) IN ('forget', 'forgotten', 'replace', 'superseded', 'deprecate', 'deprecated', 'isolate', 'isolated', 'redact', 'redacted') THEN 0
        ELSE 1
    END AS include_in_pack,
    le.replacement_charge_id,
    le.event_id AS latest_lifecycle_event_id,
    le.created_at AS latest_lifecycle_event_at
FROM traces t
LEFT JOIN v_latest_charge_lifecycle_event le ON le.charge_id = t.trace_id;
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    """Bring older materialized stores up to the current schema."""
    review_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(reviews)").fetchall()
    }
    if "review_sequence" not in review_columns:
        conn.execute(
            "ALTER TABLE reviews "
            "ADD COLUMN review_sequence INTEGER NOT NULL DEFAULT 0"
        )

    trace_columns = {row[1] for row in conn.execute("PRAGMA table_info(traces)").fetchall()}
    if "memory_type" not in trace_columns:
        conn.execute("ALTER TABLE traces ADD COLUMN memory_type TEXT")


def open_sqlite(db_path: PathLike) -> sqlite3.Connection:
    """Open (or create) a SQLite database in WAL mode with schema applied.

    Parent directories are created as needed.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_TABLES_DDL)
    _ensure_schema_migrations(conn)
    conn.executescript(_VIEWS_DDL)
    conn.commit()
    return conn


def rebuild_from_cell(conn: sqlite3.Connection, cell_path: PathLike) -> None:
    """Deterministically rebuild all SQLite tables from a Cell's JSONL ledgers.

    Existing rows for this cell are cleared and repopulated. This is
    idempotent: running rebuild twice produces the same result. Multiple
    cells can coexist in the same database.
    """
    cell = Path(cell_path)
    cell_id = _read_cell_id(cell)

    # Clear rows belonging to this cell.
    # reviews/promotions don't have cell_id, so clear them first via fragment/trace joins.
    conn.execute(
        "DELETE FROM reviews WHERE fragment_id IN "
        "(SELECT fragment_id FROM fragments WHERE cell_id = ?)",
        (cell_id,),
    )
    conn.execute(
        "DELETE FROM promotions WHERE trace_id IN "
        "(SELECT trace_id FROM traces WHERE cell_id = ?)",
        (cell_id,),
    )
    conn.execute(
        "DELETE FROM promotions WHERE fragment_id IN "
        "(SELECT fragment_id FROM fragments WHERE cell_id = ?)",
        (cell_id,),
    )
    for table in ("outcomes", "retrieval_logs", "traces", "fragments", "sources",
                   "audit_reviews", "audit_sparks",
                   "retrieval_affinity_events", "confidence_events", "lifecycle_events"):
        conn.execute(f"DELETE FROM {table} WHERE cell_id = ?", (cell_id,))

    # 1. Sources
    _rebuild_sources(conn, cell)

    # 2. Fragments
    _rebuild_fragments(conn, cell)

    # 3. Traces (approved)
    _rebuild_traces(conn, cell)

    # 4. Reviews
    _rebuild_reviews(conn, cell)

    # 5. Promotions
    _rebuild_promotions(conn, cell)

    # 6. Retrieval logs
    _rebuild_retrieval_logs(conn, cell)

    # 7. Outcomes
    _rebuild_outcomes(conn, cell)

    # 8. Confidence events (AL-1)
    _rebuild_confidence_events(conn, cell)

    # 9. Retrieval affinity events (AL-1)
    _rebuild_retrieval_affinity_events(conn, cell)

    # 10. Audit sparks (AL-1)
    _rebuild_audit_sparks(conn, cell)

    # 11. Audit reviews (AL-1)
    _rebuild_audit_reviews(conn, cell)

    # 12. Lifecycle mutation events (UMS-4)
    _rebuild_lifecycle_events(conn, cell)

    conn.commit()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def latest_review_for_fragment(
    conn: sqlite3.Connection, fragment_id: str
) -> Optional[Dict[str, Any]]:
    """Return the latest review event for a fragment, or None."""
    row = conn.execute(
        "SELECT * FROM v_latest_fragment_review WHERE fragment_id = ?",
        (fragment_id,),
    ).fetchone()
    if row is None:
        return None
    cols = [d[0] for d in conn.execute(
        "SELECT * FROM v_latest_fragment_review LIMIT 0"
    ).description]
    return dict(zip(cols, row))


def trace_lifecycle_view(
    conn: sqlite3.Connection, cell_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return the trace lifecycle view, optionally filtered by cell_id."""
    if cell_id:
        rows = conn.execute(
            "SELECT * FROM v_trace_lifecycle WHERE cell_id = ?", (cell_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM v_trace_lifecycle").fetchall()
    cols = [d[0] for d in conn.execute(
        "SELECT * FROM v_trace_lifecycle LIMIT 0"
    ).description]
    return [dict(zip(cols, row)) for row in rows]


# ---------------------------------------------------------------------------
# Internal rebuild helpers
# ---------------------------------------------------------------------------

def _rebuild_sources(conn: sqlite3.Connection, cell: Path) -> None:
    ledger = cell / "ledger" / "sources.jsonl"
    if not ledger.exists():
        return
    for _, record in read_jsonl(ledger):
        conn.execute(
            "INSERT OR REPLACE INTO sources "
            "(source_id, cell_id, kind, sha256, captured_at, uri, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("source_id"),
                record.get("cell_id"),
                record.get("kind"),
                record.get("sha256"),
                record.get("captured_at"),
                record.get("uri"),
                json.dumps(record.get("metadata"), sort_keys=True)
                if record.get("metadata") is not None else None,
            ),
        )


def _rebuild_fragments(conn: sqlite3.Connection, cell: Path) -> None:
    ledger = cell / "ledger" / "fragments.jsonl"
    if not ledger.exists():
        return
    for _, record in read_jsonl(ledger):
        conn.execute(
            "INSERT OR REPLACE INTO fragments "
            "(fragment_id, source_id, cell_id, kind, text, source_excerpt, "
            " boundary_status, review_status, confidence, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("fragment_id"),
                record.get("source_id"),
                record.get("cell_id"),
                record.get("kind"),
                record.get("text"),
                record.get("source_excerpt"),
                record.get("boundary_status", "pending"),
                record.get("review_status", "pending"),
                record.get("confidence"),
                json.dumps(record.get("tags", []), sort_keys=True),
            ),
        )


def _rebuild_traces(conn: sqlite3.Connection, cell: Path) -> None:
    ledger = cell / "traces" / "approved.jsonl"
    if not ledger.exists():
        return
    for _, record in read_jsonl(ledger):
        conn.execute(
            "INSERT OR REPLACE INTO traces "
            "(trace_id, cell_id, statement, source_fragment_ids, memory_type, rationale, "
            " status, confidence, tags, use_count, success_count, failure_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("trace_id"),
                record.get("cell_id"),
                record.get("statement"),
                json.dumps(record.get("source_fragment_ids", []), sort_keys=True),
                resolve_memory_type(record.get("memory_type"), kind=record.get("kind"), trust_tier="trace"),
                record.get("rationale"),
                record.get("status", "proposed"),
                record.get("confidence"),
                json.dumps(record.get("tags", []), sort_keys=True),
                record.get("use_count", 0),
                record.get("success_count", 0),
                record.get("failure_count", 0),
            ),
        )


def _rebuild_reviews(conn: sqlite3.Connection, cell: Path) -> None:
    ledger = cell / "ledger" / "reviews.jsonl"
    if not ledger.exists():
        return
    for line_number, record in read_jsonl(ledger):
        conn.execute(
            "INSERT OR REPLACE INTO reviews "
            "(review_id, fragment_id, review_action, review_status, "
            " reviewed_at, reviewer, rationale, metadata, review_sequence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("review_id"),
                record.get("fragment_id"),
                record.get("review_action"),
                record.get("review_status"),
                record.get("reviewed_at"),
                record.get("reviewer"),
                record.get("rationale"),
                json.dumps(record.get("metadata"), sort_keys=True)
                if record.get("metadata") is not None else None,
                line_number,
            ),
        )


def _rebuild_promotions(conn: sqlite3.Connection, cell: Path) -> None:
    ledger = cell / "ledger" / "promotions.jsonl"
    if not ledger.exists():
        return
    for _, record in read_jsonl(ledger):
        conn.execute(
            "INSERT OR REPLACE INTO promotions "
            "(promotion_id, fragment_id, trace_id, source_id, "
            " source_fragment_ids, promoted_at, promoter, review_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("promotion_id"),
                record.get("fragment_id"),
                record.get("trace_id"),
                record.get("source_id"),
                json.dumps(record.get("source_fragment_ids", []), sort_keys=True)
                if record.get("source_fragment_ids") is not None else None,
                record.get("promoted_at"),
                record.get("promoter"),
                record.get("review_id"),
            ),
        )


def _rebuild_retrieval_logs(conn: sqlite3.Connection, cell: Path) -> None:
    ledger = cell / "ledger" / "retrieval_logs.jsonl"
    if not ledger.exists():
        return
    for _, record in read_jsonl(ledger):
        conn.execute(
            "INSERT OR REPLACE INTO retrieval_logs "
            "(retrieval_id, cell_id, query, selected_ids, score_traces, logged_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.get("retrieval_id"),
                record.get("cell_id") or _read_cell_id(cell),
                record.get("query"),
                json.dumps(record.get("selected_ids", []), sort_keys=True)
                if record.get("selected_ids") is not None else None,
                json.dumps(record.get("score_traces"), sort_keys=True)
                if record.get("score_traces") is not None else None,
                record.get("logged_at") or record.get("generated_at"),
            ),
        )


def _rebuild_outcomes(conn: sqlite3.Connection, cell: Path) -> None:
    ledger = cell / "ledger" / "outcomes.jsonl"
    if not ledger.exists():
        return
    for _, record in read_jsonl(ledger):
        conn.execute(
            "INSERT OR REPLACE INTO outcomes "
            "(outcome_id, cell_id, loadout_id, task_id, verdict, "
            " trace_ids, score, observed_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("outcome_id"),
                record.get("cell_id"),
                record.get("loadout_id"),
                record.get("task_id"),
                record.get("verdict"),
                json.dumps(record.get("trace_ids", []), sort_keys=True),
                record.get("score"),
                record.get("observed_at"),
                json.dumps(record.get("metadata"), sort_keys=True)
                if record.get("metadata") is not None else None,
            ),
        )


def _rebuild_confidence_events(conn: sqlite3.Connection, cell: Path) -> None:
    """Rebuild confidence_events from ledger/confidence_events.jsonl."""
    ledger = cell / "ledger" / "confidence_events.jsonl"
    if not ledger.exists():
        return
    for _, record in read_confidence_events(cell):
        conn.execute(
            "INSERT OR REPLACE INTO confidence_events "
            "(confidence_event_id, cell_id, fragment_id, confidence, reason, observed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.get("confidence_event_id"),
                record.get("cell_id"),
                record.get("fragment_id"),
                record.get("confidence"),
                record.get("reason"),
                record.get("observed_at"),
            ),
        )


def _rebuild_retrieval_affinity_events(conn: sqlite3.Connection, cell: Path) -> None:
    """Rebuild retrieval_affinity_events from ledger/retrieval_affinity_events.jsonl."""
    ledger = cell / "ledger" / "retrieval_affinity_events.jsonl"
    if not ledger.exists():
        return
    for _, record in read_retrieval_affinity_events(cell):
        conn.execute(
            "INSERT OR REPLACE INTO retrieval_affinity_events "
            "(affinity_event_id, cell_id, query, result_id, score, observed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.get("affinity_event_id"),
                record.get("cell_id"),
                record.get("query"),
                record.get("result_id"),
                record.get("score"),
                record.get("observed_at"),
            ),
        )


def _rebuild_audit_sparks(conn: sqlite3.Connection, cell: Path) -> None:
    """Rebuild audit_sparks from ledger/audit_sparks.jsonl."""
    ledger = cell / "ledger" / "audit_sparks.jsonl"
    if not ledger.exists():
        return
    for _, record in read_audit_sparks(cell):
        conn.execute(
            "INSERT OR REPLACE INTO audit_sparks "
            "(spark_id, cell_id, fragment_id, action, rationale, observed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.get("spark_id"),
                record.get("cell_id"),
                record.get("fragment_id"),
                record.get("action"),
                record.get("rationale"),
                record.get("observed_at"),
            ),
        )


def _rebuild_audit_reviews(conn: sqlite3.Connection, cell: Path) -> None:
    """Rebuild audit_reviews from ledger/audit_reviews.jsonl."""
    ledger = cell / "ledger" / "audit_reviews.jsonl"
    if not ledger.exists():
        return
    for _, record in read_audit_reviews(cell):
        conn.execute(
            "INSERT OR REPLACE INTO audit_reviews "
            "(review_id, cell_id, spark_id, decision, reviewer, reviewed_at, rationale) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("review_id"),
                record.get("cell_id"),
                record.get("spark_id"),
                record.get("decision"),
                record.get("reviewer"),
                record.get("reviewed_at"),
                record.get("rationale"),
            ),
        )


def _rebuild_lifecycle_events(conn: sqlite3.Connection, cell: Path) -> None:
    """Rebuild append-only lifecycle mutation events from UMS-4 ledgers."""
    cell_id = _read_cell_id(cell)
    ledgers = (
        ("status_events", cell / "ledger" / "status_events.jsonl"),
        ("supersession_events", cell / "ledger" / "supersession_events.jsonl"),
        ("deprecation_events", cell / "ledger" / "deprecation_events.jsonl"),
        ("isolation_events", cell / "ledger" / "isolation_events.jsonl"),
        ("conflict_events", cell / "ledger" / "conflict_events.jsonl"),
        ("redaction_events", cell / "ledger" / "redaction_events.jsonl"),
        ("memory_provider_events", cell / "ledger" / "memory_provider_events.jsonl"),
    )
    sequence = 0
    for ledger_name, ledger in ledgers:
        if not ledger.exists():
            continue
        for line_number, record in read_jsonl(ledger):
            sequence += 1
            action = str(record.get("action") or _action_from_ledger_name(ledger_name))
            charge_id = (
                record.get("charge_id")
                or record.get("old_charge_id")
                or record.get("left_charge_id")
            )
            if not isinstance(charge_id, str) or not charge_id:
                continue
            related = record.get("charge_ids")
            if related is None:
                related = [value for value in (record.get("left_charge_id"), record.get("right_charge_id")) if value]
            event_id = record.get("event_id") or f"{ledger_name}-{line_number}"
            status = record.get("status")
            if status is None and action == "forget":
                status = "forgotten"
            elif status is None and action == "replace":
                status = "superseded"
            elif status is None and action == "deprecate":
                status = "deprecated"
            elif status is None and action == "isolate":
                status = "isolated"
            elif status is None and action == "redact":
                status = "redacted"
            conn.execute(
                "INSERT OR REPLACE INTO lifecycle_events "
                "(event_id, cell_id, charge_id, action, status, replacement_charge_id, "
                " related_charge_ids, actor, reason, created_at, ledger_name, "
                " event_sequence, event_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    cell_id,
                    charge_id,
                    action,
                    status,
                    record.get("replacement_charge_id") or record.get("new_charge_id"),
                    json.dumps(related or [], sort_keys=True),
                    record.get("actor"),
                    record.get("reason"),
                    record.get("created_at") or record.get("observed_at") or "",
                    ledger_name,
                    sequence,
                    json.dumps(record, sort_keys=True),
                ),
            )


def _action_from_ledger_name(ledger_name: str) -> str:
    return {
        "status_events": "status",
        "supersession_events": "replace",
        "deprecation_events": "deprecate",
        "isolation_events": "isolate",
        "conflict_events": "conflict",
        "redaction_events": "redact",
    }.get(ledger_name, ledger_name)
