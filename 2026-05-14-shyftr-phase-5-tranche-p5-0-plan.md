# ShyftR Phase 5 — Tranche P5-0 plan (contract-first)

Date: 2026-05-14
Repo: /Users/stefan/ShyftR
Phase: Phase 5 — episodic consolidation and rehearsal
Tranche: P5-0 (planning + contract definition only)
Status after implementation: complete; superseded operationally by P5-1 implementation tranche

This artifact remains intentionally small and concrete. It defined the minimum operator-visible proposal contracts and a first implementation slice matrix before coding began. It no longer describes the live implementation state by itself; read the P5-1 plan and updated handoff packet for the current state.

## 1) Scope and stop boundary (P5-0)

In scope for P5-0:
- Read and reconcile Phase 5 intent across:
  - `2026-05-14-shyftr-phase-4-closeout.md`
  - `2026-05-14-shyftr-phase-5-handoff-packet.md`
  - `broad-roadmap-concept.md` (Phase 5 section)
  - `deep-research-report.md` (Phase 5 / consolidation / rehearsal discussion)
- Confirm existing repo contracts and terminology in:
  - `src/shyftr/models.py` (candidate + durable memory model)
  - `src/shyftr/promote.py` (review-gated promotion helper)
  - `src/shyftr/evolution.py` (review-gated proposal ledger + existing proposal types)
  - relevant tests (`tests/test_memory_evolution_consolidation.py`, `tests/test_promote.py`)
- Define explicit operator-visible proposal schemas for Phase 5 consolidation outputs:
  - duplicate merge
  - semantic promotion
  - procedural promotion
  - stale/challenge/deprecate (and adjacent “retire” actions)
- Identify the smallest realistic first implementation slice (code/file matrix) that can land in P5-1.
- Identify minimal RED test targets for P5-1 (tests that should be written first and initially fail).
- Provide verification commands for this planning tranche.

Stop boundary for P5-0:
- Stop after creating this single tranche plan file.
- Do not edit or claim changes in source code, tests, scripts, or existing docs.
- Do not claim Phase 5 implementation, consolidation, or rehearsal exists yet.

Safety posture (non-negotiable):
- All Phase 5 outputs remain review-gated and additive.
- No tranche in Phase 5 should silently mutate durable memory; it should propose.

## 2) Operator-visible proposal schemas (Phase 5)

Design constraints (must hold for all schemas below):
- Deterministic serialization (stable keys, stable ordering where applicable).
- Append-only: proposals are written to an append-only ledger and are never edited in place.
- Review-gated: proposals are never auto-applied.
- Additive: proposals and simulations may be appended; durable memory mutation happens only via explicit accepted actions.

Schema conventions:
- `proposal_type` MUST be one of the values already enforced in `src/shyftr/evolution.py` unless/until a new type is added by a later tranche.
- `target_ids` MUST refer to durable memory identifiers for lifecycle-affecting proposals.
- `candidate_ids` SHOULD carry lineage identifiers when known.
- `evidence_refs` MUST be non-empty. For Phase 5, it may include synthetic rehearsal fixture ids and/or memory refs.

### 2.1 Duplicate merge proposal schema (operator-visible)

Intent:
- Consolidate two or more duplicate/near-duplicate durable memories into a single retained durable memory statement while preserving lineage.
- This MUST be review-gated and MUST be simulation-required because it affects retrieval surfaces.

Operator-visible record shape:
- `proposal_type="merge_memories"`
- `target_ids=[old ids...]`
- `requires_simulation=true`
- `projection_delta.active_memory_delta=-1`
- `proposed_memory.statement=<merged statement>`
- `proposed_memory.source_memory_ids=[old ids...]`

Live implementation note:
- The minimal local implementation keeps merge acceptance conservative: accepting a merge deprecates duplicate source memories and does not silently create a new consolidated durable memory.

### 2.2 Semantic promotion proposal schema (operator-visible)

Intent:
- Propose a new durable memory that represents a stable semantic distillation extracted from episodic/session material.

Operator-visible record shape:
- `proposal_type="promote_missing_memory"`
- `target_ids=[]`
- `requires_simulation=false`
- `projection_delta.active_memory_delta=1`
- `projection_delta.new_memory_type="semantic"`
- `proposed_memory.statement=<semantic statement>`
- `proposed_memory.memory_type="semantic"`
- `proposed_memory.kind=<stable kind label>`

Live implementation note:
- This proposal path is now implemented locally and can be accepted into durable approved memory append-only.

### 2.3 Procedural promotion proposal schema (operator-visible)

Intent:
- Propose a durable procedural memory (skills/workflows/recovery recipes) extracted from repeated outcomes.

Operator-visible record shape:
- `proposal_type="promote_missing_memory"`
- `target_ids=[]`
- `requires_simulation=false`
- `projection_delta.active_memory_delta=1`
- `projection_delta.new_memory_type="procedural"`
- `proposed_memory.statement=<procedure/workflow statement>`
- `proposed_memory.memory_type="procedural"`
- `proposed_memory.kind="workflow"`

Live implementation note:
- The minimal local implementation differentiates semantic vs procedural promotion deterministically through heuristics over missing-memory candidate text.

### 2.4 Stale / challenge / deprecate proposal schema (operator-visible)

Intent:
- Identify durable memories that are stale, contradicted, or no longer appropriate; propose an operator decision.
- These affect retrieval, so proposals MUST require simulation.

Deprecate shape:
- `proposal_type="deprecate_memory"`
- `projection_delta.status_transition="approved -> deprecated"`
- `projection_delta.active_memory_delta=-1`

Challenge shape:
- `proposal_type="challenge_memory"`
- `projection_delta.status_transition="approved -> challenged"`
- `projection_delta.active_memory_delta=0`

Live implementation note:
- The local implementation now includes an explicit `challenge_memory` proposal type and acceptance path; the earlier planning workaround using an existing proposal type is no longer the current contract.

## 3) Minimal first implementation slice matrix (P5-1)

Planned file matrix:
- `src/shyftr/evolution.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/mutations.py`
- `tests/test_memory_evolution_consolidation.py`
- `tests/test_memory_evolution_forgetting.py`
- new focused Phase 5 evolution tests

What actually landed locally in the minimal implementation tranche:
- `src/shyftr/evolution.py`
- `tests/test_memory_evolution_phase5.py`
- `tests/test_memory_evolution_forgetting.py`

## 4) Minimal RED tests identified for P5-1

These were the correct initial RED targets:
1. accepting `promote_missing_memory` should append a review and create durable approved memory append-only;
2. repeated questioning feedback should emit a challenge proposal and acceptance should record challenged status;
3. deterministic rehearsal fixtures and appended rehearsal reports should exist;
4. existing consolidation/supersession/forgetting contracts should continue to pass.

Status now:
- Those tests were written and passed locally on the focused implementation surface.

## 5) Planning-tranche verification commands

Original P5-0 verification commands:
- `cd /Users/stefan/ShyftR && git status --short --branch`
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_current_state_baseline_smoke.py tests/test_current_state_metrics_schema.py tests/test_public_readiness_check.py tests/test_terminology_inventory.py`
- `cd /Users/stefan/ShyftR && git diff --check`

Updated interpretation:
- Those commands were appropriate for planning-only status.
- Current live implementation verification is now captured in the P5-1 plan and handoff packet.

## 6) Current guidance

Do not use this P5-0 file alone as the source of truth for live implementation state.
Use these in order instead:
1. `2026-05-14-shyftr-phase-5-handoff-packet.md`
2. `2026-05-14-shyftr-phase-5-tranche-p5-1-plan.md`
3. `src/shyftr/evolution.py`
4. `tests/test_memory_evolution_phase5.py`

## 7) Final note

P5-0 did its job: it defined the operator-visible contract and implementation boundary before code changes began.
The live repo has since moved into and through a minimal P5-1 implementation slice, with broader hardening/closeout still to be completed.