# ShyftR Phase 10 Ready Handoff Packet

Date: 2026-05-16
Recorded: 2026-05-16 15:53:02 AEST
Repo: `/Users/stefan/ShyftR`
Status: ready to start Phase 10 planning-contract tranche

## Current truth

Phase 9 Core Contract Hardening is complete locally and fully verified.

Phase 10 is now planned as:

```text
ShyftR Phase 10: First-Class Episodic Memory Objects
```

Canonical plan:

- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-10-first-class-episodic-memory-objects-tranched-plan.md`

Read first:

- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-10-first-class-episodic-memory-objects-tranched-plan.md`
- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-9-core-contract-hardening-closeout.md`
- `/Users/stefan/ShyftR/2026-05-16-shyftr-post-phase-9-handoff-packet.md`
- `/Users/stefan/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/ShyftR/deep-research-report.md`
- `/Users/stefan/ShyftR/docs/concepts/memory-class-contract.md`
- `/Users/stefan/ShyftR/docs/status/current-implementation-status.md`

## Resume point

Begin at P10-0 in the Phase 10 plan.

P10-0 objective:

- create `docs/concepts/episodic-memory-contract.md`;
- patch `docs/concepts/memory-class-contract.md` to point at the new contract;
- keep the work documentation-only and public-safe;
- run terminology/public-readiness checks before code changes.

Do not start code until P10-0 is filed and checked.

## What Phase 10 is implementing

Phase 10 implements roadmap item 10:

```text
First-class episodic memory objects.
```

The intended object is `Episode`.

An Episode is a timestamped, provenance-anchored, review-gated event-history object. It records what happened, when, involving which runtime/session/task context, actor/tool/action, outcome, sensitivity, and evidence anchors.

`episodic` is the memory class value. `Episode` is the object.

## What already exists

Do not redo these unless tests prove regression:

- `episodic` is already a valid memory class in `src/shyftr/memory_classes.py`.
- Generic durable-memory rows can carry `memory_type='episodic'`.
- Live-context harvest can classify archived/completed working-state rows as episodic archive material.
- Pack/provider paths already have generic `memory_type` filtering.
- Phase 9 already hardened pack canonicalization, append-only latest-row behavior where touched, retrieval-log projection fidelity, and provider filter/label semantics.

## What does not exist yet

Phase 10 should add these, in order:

1. Episode contract doc.
2. Episode model and validation.
3. Append-only episode ledger and latest-row reads.
4. SQLite projection/rebuild for episodes.
5. Live-context harvest to review-gated episode proposals.
6. Episode-aware search/pack policy.
7. Minimal dry-run-safe CLI/MCP/HTTP surfaces if exposed.
8. Evaluation/status/closeout.

## Non-goals

Do not drift into:

- offline clustering/consolidation;
- automatic semantic/procedural promotion;
- learned reranking or vector-service redesign;
- hosted or multi-tenant behavior;
- destructive migration of existing ledgers;
- broad live-context/carry rewrite;
- task-success improvement claims before measurement.

## First files to inspect for implementation

- `src/shyftr/models.py`
- `src/shyftr/memory_classes.py`
- `src/shyftr/live_context.py`
- `src/shyftr/ledger_state.py`
- `src/shyftr/layout.py`
- `src/shyftr/store/sqlite.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/pack.py`
- `src/shyftr/cli.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/server.py`

## First tests to write

P10-1 should start with:

- `tests/test_phase10_episode_contract.py`

Minimum RED assertions:

- `Episode` round-trips through dict serialization.
- `Episode` requires `memory_type='episodic'`.
- approved episodes require at least one anchor.
- invalid lifecycle status is rejected.
- sensitivity and relationship fields are preserved.

P10-2 should then add:

- `tests/test_phase10_episode_ledger.py`

P10-3 should then add:

- `tests/test_phase10_episode_sqlite_projection.py`

## Verification contract

P10-0 docs-only checks:

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
```

Focused implementation checks as tranches land:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_contract.py
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_ledger.py
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_sqlite_projection.py
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_harvest.py
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_provider_pack.py
```

Full closeout bundle:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
PYTHONPATH=.:src pytest -q
```

## Worktree caution

The worktree was already dirty before this Phase 10 planning artifact was created. Do not reset, clean, stash, commit, or push without reviewing the full `git status --short --branch` output and deciding which Phase 8/9/10 artifacts belong together.

Expected new Phase 10 planning artifacts from this pass:

- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-10-first-class-episodic-memory-objects-tranched-plan.md`
- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-10-ready-handoff-packet.md`

## Swarm/research note

This handoff was prepared after:

- controller-side repo inspection;
- a read-only `swarm2` planning lane;
- bounded delegate research lanes for implementation surfaces, architecture constraints, and roadmap sequencing.

The swarm/delegate lanes were advisory. The canonical plan and this handoff were written and verified controller-side from repo files.
