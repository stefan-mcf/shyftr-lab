# Memory class contract

Status: implemented public alpha

ShyftR Phase 3 introduces a canonical first-class memory-class layer while preserving append-only cell ledgers as truth and keeping older ledgers readable without destructive migration.

## Canonical classes

- `working`
- `continuity`
- `episodic`
- `semantic`
- `procedural`
- `resource`
- `rule`

## `memory_type` and `kind`

Use this separation:

- `memory_type` is the broad class describing authority, retention, and retrieval semantics.
- `kind` is the finer subtype or behavioral label inside that class.

Examples:

- `memory_type=semantic`, `kind=preference`
- `memory_type=semantic`, `kind=constraint`
- `memory_type=procedural`, `kind=workflow`
- `memory_type=procedural`, `kind=recovery_pattern`
- `memory_type=resource`, `kind=artifact_ref`
- `memory_type=rule`, `kind=escalation_rule`

## Class authority and retention

| class | authority | default retention | notes |
|---|---|---|---|
| working | runtime-only | session | active state only; not durable memory by default |
| continuity | advisory runtime | session resume | carry/checkpoint support, not durable semantic truth |
| episodic | review-gated | event history | provenance-preserving session/event memory |
| semantic | review-gated | durable | stable facts, preferences, constraints |
| procedural | review-gated | durable | workflows, recovery patterns, verification recipes |
| resource | grounded reference | durable reference | references/handles only, not blob dumps |
| rule | reviewed precedence | durable policy | highest behavioral authority after review |

## Compatibility doctrine

- Existing records may omit `memory_type`; they remain valid legacy inputs.
- Compatibility readers infer a safe default class from `kind`, trust tier, or typed live-context entry kind when possible.
- Missing `memory_type` is not itself a migration failure.
- SQLite and other projections preserve `memory_type` when present and tolerate absence for older rows.

Clarification:
- Phase 3 introduced memory classes as a contract and retrieval concept, but did not split canonical storage by class.
- Phase 10 may add an additive Episode ledger for first-class episodic objects (see `docs/concepts/episodic-memory-contract.md`) without rewriting older durable-memory rows.
- Historical durable-memory rows with `memory_type='episodic'` remain readable as durable-memory rows; they are not implicitly reinterpreted as first-class Episodes.

## Write-path boundaries

- live context captures `working` state, not durable memory by default.
- continuity/carry records remain advisory and classed as `continuity` unless promoted through a reviewed path.
- semantic and procedural durable memory remain review-gated or explicit-policy-gated.
- resource memory requires a stable reference or handle.
- rule memory outranks other durable classes in retrieval/pack posture, but promotion remains reviewed.

## Retrieval and pack expectations

- provider search and pack assembly may filter by `memory_type`.
- role assignment prefers class metadata over fragile flat kind lists.
- rule memory receives explicit higher precedence while staying explainable and deterministic.
- resource and episodic items remain distinguishable from semantic/procedural guidance.

## Explicit non-goals for this phase

- no hosted or multi-tenant redesign
- no class-specific storage backend split
- no learned rerankers or opaque scoring
- no destructive migration requirement for legacy cells
- no automatic transient-working-state promotion into durable semantic memory
