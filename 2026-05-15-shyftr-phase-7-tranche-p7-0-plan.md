# ShyftR Phase 7 — Tranche P7-0 plan (privacy/policy kickoff)

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 7 — privacy, policy, and safety hardening
Tranche: P7-0 (planning + contract definition only)
Status: ready to start after Phase 6 completion
Predecessor closeoff: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-closeoff.md`
Roadmap source: `/Users/stefan/ShyftR/broad-roadmap-concept.md`
Supporting public note: `/Users/stefan/ShyftR/docs/future-work.md`

## Objective

Start Phase 7 with a narrow, contract-first tranche that defines the smallest additive safety and policy hardening surface needed after Phase 6.

This tranche does not implement the full safety system.
It defines scope, stop boundary, schema direction, tranche split, minimum RED tests, and verification gates so implementation can proceed without blurring policy, privacy, and authority boundaries.

## Why Phase 7 is next

Phase 6 completed the reference-first resource-memory baseline.
The next highest-value gap is not broader multimodal capability; it is stronger control over:
- what may be written durably,
- what may be exported or packed,
- how sensitivity and contradictions are handled,
- and how unsafe/poisoned memory is prevented from gaining authority.

The roadmap already names Phase 7 as:
- privacy, policy, and safety hardening;
- stronger write policy and authority boundaries;
- contradiction/poisoning/prompt-injection defense;
- redactable projections and export filters.

## Non-negotiable constraints

- Keep work local to `/Users/stefan/ShyftR`.
- Preserve local-first and ledger-first design.
- Preserve the public-safe rule: ShyftR proposes; runtime/operator applies.
- Keep durable mutation review-gated unless an explicit local policy says otherwise.
- Preserve Phase 6 behavior unless a test-driven safety rule intentionally tightens it.
- Additive compatibility only: older rows and ledgers must continue to load.
- No hosted/platform claims.
- No private-core heuristics or real-user data in fixtures.

## Phase 7 baseline, tightened

The first implementation slice should stay narrow and measurable:
1. define the first explicit policy/authority contract for durable writes and promotions;
2. extend privacy/sensitivity handling beyond statement-only redaction where needed;
3. add contradiction and poisoning test fixtures before deeper policy machinery;
4. keep the first tranche additive and review-gated;
5. avoid broad runtime integration changes until policy semantics are pinned in tests.

Not yet in the first implementation slice unless separately chosen later:
- a large new policy DSL;
- fully automated durable writes without review;
- hosted access-control surfaces;
- heavyweight runtime identity systems;
- broad benchmark claims beyond focused safety fixtures.

## Contract decisions before implementation

### 1) Authority boundary remains explicit

Phase 7 should preserve and strengthen the boundary:
- ShyftR may classify, propose, and redact;
- runtime/operator remains the authority that applies durable changes;
- direct durable-memory writes remain disabled by default outside explicit local policy.

### 2) Safety should be test-first and fixture-safe

The first tranche should begin from synthetic fixtures for:
- contradictory memory rows;
- poisoned or prompt-injected source text;
- sensitive resource-backed rows with nested metadata;
- unsafe write requests through provider/CLI/MCP-like paths where applicable.

### 3) Sensitivity should be field-aware, not statement-only

Phase 6 already redacts resource locators for sensitive rows.
Phase 7 should define the next additive step:
- which nested fields participate in redaction/export filtering;
- which safe display fields remain visible;
- and how the rules are surfaced in pack/export/search projections.

### 4) Contradiction handling must be explicit, not incidental

The current repo has suppression/challenge/deprecation concepts, but Phase 7 should pin an operator-visible contract for contradiction-sensitive memory handling, at least for the first durable-memory surfaces.

### 5) Write-path defaults must be safe by construction

CLI/MCP/provider write paths should remain conservative unless explicit reviewed policy enables stronger behavior.
The tranche should verify the default-safe behavior before implementing any optional expanded policy surface.

## Proposed tranche split after P7-0

### Tranche P7-1: policy/authority baseline

Target:
- define minimal additive policy schema/helpers;
- pin direct-write guardrails and review-gated defaults in tests;
- ensure older rows still load;
- harden provider-facing write decisions first.

### Tranche P7-2: privacy/export/redaction deepening

Target:
- extend nested-field redaction/export filtering;
- add focused tests for resource metadata, grounded rows, and pack/export surfaces;
- ensure safe labels remain available where allowed.

### Tranche P7-3: contradiction and poisoning fixtures

Target:
- add synthetic contradiction/poisoning/prompt-injection fixtures;
- define first measurable suppression/challenge expectations;
- keep the evaluation fixture-safe and local.

### Tranche P7-4: review surfaces and policy visibility

Target:
- improve operator visibility for blocked/challenged/proposed durable changes;
- make policy outcomes legible in ledgers/reports without over-expanding runtime scope.

### Tranche P7-5: broader safety verification pass

Target:
- full focused regression across provider/privacy/pack/runtime surfaces;
- updated public/private readiness and safety fixtures;
- canonical Phase 7 closeoff artifact.

## File/code matrix for the next execution tranche

Read first:
- `src/shyftr/privacy.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/models.py`
- `src/shyftr/memory_classes.py`
- `src/shyftr/pack.py`
- `src/shyftr/promote.py`
- `src/shyftr/continuity.py`
- `tests/test_privacy_sensitivity.py`
- `tests/test_memory_provider.py`
- `tests/test_pack.py`
- `docs/concepts/implementation-guardrails.md`
- `broad-roadmap-concept.md` (Phase 7 section)

Likely implementation touchpoints for P7-1:
- `src/shyftr/privacy.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/models.py`
- `src/shyftr/memory_classes.py`
- maybe `src/shyftr/promote.py`

Likely new/expanded tests:
- `tests/test_phase7_policy_authority.py`
- `tests/test_phase7_privacy_redaction.py`
- `tests/test_phase7_contradiction_safety.py`

## Minimum RED tests for the next tranche

P7-1 should begin by writing failing tests for at least:
1. default durable write policy rejects or gates unsafe direct-write paths unless explicitly allowed;
2. reviewed durable writes still succeed for safe rows;
3. sensitive nested resource metadata is redacted in projections where policy requires it;
4. older approved memory rows still round-trip unchanged;
5. contradiction-sensitive rows can be represented without breaking existing pack/provider behavior.

P7-2 and later should then add failing tests for at least:
1. pack/export surfaces do not leak disallowed nested sensitive fields;
2. contradictory memory can be surfaced as reviewable/challenged rather than silently authoritative;
3. prompt-injection-like source text does not automatically gain durable authority;
4. safe defaults remain intact across CLI/MCP/provider-facing write paths.

## Verification commands for the next tranche

Focused P7-1 commands once implementation begins:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase7_policy_authority.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase7_privacy_redaction.py`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_privacy_sensitivity.py tests/test_memory_provider.py tests/test_pack.py`

Broader gates after focused green:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`

## Stop boundary for P7-0

P7-0 is complete when:
- Phase 6 closeoff exists and is the new predecessor truth;
- this Phase 7 kickoff plan exists;
- tranche ordering, minimum RED tests, and verification commands are explicit;
- no Phase 7 implementation changes have been made yet in this planning tranche.

## Exact next tranche after this one

### Tranche P7-1: policy/authority baseline

Target:
- land the smallest additive safety/policy baseline that pins review-gated durable-write defaults, nested redaction expectations, and compatibility-safe authority handling before deeper contradiction/poisoning work.

## One-line summary

Phase 7 should begin with a narrow P7-1 policy/authority tranche that hardens durable-write defaults and privacy behavior in tests before broader contradiction or poisoning work.