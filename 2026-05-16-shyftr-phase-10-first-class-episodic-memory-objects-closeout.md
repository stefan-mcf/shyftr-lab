# ShyftR Phase 10 Closeout: First-Class Episodic Memory Objects

Date: 2026-05-17
Repo: `/Users/stefan/ShyftR`
Status: complete; direct main commit/push authorized on 2026-05-17

## Verdict

Phase 10 is complete end to end locally.

ShyftR now has a first-class `Episode` object for timestamped, provenance-anchored, review-gated event history. Episodes are distinct from generic durable-memory rows with `memory_type='episodic'`; older rows remain compatibility records and are not migrated destructively.

Episodes are background event-history/provenance records. They do not replace semantic, procedural, resource, or rule guidance, and Phase 10 does not claim measured task-success lift.

## Implemented surface

### Contract and model

- Added `docs/concepts/episodic-memory-contract.md`.
- Updated `docs/concepts/memory-class-contract.md` to distinguish `Episode` objects from compatibility `memory_type='episodic'` rows.
- Added `Episode` dataclass and bounded validation in `src/shyftr/models.py`.
- Enforced fixed `memory_type='episodic'`, `authority='review_gated'`, `retention='event_history'`.
- Enforced approved-Episode anchor requirement.

### Ledger and projection

- Added `src/shyftr/episodes.py` with append-only helpers and latest-row reads.
- Added `ledger/episodes.jsonl` to the Cell layout allowlist.
- Added SQLite `episodes` projection and rebuild path in `src/shyftr/store/sqlite.py`.
- Tested latest-row lifecycle behavior for proposed, approved, archived, and redacted rows.

### Harvest bridge

- Extended session harvest in `src/shyftr/live_context.py` to create review-gated Episode proposals from harvested live-context entries.
- Added `episode_proposal_count` to the harvest report.
- Preserved default proposal posture; direct durable writes remain policy-gated.

### Retrieval, provider, and pack

- Added approved-Episode retrieval into `src/shyftr/provider/memory.py`.
- Added Episode snippets into canonical pack assembly in `src/shyftr/pack.py` as background/provenance context.
- Preserved compatibility with legacy `memory_type='episodic'` durable-memory rows.
- Did not add learned reranking or vector dependencies.

### CLI, MCP, and HTTP surfaces

- Added `shyftr episode capture` and `shyftr episode search`.
- Added MCP tools `shyftr_episode_capture` and `shyftr_episode_search`.
- Added local HTTP routes `/episode/capture` and `/episode/search`.
- Write-capable capture surfaces are dry-run by default and require explicit `--write` / `write=true`.
- Search returns sensitivity-safe Episode capsules.

### Evaluation and status reporting

- Extended `src/shyftr/evaluation_bundle.py` with `episode_contract_coverage`.
- Coverage reports:
  - ledger event count;
  - latest Episode count;
  - lifecycle status buckets;
  - Episode kind buckets;
  - sensitivity buckets;
  - anchor completeness;
  - privacy posture;
  - explicit `task_success_lift.status = unmeasured`.
- Updated `docs/status/current-implementation-status.md` with the Phase 10 capability row.
- Updated the Phase 10 tranche plan status and superseded the ready handoff packet.

## Test evidence added

New focused tests:

- `tests/test_phase10_episode_contract.py`
- `tests/test_phase10_episode_ledger.py`
- `tests/test_phase10_episode_sqlite_projection.py`
- `tests/test_phase10_episode_harvest.py`
- `tests/test_phase10_episode_provider_pack.py`
- `tests/test_phase10_episode_cli.py`
- `tests/test_phase10_episode_mcp.py`
- `tests/test_phase10_episode_server.py`
- `tests/test_phase10_episode_evaluation.py`

Updated regression tests:

- `tests/test_mcp_server.py`
- `tests/test_phase8_eval_bundle_runner.py`

## Verification performed

Focused tranche checks performed during implementation:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_contract.py
# 6 passed

PYTHONPATH=.:src pytest -q tests/test_phase10_episode_contract.py tests/test_phase10_episode_ledger.py
# 11 passed

PYTHONPATH=.:src pytest -q tests/test_phase10_episode_sqlite_projection.py tests/test_phase10_episode_ledger.py tests/test_phase10_episode_contract.py
# 15 passed

PYTHONPATH=.:src pytest -q tests/test_phase10_episode_harvest.py tests/test_session_harvest.py tests/test_live_context.py
# 12 passed

PYTHONPATH=.:src pytest -q tests/test_phase10_episode_provider_pack.py tests/test_phase9_provider_contract.py tests/test_phase9_pack_loadout_equivalence.py
# 10 passed

PYTHONPATH=.:src pytest -q tests/test_phase10_episode_cli.py tests/test_phase10_episode_mcp.py tests/test_phase10_episode_server.py tests/test_server.py
# 32 passed

PYTHONPATH=.:src pytest -q tests/test_phase10_episode_evaluation.py tests/test_phase8_eval_bundle_runner.py tests/test_phase8_cli_eval_bundle.py
# 16 passed
```

Full closeout gate performed after status/closeout edits:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
PYTHONPATH=.:src pytest -q
```

Result:

```text
ShyftR public readiness check
PASS
1095 passed, 40 warnings in 18.82s
```

Warnings are existing `httpx` TestClient deprecation warnings from FastAPI tests.

## Swarm and controller execution note

- A persistent `swarm2` builder lane was launched for P10-0/P10-1 work; it completed P10-0 and partially seeded P10-1 before stalling, after which the controller recovered and verified the model/test implementation.
- A persistent `swarm3` reviewer lane was launched for end-to-end Phase 10 review. It exited successfully with no blocker and confirmed the remaining verification path.
- Later narrow completion work was finished controller-side against the already-dirty local worktree to preserve attribution and avoid broad write-scope drift.

## Files changed or added

Changed:

- `2026-05-16-shyftr-phase-10-first-class-episodic-memory-objects-tranched-plan.md`
- `2026-05-16-shyftr-phase-10-ready-handoff-packet.md`
- `docs/concepts/memory-class-contract.md`
- `src/shyftr/cli.py`
- `src/shyftr/evaluation_bundle.py`
- `src/shyftr/integrations/pack_api.py`
- `src/shyftr/layout.py`
- `src/shyftr/live_context.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/models.py`
- `src/shyftr/pack.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/server.py`
- `src/shyftr/store/sqlite.py`
- `tests/test_mcp_server.py`
- `tests/test_phase8_eval_bundle_runner.py`

Added:

- `docs/concepts/episodic-memory-contract.md`
- `src/shyftr/episodes.py`
- `tests/test_phase10_episode_cli.py`
- `tests/test_phase10_episode_contract.py`
- `tests/test_phase10_episode_evaluation.py`
- `tests/test_phase10_episode_harvest.py`
- `tests/test_phase10_episode_ledger.py`
- `tests/test_phase10_episode_mcp.py`
- `tests/test_phase10_episode_provider_pack.py`
- `tests/test_phase10_episode_server.py`
- `tests/test_phase10_episode_sqlite_projection.py`

## Deferred work

Phase 10 intentionally does not include:

- offline clustering or Episode consolidation;
- automatic semantic/procedural promotion from Episodes;
- learned reranking or vector-service redesign;
- hosted or multi-tenant behavior;
- destructive migration of existing ledgers;
- task-success lift claims.

Recommended next tranche is a separate planning pass that chooses between temporal retrieval/reranking hardening, Episode consolidation, or class-aware evaluation expansion. Do not start it by modifying Phase 10 surfaces unless a regression appears.
