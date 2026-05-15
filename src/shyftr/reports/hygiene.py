"""Read-only hygiene reports for ShyftR Cell ledgers.

Hygiene reporting explains memory health without mutating canonical ledgers.
The functions here read JSONL rows from a Cell and return deterministic plain
Python dictionaries/lists suitable for CLI output, tests, or review gates.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from shyftr.ledger import read_jsonl

PathLike = Union[str, Path]
JsonRecord = Dict[str, Any]


def fragment_status_counts(cell_path: PathLike) -> Dict[str, Dict[str, int]]:
    """Return Fragment boundary/review status distributions.

    Missing status fields are counted as ``pending`` to match the Fragment model
    defaults.  The return value uses sorted keys for deterministic output.
    """
    boundary: Counter[str] = Counter()
    review: Counter[str] = Counter()
    for fragment in _read_records(Path(cell_path) / "ledger" / "fragments.jsonl"):
        boundary[str(fragment.get("boundary_status") or "pending")] += 1
        review[str(fragment.get("review_status") or "pending")] += 1
    return {
        "boundary_status": _sorted_counts(boundary),
        "review_status": _sorted_counts(review),
    }


def trace_confidence_distribution(cell_path: PathLike) -> Dict[str, Any]:
    """Report Trace status counts and confidence bands across Trace ledgers."""
    rows = _trace_rows(cell_path)
    status_counts: Counter[str] = Counter()
    confidence_by_status: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        status = str(row.get("status") or row.get("ledger_status") or "unknown")
        status_counts[status] += 1
        confidence_by_status[status][_confidence_band(row.get("confidence"))] += 1

    return {
        "total": len(rows),
        "status_counts": _sorted_counts(status_counts),
        "confidence_bands": {
            status: _ordered_bands(counts)
            for status, counts in sorted(confidence_by_status.items())
        },
    }


def trace_decay_distribution(cell_path: PathLike) -> Dict[str, Any]:
    """Backward-compatible alias for confidence/decay distribution reports."""
    return trace_confidence_distribution(cell_path)


def missing_source_references(cell_path: PathLike) -> Dict[str, List[Dict[str, Any]]]:
    """Find unresolved Source and Fragment references.

    Reports:
    - Fragments whose ``source_id`` is not present in ``ledger/sources.jsonl``.
    - Traces whose ``source_fragment_ids`` are not present in
      ``ledger/fragments.jsonl``.
    """
    cell = Path(cell_path)
    source_ids = {
        str(row.get("source_id"))
        for row in _read_records(cell / "ledger" / "sources.jsonl")
        if row.get("source_id") is not None
    }
    fragment_rows = _read_records(cell / "ledger" / "fragments.jsonl")
    fragment_ids = {
        str(row.get("fragment_id"))
        for row in fragment_rows
        if row.get("fragment_id") is not None
    }

    missing_sources = []
    for row in fragment_rows:
        source_id = row.get("source_id")
        if source_id is not None and str(source_id) not in source_ids:
            missing_sources.append(
                {
                    "fragment_id": row.get("fragment_id"),
                    "source_id": source_id,
                    "cell_id": row.get("cell_id"),
                }
            )

    missing_fragments = []
    for row in _trace_rows(cell):
        unresolved = [
            fragment_id
            for fragment_id in row.get("source_fragment_ids", [])
            if str(fragment_id) not in fragment_ids
        ]
        if unresolved:
            missing_fragments.append(
                {
                    "trace_id": row.get("trace_id"),
                    "status": row.get("status"),
                    "ledger_status": row.get("ledger_status"),
                    "unresolved_fragment_ids": unresolved,
                }
            )

    return {
        "fragments_with_missing_sources": sorted(
            missing_sources, key=lambda item: str(item.get("fragment_id") or "")
        ),
        "traces_with_missing_fragments": sorted(
            missing_fragments, key=lambda item: str(item.get("trace_id") or "")
        ),
    }


def sweep_report(cell_path: PathLike, *, output_path: Optional[PathLike] = None) -> Dict[str, Any]:
    """Return a read-only Sweep dry-run report for a Cell."""
    from shyftr.sweep import run_sweep

    return run_sweep(cell_path, dry_run=True, output_path=output_path).to_dict()


def duplicate_traces(cell_path: PathLike) -> List[Dict[str, Any]]:
    """Return groups of Traces with case-insensitive identical statements."""
    groups: Dict[str, List[JsonRecord]] = defaultdict(list)
    canonical_statement: Dict[str, str] = {}
    for row in _trace_rows(cell_path):
        key = str(row.get("statement") or "").strip().lower()
        if not key:
            continue
        canonical_statement.setdefault(key, str(row.get("statement") or ""))
        groups[key].append(row)

    result = []
    for key, rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        result.append(
            {
                "statement": canonical_statement[key],
                "trace_ids": [
                    {
                        "trace_id": row.get("trace_id"),
                        "status": row.get("status"),
                        "ledger_status": row.get("ledger_status"),
                        "confidence": row.get("confidence"),
                    }
                    for row in sorted(rows, key=lambda item: str(item.get("trace_id") or ""))
                ],
            }
        )
    return result


def conflicting_traces(cell_path: PathLike) -> List[Dict[str, Any]]:
    """Detect simple opposite-polarity Trace conflicts sharing tags.

    This deterministic heuristic mirrors the Alloy conflict detector style:
    same tag overlap + one statement with negation and one without + sparse
    lexical overlap.
    """
    rows = _trace_rows(cell_path)
    conflicts: List[Dict[str, Any]] = []
    for index, left in enumerate(rows):
        left_tags = set(left.get("tags") or [])
        left_tokens = _tokenize(str(left.get("statement") or ""))
        left_negated = _has_negation(left_tokens)
        for right in rows[index + 1 :]:
            tag_overlap = left_tags & set(right.get("tags") or [])
            if not tag_overlap:
                continue
            right_tokens = _tokenize(str(right.get("statement") or ""))
            if left_negated == _has_negation(right_tokens):
                continue
            if _jaccard(left_tokens, right_tokens) <= 0.30:
                continue
            conflicts.append(
                {
                    "trace_ids": sorted([left.get("trace_id"), right.get("trace_id")]),
                    "shared_tags": sorted(tag_overlap),
                    "statements": {
                        str(left.get("trace_id")): left.get("statement"),
                        str(right.get("trace_id")): right.get("statement"),
                    },
                }
            )
    return sorted(conflicts, key=lambda item: tuple(item["trace_ids"]))


def hygiene_report(cell_path: PathLike) -> Dict[str, Any]:
    """Return the combined read-only hygiene report for a Cell."""
    from shyftr.audit import audit_summary

    return {
        "fragment_status_counts": fragment_status_counts(cell_path),
        "trace_confidence_distribution": trace_confidence_distribution(cell_path),
        "missing_source_references": missing_source_references(cell_path),
        "duplicate_traces": duplicate_traces(cell_path),
        "conflicting_traces": conflicting_traces(cell_path),
        "audit_findings": audit_summary(cell_path),
        "miss_summary": miss_summary(cell_path),
        "misses_by_category": misses_by_category(cell_path),
        "most_missed_charges": most_missed_charges(cell_path),
        "most_over_retrieved_charges": most_over_retrieved_charges(cell_path),
        "high_confidence_missed_charges": high_confidence_missed_charges(cell_path),
        "charges_with_mixed_signal": charges_with_mixed_signal(cell_path),
    }


# ---------------------------------------------------------------------------
# Pack miss summary functions
# ---------------------------------------------------------------------------


def miss_summary(cell_path: PathLike) -> Dict[str, Any]:
    """Return miss-related summary statistics across all Outcome records.

    Reports:
    - ``total_misses``: total number of pack miss records across all Outcomes
    - ``misses_by_type``: count per ``miss_type`` (not_relevant, not_actionable,
      contradicted, duplicative, unknown)
    - ``total_charges_with_misses``: number of unique charge IDs that appear
      as misses
    """

    miss_counts, by_type, _over = _miss_counters(cell_path)

    return {
        "total_misses": sum(miss_counts.values()),
        "misses_by_type": dict(sorted(by_type.items())),
        "total_charges_with_misses": len(miss_counts),
    }


def misses_by_category(cell_path: PathLike) -> Dict[str, int]:
    """Return miss counts grouped by miss_type category.

    Convenience view that omits the charge-level detail and just presents
    aggregate counts per ``miss_type``.
    """
    summary = miss_summary(cell_path)
    return dict(summary.get("misses_by_type", {}))


def most_missed_charges(cell_path: PathLike, limit: int = 10) -> List[Dict[str, Any]]:
    """Return the most frequently missed Charges/Traces."""
    counts, _types, _over = _miss_counters(cell_path)
    return [
        {"charge_id": charge_id, "miss_count": count}
        for charge_id, count in counts.most_common(limit)
    ]


def most_over_retrieved_charges(cell_path: PathLike, limit: int = 10) -> List[Dict[str, Any]]:
    """Return Charges/Traces most often marked as over-retrieved."""
    _counts, _types, over = _miss_counters(cell_path)
    return [
        {"charge_id": charge_id, "over_retrieved_count": count}
        for charge_id, count in over.most_common(limit)
    ]


def high_confidence_missed_charges(
    cell_path: PathLike, min_confidence: float = 0.67
) -> List[Dict[str, Any]]:
    """Return high-confidence Charges/Traces that also have miss history."""
    miss_counts, _types, _over = _miss_counters(cell_path)
    trace_by_id = {str(row.get("trace_id")): row for row in _trace_rows(cell_path)}
    result = []
    for charge_id, count in miss_counts.most_common():
        row = trace_by_id.get(charge_id)
        if not row:
            continue
        confidence = row.get("confidence")
        if isinstance(confidence, (int, float)) and confidence >= min_confidence:
            result.append(
                {
                    "charge_id": charge_id,
                    "miss_count": count,
                    "confidence": confidence,
                    "ledger_status": row.get("ledger_status"),
                    "status": row.get("status"),
                }
            )
    return result


def charges_with_mixed_signal(cell_path: PathLike) -> List[Dict[str, Any]]:
    """Return charge IDs that appear as both useful and harmful in any Outcome.

    A "mixed signal" charge is one where different outcomes or loadouts
    disagreed: in one context it was helpful, in another harmful. These
    are candidates for review but are not automatically penalised.
    """
    outcomes = _read_outcome_records(cell_path)
    per_charge: Dict[str, Dict[str, set[str]]] = defaultdict(
        lambda: {"useful_outcomes": set(), "harmful_outcomes": set()}
    )

    for outcome in outcomes:
        meta = outcome.get("metadata", {})
        oid = outcome.get("outcome_id", "")
        for tid in meta.get("useful_trace_ids", []):
            per_charge[str(tid)]["useful_outcomes"].add(oid)
        for tid in meta.get("harmful_trace_ids", []):
            per_charge[str(tid)]["harmful_outcomes"].add(oid)

    result = []
    for charge_id in sorted(per_charge):
        info = per_charge[charge_id]
        if info["useful_outcomes"] and info["harmful_outcomes"]:
            result.append(
                {
                    "charge_id": charge_id,
                    "useful_outcomes": sorted(info["useful_outcomes"]),
                    "harmful_outcomes": sorted(info["harmful_outcomes"]),
                }
            )
    return result


def _miss_counters(cell_path: PathLike) -> Tuple[Counter[str], Counter[str], Counter[str]]:
    """Return miss, miss-type, and over-retrieval counters for Outcome rows."""
    miss_counts: Counter[str] = Counter()
    miss_types: Counter[str] = Counter()
    over_counts: Counter[str] = Counter()

    for outcome in _read_outcome_records(cell_path):
        miss_rows = outcome.get("pack_miss_details") or outcome.get("pack_misses", [])
        for pm in miss_rows:
            if isinstance(pm, dict):
                charge_id = str(pm.get("charge_id") or "")
                miss_type = str(pm.get("miss_type") or "unknown")
            else:
                charge_id = str(pm)
                miss_type = "unknown"
            if not charge_id:
                continue
            miss_counts[charge_id] += 1
            miss_types[miss_type] += 1

        for charge_id in outcome.get("over_retrieved_charge_ids", []):
            over_counts[str(charge_id)] += 1

    return miss_counts, miss_types, over_counts


def _read_outcome_records(cell_path: PathLike) -> List[JsonRecord]:
    """Read all Outcome rows from ledger/outcomes.jsonl."""
    path = Path(cell_path) / "ledger" / "outcomes.jsonl"
    return _read_records(path)


def _read_records(path: PathLike) -> List[JsonRecord]:
    path = Path(path)
    if not path.exists():
        return []
    return [record for _line, record in read_jsonl(path)]


def _trace_rows(cell_path: PathLike) -> List[JsonRecord]:
    cell = Path(cell_path)
    rows: List[JsonRecord] = []
    for ledger_status, relpath in (
        ("approved", "traces/approved.jsonl"),
        ("deprecated", "traces/deprecated.jsonl"),
        ("proposed", "traces/proposed.jsonl"),
    ):
        for row in _read_records(cell / relpath):
            rows.append({**row, "ledger_status": ledger_status})
    return rows


def _confidence_band(value: Any) -> str:
    if value is None:
        return "none"
    if value <= 0.33:
        return "low"
    if value <= 0.66:
        return "medium"
    return "high"


def _ordered_bands(counter: Counter[str]) -> Dict[str, int]:
    return {band: counter.get(band, 0) for band in ("none", "low", "medium", "high")}


def _sorted_counts(counter: Counter[str]) -> Dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _tokenize(text: str) -> set[str]:
    tokens = set()
    for word in text.lower().split():
        token = "".join(ch for ch in word if ch.isalnum())
        if token:
            tokens.add(token)
    return tokens


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _has_negation(tokens: Iterable[str]) -> bool:
    return bool(set(tokens) & {"never", "not", "no", "cannot", "dont", "dont", "shouldnt", "mustnt"})
