# Storage, Retrieval, and Learning rule

ShyftR is a file-backed, auditable memory-cell substrate. Databases and vector stores accelerate retrieval, while cell ledgers remain canonical truth.

Canonical storage and application vocabulary:

- ShyftR cell: a bounded attachable memory unit.
- regulator: the review and policy layer controlling admission, promotion, retrieval, and export.
- cell ledger: the append-only canonical truth inside a cell.
- memory: a reviewed durable memory item.
- grid: the rebuildable retrieval and index layer.
- pack: the bounded memory bundle supplied to an agent or runtime.
- feedback: the evidenceback record that tells ShyftR whether retrieved memory helped or harmed.

## Storage rule

The cell ledger is canonical truth. It lives in append-only, replayable files:

```text
cells/<cell_id>/memory/
  ledger/
    evidences.jsonl
    candidates.jsonl
    reviews.jsonl
    promotions.jsonl
    retrieval_logs.jsonl
    feedback.jsonl
  memories/
    approved.jsonl
    decayed.jsonl
  patterns/
    proposed.jsonl
    approved.jsonl
  rule/
    proposed.jsonl
    approved.jsonl
```

The grid is rebuildable acceleration. It materializes retrieval/index views from the cell ledger:

```text
cells/<cell_id>/memory/
  grid/
    metadata.sqlite
    sparse.sqlite
    vectors.sqlite
```

Golden rule:

```text
cell ledgers are truth.
The grid is acceleration.
The pack is application.
feedback is learning.
memory confidence is evolution.
```

## Recommended MVP database stack

Use this for the first implementation:

- JSONL append-only ledgers for canonical truth
- SQLite in WAL mode for metadata, audit views, and query materialization
- SQLite FTS5 for sparse/BM25 retrieval
- sqlite-vec for local vector retrieval
- local embedding provider interface, with deterministic test embeddings

Why this stack:

- local-first
- inspectable
- portable
- no server required
- fast enough for early cells
- easy proof-of-work story
- indexes can be rebuilt from ledgers

Future adapters can support LanceDB or Qdrant for larger deployments, but they should remain optional indexes rather than canonical stores.

## Retrieval rule

ShyftR should not retrieve nearest text. ShyftR should retrieve the safest, most relevant, most proven memory for the current agent/task.

Retrieval should be hybrid and trust-aware:

1. cell scope filter
2. trust-tier filter
3. type/kind filter
4. sparse search
5. dense vector search
6. symbolic tag match
7. confidence/feedback weighting
8. optional reranking
9. bounded pack assembly

Suggested trust tiers:

- Tier 1: rule — shared promoted rules
- Tier 2: memories — reviewed durable memory
- Tier 3: patterns — recursively distilled patterns
- Tier 4: candidates — candidate memory, background-only unless approved
- Tier 5: evidences — raw evidence only

A pack must label trust tiers clearly. candidates must never masquerade as memories. The regulator applies scope, trust, token, and export limits before a pack can be supplied to an agent or runtime.

### Role-labeled pack assembly

pack assembly separates retrieved memory into explicit roles so an attached runtime can apply guidance without losing warnings or provenance:

- `guidance_items`: action-oriented memories and rules the agent should apply.
- `caution_items`: failure signatures, anti-patterns, supersession warnings, and other negative-space memories that should shape safe behavior.
- `background_items`: supporting patterns, candidates, and contextual evidence that may help interpretation.
- `conflict_items`: items flagged as contradictory or requiring review before use.

Caution items carry the same trust tier, kind, confidence, score, and provenance as guidance items. The pack budget reserves bounded space for caution while preserving the total item and token caps, so warnings cannot crowd out all action guidance. Retrieval logs record candidate IDs, selected IDs, caution IDs, suppressed IDs, and per-item score memories for later Sweep and feedback analysis.

## feedback learning rule

Every agent run should eventually produce feedback. feedback teach ShyftR whether retrieved memory helped or harmed.

Recommended `feedback.jsonl` fields:

```json
{
  "feedback_id": "tel_...",
  "cell_id": "core",
  "task_id": "task_...",
  "pack_id": "pack_...",
  "retrieved_memory_ids": [],
  "applied_memory_ids": [],
  "useful_memory_ids": [],
  "harmful_memory_ids": [],
  "missing_memory": [],
  "result": "success|failure|partial|unknown",
  "verification_evidence": [],
  "evidenceback": [],
  "error_signatures": [],
  "created_at": "..."
}
```

memory confidence should rise when a memory is retrieved, applied, and followed by verified success. It should fall when a memory is applied and followed by failure, contradicted, superseded, or marked harmful.

## Automatic learning regulator

ShyftR should automate discovery but gate durable authority. These gates are the regulator in practice: admission checks before evidences become usable, review gates before candidates become memories, retrieval filters before packs leave the cell, and explicit review before shared rules or external proposals gain authority.

Automatic:

- evidence capture
- candidate extraction
- regulator checks
- duplicate detection
- clustering
- confidence scoring
- pattern proposals
- decay proposals
- index rebuilds

Gated:

- memory promotion
- rule promotion
- destructive deprecation
- policy changes shared between cells

This keeps agents learning constantly without allowing unreviewed noise to become durable authority.

## Learning from success and failure

ShyftR should learn from mistakes and successes. memory kinds should include:

- success_pattern
- failure_signature
- anti_pattern
- recovery_pattern
- verification_heuristic
- routing_heuristic
- tool_quirk
- escalation_rule
- preference
- constraint
- workflow
- rule_candidate

A high-quality failure learning loop usually separates:

- failure_signature: how to recognize the problem
- anti_pattern: behavior that caused or worsened it
- recovery_pattern: what fixed it
- verification_heuristic: how to prove it is fixed

## Cross-cell resonance

If similar candidates, memories, or patterns recur across cells, ShyftR should detect resonance and propose stronger learning.

Example:

```text
core cell sees a verification-provenance candidate
project cell sees the same pattern
agent cell sees the same pattern
domain cell sees the same pattern
  -> propose pattern
  -> if reviewed and broadly useful, propose rule
```

Resonance should increase promotion readiness but should not bypass review.

## Runtime integration

ShyftR cells are designed to attach to any external agent runtime. The
[runtime integration contract](runtime-integration-contract.md)
defines the four flows (evidence ingest, pack request, feedback report, and
Proposal review/export), the external identity fields that link runtime state
to ShyftR memory, idempotency requirements for file and JSONL ingest, and the
safety regulator that keeps ShyftR proposing and the runtime applying.

A context-optimization runtime can also use a live context cell as a working buffer. Live context capture is not durable memory by default. At session close, a harvest process classifies live entries into discard, archive, continuity feedback, memory candidate, direct durable memory, or skill proposal buckets. Only reviewed or policy-approved durable material should enter the memory cell.

This keeps the active prompt lean while preserving inspectable ledgers. Cells may grow, but packs supplied to a runtime remain bounded by explicit item and token budgets.

This contract is runtime-agnostic. It contains no assumptions about any
specific agent framework, queue system, worker model, or transport protocol.

## Universal memory substrate contracts

The universal substrate scope extends the same storage, retrieval, and learning
rule to agent-memory providers and knowledge workspaces. The core remains the
cell ledger model:

```text
cell ledgers are truth.
The grid is acceleration.
packs, profiles, markdown pages, documents, dashboards, and summaries are
applications or projections.
```

The [universal memory substrate](universal-memory-substrate.md) scope defines
ShyftR as a local-first memory substrate while keeping orchestration, note
editing, hosted collaboration, and vector storage as optional external surfaces
or adapters. The [memory provider contract](memory-provider-contract.md)
defines ShyftR-native compatibility for `remember`, `search`, `profile`,
`forget`, `replace`, `deprecate`, `pack`, `record_feedback`,
`import_memory_export`, and `export_memory_snapshot`. The
[knowledge workspace contract](knowledge-workspace-contract.md) defines
compatibility for note ingest, note sync, document ingest, backlinks, topic and
project projections, review queues, and markdown export.

These contracts are category-level. Adapters may map named tools into the
contracts, but public ShyftR docs should describe capability categories rather
than product-specific comparisons. Generated profiles, snapshots, markdown,
documents, dashboards, and indexes remain rebuildable outputs derived from cell
ledgers.

The first UMS implementation pass exposes the direct provider API under
`shyftr.provider`. That pass implements `remember`, `search`, `profile`,
`forget`, `replace`, and `deprecate` as a narrow provider surface over cell
ledgers. UMS-2 adds `remember_trusted` and `TrustedmemoryProvider` as a narrow
trusted explicit-memory surface: callers must supply actor, trust reason, evidence
channel, and creation time; trusted writes still pass regulator pollution checks;
and promotion remains provenance-linked through evidence, candidate,
review, promotion, memory, and memory rows. ShyftR does not move canonical truth
into profile text, search indexes, trusted-call metadata, or external runtime
state. Later UMS work slices cover profile projection hardening, lifecycle
semantics, pack and feedback wrappers, and import/export compatibility.
