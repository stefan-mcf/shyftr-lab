"""Mechanical helpers for append-only effective-state reads.

These helpers deduplicate append-only ledger rows by logical key while preserving
first-seen order and keeping the latest values for each key.
"""
from __future__ import annotations

from typing import Any, Iterable


def latest_by_key(records: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Return records deduplicated by logical key.

    The first time a logical key appears establishes output order. Later rows for
    the same key replace the stored value so the returned record reflects the
    latest append-only state.
    """
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in records:
        value = record.get(key)
        if value is None:
            continue
        logical_key = str(value)
        if logical_key not in latest:
            order.append(logical_key)
        latest[logical_key] = record
    return [latest[logical_key] for logical_key in order]


def latest_record_by_key(records: Iterable[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    """Return the latest record whose logical key equals *value*."""
    latest: dict[str, Any] | None = None
    for record in records:
        if str(record.get(key) or "") == value:
            latest = record
    return latest
