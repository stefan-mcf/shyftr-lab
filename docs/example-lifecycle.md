# ShyftR Local Demo

This guide walks through the complete ShyftR memory lifecycle from evidence
capture through feedback recording. All commands run locally — no network,
no API keys, no external services needed.

ShyftR uses append-only JSONL ledgers as canonical truth. Indexes and
search are rebuildable acceleration layers on top of that truth.

---

## Prerequisites

Python 3.11+ and ShyftR installed (see README for setup).

---

## 1. Create a cell

A cell is an attachable memory namespace. Create one with:

```bash
shyftr init-cell ./demo-cell
```

This creates the directory layout: `config/`, `ledger/`, `grid/`, and
empty JSONL ledgers for evidences, candidates, memories, patterns, rules,
packs, and feedback.

---

## 2. Ingest evidence

A evidence is raw evidence — a file, a log, a chat transcript. Ingest it:

```bash
shyftr ingest ./demo-cell examples/evidence.md --kind lesson
```

The ingester computes a SHA-256 fingerprint, returns a current `source_id`, and
appends a evidence record to `ledger/evidences.jsonl`.

---

## 3. Extract candidates

candidates are bounded, typed pieces extracted from a evidence:

```bash
shyftr candidates ./demo-cell <source_id>
```

This reads the evidence record, parses the file into candidate memory
pieces (candidates), and appends them to `ledger/candidates.jsonl`.

---

## 4. Approve candidates

Review each candidate and approve it for promotion:

```bash
shyftr approve ./demo-cell <candidate_id> --reviewer demo --rationale "Accurate and relevant lesson"
```

Approved candidates remain in `ledger/candidates.jsonl` with
`review_status: approved`.

---

## 5. Promote to memory

Promote an approved candidate into a durable memory:

```bash
shyftr memory ./demo-cell <candidate_id> --promoter demo --rationale "regulator-scoping pattern confirmed"
```

The promotion creates a memory record in `memories/approved.jsonl` with an
identifier, a `statement`, and provenance back to the original candidate.

---

## 6. Search Approved memories

The search command rebuilds or queries the sparse FTS5 index:

```bash
shyftr search ./demo-cell "pack confidence"
```

Results include `memory_id` / compatibility `memory_id`, `statement`, `confidence`, `bm25_score`,
and tags — useful for verifying what was promoted.

---

## 7. Assemble a pack

A pack is a bounded, trust-labeled memory context for a task:

```bash
shyftr pack ./demo-cell "How to improve pack relevance" --task-id demo-task-001
```

The pack selects memories by relevance score and returns a bounded
context with a `trust_label`.

---

## 8. Record feedback

After the task completes, record what happened:

```bash
shyftr feedback ./demo-cell <pack_id> success \
  --useful <memory_id_1>,<memory_id_2> \
  --missing "more scope-tagged memories"
```

feedbacks flow back into the confidence engine, decaying or boosting
memory confidence based on verified results.

---

## Lifecycle Summary

```
evidence -> candidate -> memory -> pack -> feedback
                 ^                      |
                 |--- confidence loop --|
```

- **Ledgers** (JSONL files under each cell) are the canonical truth.
- **Indexes** (SQLite FTS5) are rebuildable acceleration.
- **packs** are the application — bounded memory for a specific task.
- **feedback** are the learning feedback — they update memory confidence.

Run the full example test suite to verify the local setup:

```bash
PYTHONPATH=src python3 -m shyftr.cli --help >/dev/null
```
