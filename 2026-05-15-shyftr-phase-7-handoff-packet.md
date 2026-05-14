# ShyftR Phase 7 handoff packet

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 7 — privacy, policy, and safety hardening
Status: ready to start from Phase 6 completion truth
Resume from this exact truth.

Canonical predecessor:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-closeoff.md`

Canonical Phase 7 planning artifact:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-0-plan.md`

## What is already complete and proven

1. Phase 6 is complete.
   - Resource-memory schema/provider/storage/retrieval/pack/privacy baseline landed.
   - Repo-wide verification returned green.
   - Phase 6 was committed and pushed.

2. The current implementation truth is on `main`.
   - Canonical pushed Phase 6 completion commit: `d09a426523c4d56b5df7b4a61f0242519384d963`

3. The next frontier is already identified in repo planning truth.
   - `broad-roadmap-concept.md` names Phase 7 as privacy, policy, and safety hardening.
   - Phase 6 closeoff implies the next correct move is not more multimodal breadth, but stronger policy/authority and privacy hardening.

## Current truth boundary

This handoff is for execution resume after Phase 6 completion and push.
No Phase 7 implementation has been started in this tranche.

Current repo-state facts at handoff time:
- branch: `main`
- local HEAD should match `origin/main` after the Phase 6 push
- canonical new planning artifacts for this phase:
  - `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-0-plan.md`
  - `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-handoff-packet.md`

Authoritative planning truth:
- Phase 7 is ready to start.
- The exact next tranche is P7-1.
- P7-1 must be policy/authority-first.
- Broader contradiction/poisoning work comes only after write/default/privacy behavior is pinned.

## Key design decisions already made

1. Phase 7 should remain additive and review-gated.
   - No default auto-apply path for durable writes.
   - Compatibility with older rows remains mandatory.

2. The first implementation slice is not a giant policy engine.
   - Start with explicit write/default authority behavior and focused nested-redaction rules.

3. Safety must be test-first.
   - Synthetic contradiction, poisoning, and prompt-injection fixtures should come only after the policy baseline is pinned.

4. Privacy must extend beyond statement-only thinking.
   - Phase 6 already redacts sensitive resource locators.
   - Phase 7 should define what additional nested metadata is filtered or redacted, and where.

## Exact ordered continuation sequence

1. Preflight the repo again.
   - Confirm repo path is `/Users/stefan/ShyftR`.
   - Confirm branch/worktree state with live `git status --short --branch`.
   - Read the Phase 6 closeoff, Phase 7 P7-0 plan, and this handoff packet first.

2. Start Phase 7 P7-1 only.
   - Do not jump straight to broad contradiction/poisoning machinery.
   - Keep scope strictly to policy/authority baseline and privacy/redaction defaults.

3. Write focused failing tests first for P7-1.
   Minimum first wave:
   - default direct-write policy remains safely gated unless explicitly allowed;
   - safe reviewed writes still succeed;
   - sensitive nested resource metadata redaction/filtering is pinned;
   - older approved memory rows still round-trip unchanged;
   - contradiction-capable rows do not break existing provider/pack behavior.

4. Implement the smallest additive code to make P7-1 green.
   Likely file touchpoints:
   - `src/shyftr/privacy.py`
   - `src/shyftr/provider/memory.py`
   - `src/shyftr/models.py`
   - `src/shyftr/memory_classes.py`
   - maybe `src/shyftr/promote.py`

5. Verify P7-1 before any broader safety work.
   Focused gates:
   - `tests/test_phase7_policy_authority.py`
   - `tests/test_phase7_privacy_redaction.py`
   - `tests/test_privacy_sensitivity.py tests/test_memory_provider.py tests/test_pack.py`

6. Only after P7-1 is green, open deeper Phase 7 work.
   - contradiction handling
   - poisoning/prompt-injection fixtures
   - review-surface visibility improvements

7. After focused green, run broader repo verification.
   - full pytest
   - compileall
   - terminology inventory checks
   - public readiness
   - `git diff --check`

8. Land a canonical Phase 7 closeoff artifact at the right stop point.

## Do-not-redo / non-goals

Do not redo:
- Phase 6 implementation work
- broad “what should Phase 7 be?” analysis already grounded in roadmap truth
- broad multimodal expansion under the Phase 7 label

Do not do in P7-1:
- a large new hosted/auth platform layer
- automatic durable-memory authority escalation
- heavyweight benchmark claims
- broad runtime integration rewrites

## Known risks to watch during implementation

1. Authority drift
- avoid silently widening direct durable-write power
- keep review-gated defaults explicit

2. Privacy leakage
- nested metadata can leak even when statement redaction exists
- tests must pin the intended visible vs redacted fields

3. Compatibility breakage
- old rows and older ledgers must remain loadable
- additive changes only in the first slice

4. Safety overreach
- do not pretend contradiction/poisoning policy is solved before focused fixtures and measurable tests exist

## Read-first file set for the next operator

Planning / truth artifacts:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-closeoff.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-0-plan.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-handoff-packet.md`

Core code:
- `/Users/stefan/ShyftR/src/shyftr/privacy.py`
- `/Users/stefan/ShyftR/src/shyftr/provider/memory.py`
- `/Users/stefan/ShyftR/src/shyftr/models.py`
- `/Users/stefan/ShyftR/src/shyftr/memory_classes.py`
- `/Users/stefan/ShyftR/src/shyftr/pack.py`
- `/Users/stefan/ShyftR/src/shyftr/promote.py`

Existing tests to extend first:
- `/Users/stefan/ShyftR/tests/test_privacy_sensitivity.py`
- `/Users/stefan/ShyftR/tests/test_memory_provider.py`
- `/Users/stefan/ShyftR/tests/test_pack.py`

## Recommended next user-facing command of work

Proceed optimally into Phase 7 P7-1:
- write the focused failing policy/privacy tests first
- implement the smallest additive policy/authority baseline
- verify before opening contradiction/poisoning work

## One-line summary

Phase 7 should resume from Phase 6 completion by executing a narrow P7-1 policy/authority tranche first, not by jumping directly into broad safety machinery.