# ShyftR Phase 7 — Tranche P7-2 plan (privacy/export/redaction deepening)

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 7 — privacy, policy, and safety hardening
Tranche: P7-2 — privacy/export/redaction deepening
Status: ready to start after P7-1 closeoff and push
Predecessor closeoff: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-p7-1-closeoff.md`
Phase kickoff plan: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-0-plan.md`
Original handoff packet: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-handoff-packet.md`

## Objective

Land the next narrow additive Phase 7 slice after the P7-1 authority baseline by deepening privacy behavior specifically on export, pack, and projection surfaces.

This tranche should pin exactly which nested sensitive fields are redacted, which fields remain visible for safe operator-facing context, and which public/export surfaces must agree on that behavior.

The tranche must stay local-first, compatibility-safe, and review-gated. It must not introduce broader contradiction/poisoning machinery yet.

## Starting truth

P7-1 is already complete and pushed on `main`:
- commit: `b047d93b758d5b600e522ae18a19bf92548441e5`
- local verification already passed for the P7-1 landing surface
- current remote check-run truth at planning time:
  - `smoke` → completed / success
  - `quality-gates` → completed / success
  - `python-smoke (3.11)` → completed / success
  - `python-smoke (3.12)` → completed / success
  - `console-build` → in progress

Current implementation truth relevant to P7-2:
- `src/shyftr/privacy.py` now recursively redacts nested sensitive fields for sensitive rows.
- `tests/test_phase6_resource_memory_privacy.py` pins the original resource-ref locator redaction contract.
- `tests/test_phase7_privacy_redaction.py` pins the first deeper nested-field case.
- `src/shyftr/provider/memory.py` already restores `pack()` `selected_ids`, profile delegation, and readiness snapshot behavior.
- P7-1 did not yet prove cross-surface parity for pack/export/projection surfaces beyond the focused redaction baseline.

## Why P7-2 is next

The roadmap and P7-1 closeoff already separate the work correctly:
- P7-1 pinned authority defaults and the first nested-redaction baseline.
- The next highest-value gap is making privacy behavior consistent and explicit across pack/export/projection surfaces.
- Broader contradiction, poisoning, and prompt-injection policy work should remain deferred to P7-3.

## Non-negotiable constraints

- Keep all work inside `/Users/stefan/ShyftR`.
- Preserve local-first, ledger-first, inspectable behavior.
- Preserve additive compatibility for older rows and ledgers.
- Do not widen durable-write authority.
- Do not introduce hosted/platform/auth scope.
- Do not start contradiction/poisoning workflow machinery here.
- Do not let any public/export surface leak nested sensitive fields that P7-1 intends to redact.
- Keep safe display/context fields available where policy allows them.

## Scope of this tranche

### In scope

1. Define the canonical nested-field privacy contract for Phase 7 export/projection surfaces.
2. Extend tests so pack/export/projection surfaces prove the same privacy behavior.
3. Tighten implementation only where current surfaces drift from the intended contract.
4. Keep the contract field-aware and additive rather than inventing a broad new policy DSL.
5. Preserve operator-usable safe fields such as labels/origins/spans where allowed.

### Out of scope

- contradiction adjudication rules
- poisoning/prompt-injection suppression logic
- review-pool or operator-ledger redesign
- new runtime identity/authorization systems
- large refactors of retrieval strategy
- hosted/public-service export flows

## Canonical privacy contract to pin in tests

For records whose effective sensitivity is `private`, `secret`, or `restricted`:

1. `statement` must remain redacted on non-audit export/projection paths.
2. Nested sensitive fields must be redacted recursively.
3. Safe operator-facing context fields may remain visible when they do not reveal the hidden secret directly.
4. Redaction must be consistent across the same record when surfaced through:
   - direct redaction/projection helpers,
   - filtered export/projection helpers,
   - pack-like retrieval surfaces that expose selected items,
   - any readiness/export snapshot surface that serializes user-visible projections.
5. Grounding/reference handles that are already considered safe in the current contract may remain visible unless a test proves they leak the protected secret.

Initial field categories for this tranche should be treated as:

Sensitive nested fields to redact:
- `locator`
- `path`
- `uri`
- `sha256`
- `content_digest`
- `token`
- `secret`

Safe nested fields to preserve where present:
- `label`
- `ref_type`
- `kind`
- `origin`
- `span`
- `safe_display`
- source-fragment identifiers
- grounding reference identifiers
- approved-memory identifier
- cell identifier

If implementation reveals any ambiguous field during execution, the tranche should resolve it by adding a focused test and classifying it explicitly instead of leaving behavior incidental.

## Read-first file set

Planning / roadmap truth:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-p7-1-closeoff.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-0-plan.md`
- `/Users/stefan/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/ShyftR/docs/future-work.md`

Core code:
- `/Users/stefan/ShyftR/src/shyftr/privacy.py`
- `/Users/stefan/ShyftR/src/shyftr/provider/memory.py`
- `/Users/stefan/ShyftR/src/shyftr/federation.py`
- `/Users/stefan/ShyftR/src/shyftr/readiness.py`
- `/Users/stefan/ShyftR/src/shyftr/mcp_server.py`

Tests to extend or add:
- `/Users/stefan/ShyftR/tests/test_phase6_resource_memory_privacy.py`
- `/Users/stefan/ShyftR/tests/test_phase7_privacy_redaction.py`
- `/Users/stefan/ShyftR/tests/test_pack.py`
- `/Users/stefan/ShyftR/tests/test_memory_provider.py`
- `/Users/stefan/ShyftR/tests/test_replacement_readiness.py`

## Likely implementation touchpoints

Expected primary touchpoints:
- `src/shyftr/privacy.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/federation.py`

Possible secondary touchpoints only if tests prove necessary:
- `src/shyftr/readiness.py`
- `src/shyftr/mcp_server.py`
- `tests/test_pack.py`
- `tests/test_memory_provider.py`
- `tests/test_replacement_readiness.py`

## Minimum RED tests for P7-2

Write failing tests first for at least these cases:

1. Direct projection helper parity
- Extend `tests/test_phase7_privacy_redaction.py` with at least one deeper nested structure case:
  - nested dict inside `resource_ref` or `metadata`
  - sensitive nested values redacted recursively
  - safe fields preserved

2. Filtered export/projection parity
- Add a test that exercises the filtered export helper on sensitive rows and asserts the included projection matches the direct redaction contract.
- Verify excluded/warnings behavior remains stable where relevant.

3. Pack-surface privacy parity
- Add or extend a focused provider/pack test proving that a sensitive resource-backed memory surfaced through pack-like retrieval does not leak nested sensitive fields in the item payload while preserving safe display context.
- The test must assert the actual returned item shape, not just selected IDs.

4. Readiness/export-surface parity
- Add a focused readiness/provider export test proving that any exported user-visible projection or serialized proof surface does not regress the nested redaction contract.
- If snapshot export intentionally carries canonical ledger truth rather than public-safe projections, the test should pin that boundary explicitly instead of pretending the surface is public-safe.

5. Compatibility-safe safe-field visibility
- Add a test showing that safe fields like `label`, `origin`, `span`, or `safe_display` remain visible after deep redaction, so privacy hardening does not collapse operator utility.

## Ordered execution plan

### Task 1: Reconfirm live P7-1 truth

Objective: start from verified repo state and correct predecessor truth.

Steps:
1. Confirm repo root and branch state.
2. Re-read:
   - `2026-05-15-shyftr-phase-7-p7-1-closeoff.md`
   - `src/shyftr/privacy.py`
   - relevant pack/export tests
3. Confirm whether `console-build` finished or still requires later monitoring.

Verification:
- `cd /Users/stefan/ShyftR && git status --short --branch`
- `cd /Users/stefan/ShyftR && gh api repos/stefan-mcf/shyftr/commits/$(git rev-parse HEAD)/check-runs --jq '.check_runs[] | [.name,.status,.conclusion] | @tsv'`

Stop boundary:
- no file writes yet beyond the tranche’s own execution artifacts if needed.

### Task 2: Write failing privacy contract tests

Objective: make the exact P7-2 contract executable before changing implementation.

Files:
- Modify: `tests/test_phase7_privacy_redaction.py`
- Modify: `tests/test_pack.py`
- Modify: `tests/test_memory_provider.py`
- Maybe modify: `tests/test_replacement_readiness.py`

Steps:
1. Add direct deep-nesting redaction tests.
2. Add filtered-export parity test.
3. Add pack-surface assertion on actual returned item payload.
4. Add readiness/export boundary test only for a real current surface.
5. Run only the new/focused tests and confirm RED where implementation is incomplete.

Focused verification commands:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase7_privacy_redaction.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_pack.py tests/test_memory_provider.py`
- if touched: `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_replacement_readiness.py`

Expected evidence:
- at least one failing assertion caused by missing/privacy-drift behavior before implementation changes.

### Task 3: Implement the smallest additive code to satisfy the tests

Objective: tighten only the surfaces the tests prove are incomplete.

Files:
- Modify: `src/shyftr/privacy.py`
- Modify if needed: `src/shyftr/provider/memory.py`
- Modify if needed: `src/shyftr/federation.py`
- Modify only if tests require it: `src/shyftr/readiness.py` or `src/shyftr/mcp_server.py`

Implementation guidance:
1. Prefer extending the existing redaction helper rather than creating a second privacy pathway.
2. Reuse the same redaction logic across pack/export/projection surfaces.
3. If one surface currently bypasses the canonical redaction helper, route it through the shared helper instead of duplicating field lists.
4. Preserve additive behavior for non-sensitive rows.
5. Preserve safe-field visibility explicitly.

Verification after implementation:
- rerun each focused test command from Task 2 until green.

### Task 4: Run tranche-focused regressions

Objective: prove the tightened contract without jumping to full Phase 7 scope.

Run:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase6_resource_memory_privacy.py tests/test_phase7_privacy_redaction.py tests/test_pack.py tests/test_memory_provider.py`
- if touched: `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_replacement_readiness.py`

Expected result:
- all focused privacy/export/projection tests pass.

### Task 5: Run repo-wide gates after focused green

Objective: ensure the tranche remains compatibility-safe and release-clean.

Run:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`

Expected result:
- repo-wide green with no new public-vocabulary or readiness regressions.

### Task 6: Land canonical P7-2 closeoff

Objective: record exact landed scope and stop boundary.

Create:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-p7-2-closeoff.md`

The closeoff must state:
- what privacy/export surfaces were proven
- which field classes are now canonical
- whether any surfaces were intentionally left for P7-3/P7-4
- exact focused and repo-wide verification results
- the next tranche anchor

## Verification command matrix

Authoritative focused commands for this tranche:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase7_privacy_redaction.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase6_resource_memory_privacy.py tests/test_pack.py tests/test_memory_provider.py`
- if touched: `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_replacement_readiness.py`

Authoritative broader gates:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`

## Human input requirement

None for the repo-local tranche itself.

Human approval remains required only for any later action that would:
- publish packages
- mutate external services/accounts
- change public release claims beyond the tested repo truth

## Stop boundary for P7-2

P7-2 is complete when:
- nested privacy/export behavior is pinned across direct projection plus the real pack/export/projection surfaces touched by the tranche;
- safe-field visibility is explicitly preserved where intended;
- all focused tests are green;
- repo-wide gates are green;
- a canonical P7-2 closeoff artifact exists.

P7-2 does not include:
- contradiction challenge logic
- poisoning/prompt-injection defenses
- operator review-surface redesign
- broader Phase 7 final closeoff

## Exact next tranche after P7-2

### Tranche P7-3: contradiction and poisoning fixtures

Target:
- add synthetic contradiction, poisoning, and prompt-injection fixtures;
- define measurable suppression/challenge expectations;
- keep the tranche local, test-first, and fixture-safe.

## One-line summary

After P7-1 pinned direct-write authority defaults, P7-2 should now make nested privacy behavior explicit and consistent across pack/export/projection surfaces before any broader contradiction or poisoning machinery is introduced.
