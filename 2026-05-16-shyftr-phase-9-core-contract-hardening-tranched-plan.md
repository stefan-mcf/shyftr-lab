# ShyftR Phase 9: Core Contract Hardening Tranched Plan

Date: 2026-05-16
Repo: `/Users/stefan/ShyftR`
Recorded: 2026-05-16 08:02:46 AEST
Status: completed locally

> This is the canonical next-step plan after Phase 8 (Evaluation Track).
> It deliberately names the next repo phase as `Phase 9`, while preserving the broad-roadmap truth that the work itself corresponds to `Roadmap Phase 1: Core memory model stabilization`.

## Why this plan exists now

Phase 8 proved that ShyftR can generate a local-first evaluation bundle, ablation report, latency contract, and bounded frontier-readiness report without overclaiming. That work also sharpened the next bottleneck: the highest-leverage remaining risks are not new memory features, but core contract drift and append-only correctness.

Authoritative repo truth points to the same conclusion:
- `2026-05-15-shyftr-phase-9-ready-handoff-packet.md` says the next honest move is a canonical planning artifact, not implementation drift.
- `broad-roadmap-concept.md` marks `Core memory model stabilization` as the highest-priority implementation phase before more advanced memory layers.
- `deep-research-report.md` prioritizes the same sequence: stabilize the core, then typed working/episodic state, then retrieval upgrades, then offline consolidation, then resource memory.
- `docs/status/current-implementation-status.md` still shows several qualified or partial surfaces whose trustworthiness depends on contract alignment.

## Goal

Make the ShyftR core runtime contracts explicit, single-sourced, append-only-correct, and projection-faithful before any new capability expansion.

## End-state definition

This plan is complete when all of the following are true:
- there is one canonical internal implementation path for pack construction;
- loadout remains only as a documented compatibility surface where still needed;
- append-only readers consistently return latest logical state rather than stale rows;
- retrieval-log writer and SQLite rebuild/projection agree on required fields and timestamp semantics;
- provider memory search/filter semantics are self-consistent and test-pinned;
- public status docs describe the post-hardening truth accurately;
- full repo verification stays green.

## Scope

In scope:
- pack/loadout contract decisions and implementation convergence;
- append-only latest-row semantics in confidence/lifecycle-adjacent reads;
- retrieval-log schema and projection fidelity;
- provider facade contract hardening where current semantics are ambiguous or mismatched;
- contract tests for replay, projection, equivalence, and filtering behavior;
- public docs/status alignment for the hardened surfaces.

Out of scope:
- typed working-context schema expansion;
- carry-state/checkpoint object redesign;
- episodic/semantic/procedural/resource memory-class expansion;
- retrieval orchestration redesign beyond what is necessary for contract correctness;
- ANN/vector backend upgrades;
- offline consolidation/rehearsal pipelines;
- external benchmark adapters;
- hosted, production, or multi-tenant work.

## Canonical source artifacts to read first

1. `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-9-ready-handoff-packet.md`
2. `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-8-evaluation-track-closeout.md`
3. `/Users/stefan/ShyftR/broad-roadmap-concept.md`
4. `/Users/stefan/ShyftR/deep-research-report.md`
5. `/Users/stefan/ShyftR/docs/status/current-implementation-status.md`

## Current repo truth that shapes the plan

Grounded observations from current files:
- `src/shyftr/loadout.py` is already a compatibility shim that re-exports from `src/shyftr/pack.py`.
- `src/shyftr/pack.py` already describes pack as the canonical public memory-bundle surface and loadout as a compatibility alias during stabilization.
- `src/shyftr/confidence.py` already uses a latest-row helper in its memory-lookup path, so the broad concern is bigger than one stale helper: Phase 9 must verify append-only latest-row semantics across the contract, not just assume the current implementation is sufficient everywhere.
- retrieval-log projection logic lives in `src/shyftr/store/sqlite.py`, and compatibility handling between `logged_at` and `generated_at` is visible there and in `src/shyftr/mcp_server.py` plus `src/shyftr/integrations/retrieval_logs.py`.
- `docs/status/tranched-plan-status.md` is about the earlier implementation-tranches plan and should not be mistaken for post-Phase-8 roadmap truth.

## Plan design doctrine

- additive compatibility first;
- one canonical codepath per behavior where possible;
- keep legacy aliases as compatibility wrappers, not competing implementations;
- tests pin semantics before broad refactors;
- public docs/status updates are a required close condition, not optional cleanup;
- Phase 8 evaluation artifacts are not to be regenerated unless a later tranche explicitly needs a post-hardening comparison run.

## Tranche plan

### P9-0: contract inventory and decision lock

Objective:
Freeze the Phase 9 contract so later edits do not drift.

Expected outputs:
- this plan remains the canonical execution brief;
- one small decision note section added here or in the closeout documenting:
  - pack is canonical internally;
  - loadout is compatibility-only unless a surviving entrypoint explicitly requires it;
  - append-only reads must be latest-row-wins by logical identifier;
  - retrieval logs must preserve a stable timestamp and identifier contract across ledger, API, MCP, and SQLite projection.

Decision lock (P9-0): canonical contract choices

These choices are now locked for Phase 9 execution and should only change with an explicit, written superseding note in this same plan.

1) Pack is the canonical internal construction path
- All internal pack construction must route through the canonical `pack` implementation (currently `src/shyftr/pack.py`).
- Compatibility names/wrappers may exist, but must delegate to the canonical pack path rather than duplicating semantics.

2) Loadout is compatibility-only unless a surviving entrypoint requires it
- `loadout` remains as a compatibility surface only.
- If a public/historical entrypoint still requires a `loadout`-named surface, it must be a thin wrapper/alias over the canonical pack path.
- No new semantic forks are permitted under `loadout` naming.

3) Append-only reads are latest-row-wins by logical identifier
- Any effective-state read over an append-only ledger must resolve by logical identifier with latest-row-wins semantics.
- Duplicate historical rows are expected; reads must not return stale rows.

4) Retrieval logs preserve stable timestamp + identifier contracts across surfaces
- Retrieval-log records must preserve a stable timestamp contract and stable identifier contract end-to-end across:
  - ledger rows / writer;
  - API/public-safe projection;
  - MCP surface;
  - SQLite rebuild/projection.
- Compatibility fallbacks may exist only where necessary, but must be deliberate and test-pinned.

Files likely touched:
- this plan only, unless a separate Phase 9 closeout later records the locked choices.

Verification:
- readback of the canonical decision section from disk.

Stop boundary:
- no implementation changes yet.

### P9-1: pack/loadout canonical-path verification and cleanup

Objective:
Ensure the repo truly has one internal pack implementation path and that compatibility surfaces do not hide duplicate logic.

Likely files:
- `src/shyftr/pack.py`
- `src/shyftr/loadout.py`
- `src/shyftr/cli.py`
- `src/shyftr/integrations/pack_api.py`
- `src/shyftr/server.py`
- `src/shyftr/console_api.py`
- any additional loadout-facing surface discovered during grep/readback

Tasks:
1. inventory every internal import/callsite that still references loadout terminology or a loadout entrypoint;
2. verify whether each use is a compatibility name only or a real semantic fork;
3. remove or reroute any surviving duplicate implementation logic into the canonical pack path;
4. preserve compatibility wrappers where public or historical entrypoints still need them;
5. add focused equivalence tests for pack/loadout entrypoints where both must continue to exist.

Focused verification:
- targeted pytest commands for pack/loadout surfaces;
- direct CLI help or smoke for any public entrypoints kept alive.

P9-1 inventory note (initial pass):
- `src/shyftr/loadout.py` is a compatibility shim that re-exports the pack module surface.
- `src/shyftr/integrations/loadout_api.py` is a compatibility alias over `integrations/pack_api.py`.
- CLI `loadout` and `pack` subcommands share the same parser/handler path.
- The canonical construction implementation now lives behind `assemble_pack(...)`; legacy `assemble_loadout(...)` delegates to it.
- Initial scoped search found no separate duplicate pack-construction implementation in the loadout shim surfaces. Remaining loadout-named calls in MCP, continuity, frontier, provider, and outcome/history surfaces are compatibility naming/correlation surfaces and should be narrowed only when their tranche makes them stale or ambiguous.

Success criteria:
- no duplicate core pack construction logic survives without an explicit compatibility boundary;
- compatibility entrypoints produce equivalent outputs for the same fixture inputs.

### P9-2: append-only latest-row correctness hardening

Objective:
Pin and verify latest-row-wins behavior across logical memory reads that depend on append-only ledgers.

Likely files:
- `src/shyftr/confidence.py`
- `src/shyftr/ledger_state.py`
- `src/shyftr/mutations.py`
- `src/shyftr/provider/memory.py`
- any adjacent helper surfaced by focused search

Tasks:
1. identify every helper that reads effective state from append-only rows by logical identifier;
2. verify that each reader follows the same latest-row-wins rule;
3. centralize semantics through shared helpers where doing so reduces drift instead of spreading it;
4. add tests that append multiple rows with the same logical id and assert the latest row is the effective read result;
5. confirm replay/materialization behavior collapses duplicates consistently.

Focused verification:
- new/updated tests around latest-row reads and append-only replay;
- `git diff --check` and targeted compile/import sanity if helpers move.

Success criteria:
- no known stale-read behavior in the targeted append-only read surfaces;
- tests explicitly prove latest-row behavior.

P9-2 completion note:
- Confidence adjustment now requires the latest append-only row for a logical memory identifier to remain approved before adjusting confidence.
- SQLite lifecycle projection now treats restore/challenge/isolation-candidate lifecycle rows deliberately instead of ignoring them as unknown historical rows.
- `tests/test_phase9_append_only_latest_row.py` pins latest-row effective-state behavior and latest restore projection.

### P9-3: retrieval-log schema and projection fidelity

Objective:
Make retrieval-log data trustworthy across ledger rows, public-safe projections, and SQLite rebuilds.

Likely files:
- `src/shyftr/pack.py`
- `src/shyftr/store/sqlite.py`
- `src/shyftr/integrations/retrieval_logs.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/readiness.py`
- any test fixtures or schema helpers discovered during implementation

Tasks:
1. inventory actual retrieval-log fields produced by the writer;
2. compare them against SQLite rebuild expectations and public-safe retrieval-log contract surfaces;
3. pick the minimal compatibility-safe contract for timestamp and identifier fields;
4. patch writer or projection surfaces so they agree deliberately rather than loosely falling back;
5. add projection-fidelity tests: ledger rows -> rebuild/projection -> expected fields and values.

Focused verification:
- retrieval-log-specific tests;
- targeted rebuild/projection smoke using a fixture cell.

Success criteria:
- retrieval-log writer/projection contract is deliberate and test-covered;
- no field/timestamp ambiguity remains untested.

P9-3 completion note:
- Retrieval-log public projection includes both canonical pack identifiers and legacy loadout identifiers, plus logged/generated timestamp fields.
- SQLite rebuild preserves pack/loadout identifiers and logged/generated timestamps from ledger rows with compatibility fallback for older rows.
- `tests/test_phase9_retrieval_log_projection.py` pins ledger -> public projection -> SQLite fidelity.

### P9-4: provider facade contract hardening

Objective:
Make provider-memory filtering and returned labeling semantics self-consistent.

Likely files:
- `src/shyftr/provider/memory.py`
- `src/shyftr/provider/trusted.py`
- potentially `src/shyftr/models.py` if contract naming needs a shared type or helper

Tasks:
1. inspect current defaults and filtering semantics for requested tiers/classes;
2. verify returned objects self-label consistently with how filters are applied;
3. patch only the narrow mismatches required for contract consistency;
4. add focused regression tests for representative filter combinations.

Focused verification:
- provider-memory focused pytest targets;
- no behavior change without tests that pin the intended semantics.

Success criteria:
- provider search/filter behavior is explicit, self-consistent, and test-covered.

P9-4 completion note:
- Provider search accepts `memory` as a compatibility alias for trace-backed reviewed durable memory filters.
- Returned search results keep the public `memory` trust label while internal filtering continues to use the reviewed durable-memory implementation path.
- `tests/test_phase9_provider_contract.py` pins tier aliasing, kind filtering, and memory-type filtering combinations.

### P9-5: public status and terminology truth alignment

Objective:
Ensure public truth surfaces describe the hardened implementation accurately.

Likely files:
- `docs/status/current-implementation-status.md`
- any directly adjacent public status or concept doc made stale by the hardening changes
- possibly minimal terminology-guard-facing docs if required by the changed truth

Tasks:
1. update the capability matrix rows affected by the hardening work;
2. call out canonical-vs-compatibility boundaries clearly;
3. ensure wording remains local-first and does not overclaim;
4. run terminology and public-readiness gates.

Focused verification:
- `python scripts/terminology_inventory.py --fail-on-public-stale`
- `python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `python scripts/public_readiness_check.py`

Success criteria:
- public truth and implementation agree;
- terminology/readiness gates remain green.

### P9-6: post-hardening verification and closeout

Objective:
Close the tranche with full repo-backed proof.

Required verification bundle:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`

Conditional comparison run:
- only if P9-1 through P9-4 materially change the evaluated runtime contracts, consider regenerating the Phase 8 evaluation bundle and related artifacts for a before/after comparison. This is optional and must be justified explicitly in the closeout.

Required close artifacts:
- `2026-05-16-shyftr-phase-9-core-contract-hardening-closeout.md`
- next-phase handoff packet, but only after the Phase 9 scope is honestly complete.

## Minimum RED tests to write first

At least one focused failing test per risky contract before major edits:
- pack/loadout equivalence for the same fixture input;
- latest-row-wins read for append-only updates by logical id;
- retrieval-log projection fidelity against SQLite rebuild expectations;
- provider filter semantics and returned labeling consistency.

Suggested test file pattern:
- `tests/test_phase9_pack_loadout_equivalence.py`
- `tests/test_phase9_append_only_latest_row.py`
- `tests/test_phase9_retrieval_log_projection.py`
- `tests/test_phase9_provider_contract.py`

Exact filenames may be adjusted to fit current repo conventions, but they must remain Phase-9-scoped and narrowly targeted.

## Risks and mitigations

1. Compatibility breakage during unification
- Mitigation: preserve wrapper entrypoints; prove equivalence before removing anything.

2. Hidden stale-read behavior in more than one reader
- Mitigation: search broadly, centralize semantics where appropriate, and pin with tests before refactors.

3. Retrieval-log fixes expand into wider projection drift
- Mitigation: keep Phase 9 limited to retrieval-log projection fidelity unless adjacent drift is required to pass the same contract tests.

4. Provider semantics change unintentionally alters downstream behavior
- Mitigation: write focused regression tests first and keep fixes minimal.

5. Documentation truth drifts while code hardens
- Mitigation: treat docs/status alignment as a required tranche, not end-of-session cleanup.

6. Phase numbering confusion
- Mitigation: every related artifact should state clearly that repo `Phase 9` corresponds to broad-roadmap `Core memory model stabilization` work.

## Explicit non-goals / do-not-open-yet list

Do not open during this plan unless a proven blocker forces reprioritization:
- typed live-context schema MVP;
- carry-state/checkpoint redesign beyond contract inspection;
- typed context versus heuristic benchmark work;
- episodic memory object model;
- semantic/procedural/resource memory-class expansion;
- retrieval orchestration policy redesign;
- temporal/utility/contradiction reranking;
- offline consolidation proposal pipeline;
- rehearsal framework expansion;
- multimodal/resource grounding implementation.

Those belong after this hardening plan or in later explicitly approved plans.

## One-line plan summary

Phase 9 should harden the core contracts ShyftR already depends on: make pack canonical, keep loadout compatibility-only, prove latest-row append-only correctness, align retrieval-log projections, tighten provider semantics, and update public truth surfaces before any new memory-layer expansion.
