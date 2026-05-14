# ShyftR Phase 6 — Tranche P6-0 plan (contract-first kickoff)

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 6 — resource and multimodal memory
Tranche: P6-0 (planning + contract definition only)
Status: hardened after deep research; ready to start
Predecessor closeoff: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-5-closeoff.md`
Roadmap source: `/Users/stefan/ShyftR/broad-roadmap-concept.md`
Research source: `/Users/stefan/ShyftR/deep-research-report.md`
Hardening inputs:
- controller code inspection across models/provider/pack/retrieval/privacy/sqlite
- swarm2 deep-research memo (`proc_6ad01d78fb44`)
- swarm3 compatibility audit memo (`proc_c1bf9fabe974`)

## Objective

Start Phase 6 with a contract-first tranche that defines the smallest additive public-safe resource-memory surface before implementation begins.

This tranche does not implement multimodal/resource memory.
It defines scope, stop boundary, schema direction, tranche split, RED tests, compatibility constraints, and verification commands so the next implementation slice can start cleanly.

## Why Phase 6 is next

The roadmap identifies Phase 6 as:
- resource and multimodal memory
- first-class memory for files, screenshots, logs, code spans, browser state, and generated artifacts
- references-first rather than blob-dump storage
- grounding links from semantic/procedural/episodic memories to exact supporting evidence

This is the next frontier after Phase 5 consolidation/rehearsal because it expands what ShyftR can remember, not just how it consolidates text memory.

## Deep-research hardening conclusions

Phase 6 should stay narrower than the original broad phrase “resource and multimodal memory” suggests.
The current codebase already has a `resource` memory type, minimal validation for resource-like writes, privacy/export policy machinery, memory-type inference, and retrieval/pack surfaces that can carry typed rows. The immediate risk is not absence of hooks; it is schema drift, provenance breakage, privacy leakage, and accidental over-indexing of sensitive locators.

The safe optimization is:
1. keep P6-1 strictly reference-first and additive
2. avoid heavy multimodal behavior in the first execution tranche
3. define one canonical typed `resource_ref` shape before touching retrieval semantics
4. preserve pack/search empty-query behavior and backward compatibility
5. make resource display text searchable, but keep raw locators and spans out of default lexical indexing unless explicitly intended

## Non-negotiable constraints

- Keep work local to `/Users/stefan/ShyftR`.
- Preserve local-first and ledger-first design.
- Prefer references/handles/hashes over raw large blobs.
- Preserve review-gated durable-memory posture.
- Keep public examples synthetic and privacy-safe.
- Additive compatibility only: tolerate older ledgers/rows where possible.
- No hosted/platform claims.
- No binary/blob storage inside ledgers.
- No OCR, screenshot embeddings, or browser-capture automation in the first implementation slice.

## Phase 6 baseline, tightened

The first implementation slice should aim for a narrow, public-safe baseline:
1. a canonical typed `resource_ref` structure
2. additive provider/model support for resource-backed memory rows
3. grounding links from semantic/procedural/episodic memories into resource identities
4. minimal resource-aware retrieval hooks over safe display text only
5. synthetic file/log/code-span/url fixtures
6. privacy/retention metadata pinned in schema and tests

Not yet in the first implementation slice unless explicitly chosen later:
- image embeddings
- OCR pipelines
- browser automation capture
- screenshot semantic QA benchmarking
- large binary blob storage inside ledgers
- hosted storage backends
- ANN/vector retrieval changes specific to multimodal artifacts

## Contract decisions before implementation

### 1) Canonical internal shape: `resource_ref`

Phase 6 should define one canonical internal structure for resource references.
Recommended baseline fields:
- `ref_type` (`file`, `log_span`, `code_span`, `url`, `screenshot`, `artifact`, `browser_state`)
- `locator` (path/url/logical handle)
- `label` (safe human-readable display text)
- `span` (typed range object when relevant)
- `content_digest` (optional)
- `captured_at` (optional)
- `origin` or `tool_name` (optional)
- `mime_type` (optional)
- `size_bytes` (optional)

Important hardening rule:
- `label` is for retrieval/display
- `locator` is for grounding/inspection
- default lexical retrieval should prefer `statement`, `label`, and maybe `ref_type`, not full raw locator strings

### 2) Keep top-level rows additive and optional

Do not make new resource-only fields globally required on existing approved memory rows.
If resource rows are represented through the current approved-memory/provider path, new fields must remain optional/additive so existing row deserialization, SQLite rebuilds, sparse indexing, pack assembly, and older ledgers still round-trip.

### 3) Preserve provenance invariants deliberately

Current approved memory rows expect fragment provenance (`source_fragment_ids`) as a hard invariant.
Phase 6 must choose one of these explicitly:
- safe near-term path: resource memories still go through source + fragment + approved memory row flow, where the fragment text is a resource summary and metadata carries the structured `resource_ref`
- deferred path: a separate dedicated resource ledger/model later, only after compatibility tests prove the migration

Recommended P6-1 choice:
- use the existing source/fragment/approved-memory provider path first
- keep `resource_ref` in metadata / typed optional fields
- do not introduce a parallel ledger yet

### 4) Normalize reference naming early

There is already overlap among:
- `resource_ref`
- `resource_refs`
- `grounding_refs`
- `evidence_refs`

Phase 6 should pick one canonical meaning now:
- `resource_ref`: the primary typed reference attached to a resource memory row
- `grounding_refs`: references from any other memory row to one or more resource memory ids or structured resource handles
- `evidence_refs`: leave as live-context / evidence lineage concept unless later unified by explicit migration

### 5) Privacy/export policy must cover resources, not just statements

Current privacy redaction mainly focuses on `statement` and sensitivity metadata.
Phase 6 must pin tests for:
- sensitive file paths not leaking through pack/export when sensitivity blocks them
- private locators being redacted or excluded under policy
- safe labels remaining available where allowed
- resource metadata obeying scope filtering just like existing rows

### 6) Empty-query behavior remains unchanged

Do not let resource memory become “always included” in search or pack by default.
Current deterministic behavior around empty query => no search results should remain intact unless a future tranche explicitly introduces a separate opt-in pack mode.

## Proposed operator-visible contracts

### Resource-backed memory row

Expected additive concepts:
- `memory_type = resource`
- compatible `kind` values may remain existing kinds in P6-1, with typed meaning coming from `memory_type` and `resource_ref`
- optional top-level or metadata-carried fields:
  - `resource_ref`
  - `grounding_refs`
  - `sensitivity`
  - `retention_hint`
  - `content_digest`
  - `metadata` for typed attributes

Recommended P6-1 rule:
- do not widen the public contract more than necessary with many new mandatory kinds
- use a small safe starter surface driven by `resource_ref.ref_type`

### Grounding links

A semantic/procedural/episodic memory should be able to reference resource support via `grounding_refs`.
The first implementation slice should make this explicit and testable without changing retrieval precedence semantics yet.

### Retrieval expectations

Phase 6 retrieval should initially support:
- resource memories participating in normal search/pack flows
- statement + safe label text search over resource refs
- result visibility that makes grounded artifacts inspectable
- future-compatible hooks for richer reranking later

Explicit non-goal for P6-1:
- retrieving by raw sensitive absolute path substrings unless specifically allowed by a future design

## Recommended tranche split after P6-0

### Tranche P6-1: resource-ref schema + provider baseline

Target:
- define canonical `resource_ref`
- support provider round-trip for resource-backed memory using the existing source/fragment/approved-memory pipeline
- add focused model/provider tests
- keep retrieval changes minimal

### Tranche P6-2: retrieval + pack integration for resource memory

Target:
- extend sparse/hybrid/pack surfaces so resource-backed memory is searchable and pack-visible by safe display text
- ensure raw locator indexing is not accidentally the default
- add focused sparse + pack tests

### Tranche P6-3: resource helper constructors + fixture discipline

Target:
- helper builders for file/code-span/log-span/url refs
- synthetic fixtures under `tests/fixtures/resources/...`
- tests guaranteeing no dependence on real local home paths or secrets

### Tranche P6-4: screenshot refs only, still reference-first

Target:
- add `screenshot` resource refs as structured references only
- no OCR, no embeddings, no image bytes in ledgers

### Tranche P6-5: optional richer multimodal layer

Only if Phase 6 baseline is stable:
- OCR / embeddings / ANN or LanceDB-style enhancements behind strict contracts and separate evaluation

## File/code matrix for the next execution tranche

Read first:
- `src/shyftr/models.py`
- `src/shyftr/memory_classes.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/pack.py`
- `src/shyftr/retrieval/sparse.py`
- `src/shyftr/retrieval/hybrid.py`
- `src/shyftr/privacy.py`
- `src/shyftr/store/sqlite.py`
- `tests/test_phase3_memory_classes.py`
- `tests/test_memory_provider.py`
- `tests/test_models.py`
- `tests/test_pack.py`
- `tests/test_sparse_retrieval.py`

Likely implementation touchpoints for P6-1:
- `src/shyftr/models.py`
- `src/shyftr/memory_classes.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/store/sqlite.py`
- maybe `src/shyftr/privacy.py` if structured resource projection/redaction needs immediate support

Likely implementation touchpoints for P6-2:
- `src/shyftr/retrieval/sparse.py`
- `src/shyftr/retrieval/hybrid.py`
- `src/shyftr/pack.py`

Likely new/expanded tests:
- `tests/test_phase6_resource_memory_schema.py`
- `tests/test_phase6_resource_memory_provider.py`
- `tests/test_phase6_resource_memory_retrieval.py`
- `tests/test_phase6_resource_memory_pack.py`

Likely synthetic fixtures:
- `tests/fixtures/resources/...`

## Minimum RED tests for the next tranche

P6-1 should begin by writing failing tests for at least:
1. a resource-backed memory round-trips through provider/model paths with `memory_type="resource"`
2. a typed `resource_ref` survives round-trip serialization/deserialization
3. legacy non-resource approved rows still round-trip unchanged
4. SQLite rebuild preserves `memory_type` and does not break on resource metadata
5. semantic/procedural memories can carry `grounding_refs` to resource identities without breaking compatibility
6. resource validation rejects blob-only content and requires a reference handle

P6-2 should begin by writing failing tests for at least:
1. sparse retrieval can find a resource-backed memory by statement or safe label text
2. pack assembly preserves resource identity and grounding visibility
3. empty queries still return no retrieval results
4. raw sensitive locator text is not the default search/display surface unless explicitly allowed

## Verification commands for the next tranche

Focused P6-1 commands once implementation begins:
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_phase6_resource_memory_schema.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_phase6_resource_memory_provider.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_models.py tests/test_phase3_memory_classes.py tests/test_memory_provider.py`

Focused P6-2 commands:
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_phase6_resource_memory_retrieval.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_phase6_resource_memory_pack.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_sparse_retrieval.py tests/test_pack.py`

Broader gates after focused green:
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`

## Stop boundary for P6-0

P6-0 is complete when:
- the Phase 5 final truth artifact exists
- this hardened Phase 6 kickoff plan exists
- the contract, tranche split, compatibility constraints, RED tests, and verification commands are explicit
- no resource-memory implementation changes have been made yet in this tranche

## Exact next tranche after this one

### Tranche P6-1: resource-ref schema + provider baseline

Target:
- land the smallest additive resource-memory schema and provider round-trip behavior with synthetic fixtures and no retrieval-policy expansion beyond what is required for compatibility.

This tranche should:
- stay reference-first
- preserve existing source/fragment/approved-memory provenance flow
- avoid heavy multimodal processing
- avoid broad pack/retrieval behavior changes

## Resume checklist

When resuming Phase 6:
1. confirm repo path is `/Users/stefan/ShyftR`
2. confirm clean branch/worktree state
3. read `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-5-closeoff.md`
4. read this hardened P6-0 plan
5. inspect `models.py`, `memory_classes.py`, `provider/memory.py`, `privacy.py`, `store/sqlite.py`, and only then the retrieval/pack files
6. write the first focused failing P6-1 schema/provider tests before any implementation
7. do not start retrieval/pack changes until schema/provider compatibility is green

## One-line summary

Phase 6 is ready to start, and the next correct move is a narrowly scoped P6-1 tranche that defines and round-trips typed `resource_ref` memory through the existing local-first review-gated pipeline before retrieval or multimodal expansion.