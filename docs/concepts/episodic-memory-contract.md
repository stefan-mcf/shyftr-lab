# Episodic memory contract (Episode)

Status: Phase 10 contract freeze (planned behavior; docs-only)

This document defines the contract for a first-class `Episode` object and the `episodic` memory class.

Scope note:
- Phase 10 P10-0 freezes terminology and the object/lifecycle contract.
- This document does not claim that storage, retrieval, or tooling is already implemented.

## Naming and terminology

Use these terms consistently:

- `Episode` (capitalized) is the first-class object that represents a review-gated unit of event history.
- `episodic` (lowercase) is the `memory_type` value for the memory class (authority/retention/retrieval semantics).
- `episode_id` is the stable logical identifier for an Episode across appended rows.
- `episode_kind` is a bounded subtype (for example: `session`, `task`, `incident`, `tool_outcome`, `decision_context`, `custom`).

Avoid introducing additional public nouns for the same concept (for example: “timeline object”, “session memory”, “experience object”) unless they are explicitly defined as compatibility aliases.

## Purpose and authority

Episodes are review-gated event history / provenance.

- Episodes record what happened, when, and under which runtime/session/task context.
- Episodes may cite evidence via anchors to support inspection and audits.
- Episodes are not guidance authority and must not outrank reviewed `rule`, `semantic`, or `procedural` memory in default pack posture.
- Episodes may support later proposals to create or update guidance memory (semantic/procedural/rule), but that promotion is explicitly out of scope for Phase 10.

Authority and retention defaults for episodic memory:

- `memory_type`: `episodic`
- `authority`: `review_gated`
- `retention`: `event_history`
- default retrieval role: `background` (unless a later reviewed policy explicitly changes it)

## Storage contract (planned)

Episodes are intended to be stored as an append-only ledger with “latest row wins” resolution by `episode_id`.

Canonical additive ledger path (chosen for Phase 10 planning):

- `ledger/episodes.jsonl`

Notes:
- The ledger is additive. Phase 10 must not require destructive migrations of existing ledgers.
- Existing durable-memory rows that already carry `memory_type='episodic'` remain valid durable-memory rows; they are not implicitly reinterpreted as first-class Episodes.

## Episode fields

This contract distinguishes:
- required fields for an approved Episode,
- a minimum set required for proposed rows, and
- optional fields.

### Required fields (approved Episodes)

An Episode row with `status=approved` must include, at minimum:

- `episode_id`: stable logical identifier.
- `cell_id`: owning cell identifier.
- `episode_kind`: one of `session`, `task`, `incident`, `tool_outcome`, `decision_context`, `custom`.
- `title`: short human-readable title.
- `summary`: concise narrative summary of what happened.
- `started_at`: ISO-8601 timestamp for the start of the episode window.
- `ended_at`: ISO-8601 timestamp for the end of the episode window.
- `actor`: bounded label for the actor (for example: operator, runtime, system, tool).
- `action`: what was attempted or observed.
- result label: one of `success`, `failure`, `partial`, `blocked`, `superseded`, `informational`, `unknown`.
- `status`: one of `proposed`, `approved`, `archived`, `redacted`, `superseded`, `rejected`.
- `memory_type`: fixed to `episodic`.
- `authority`: fixed/defaulted to `review_gated`.
- `retention`: fixed/defaulted to `event_history`.
- `confidence`: bounded numeric confidence (scale and bounds defined by implementation, but must be consistent).
- `sensitivity`: `public` | `internal` | `private` | `sensitive`.
- `created_at`: ISO-8601 timestamp indicating when this row was appended.

### Minimum fields for proposed Episodes

A row with `status=proposed` is allowed to be incomplete relative to `approved` as long as it remains review-gated and is not treated as eligible for default retrieval.

At minimum, proposed rows must include:

- `episode_id`, `cell_id`, `episode_kind`
- `status=proposed`
- `memory_type=episodic`
- `created_at`

### Optional fields (planned / permitted)

The following are permitted when available, but not required by this tranche:

- runtime/session/task context: `runtime_id`, `session_id`, `task_id`
- tool provenance: `tool_name`, `tool_action`
- capsule structure: `key_points` (short bullet list)
- failure analysis: `failure_signature`, `recovery_summary`
- relationships: `parent_episode_id`, `related_episode_ids`
- derived links: `derived_memory_ids`
- supersession: `supersedes_episode_id`, `superseded_by_episode_id`
- retention controls: `valid_until`, `retention_hint`
- freeform metadata: `metadata` (JSON object)

## Anchor requirement

An approved Episode must include at least one evidence anchor.

Approved Episode anchor fields (one or more must be non-empty):

- `live_context_entry_ids`
- `memory_ids`
- `feedback_ids`
- `resource_refs`
- `grounding_refs`
- `artifact_refs`

Rules:
- A proposed Episode may be anchor-incomplete.
- Approval must fail if all anchor lists are empty.
- Anchors are part of the provenance record. A later redaction should preserve identifiers and anchor structure even if prose is removed.

## Lifecycle and append-only behavior

Episodes use an append-only lifecycle. Edits are represented by appending a new row with the same `episode_id` and a new `created_at`.

Allowed high-level transitions:

- `proposed -> approved -> archived | redacted | superseded`
- `proposed -> rejected`

Lifecycle rules:

- Every state transition appends a new row; there is no in-place update requirement.
- Readers resolve the current state by `episode_id` using latest-row-wins.
- `approved` is the threshold for eligibility in episode-aware retrieval.
- `rejected` is never eligible for retrieval.
- `archived` remains inspectable but is intended to be downranked or excluded from default packs.
- `redacted` preserves audit identity and anchors while redacting unsafe prose fields.
- Phase 10 introduces no physical deletion requirement.

## Retrieval stance (planned)

Episode-aware retrieval must remain deterministic and conservative.

Default stance:

- Include Episodes when the query explicitly asks for history, prior attempts, incidents, results, failures, or provenance.
- Include Episodes in diagnostic/forensics contexts.
- Prefer capsule exposure by default: title, summary, timeframe, result label, sensitivity label, and anchors.
- Keep episodic role as `background` unless an explicit reviewed policy says otherwise.

Phase 10 does not introduce learned rerankers, vector-service dependencies, or a broad retrieval-orchestration redesign.

## Privacy and export behavior (planned)

Episodes are high-risk records because they summarize real interactions, failures, and operational details.

Privacy and export contract:

- `sensitivity` must be explicitly tracked on Episodes.
- Sensitivity should default conservatively (for example: to the maximum sensitivity of the referenced anchors when that is available).
- `private` and `sensitive` Episodes must be excluded from public-safe exports.
- Redaction must preserve audit identity (for example `episode_id`, timestamps, and anchors) while redacting unsafe prose.
- Episodes should not store raw large tool outputs or blob dumps; they should store references/handles/anchors.

## Phase 10 non-goals

Phase 10 does not include:

- offline episode clustering or consolidation
- automatic promotion from Episodes into semantic/procedural/rule memory
- learned reranking or approximate nearest-neighbor/vector redesign
- hosted or multi-tenant service claims
- destructive migration of existing ledgers
- broad rewrite of live-context or carry semantics
- claims that Episodes improve success rates before measurement
