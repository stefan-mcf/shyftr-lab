# ShyftR Universal memory Substrate Follow-up Plan

> For Hermes: implement this only after the current ShyftR main, runtime-integration, and active-learning plans are complete, verified, committed, and pushed. Use subagent-driven-development for implementation, and keep each tranche small, tested, and committed.

Status: future follow-up implementation plan. This plan extends the current ShyftR roadmap after the existing MVP, runtime-integration, and active-learning plans.

Guardrules: before implementing or reviewing any tranche in this plan, read `docs/concepts/implementation-guardrules.md`. The guardrules keep ShyftR as a thin memory-cell core with optional modules and projections rather than a bloated monolith.

Goal: evolve ShyftR from an agent memory-cell engine into the canonical local-first memory and knowledge substrate for assistants, agents, projects, teams, personal knowledge, and long-running autonomous systems.

Architecture: canonical truth remains append-only cell ledgers. Managed memory services, assistant profile stores, vector-memory platforms, markdown vaults, note applications, dashboards, and generated knowledge views become adapters, evidences, projections, or user interfaces. ShyftR cells own durable memory, provenance, review gates, packs, feedback, confidence, profile generation, knowledge projections, and portability.

Tech stack: Python 3.11+, dataclasses or Pydantic-compatible models, JSONL cell ledgers, SQLite WAL, SQLite FTS5, sqlite-vec or equivalent local vector grid, optional LanceDB/Qdrant adapters, Markdown import/export, pytest, CLI-first workflows, optional local service/UI later.

---

## Relationship to existing plans

This plan begins only after these are complete:

1. `docs/plans/2026-04-24-shyftr-implementation-tranches.md`
2. `docs/plans/2026-04-24-shyftr-runtime-integration-adapter-plan.md`
3. `docs/plans/2026-04-24-shyftr-active-learning-follow-up-plan.md`

Recommended sequence:

```text
Main ShyftR implementation plan
  -> Runtime integration adapter plan
  -> Active learning follow-up plan
  -> Universal memory substrate plan
```

The earlier plans make this plan possible by delivering:

- evidence ingest
- candidate extraction
- review-gated memory promotion
- hybrid retrieval
- pack assembly
- feedback recording
- confidence evolution
- runtime integration contracts
- proposal export
- negative-space retrieval
- pack misses
- Sweep and Challenger maintenance loops
- disk-backed grid scale path

This plan should not shortcut those foundations.

---

## Product thesis

ShyftR should become the canonical durable memory layer underneath agent runtimes and human knowledge workflows.

The long-term model:

```text
Human input, notes, documents, chats, tasks, tool runs, reviews, feedback
  -> evidences
  -> candidates
  -> memories
  -> patterns
  -> rule
  -> packs, profiles, summaries, projections, proposals
```

ShyftR owns truth. Other systems provide capture, display, retrieval acceleration, execution, or review surfaces.

Canonical rule remains:

```text
cell ledgers are truth.
The regulator controls admission, promotion, retrieval, and export.
The grid is acceleration.
The pack is application.
feedback is learning.
memory confidence is evolution.
Markdown and dashboards are projections.
External runtimes apply; ShyftR proposes.
```

---

## Capability targets

This plan has two replacement targets and one expansion target.

### 1. Agent memory provider replacement

ShyftR should replace hosted or managed assistant-memory/profile layers by providing:

- durable preference storage
- semantic search
- compact profile generation
- scoped memory cells
- forget, replace, deprecate, supersede, quarantine, and sensitive-memory exclusion
- pre-task packs
- post-task feedback
- profile and pack injection hooks for assistant runtimes
- migration/import from existing memory exports
- local backup, restore, and validation

### 2. Knowledge workspace substrate

ShyftR should subsume the durable/retrievable parts of markdown note workspaces by providing:

- markdown note ingest
- frontmatter, tag, link, and backlink capture
- document and research evidence ingest
- topic pages and project pages as projections
- daily/weekly summaries as projections
- review queues
- decision records
- rule pages
- generated markdown export
- optional native review/search/dashboard UI

Markdown workspaces may remain useful as human-facing surfaces, but they should not be canonical truth once ShyftR owns the cell ledgers.

### 3. Universal cell substrate

ShyftR should support durable memory across:

- user/core cells
- personal cells
- project cells
- agent cells
- team cells
- domain/capability cells
- global rule cells

Cross-cell promotion remains explicit and review-gated.

---

## Tranche UMS-0: Scope and compatibility contracts

Objective: define the full replacement scope before adding implementation.

Files:

- Create: `docs/concepts/universal-memory-substrate.md`
- Create: `docs/concepts/memory-provider-contract.md`
- Create: `docs/concepts/knowledge-workspace-contract.md`
- Modify: `docs/concepts/storage-retrieval-learning.md`

Tasks:

1. Document the universal substrate thesis.
2. Define the agent memory provider contract:
   - `remember`
   - `search`
   - `profile`
   - `forget`
   - `replace`
   - `deprecate`
   - `pack`
   - `record_feedback`
   - `import_memory_export`
   - `export_memory_snapshot`
3. Define the knowledge workspace contract:
   - note ingest
   - note sync
   - document ingest
   - backlinks
   - topic projection
   - project projection
   - review queue
   - markdown export
4. Map hosted memory provider capabilities to ShyftR-native equivalents using broad provider categories rather than product-specific names.
5. Map markdown workspace capabilities to ShyftR-native equivalents using broad workspace categories rather than product-specific names.
6. Reaffirm that generated profiles, summaries, dashboards, and markdown files are projections.
7. Reaffirm that cell ledgers are canonical truth.
8. Run stale-term and weak-phrasing scans.
9. Commit: `docs: define universal memory substrate scope`.

Acceptance criteria:

- A future implementer can see exactly what ShyftR must replace.
- The contract is runtime-agnostic and workspace-agnostic.
- Public docs avoid product-specific comparison language.
- No canonical truth is assigned to generated markdown or profile artifacts.

---

## Tranche UMS-1: ShyftR-native memory provider API

Objective: add first-class memory-provider functions that assistant runtimes can call directly.

Files:

- Create: `src/shyftr/provider/__init__.py`
- Create: `src/shyftr/provider/memory.py`
- Create: `tests/test_memory_provider.py`
- Modify: `src/shyftr/models.py`
- Modify: `src/shyftr/policy.py`

Tasks:

1. Define a `memoryProvider` class or function set with:
   - `remember(cell_path, statement, kind, evidence_context=None, metadata=None)`
   - `search(cell_path, query, top_k=10, trust_tiers=None, kinds=None)`
   - `profile(cell_path, max_tokens=2000)`
   - `forget(cell_path, memory_id, reason, actor)`
   - `replace(cell_path, memory_id, new_statement, reason, actor)`
   - `deprecate(cell_path, memory_id, reason, actor)`
2. Add tests for direct explicit user preference memory.
3. Add tests that operational-state pollution remains blocked.
4. Add tests that every direct memory write preserves evidence or policy-approved event provenance.
5. Add tests that provider search returns trust labels and memory IDs.
6. Keep the API ShyftR-native rather than imitating any specific managed provider.
7. Commit: `feat: add ShyftR memory provider API`.

Acceptance criteria:

- An assistant runtime can write and search durable memory with simple ShyftR calls.
- Direct writes still pass through the regulator.
- Durable memories remain provenance-linked.
- Operational state does not become durable memory.

---

## Tranche UMS-2: Trusted explicit-memory path

Objective: make explicit user memories low-friction while preserving auditability.

Files:

- Create: `src/shyftr/provider/trusted.py`
- Modify: `src/shyftr/review.py`
- Modify: `src/shyftr/promote.py`
- Modify: `tests/test_memory_provider.py`
- Create: `tests/test_trusted_memory.py`

Tasks:

1. Add a `trusted_evidence_kind` or equivalent policy for explicit user statements.
2. Add a policy-approved path that can create a evidence, candidate, review event, promotion event, and memory in one operation when configured.
3. Require metadata fields for trusted direct promotion:
   - actor
   - trust_reason
   - evidence_channel
   - created_at
4. Add tests for `kind=preference`, `kind=constraint`, `kind=workflow`, and `kind=tool_quirk`.
5. Add tests that trusted direct promotion cannot bypass pollution checks.
6. Add tests that deployments can disable direct promotion and require manual review.
7. Commit: `feat: add trusted explicit memory promotion`.

Acceptance criteria:

- Explicit user preferences can become memories without a burdensome manual flow.
- Trusted promotion is auditable and configurable.
- Untrusted or polluted material still requires review or rejection.

---

## Tranche UMS-3: Compact profile builder

Objective: replace assistant profile-store reads with rebuildable ShyftR profile projections.

Files:

- Create: `src/shyftr/profile.py`
- Create: `tests/test_profile.py`
- Modify: `src/shyftr/layout.py`
- Modify: `src/shyftr/cli.py`

Generated projections:

- `summaries/profile.json`
- `summaries/profile.md`
- `summaries/profile.compact.md`
- `summaries/profile.index.json`

Tasks:

1. Define profile sections:
   - identity facts
   - stable preferences
   - naming and style preferences
   - project vocabulary
   - architecture preferences
   - durable workflows
   - tool quirks
   - safety boundaries
   - active constraints
2. Implement `build_profile(cell_path, max_tokens=None)`.
3. Implement deterministic ordering by kind, confidence, status, and stable ID.
4. Exclude deprecated, superseded, quarantined, and sensitive-excluded memories by default.
5. Include evidence memory IDs for every profile item.
6. Add CLI command: `shyftr profile <cell_path> [--compact] [--max-tokens N]`.
7. Test token-bounded compact output.
8. Test conflict rendering when approved memories disagree.
9. Commit: `feat: build compact profile projections`.

Acceptance criteria:

- A runtime can inject a compact ShyftR profile before work.
- Profile artifacts are rebuildable projections.
- Deprecated and superseded memories do not appear in normal profile output.
- Profile output remains stable across rebuilds.

---

## Tranche UMS-4: memory mutation and lifecycle semantics

Objective: implement forget, replace, supersede, deprecate, quarantine, conflict, and sensitive-memory handling.

Files:

- Modify: `src/shyftr/models.py`
- Create: `src/shyftr/mutations.py`
- Create: `tests/test_memory_mutations.py`
- Modify: `src/shyftr/layout.py`
- Modify: `src/shyftr/store/sqlite.py`

New ledgers:

- `ledger/status_events.jsonl`
- `ledger/supersession_events.jsonl`
- `ledger/deprecation_events.jsonl`
- `ledger/quarantine_events.jsonl`
- `ledger/conflict_events.jsonl`
- `ledger/redaction_events.jsonl`

Tasks:

1. Add event models for status change, supersession, deprecation, quarantine, conflict, and redaction projection.
2. Implement `forget_memory` as retrieval/profile exclusion through append-only status event.
3. Implement `replace_memory` as new memory plus supersession event.
4. Implement `deprecate_memory` as a status event with reason and actor.
5. Implement `quarantine_memory` as a status event that blocks pack inclusion by default.
6. Implement conflict recording without silently picking a winner.
7. Implement sensitive-memory projection exclusion.
8. Update SQLite materialization to compute latest effective memory state.
9. Test append-only behavior.
10. Commit: `feat: add memory lifecycle mutation events`.

Acceptance criteria:

- User-facing forget prevents retrieval/profile inclusion.
- Replacement preserves the old/new relationship.
- Deprecation and quarantine are auditable.
- Sensitive content can be excluded from projections without rewriting ledger history.

---

## Tranche UMS-5: Persistent semantic grid

Objective: make semantic retrieval persistent, rebuildable, and competitive for personal and project memory.

Files:

- Modify: `src/shyftr/retrieval/vector.py`
- Create: `src/shyftr/retrieval/sqlite_vec.py`
- Modify: `src/shyftr/retrieval/embeddings.py`
- Create: `src/shyftr/grid.py`
- Create: `tests/test_grid.py`
- Modify: `src/shyftr/cli.py`
- Modify: `pyproject.toml`

Tasks:

1. Add a persistent vector index adapter interface if the existing interface needs expansion.
2. Implement a sqlite-vec backed adapter when available.
3. Keep deterministic test embeddings for tests.
4. Add optional dependency group for vector support.
5. Implement `rebuild_grid(cell_path)`.
6. Implement `grid_status(cell_path)`.
7. Implement `verify_grid(cell_path)`.
8. Add CLI commands:
   - `shyftr grid rebuild <cell_path>`
   - `shyftr grid status <cell_path>`
   - `shyftr grid verify <cell_path>`
9. Test that deleting indexes and rebuilding restores retrieval.
10. Commit: `feat: add persistent semantic grid`.

Acceptance criteria:

- Vector indexes persist across process runs.
- Sparse, vector, symbolic, confidence, and status filters can combine.
- Indexes remain rebuildable from cell ledgers.
- Tests do not require network access.

---

## Tranche UMS-6: Multi-cell registry and routing

Objective: support scoped memory across user, project, agent, team, domain, and rule cells.

Files:

- Create: `src/shyftr/cells/registry.py`
- Create: `src/shyftr/cells/routing.py`
- Create: `src/shyftr/cells/__init__.py`
- Create: `tests/test_cell_registry.py`
- Create: `tests/test_cell_routing.py`
- Create: `examples/cell-routing-policy.yaml`

Tasks:

1. Define a cell registry format with:
   - cell_id
   - cell_path
   - cell_type
   - owner or scope
   - trust/export policy
   - enabled retrieval roles
2. Define routing policy for write targets.
3. Define routing policy for read targets.
4. Implement `select_write_cell(evidence_metadata, policy)`.
5. Implement `select_read_cells(task_metadata, policy)`.
6. Implement `cross_cell_pack(cell_paths, query, limits)`.
7. Keep shared rule promotion review-gated.
8. Test that project memory does not pollute core memory by default.
9. Test that a task can query core + project + domain cells.
10. Commit: `feat: add multi-cell registry and routing`.

Acceptance criteria:

- Assistant runtimes can request memory from the right cells.
- Durable writes land in the correct cell.
- Cross-cell memory flow is policy-controlled.

---

## Tranche UMS-7: Managed memory export migration

Objective: import existing assistant-memory exports into ShyftR safely.

Files:

- Create: `src/shyftr/importers/__init__.py`
- Create: `src/shyftr/importers/memory_export.py`
- Create: `tests/test_memory_export_import.py`
- Modify: `src/shyftr/cli.py`

Tasks:

1. Define a generic JSON/JSONL memory export schema.
2. Implement parser for records with statement, metadata, created_at, updated_at, and evidence labels.
3. Convert imported records into evidences with `kind=memory_export` or configured kind.
4. Classify likely memory kind:
   - preference
   - constraint
   - workflow
   - tool_quirk
   - project_convention
   - architecture_preference
   - unknown
5. Detect duplicates against existing memories.
6. Run operational-state regulator checks.
7. Produce an import review report before promotion.
8. Add CLI command: `shyftr import memory-export <cell_path> <export_file> [--review-only]`.
9. Test safe import, duplicate detection, and pollution rejection.
10. Commit: `feat: import managed memory exports`.

Acceptance criteria:

- Existing durable memory can be migrated into ShyftR.
- Imports preserve provenance.
- Operational or stale records are blocked, quarantined, or sent to review.
- No blind bulk import bypasses review policy.

---

## Tranche UMS-8: Assistant runtime integration modes

Objective: make assistant runtimes use ShyftR as primary durable memory.

Files:

- Create: `src/shyftr/runtime/assistant.py`
- Create: `src/shyftr/runtime/__init__.py`
- Create: `tests/test_assistant_runtime_memory.py`
- Create: `docs/concepts/assistant-runtime-integration.md`

Modes:

- `shadow`
- `primary_with_fallback`
- `primary_only`

Tasks:

1. Define runtime hooks:
   - pre-turn profile injection
   - pre-task pack injection
   - durable memory write
   - semantic memory search
   - post-task feedback report
2. Implement a local Python integration adapter.
3. Implement config for mode selection.
4. In `shadow` mode, write to ShyftR while preserving existing provider reads.
5. In `primary_with_fallback` mode, read ShyftR first and fallback on miss/error.
6. In `primary_only` mode, use ShyftR exclusively.
7. Record feedback for useful, harmful, ignored, and missing memory when runtime evidenceback is available.
8. Test all three modes with fake provider fixtures.
9. Commit: `feat: add assistant runtime memory modes`.

Acceptance criteria:

- An assistant can run with ShyftR-only durable memory.
- Shadow and fallback modes support safe migration.
- Profile/search/write behavior is testable without external services.

---

## Tranche UMS-9: Agent runtime memory loop

Objective: extend the memory provider into autonomous worker and task runtimes.

Files:

- Create: `src/shyftr/runtime/agent_loop.py`
- Create: `tests/test_agent_runtime_loop.py`
- Modify: `docs/concepts/runtime-integration-contract.md`

Tasks:

1. Define pre-task pack request helpers.
2. Define worker/task evidence capture helpers.
3. Define feedback report helpers for success, failure, partial, and unknown results.
4. Define proposal export helpers.
5. Ensure external queue/task state remains metadata only.
6. Ensure runtime operational state does not become durable lesson content.
7. Test evidence -> pack -> feedback -> proposal flow with fake task records.
8. Commit: `feat: add agent runtime memory loop helpers`.

Acceptance criteria:

- Autonomous runtimes can consume packs and report feedback.
- Repeated successes/failures supply ShyftR learning.
- ShyftR advises the runtime but does not mutate runtime operations directly.

---

## Tranche UMS-10: Markdown note ingest

Objective: ingest human-authored markdown notes as evidences.

Files:

- Create: `src/shyftr/notes/__init__.py`
- Create: `src/shyftr/notes/markdown.py`
- Create: `src/shyftr/notes/sync.py`
- Create: `tests/test_markdown_notes.py`
- Modify: `src/shyftr/cli.py`

Tasks:

1. Parse markdown files as evidences.
2. Capture frontmatter metadata.
3. Capture tags.
4. Capture wikilinks and markdown links.
5. Capture backlinks as rebuildable metadata.
6. Hash file content for idempotent ingest.
7. Support incremental directory sync.
8. Add CLI commands:
   - `shyftr notes ingest <cell_path> <file_or_dir>`
   - `shyftr notes sync <cell_path> <config_file>`
   - `shyftr notes status <cell_path>`
9. Test idempotent re-ingest.
10. Commit: `feat: ingest markdown notes as evidences`.

Acceptance criteria:

- Human-authored notes can enter ShyftR without becoming durable memories automatically.
- Links and tags are preserved as metadata.
- Incremental sync avoids duplicate evidences.

---

## Tranche UMS-11: Knowledge projections and markdown export

Objective: generate human-readable knowledge views from ShyftR.

Files:

- Create: `src/shyftr/exporters/__init__.py`
- Create: `src/shyftr/exporters/markdown.py`
- Create: `tests/test_markdown_export.py`
- Modify: `src/shyftr/cli.py`

Generated views:

- topic pages
- project pages
- daily summaries
- weekly summaries
- decision records
- rule pages
- open review queues
- conflict reports
- stale memory reports
- provenance indexes

Tasks:

1. Implement markdown export config.
2. Generate topic pages from tags and memory kinds.
3. Generate project pages from cell metadata.
4. Generate rule pages from approved rule ledgers.
5. Generate review queue pages from pending candidates and proposals.
6. Include provenance links back to memory, evidence, and candidate IDs.
7. Protect generated directories with a marker file.
8. Treat edits to generated files as new evidences only when explicitly configured.
9. Add CLI command: `shyftr export markdown <cell_path> <target_dir>`.
10. Test deterministic export output.
11. Commit: `feat: export markdown knowledge projections`.

Acceptance criteria:

- ShyftR can generate a usable markdown knowledge workspace.
- Generated markdown remains a projection.
- Provenance stays visible.
- Human edits do not silently rewrite canonical memory.

---

## Tranche UMS-12: Native review workspace CLI/TUI foundation

Objective: make memory and knowledge review manageable without external note tools.

Files:

- Create: `src/shyftr/review_workspace.py`
- Create: `tests/test_review_workspace.py`
- Modify: `src/shyftr/cli.py`

Tasks:

1. Add list helpers for pending candidates.
2. Add list helpers for proposal queues.
3. Add review helpers for approve, reject, defer, split, merge, supersede, and deprecate.
4. Add conflict review helpers.
5. Add rule proposal review helpers.
6. Add CLI commands under `shyftr workspace`.
7. Keep all review actions append-only.
8. Test common review flows.
9. Commit: `feat: add review workspace helpers`.

Acceptance criteria:

- A user can review memory without editing JSONL directly.
- Every review decision appends an event.
- Review queues can serve both agent memory and note-derived knowledge.

---

## Tranche UMS-13: Research and document knowledge layer

Objective: support research/document workflows commonly handled in note workspaces.

Files:

- Create: `src/shyftr/documents/__init__.py`
- Create: `src/shyftr/documents/text.py`
- Create: `src/shyftr/documents/citations.py`
- Create: `tests/test_documents.py`
- Create: `docs/concepts/research-knowledge-layer.md`

Tasks:

1. Ingest plain text and markdown documents as document evidences.
2. Define optional PDF/OCR adapter hooks without making them required dependencies.
3. Extract title, author, date, citation-like metadata, and section structure where available.
4. Extract quote/excerpt candidates with evidence offsets.
5. Extract claim candidates with provenance.
6. Build literature/research packs from reviewed memories.
7. Generate contradiction and support reports.
8. Test citation/provenance preservation.
9. Commit: `feat: add research document knowledge layer`.

Acceptance criteria:

- Documents become evidences with strong provenance.
- Claims and quotes can become reviewable candidates.
- Research summaries can cite evidence and candidate provenance.

---

## Tranche UMS-14: Personal knowledge maintenance loops

Objective: make ShyftR actively maintain memory quality rather than accumulating stale material.

Files:

- Create: `src/shyftr/maintenance/personal.py`
- Create: `src/shyftr/maintenance/__init__.py`
- Create: `tests/test_personal_maintenance.py`
- Modify: `src/shyftr/cli.py`

Tasks:

1. Add daily capture inbox report.
2. Add weekly memory review report.
3. Add stale preference audit.
4. Add contradiction audit.
5. Add low-use high-confidence memory audit.
6. Add repeated-miss report.
7. Add rule candidate report.
8. Add CLI command: `shyftr maintenance personal <cell_path>`.
9. Test generated reports are proposal-only.
10. Commit: `feat: add personal knowledge maintenance reports`.

Acceptance criteria:

- ShyftR proposes cleanup and consolidation.
- Background maintenance does not silently mutate durable authority.
- Reports help decide what to promote, retire, or revisit.

---

## Tranche UMS-15: Workspace interoperability and displacement path

Objective: keep markdown workspaces useful during transition while making them optional.

Files:

- Create: `docs/concepts/workspace-interoperability.md`
- Create: `examples/markdown-workspace-sync.yaml`
- Modify: `src/shyftr/notes/sync.py`
- Modify: `src/shyftr/exporters/markdown.py`
- Create: `tests/test_workspace_interoperability.py`

Modes:

1. Workspace as evidence:
   - human writes notes externally
   - ShyftR ingests notes as evidences
2. Workspace as Projection:
   - ShyftR exports generated markdown views
   - external tools display them
3. ShyftR-native:
   - ShyftR review/search/profile tools operate without external note software

Tasks:

1. Document the three modes.
2. Implement sync config for evidence mode.
3. Implement export config for Projection mode.
4. Detect generated-file edits and require explicit ingest as new evidences.
5. Test evidence mode and Projection mode do not conflict.
6. Commit: `feat: define markdown workspace interoperability`.

Acceptance criteria:

- Users can keep an external markdown workspace during migration.
- ShyftR remains canonical.
- External workspace removal does not break memory operations.

---

## Tranche UMS-16: Backup, restore, portability, and sync safety

Objective: make ShyftR trustworthy as the only durable memory system.

Files:

- Create: `src/shyftr/backup.py`
- Create: `src/shyftr/restore.py`
- Create: `tests/test_backup_restore.py`
- Modify: `src/shyftr/cli.py`
- Create: `docs/concepts/backup-portability.md`

Tasks:

1. Implement cell snapshot export.
2. Generate hash manifests for ledgers and projections.
3. Exclude rebuildable indexes by default or mark them as rebuildable.
4. Implement restore validation.
5. Implement restore dry-run.
6. Implement backup verification.
7. Add optional encrypted archive hook without making encryption a hard dependency.
8. Add CLI commands:
   - `shyftr backup <cell_path> <target>`
   - `shyftr restore <snapshot> <target>`
   - `shyftr backup verify <snapshot>`
9. Test backup, restore, index rebuild, and manifest validation.
10. Commit: `feat: add cell backup and restore`.

Acceptance criteria:

- A cell can be backed up, restored, and verified.
- Restored indexes can be rebuilt from ledgers.
- No canonical memory depends on a hosted service.

---

## Tranche UMS-17: Production hardening

Objective: harden ShyftR enough to act as the only memory substrate.

Files:

- Create: `src/shyftr/validation.py`
- Create: `src/shyftr/migrations.py`
- Create: `tests/test_validation.py`
- Create: `tests/test_migrations.py`
- Create: `docs/operations/production-hardening.md`

Tasks:

1. Add ledger schema validation.
2. Add append integrity validation.
3. Add corruption detection reports.
4. Add migration registry and dry-run support.
5. Add concurrency-safe append tests.
6. Add large cell benchmark fixtures.
7. Add token budget regression tests.
8. Add privacy/security policy docs.
9. Add failure recovery docs.
10. Commit: `feat: harden ShyftR for production memory use`.

Acceptance criteria:

- ShyftR has a recovery path after interrupted writes.
- Schema changes are migratable and testable.
- Large cells remain queryable.
- The project has enough operational safety to retire previous memory providers.

---

## Migration sequence

Use this sequence when moving an assistant runtime from an existing memory provider to ShyftR.

### Phase 1: Shadow

- Existing provider remains active.
- ShyftR receives duplicate durable memory writes.
- ShyftR builds profiles and packs in parallel.
- Compare search/profile quality.
- Record missing-memory feedback.

Exit criteria:

- ShyftR profile output is accurate.
- ShyftR search finds expected preferences and workflows.
- Import/mutation paths are tested.

### Phase 2: Primary with fallback

- Runtime reads ShyftR first.
- Existing provider is used only when ShyftR misses or errors.
- ShyftR receives feedback for useful, harmful, ignored, and missing memory.
- Existing provider writes are frozen or mirrored only for backup.

Exit criteria:

- Fallback rarely triggers.
- Profile/search regressions are resolved.
- Backups and restore tests pass.

### Phase 3: Primary only

- Runtime uses ShyftR for durable memory.
- Existing provider is archived as cold export.
- ShyftR handles remember, search, profile, forget, replace, pack, and feedback flows.

Exit criteria:

- No active runtime dependency on the previous memory provider.
- cell backup/restore is verified.
- Profile and search quality meet or exceed the previous provider for routine use.

---

## Workspace transition sequence

Use this sequence when moving durable knowledge workflows into ShyftR.

### Phase 1: Markdown workspace as evidence

- Human-authored notes remain in the external workspace.
- ShyftR ingests notes as evidences.
- Review gates decide which note-derived candidates become memories.

### Phase 2: Markdown workspace as Projection

- ShyftR exports generated knowledge views.
- External workspace displays generated markdown.
- Edits to generated files are controlled and optionally re-ingested as new evidences.

### Phase 3: ShyftR-native workspace

- ShyftR review/search/profile/dashboard tools are sufficient for routine work.
- External markdown workspace becomes optional.
- Markdown export remains available for portability and human-readable backup.

---

## Final retirement criteria for previous memory providers

Previous assistant-memory providers can be retired when ShyftR has:

- trusted explicit memory writes
- semantic and sparse search
- compact profile projection
- scoped multi-cell routing
- forget, replace, supersede, deprecate, quarantine, and sensitive exclusion
- assistant runtime integration in `primary_only` mode
- migration/import from existing memory exports
- backup and restore verification
- index rebuild verification
- enough feedback data to validate retrieval quality

At that point, ShyftR is the canonical durable memory substrate.

---

## Final displacement criteria for markdown workspaces

External markdown workspaces can become optional when ShyftR has:

- markdown note ingest
- document/research evidence ingest
- generated topic and project pages
- daily and weekly summaries
- review workspace commands or UI
- backlink and provenance projections
- portable markdown export
- backup and restore verification

At that point, external markdown tools remain useful surfaces, but ShyftR owns durable knowledge truth.

---

## Non-goals for the first implementation pass

- No hosted service requirement.
- No mandatory external vector database.
- No automatic destructive mutation of durable memory.
- No direct runtime operation mutation by ShyftR.
- No generated markdown as canonical truth.
- No product-specific lock-in.
- No bulk import that bypasses regulator review policy.

---

## Verification before each tranche commit

Run from a private ShyftR lab checkout:

```bash
python3 -m pytest -q
# Run the stale-term and weak-phrasing scans defined in the ShyftR project rule.
git status --short
```

Expected:

- tests pass
- stale-term and weak-phrasing scans have no public-doc matches
- only intended files are changed

---

## Plan completion target

When this plan is complete, ShyftR should be able to operate as:

- the assistant runtime's primary durable memory provider
- the canonical profile and preference store
- the project and domain memory substrate
- the evidence/pack/feedback learning loop for autonomous runtimes
- the canonical substrate for human-authored knowledge
- the generator of portable markdown knowledge workspaces
- the backup, restore, audit, and validation authority for memory cells

The desired end state:

```text
ShyftR owns canonical memory.
Runtimes consume packs and report feedback.
Human tools create evidences and display projections.
cell ledgers remain inspectable, local-first, and portable.
```
