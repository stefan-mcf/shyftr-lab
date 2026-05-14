# ShyftR Phase 5 — Tranche P5-1 plan (implementation start)

Date: 2026-05-14
Repo: /Users/stefan/ShyftR
Phase: Phase 5 — episodic consolidation and rehearsal
Tranche: P5-1 (minimal additive implementation)

## Objective

Land the smallest end-to-end Phase 5 implementation that is honestly complete on the public-safe baseline:
- proposal-only consolidation remains review-gated;
- missing-memory promotions become acceptably actionable;
- challenge lifecycle becomes explicit rather than implicit;
- rehearsal fixtures/reports exist and are deterministic;
- CLI/API/console surfaces stay aligned.

## Why this tranche order is correct

The current repo already has:
- duplicate merge proposals;
- supersession/deprecate proposals;
- forgetting/redaction proposals;
- simulation and review ledgers;
- CLI/API routes for scan, simulate, review;
- console frontier dry-run evolution surface.

The main blocker to Phase 5 being end-to-end complete is that `promote_missing_memory` still raises `NotImplementedError` on acceptance, and there is not yet a deterministic rehearsal surface.

## Scope for P5-1

In scope:
1. implement missing-memory promotion proposal generation from `ledger/missing_memory_candidates.jsonl`;
2. implement acceptance path for `promote_missing_memory` so it creates durable approved memory append-only;
3. add an explicit `challenge_memory` proposal type and acceptance path using existing mutation helpers;
4. add deterministic rehearsal fixture generation and rehearsal report append path;
5. extend scan/eval/CLI/API/console surfaces only as needed to expose the above behavior;
6. keep docs current as code changes land.

Out of scope:
- dense clustering or semantic ANN changes;
- automatic merge acceptance creating consolidated memory silently;
- non-deterministic or model-dependent summarisation;
- hosted/background schedulers.

## TDD slices

1. RED: new focused Phase 5 tests fail because promotion + rehearsal functions do not exist.
2. GREEN slice A: add proposal generation for semantic/procedural missing-memory promotions.
3. GREEN slice B: implement acceptance path for `promote_missing_memory`.
4. GREEN slice C: add `challenge_memory` proposal + acceptance path.
5. GREEN slice D: add rehearsal fixture/report generation.
6. REFACTOR: align scan/eval/CLI/API/console docs and run focused/full verification.

## Verification sequence

Focused first:
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_memory_evolution_phase5.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q tests/test_memory_evolution_consolidation.py tests/test_memory_evolution_supersession.py tests/test_memory_evolution_forgetting.py tests/test_memory_evolution_evalgen.py tests/test_memory_evolution_simulation.py tests/test_memory_evolution_cli.py tests/test_memory_evolution_api.py tests/test_memory_evolution_schema.py`

Then broader:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`
- `cd /Users/stefan/ShyftR && PYTHONPATH=src:. pytest -q`

## Docs to update during tranche

At minimum keep these current as implementation lands:
- `/Users/stefan/ShyftR/2026-05-14-shyftr-phase-5-handoff-packet.md`
- `/Users/stefan/ShyftR/2026-05-14-shyftr-phase-5-tranche-p5-0-plan.md`
- a new Phase 5 closeout doc at the end of tranche completion

## Stop boundary

Stop only after:
- focused Phase 5 tests are green;
- implementation surfaces are read back from disk;
- docs are updated to match live behavior;
- repo-wide verification has been run and classified honestly.
