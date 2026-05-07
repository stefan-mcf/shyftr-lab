# memory Provider Contract

This contract defines how ShyftR presents a local-first memory-provider surface to assistant runtimes and automation tools. The contract is category-level and provider-neutral. It captures the durable memory responsibilities commonly expected from assistant-memory layers while preserving ShyftR's cell ledger truth model.

## Contract principles

- cell ledgers are canonical truth for every memory write, mutation, review event, and feedback.
- The regulator controls admission, promotion, retrieval, mutation, and export.
- Search uses the grid as rebuildable acceleration over ledger-backed memories, patterns, rules, and evidence.
- Profiles are projections generated from reviewed memory.
- packs are bounded applications of memory for a task or runtime context.
- Importers convert provider exports into evidences with provenance before promotion.
- Exports produce snapshots or projection artifacts without transferring canonical authority away from the cell ledger.

## Compatibility surface

### `remember`

Purpose: add explicit durable memory material.

Expected inputs:

- target cell
- memory statement or structured fact
- kind such as preference, constraint, workflow, tool quirk, identity fact, project vocabulary, or safety boundary
- actor and source context
- optional sensitivity, scope, and review policy metadata

ShyftR behavior:

1. Record a evidence or accepted trusted-memory event.
2. Apply regulator checks for scope, sensitivity, pollution, duplication, and policy.
3. Create a candidate or, when policy allows, a reviewed memory with full provenance.
4. Preserve review and promotion evidence in append-only ledgers.

Output should include a stable ShyftR identifier, review state, provenance pointers, and any regulator warnings.

### `search`

Purpose: retrieve durable memory relevant to a query, task, profile section, or runtime context.

Expected inputs:

- target cell or cell scope set
- query text or structured query
- optional trust tiers, kinds, status filters, sensitivity filters, and result limit
- optional task or runtime context for scoring

ShyftR behavior:

1. Query the grid and ledger-derived metadata.
2. Apply status, sensitivity, scope, confidence, and trust filters.
3. Return labeled results with memory, pattern, rule, candidate, or evidence provenance.
4. Record retrieval logs when the search contributes to a pack or task.

Results must identify trust tier, confidence, lifecycle status, source IDs, and selection rationale.

### `profile`

Purpose: build a compact assistant profile from reviewed memory.

Expected inputs:

- target cell or cell scope set
- optional section filters
- token or character budget
- target runtime constraints

ShyftR behavior:

1. Select reviewed memories, patterns, and rules that belong in stable profile material.
2. Exclude deprecated, superseded, isolated, or sensitivity-excluded memory by default.
3. Render deterministic profile sections with provenance references.
4. Preserve the profile as a rebuildable projection.

Profiles must never become canonical truth. The cell ledger remains the source.

### `forget`

Purpose: remove memory from normal retrieval and profile projections while preserving auditability.

Expected inputs:

- memory ID or query-resolved target
- actor
- reason
- optional scope and effective policy

ShyftR behavior:

1. Append a lifecycle or redaction/exclusion event.
2. Exclude the affected memory from normal search, pack assembly, and profile generation.
3. Preserve enough ledger metadata for audit, conflict handling, backup validation, and lawful export policies.

Forget is implemented through append-only exclusion semantics, not silent ledger rewriting.

### `replace`

Purpose: supersede one memory with a corrected or more current memory.

Expected inputs:

- source memory ID
- replacement statement or structured fact
- actor and reason
- optional review policy metadata

ShyftR behavior:

1. Record the replacement material as new evidence.
2. Promote the replacement through the regulator.
3. Append a supersession event linking old and new memory.
4. Exclude superseded memory from normal pack/profile output unless explicitly requested.

### `deprecate`

Purpose: reduce or remove authority from memory that has aged, failed, conflicted, or become less useful.

Expected inputs:

- memory ID or target set
- actor or automated proposal source
- reason and evidence
- optional severity and review state

ShyftR behavior:

1. Append a deprecation proposal or approved deprecation event.
2. Adjust retrieval and pack eligibility according to policy.
3. Preserve the memory, reason, and evidence for audit and future review.

Destructive deprecation should remain review-gated.

### `pack`

Purpose: provide bounded task-ready memory context to an assistant runtime.

Expected inputs:

- target cell or cell scope set
- task description or structured task context
- runtime identity and scope
- optional token budget, trust tiers, roles, and sensitivity rules

ShyftR behavior:

1. Retrieve and rank relevant memory.
2. Apply regulator limits for trust, sensitivity, scope, lifecycle status, and export policy.
3. Produce role-labeled guidance, caution, background, and conflict items.
4. Record retrieval logs and pack identifiers for later feedback.

The pack is an application artifact. The ledger remains canonical.

### `record_feedback`

Purpose: record whether memory helped, harmed, was ignored, or was missing after use.

Expected inputs:

- pack ID or retrieval log reference
- runtime/task identifiers
- useful, harmful, ignored, violated, or missing memory details
- verification evidence
- result status

ShyftR behavior:

1. Append feedback and related confidence events.
2. Update confidence projections from append-only ledgers.
3. Preserve pack miss details and evidence for Sweep, Challenger, and review workflows.
4. Avoid lowering global confidence from a single ambiguous miss without corroborating evidence.

feedback drives learning but does not rewrite memory history.

### `import_memory_export`

Purpose: ingest an exported memory set from another provider category.

Expected inputs:

- export artifact or parsed records
- evidence category and provenance metadata
- target cell
- import policy and review mode

ShyftR behavior:

1. Treat every imported item as an evidence record with provenance.
2. Normalize fields into ShyftR kinds, scopes, timestamps, and sensitivity metadata.
3. Detect duplicates and conflicts before promotion.
4. Require review or configured trusted-import policy before imported material becomes durable memories.
5. Preserve an import manifest with counts, rejected rows, warnings, and source hashes.

Imports are migration evidence records, not direct canonical replacements.

### `export_memory_snapshot`

Purpose: produce portable memory output for backup, audit, runtime injection, or migration.

Expected inputs:

- target cell or cell scope set
- requested projection type
- sensitivity and redaction policy
- format such as JSONL, JSON, or markdown

ShyftR behavior:

1. Export ledger-backed records or projection artifacts according to policy.
2. Include provenance, lifecycle status, confidence, and evidence references when allowed.
3. Exclude sensitive, forgotten, deprecated, or isolated items by default unless an audit policy explicitly includes them.
4. Include snapshot metadata, schema version, and originating-ledger hashes.

Snapshots are portable artifacts. The originating cell ledger remains authoritative.

## Category capability mapping

| Provider-category capability | ShyftR contract operation | ShyftR-native authority |
|---|---|---|
| Store a user preference | `remember` | evidence/candidate/memory ledgers |
| Search memories | `search` | grid over cell ledgers |
| Generate assistant profile | `profile` | Profile projection from reviewed memory |
| Supply task context | `pack` | pack projection plus retrieval logs |
| Record usefulness | `record_feedback` | feedback and confidence ledgers |
| Forget memory | `forget` | Lifecycle/redaction/exclusion ledgers |
| Correct memory | `replace` | Supersession ledgers plus new memory |
| Age out weak memory | `deprecate` | Deprecation events and review state |
| Migrate from an export | `import_memory_export` | Imported evidence records with provenance |
| Create a backup or migration artifact | `export_memory_snapshot` | Policy-bound snapshot projection |

## Implementation status

Current implementation status after UMS-2:

- `shyftr.provider.memoryProvider` provides a cell-bound facade for the implemented memory-provider surface.
- `remember(cell_path, statement, kind, evidence_context=None, metadata=None)` writes explicit memory through the regulator and records a evidence, candidate review, promotion event, and memory with provenance.
- `remember_trusted(cell_path, statement, kind, actor, trust_reason, evidence_channel, created_at, trusted_direct_promotion=True, metadata=None)` is the hardened trusted explicit-memory path. It requires actor, trust reason, evidence channel, and creation time before any ledger write.
- `TrustedmemoryProvider(cell_path, actor, evidence_channel)` wraps the same trusted path for cell-bound runtime use.
- Trusted kinds are intentionally narrow: `preference`, `constraint`, `workflow`, and `tool_quirk`. Unsupported kinds fail before ledger writes.
- Trusted writes still pass regulator pollution checks. Operational state, branch/worktree details, artifact paths, queue status, and unverified completion claims are rejected before admission.
- When trusted direct promotion is enabled, the trusted path still records evidence, a candidate, review metadata, a promotion event, and an approved memory. It does not write memories directly.
- When trusted direct promotion is disabled, ShyftR captures the evidence record and pending candidate evidence without creating a review, promotion event, or approved memory automatically.
- `search(cell_path, query, top_k=10, trust_tiers=None, kinds=None)` reads approved memory rows, collapses append-only ledger updates to the latest row per memory ID, excludes user-facing forgotten or replaced memories, and returns trust tier, memory ID, confidence, lifecycle status, selection rationale, and provenance.
- `profile(cell_path, max_tokens=2000)` returns a compact markdown profile projection with provenance memory IDs. It is a rebuildable projection, not canonical truth.
- `forget(cell_path, memory_id, reason, actor)`, `replace(cell_path, memory_id, new_statement, reason, actor)`, and `deprecate(cell_path, memory_id, reason, actor)` append provider lifecycle events. `forget` and `replace` exclude affected memories from normal provider search/profile reads; broader lifecycle ledgers remain planned for UMS-4.

Current boundaries:

- UMS-1 covers the direct provider API and local lexical search/profile projection path.
- UMS-2 covers the trusted explicit-memory path, required metadata, narrow trusted kinds, regulator pollution protection, and the direct-promotion disable switch.
- `pack`, `record_feedback`, `import_memory_export`, and `export_memory_snapshot` remain contract items for later work slices.
- Lifecycle semantics are provider-local until UMS-4 adds broader status, supersession, deprecation, quarantine, conflict, and redaction event models.
- Provider outputs remain ShyftR-native and category-level; adapters can map external categories into this surface without making any external provider canonical.

## Runtime compatibility notes

Assistant runtimes integrating with this contract should send explicit source identity, task identity, actor identity, and scope. They should treat ShyftR IDs as stable references and report feedback after using packs. They should avoid treating profile text as the source of truth; profiles should be regenerated when relevant ledger state changes.

The contract deliberately avoids product-specific field names. Adapters can map named provider exports into this contract, but the public ShyftR surface stays ShyftR-native.
