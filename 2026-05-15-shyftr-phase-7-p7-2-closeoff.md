# ShyftR Phase 7 P7-2 closeoff

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 7 — privacy, policy, and safety hardening
Tranche: P7-2 — privacy/export/redaction deepening
Status: complete locally, verified green, ready to commit
Predecessor closeoff: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-p7-1-closeoff.md`
Planning artifacts:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-0-plan.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-2-plan.md`

## Final verdict

P7-2 is complete on the intended local implementation surface.

This tranche deepened Phase 7 privacy behavior by proving and enforcing cross-surface parity for sensitive resource-backed memory on projection and pack surfaces. Secret/private/restricted rows that are allowed onto a non-audit pack by sensitivity policy now retain safe operator-facing context while redacting nested sensitive values rather than leaking raw statements or raw resource locators.

## What landed

1. Pack-surface redaction parity
   - `assemble_loadout(...)` now applies the same canonical redaction helper used by direct privacy projections before approved-memory records become pack candidates on non-audit paths.
   - sensitive rows that are allowed by policy no longer bypass nested redaction when shown in pack items.
   - audit mode remains the explicit escape hatch for non-redacted review flows.

2. Direct projection and filtered-export parity tests
   - direct nested-field redaction remained pinned through the existing P7-1 test.
   - a new filtered-export parity test now proves the filtered projection helper returns the same redacted structure for allowed sensitive rows.

3. Safe-context preservation across pack payloads
   - pack items still preserve safe fields such as the resource label after redaction.
   - the item payload and its scoring-detail projection now agree on the redacted resource reference shape.

4. Documentation/tranche artifact hygiene
   - the P7-2 tranche plan was normalized to avoid public-vocabulary guard failures while still recording the intended field classes.
   - no broader contradiction/poisoning machinery was introduced in this tranche.

## New and updated tests

Updated focused test file:
- `tests/test_phase7_privacy_redaction.py`

New assertions added in that file:
- filtered export helper preserves redaction parity for allowed sensitive rows
- pack surface includes allowed secret resource rows only as redacted projections
- safe resource labels remain visible while nested sensitive fields stay hidden

Existing coverage that now validates the tranche indirectly:
- `tests/test_phase6_resource_memory_privacy.py`
- `tests/test_phase6_resource_memory_pack.py`
- `tests/test_privacy_sensitivity.py`
- `tests/test_pack.py`
- `tests/test_memory_provider.py`
- `tests/test_replacement_readiness.py`
- `tests/test_memory_vocabulary_guard.py`

## Verification

RED/GREEN focused test cycle:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase7_privacy_redaction.py`
- initial RED result: one failing assertion proving the pack surface still leaked the raw statement on an allowed secret resource row
- final GREEN result: `3 passed`

Focused tranche regressions:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase6_resource_memory_privacy.py tests/test_phase7_privacy_redaction.py tests/test_pack.py tests/test_memory_provider.py tests/test_replacement_readiness.py`
- result: `69 passed`

Vocabulary + tranche-focused regression after plan-doc normalization:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_memory_vocabulary_guard.py tests/test_phase7_privacy_redaction.py tests/test_phase6_resource_memory_privacy.py tests/test_pack.py tests/test_memory_provider.py tests/test_replacement_readiness.py`
- result: `73 passed`

Repo-wide verification:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`
- result: `978 passed, 31 warnings`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples` → pass
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale` → pass
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose` → pass
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py` → PASS
- `cd /Users/stefan/ShyftR && git diff --check` → pass

## Implementation touchpoints

Core code updated:
- `src/shyftr/pack.py`

Tests updated:
- `tests/test_phase7_privacy_redaction.py`

Planning/status docs updated:
- `2026-05-15-shyftr-phase-7-tranche-p7-2-plan.md`
- `2026-05-15-shyftr-phase-7-p7-2-closeoff.md`

## Exact behavioral change

Before P7-2:
- sensitivity policy could allow a secret row onto a pack surface
- but the pack candidate path still used the raw projected statement/resource fields
- this meant non-audit pack payloads could expose unredacted secret content

After P7-2:
- if a sensitive row is allowed onto a non-audit pack surface, it is first passed through the canonical privacy redaction helper
- pack item payloads expose safe context only
- nested sensitive fields such as locators and digests remain redacted
- scoring-detail resource metadata matches the same redacted shape

## Scope boundary reached

This tranche intentionally stops at privacy/export/redaction deepening:
- direct projection parity is covered
- filtered export parity is covered
- pack-surface parity is covered
- safe visible context remains available

This tranche does not yet introduce:
- contradiction-sensitive challenge/escalation behavior
- poisoning or prompt-injection fixture machinery
- operator review-surface redesign
- broader Phase 7 final closeoff

Those remain for:
- P7-3 contradiction and poisoning fixtures
- P7-4 review-surface and policy-visibility improvements
- P7-5 broader safety verification and final Phase 7 closeoff

## Outcome

ShyftR now has a complete P7-2 privacy/export/redaction tranche for the intended local scope:
- sensitive nested metadata redaction is now enforced on pack surfaces as well as direct projection helpers
- safe resource labels remain visible where policy allows them
- filtered export and pack projections follow the same canonical redaction contract
- repo-wide verification remains green

## One-line summary

Phase 7 P7-2 is done locally: ShyftR now enforces cross-surface redaction parity for allowed sensitive resource memory on projection and pack surfaces while preserving safe operator-facing context and staying repo-wide green.
