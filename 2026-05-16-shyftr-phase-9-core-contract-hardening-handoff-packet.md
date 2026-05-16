# ShyftR Phase 9 Core Contract Hardening Handoff Packet

Date: 2026-05-16
Repo: `/Users/stefan/ShyftR`
Recorded: 2026-05-16 08:02:46 AEST
Status: superseded by completed Phase 9 closeout
Resume from the post-Phase-9 handoff unless intentionally auditing this historical packet.

Superseding artifacts:
- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-9-core-contract-hardening-closeout.md`
- `/Users/stefan/ShyftR/2026-05-16-shyftr-post-phase-9-handoff-packet.md`

Canonical plan to execute:
- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-9-core-contract-hardening-tranched-plan.md`

Canonical predecessor artifacts:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-9-ready-handoff-packet.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-8-evaluation-track-closeout.md`
- `/Users/stefan/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/ShyftR/deep-research-report.md`
- `/Users/stefan/ShyftR/docs/status/current-implementation-status.md`

## What is already true before execution starts

1. Phase 8 (Evaluation Track) is complete locally and fully verified.
2. The repo already has Phase 8 evaluation surfaces and generated status artifacts on disk.
3. There is still no canonical post-Phase-8 implementation boundary on disk beyond planning until this packet and its paired plan.
4. Current file-backed evidence strongly supports making core contract hardening the next move instead of opening new feature work.

## Why this plan is next

The best next work is not a fresh memory feature. It is contract hardening.

The strongest reasons are already visible from repo truth:
- the broad roadmap calls core stabilization the highest-priority implementation phase before typed context, retrieval upgrades, consolidation, or resource memory;
- the deep research recommends the same dependency order;
- the current repo still carries meaningful compatibility boundaries across pack/loadout, append-only effective-state reads, retrieval-log field handling, and provider semantics;
- Phase 8 evaluation is only as trustworthy as those contracts.

## Current truth boundary

This plan must begin from the following disciplined assumptions:
- pack is already the canonical public memory-bundle surface in `src/shyftr/pack.py`;
- `src/shyftr/loadout.py` is already a compatibility shim and should be treated as such unless a surviving public surface requires it;
- append-only latest-row semantics must be verified broadly, not assumed from one helper alone;
- retrieval-log timestamp and identifier compatibility currently exists across more than one surface and needs a deliberate contract, not ad hoc fallbacks;
- public docs/status must stay aligned with the hardened runtime truth.

## Exact first tranche to resume from

Resume at `P9-0` then go directly into `P9-1` from the canonical plan.

Ordered start sequence:
1. Re-read the canonical Phase 9 plan.
2. Snapshot live repo status before edits.
3. Inventory current pack/loadout callsites and compatibility boundaries.
4. Write the first failing equivalence and contract tests before any major refactor.
5. Only then begin the narrow code changes required by `P9-1`.

## Minimum read-first source files for execution

Start with these concrete files:
- `/Users/stefan/ShyftR/src/shyftr/pack.py`
- `/Users/stefan/ShyftR/src/shyftr/loadout.py`
- `/Users/stefan/ShyftR/src/shyftr/confidence.py`
- `/Users/stefan/ShyftR/src/shyftr/ledger_state.py`
- `/Users/stefan/ShyftR/src/shyftr/mutations.py`
- `/Users/stefan/ShyftR/src/shyftr/store/sqlite.py`
- `/Users/stefan/ShyftR/src/shyftr/integrations/retrieval_logs.py`
- `/Users/stefan/ShyftR/src/shyftr/provider/memory.py`
- `/Users/stefan/ShyftR/docs/status/current-implementation-status.md`

## First tests to add or update

Write these focused tests first, or repo-equivalent filenames that preserve the same scope:
- `tests/test_phase9_pack_loadout_equivalence.py`
- `tests/test_phase9_append_only_latest_row.py`
- `tests/test_phase9_retrieval_log_projection.py`
- `tests/test_phase9_provider_contract.py`

## Verification contract to preserve throughout execution

Focused-first, full-suite-last:
- run focused Phase 9 tests after each tranche;
- only run the full verification bundle after the tranche set is complete enough to justify it.

Full verification bundle:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`

## Non-goals / do-not-redo

Do not redo:
- Phase 8 implementation or regeneration work by default;
- prior phase closeout writing unless Phase 9 changes require cross-reference fixes;
- broad roadmap refresh;
- new typed-context or memory-class implementation work.

Do not open:
- typed live-context schema MVP;
- carry-state/checkpoint redesign;
- retrieval orchestration redesign;
- offline consolidation pipeline;
- multimodal/resource memory implementation;
- external benchmark adapters.

## Biggest execution risks

1. Accidentally breaking compatibility while unifying internal pack behavior.
2. Fixing one append-only stale-read surface while leaving another unpinned.
3. Expanding retrieval-log work into an unbounded projection rewrite.
4. Changing provider semantics without enough regression coverage.
5. Letting public docs/status drift behind the hardened runtime.

## What good completion looks like

A good Phase 9 completion produces:
- one canonical internal pack implementation path;
- explicit compatibility boundaries for legacy loadout naming;
- append-only latest-row semantics proven by tests;
- retrieval-log writer/projection fidelity proven by tests;
- provider-memory filter semantics pinned and consistent;
- updated `current-implementation-status.md` that tells the same story as the code;
- a full green verification bundle;
- a closeout artifact and next-phase handoff that do not overclaim.

## One-line resume summary

Start Phase 9 by hardening ShyftR’s core contracts before building anything new: verify pack/loadout unification, append-only latest-row correctness, retrieval-log projection fidelity, provider semantics, and public truth alignment in that order.
