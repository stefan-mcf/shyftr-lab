# Phase 1 Research-Hardened Implementation Guide
## Local-First Event-Sourced Schema Migrations & Backward-Compatible API Deprecation

This document provides implementation-actionable design patterns for Phase 1
of the ShyftR roadmap. Every recommendation is anchored to concrete code
paths confirmed in the current source.

---

## 1. Event-Sourced Schema Migration Pattern: Ledger Adapter Layer

### Problem
ShyftR has two co-existing ontologies: a legacy internal vocabulary
(sources.jsonl, fragments.jsonl, traces/approved.jsonl, charge/pulse) and the
newer public vocabulary (evidence, candidates, memory, pack, feedback).  The
SQLite projection schema still reflects the legacy layer. New code imports
from both pack.py and loadout.py which are near-duplicates with identical
class definitions (RetrievalLog at pack.py:220 and loadout.py:263).

### Pattern: Adapter-Before-Canonicity
Do NOT rename ledger files or restructure the cell directory layout in Phase 1.
Instead, add a thin adapter layer that normalizes reads:

```
canonical_read(trace_id, cell_path) -> latest_row_wins
```

The principle: *ledger files on disk stay as they are; every read path
goes through a single canonical reader that knows how to collapse
append-only duplicates.*

### Concrete implementation plan

**Step 1: Create `src/shyftr/canonical.py`** (single source of truth for reads)

```python
# canonical.py — the ONE place that reads append-only ledgers with correct
# latest-row-wins semantics. All other modules must go through this.

def latest_trace_by_id(cell_path: PathLike, trace_id: str) -> Optional[dict]:
    """Return the MOST RECENT row for trace_id from traces/approved.jsonl.
    Fixes the stale-read in confidence._trace_by_id which returns the FIRST row."""
    ...

def approved_traces(cell_path: PathLike) -> list[dict]:
    """Return latest-row-wins projection of all approved traces.
    Replaces the current two diverging implementations:
      - confidence._trace_by_id (FIRST-match, BUG)
      - mutations.approved_traces (latest-row-wins, CORRECT)"""
    ...

def write_retrieval_log(cell_path: PathLike, log: RetrievalLog) -> None:
    """Append to ledger/retrieval_logs.jsonl with cell_id AND logged_at.
    Fixes the mismatch where RetrievalLog.to_dict() emits generated_at but
    _rebuild_retrieval_logs expects cell_id and logged_at."""
    ...
```

**Step 2: Migrate callers one by one**
- `confidence._trace_by_id()` → `canonical.latest_trace_by_id()`
- `confidence._read_traces()` → `canonical.approved_traces()`
- Any direct `read_jsonl(ledger)` call that needs latest-row → `canonical.*`
- `RetrievalLog.to_dict()` → add `cell_id` and `logged_at` fields (or wrap in `canonical.write_retrieval_log`)

**Step 3: Add a terminology alias map**
A single module (`src/shyftr/terminology.py`) that maps between legacy and
public terms, consumed by docs/status checks but never by core logic:

```python
LEGACY_TO_PUBLIC = {
    "source": "evidence",
    "fragment": "candidate",
    "trace": "memory",
    "charge": "memory item",
    "pulse": "ingest event",
    "spark": "audit trigger",
}
```

The core code stays with one canonical term per concept. The alias map
exists ONLY for the compatibility surface (CLI help text, status page,
terminology guard CI check).

---

## 2. Latest-Row-Wins Semantics: The ONE Rule

### The rule
For every append-only JSONL ledger, the effective/canonical state of a
row identified by its logical key is the **last** row with that key.

### Where it's currently violated
`confidence.py:99-104` — `_trace_by_id()` scans with `read_jsonl()` and
returns on first match. The caller then reads `old_confidence` from the
stale first row, computes `new_confidence` from the stale value, and
appends a new row. After N updates, the confidence value is N * delta
from the ORIGINAL value, not from the most recent.

**Fix**: Change `_trace_by_id()` to scan the full ledger and keep the
last match per `trace_id`. This is a one-line logic change (remove the
early return) plus a test.

### Test that must pass
```python
def test_confidence_reads_latest_not_first(tmp_path):
    cell = _make_cell(tmp_path)
    _seed_traces(cell, [_make_trace("t1", confidence=0.5)])

    # First adjustment
    adjust_confidence(cell, "oc-1", useful_trace_ids=["t1"],
                      harmful_trace_ids=[], result="success")
    # Second adjustment — must read the 0.55 from the appended row, not 0.5
    adjustments = adjust_confidence(cell, "oc-2", useful_trace_ids=["t1"],
                                    harmful_trace_ids=[], result="success")
    assert adjustments[0].old_confidence == pytest.approx(0.55)
    assert adjustments[0].new_confidence == pytest.approx(0.60)
```

### Generalize: add a ledger helper
```python
def latest_rows(records: Iterator[tuple[int, dict]], key: str) -> dict[str, dict]:
    """Collapse append-only stream to latest-row-per-key."""
    result = {}
    for _, record in records:
        result[record[key]] = record
    return result
```

---

## 3. Retrieval Log Projection Fix

### The mismatch
`RetrievalLog.to_dict()` (loadout.py:276-287, identical in pack.py:233-244):

```python
def to_dict(self):
    return {
        "retrieval_id": ...,
        "loadout_id": ...,      # present
        "generated_at": ...,    # present
        # cell_id: MISSING
        # logged_at: MISSING
    }
```

`_rebuild_retrieval_logs()` (sqlite.py:544-562) expects:

```python
record.get("cell_id")     # will be None — silently wrong
record.get("logged_at")   # will be None — silently wrong
```

### Fix (two options, pick ONE)

**Option A (minimal):** Add `cell_id` and `logged_at` fields to `RetrievalLog`
dataclass and its `to_dict()`, matching what the SQLite projection expects.

**Option B (cleaner):** Have `_rebuild_retrieval_logs()` derive `cell_id` from
the cell manifest (as other rebuilders do) and derive `logged_at` from
`generated_at` if `logged_at` is missing:

```python
def _rebuild_retrieval_logs(conn, cell):
    cell_id = _read_cell_id(cell)  # already available
    for _, record in read_jsonl(ledger):
        logged_at = record.get("logged_at") or record.get("generated_at") or ""
        conn.execute(..., (record.get("retrieval_id"), cell_id, ...))
```

**Recommendation:** Do both. Add the fields to the dataclass for correctness,
AND add the fallback in the rebuilder so existing ledger rows don't break.

---

## 4. Pack/Loadout Convergence Plan

### The duplication
pack.py and loadout.py are near-identical modules (697 and 747 lines) with:
- Identical docstrings
- Identical `RetrievalLog` class (pack.py:220-248, loadout.py:263-291)
- Identical `AssembledLoadout` class (pack.py:256-296, loadout.py:299-339)
- Identical `LoadoutItem`, `LoadoutTaskInput` classes
- Different downstream consumers (pack_api.py vs loadout_api.py, continuity
  imports loadout, provider facade imports loadout, CLI references pack)

### Convergence pattern: Single Canonical Module + Re-Export Shim

**Step 1:** Pick `loadout.py` as canonical (it has the `replace` import for
immutable dataclass updates and the `decay` import — slightly more complete).

**Step 2:** Reduce `pack.py` to a re-export shim:

```python
# pack.py — backward-compatible re-export shim
# All logic lives in loadout.py. This module exists only for callers
# that haven't migrated yet. Deprecated: import from shyftr.loadout directly.
from shyftr.loadout import (
    AssembledLoadout,
    LoadoutItem,
    LoadoutTaskInput,
    RetrievalLog,
    assemble_loadout,
    # ... all public names
)
```

**Step 3:** Add deprecation warnings (only in dev mode, not in production
hot paths):

```python
import warnings
warnings.warn(
    "shyftr.pack is deprecated; use shyftr.loadout",
    DeprecationWarning,
    stacklevel=2,
)
```

**Step 4:** Consolidate `pack_api.py` and `loadout_api.py` into one surface.

**Step 5:** Update CI terminology guard to allow both for one release cycle,
then flag `pack` imports as warnings, then errors.

---

## 5. Backward-Compatible API Deprecation Pattern

### Pattern: Deprecation Window with Structured Warnings
For any public API change (CLI flag rename, MCP tool rename, function
signature change):

1. **Phase A (this release):** Add the new name. Keep the old name working.
   Add a `DeprecationWarning` (not `FutureWarning` — those are silent by
   default in production). Log once per process.

2. **Phase B (next release):** Change warning to `FutureWarning` so it's
   visible. Add a CI check that fails on deprecated usage in tests.

3. **Phase C (release after):** Remove the old name.

### Concrete: terminology migration

```python
# terminology.py
import warnings
from functools import wraps

_DEPRECATED_TERMS = {
    "source": "evidence",
    "fragment": "candidate",
}

def warn_deprecated_term(old: str) -> None:
    if old in _DEPRECATED_TERMS:
        warnings.warn(
            f"Term '{old}' is deprecated; use '{_DEPRECATED_TERMS[old]}'",
            DeprecationWarning,
            stacklevel=3,
        )
```

### Concrete: CLI flag deprecation
Use Click's `hidden=True` + custom callback for deprecated flags:

```python
def _deprecated_flag(ctx, param, value):
    if value is not None:
        warnings.warn(f"--{param.name} is deprecated", DeprecationWarning)
    return value
```

---

## 6. Contract Test Strategy

### What to test
Phase 1 contract tests must cover the invariant: "append-only ledgers are
canonical truth; every read path sees the latest row."

### Test categories

**A. Ledger integrity contracts** (new file: `tests/test_ledger_contracts.py`)

| Test | What it verifies |
|---|---|
| `test_append_preserves_history` | Old rows are never deleted or mutated |
| `test_latest_row_wins_by_id` | canonical.latest_rows() returns last row per key |
| `test_confidence_reads_latest` | The specific bug: second adjustment uses latest confidence |
| `test_retrieval_log_roundtrip` | Write→read produces identical data (with cell_id, logged_at) |
| `test_sqlite_rebuild_deterministic` | Rebuild twice → same SQLite rows |
| `test_sqlite_rebuild_from_canonical` | SQLite rows match canonical.latest_rows() output |
| `test_hash_chain_intact_after_updates` | append_jsonl maintains hash chain across confidence updates |
| `test_collapse_semantics_consistent` | mutations.approved_traces() == canonical.approved_traces() |

**B. Schema compatibility contracts** (new file: `tests/test_schema_contracts.py`)

| Test | What it verifies |
|---|---|
| `test_retrieval_log_to_dict_has_cell_id` | After fix, RetrivalLog.to_dict() includes cell_id |
| `test_retrieval_log_to_dict_has_logged_at` | After fix, includes logged_at |
| `test_pack_loadout_same_interface` | pack.AssembledLoadout has same fields as loadout.AssembledLoadout |
| `test_legacy_ledger_still_readable` | Old sources.jsonl / fragments.jsonl still parse |
| `test_terminology_alias_map_complete` | Every legacy term in SQLite schema has a public alias |

**C. Regression contracts** (extend existing tests)

| Test | What it verifies |
|---|---|
| `test_confidence_does_not_regress` | Existing confidence tests still pass after _trace_by_id fix |
| `test_baseline_unchanged` | Phase 0 metrics don't regress |

### How to run
```bash
# Contract tests only
pytest tests/test_ledger_contracts.py tests/test_schema_contracts.py -v

# Full suite with contract focus
pytest -m "contract or ledger" -v
```

---

## 7. Human Review Gates

### Gate 1: Canonical module review
Before merging `canonical.py`:
- [ ] Every existing `read_jsonl()` call site is audited and classified as
      "needs latest-row" or "needs full-history"
- [ ] `latest_trace_by_id()` replaces `confidence._trace_by_id()`
- [ ] `approved_traces()` replaces both `mutations.approved_traces()` and
      `confidence._read_traces()`
- [ ] `write_retrieval_log()` fixes the cell_id/logged_at mismatch

### Gate 2: Pack/loadout convergence review
Before merging the shim:
- [ ] `grep -r "from shyftr.pack import" src/` — all callers documented
- [ ] `grep -r "from shyftr.loadout import" src/` — confirms loadout is canonical
- [ ] `diff <(python -c "import shyftr.pack; print(dir(shyftr.pack))") <(python -c "import shyftr.loadout; print(dir(shyftr.loadout))")` — identical public surfaces

### Gate 3: Contract test green
- [ ] All contract tests pass on CI
- [ ] Phase 0 baseline metrics unchanged (±tolerance)
- [ ] Terminology guard CI step passes (or has documented exceptions)

### Gate 4: Manual audit checklist
- [ ] Run `python scripts/terminology_inventory.py` — no undocumented legacy terms
- [ ] Run `python scripts/public_readiness_check.py` — passes
- [ ] Spot-check: pick one trace_id, run three confidence adjustments, verify
      `canonical.latest_trace_by_id()` returns the correct final confidence
- [ ] Spot-check: assemble a loadout, verify `retrieval_logs.jsonl` has non-null
      `cell_id` and `logged_at`
- [ ] Spot-check: `rebuild_from_cell()` produces retrieval_logs rows with
      non-null `cell_id` and `logged_at`

---

## 8. Migration Order (Least Risk First)

1. **Create `canonical.py`** with latest-row-wins helpers — no callers changed yet
2. **Add contract tests** — they'll fail on the known bugs, proving the tests work
3. **Fix `RetrievalLog` schema** — add `cell_id`/`logged_at` to dataclass + to_dict
4. **Fix `_trace_by_id` stale-read** — change to latest-match in canonical.py
5. **Migrate callers to canonical.py** — one module at a time
6. **Add terminology alias map** — no-op aliases, consumed by docs/CI
7. **Reduce pack.py to shim** — after all callers confirmed on loadout
8. **Run Phase 0 baseline** — confirm no regression
9. **Update docs/status** — reflect canonical terms

### Rollback safety
Every step is independently revertible. The ledger format on disk never
changes — only the read interpretation. If canonical.py introduces a bug,
revert to the old per-module readers.

---

## Summary of Confirmed Bugs and Fixes

| Bug | Location | Fix | Risk |
|-----|----------|-----|------|
| Confidence reads first trace, not latest | confidence.py:99-104 | `canonical.latest_trace_by_id()` scans full ledger | Low: logic change only |
| RetrievalLog missing cell_id/logged_at | loadout.py:277, pack.py:234 | Add fields + fallback in sqlite rebuilder | Low: additive only |
| Duplicated pack/loadout logic | pack.py + loadout.py | Reduce pack.py to re-export shim | Medium: callers need migration |
| Ontology drift (sources/fragments vs evidence/candidates) | Multiple modules | Terminology alias map, no ledger rename | Low: docs/CI only |
