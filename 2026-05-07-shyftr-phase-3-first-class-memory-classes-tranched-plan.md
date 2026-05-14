# ShyftR Phase 3 First-Class Memory Classes Tranched Plan

> **For Hermes:** Use `subagent-driven-development` or named persistent worker lanes only after reading this entire plan. Execute tranches in order. Do not cross the final human-review tranche unless the operator explicitly approves.

**Goal:** Formalize first-class memory classes in ShyftR without breaking its local-first, append-only, review-gated substrate. Introduce a canonical class model, typed `memory_type` behavior, class-aware write/retrieval/retention rules, and file-backed verification so later retrieval, consolidation, and resource-memory upgrades have a stable base.

**Architecture:** Phase 3 is a schema-and-behavior expansion phase built on top of the stabilized Phase 1 core. It must preserve canonical ledgers as truth, additive compatibility for existing cells, and ShyftR’s separation between working context, carry/continuity, durable memory, and regulator-reviewed promotion. The implementation should add one canonical class layer and gradually route existing surfaces through it, rather than splitting storage prematurely or introducing a new opaque backend.

**Tech Stack:** Python 3.11/3.12, JSONL append-only ledgers, SQLite projections/indexes, ShyftR CLI/MCP/HTTP/provider surfaces, deterministic synthetic fixtures, baseline comparison scripts, public-readiness and terminology gates.

**Primary repo:** `/Users/stefan/ShyftR`

**Planning/reference artifacts:**
- `/Users/stefan/Desktop/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/Desktop/ShyftR/deep-research-report.md`
- `/Users/stefan/Desktop/ShyftR/2026-05-07-shyftr-phase-1-pass-off-report.md`
- `/Users/stefan/Desktop/ShyftR/2026-05-07-shyftr-phase-1-core-memory-model-stabilization-tranched-plan.md`

---

## 0. Executive summary

Phase 0 baseline/evidence harness work is complete.

Phase 1 core memory model stabilization is complete and landed on `main` with:
- canonical public `pack` surface;
- `loadout` retained as compatibility shim;
- latest-row-wins append-only semantics through shared helpers;
- retrieval-log/runtime compatibility hardening;
- tracked baseline harness scripts and fixtures;
- passing terminology, readiness, baseline, and pytest gates.

Phase 3 should not assume a fully completed typed live-context redesign first. Instead, it should:
1. preserve the current live-context/carry architecture as the working boundary;
2. add a canonical memory-class layer that is compatible with current cells and APIs;
3. land class-aware behavior incrementally, with heavy regression gating against the current-state baseline;
4. stage the hardest carry/live-context bridging work after the canonical class contract is already stable.

The deep research and repo audit both point to the same hardening rule:
- do not try to ship all frontier-memory features at once;
- do not split storage by class in the first implementation;
- do not remove legacy fields/readers early;
- do not rely on implicit heuristics as the only class assignment path.

This plan therefore uses a phased-assembly shape with additive compatibility, explicit stop boundaries, and a final human-review tranche.

---

## 1. Non-negotiable scope boundary

### In scope for Phase 3

- Define a canonical first-class memory-class contract for ShyftR.
- Introduce a typed `memory_type` concept and class metadata while keeping existing cells readable.
- Formalize class responsibilities for:
  - working/context memory;
  - carry/continuity memory;
  - episodic memory;
  - semantic memory;
  - procedural memory;
  - resource memory;
  - rule memory.
- Add class-aware validation, retention, write-authority, and retrieval-filter behavior.
- Preserve current public/local-first safety posture.
- Add migration/backfill strategy for existing memories and compatibility aliases.
- Add deterministic regression coverage for class-aware behavior.
- Update docs so current public claims match implementation.
- Save review-ready repo-local artifacts and a final human-review packet.

### Explicitly out of scope for Phase 3

- Replacing JSONL ledgers as canonical truth.
- Cloud/service-dependent retrieval or storage.
- Full retrieval-orchestration overhaul beyond class filters/weights required by class separation.
- Advanced learned rerankers.
- Offline consolidation/sleep-time rehearsal pipeline implementation.
- Full multimodal retrieval stack or hosted artifact service.
- Hosted/multi-tenant deployment.
- Package publication or public release-tag decisions.
- Destructive migration of old ledgers.
- Removing legacy compatibility readers/aliases without explicit later approval.
- Broad policy/privacy-engine redesign beyond what Phase 3 directly needs.

### Phase boundary discipline

Phase 3 should establish memory classes as a stable substrate layer so later phases can safely build:
- deeper typed working-state/carry evolution;
- stronger retrieval orchestration;
- sleep-time consolidation;
- richer resource memory;
- evaluation claims beyond the current local proof posture.

### Collision boundary

Work is expected in `/Users/stefan/ShyftR` on `main` or a fresh branch/worktree derived from current `main`.

Do not:
- overwrite or rewrite canonical historical ledgers;
- mutate unrelated roadmap/release surfaces outside files listed in this plan;
- silently expand into hosted/platform/productization work;
- assume ignored `docs/status/` paths are canonical public truth.

---

## 2. Human input requirement

Autonomous tranches 0-11 require no human input by design.

All human-gated review items are pooled into the final tranches:
- Tranche 12: final review packet and decision matrix.
- Tranche 13: optional post-approval landing actions.

Before Tranche 12, the executor should not ask the operator to choose memory-class names, field names, or migration policy unless a true blocker is discovered. Use the safe defaults below.

### Safe defaults for autonomous execution

1. The canonical new field is `memory_type`.
2. Existing `kind` remains readable and may continue to carry finer-grained subtype semantics.
3. Existing cells without `memory_type` stay valid; `memory_type` may be absent during compatibility/backfill.
4. No table-per-class or ledger-per-class split in the first implementation wave.
5. Working/context and carry/continuity remain non-authoritative by default.
6. Semantic, procedural, resource, and rule memory stay review-gated or explicit-authority-gated.
7. Rule memory has the highest retrieval/behavioral authority, but no unreviewed rule promotion is introduced.
8. Resource memory stores references/handles, not arbitrary blob dumps.
9. Procedural memory should route toward skills/workflows/recovery recipes rather than generic factual notes.
10. Every new class behavior must be proven against deterministic fixtures and baseline comparison before landing.

---

## 3. Evidence base from source artifacts

### From `broad-roadmap-concept.md`

Phase 3 is defined as first-class memory classes with distinct write, merge, retention, and retrieval rules.

The roadmap names these target classes:
- working/context;
- carry/continuity;
- episodic;
- semantic;
- procedural;
- resource;
- rule.

The roadmap also states:
- write paths must not mix transient state with durable semantic memory;
- procedural memory should route toward skills/workflows rather than generic fact storage;
- resource memory should store grounding handles rather than large blobs;
- benchmarks during this phase should compare class-separated behavior and stale/harmful/missing-memory suppression by class.

### From `deep-research-report.md`

The report recommends:
- a unified canonical memory object with `memory_type` and explicit provenance/grounding/confidence/utility state;
- typed working-state instead of flat text heuristics;
- a real episodic store as the source for later semantic distillation;
- retrieval orchestration by policy, with class-aware distinctions;
- first-class resource memory;
- offline consolidation later, not mixed into this initial class-separation landing.

The report also identifies practical risks:
- current newer paths are still largely lexical/rule-based;
- documentation/code skew must be assumed and verified from live repo files;
- multiple ontologies and compatibility surfaces already exist, so Phase 3 must not widen drift again.

### From the Phase 1 pass-off report

Phase 1 left the repo in a good position for Phase 3 because:
- core pack naming is settled enough for deeper type work;
- append-only effective-state reads are consistent across key paths;
- retrieval-log projection is more reliable;
- compatibility boundaries are explicit instead of implicit;
- current-state baseline harness artifacts are tracked and usable as regression anchors.

The pass-off also explicitly says not started:
- typed live-context state model work;
- destructive migration tooling;
- compatibility alias removals.

Phase 3 must therefore treat deep typed live-context redesign and destructive migration as future or deferred work, not as assumed foundations.

### From repo inspection and targeted research hardening

Repo-local audit and external research together indicate:
- `src/shyftr/models.py` currently holds a flat `MEMORY_KINDS` list and a single `Memory` dataclass, so Phase 3 needs a canonical class layer without breaking current consumers.
- `src/shyftr/pack.py` currently hardcodes kind-to-role behavior in `_compute_loadout_role()`, so class metadata should eventually drive pack role mapping.
- trusted/provider/live-context/continuity surfaces already each carry partial memory semantics, so a canonical class contract must unify rather than duplicate them.
- systems like MemGPT, LightMem, Generative Agents, and MIRIX support a staged rollout: one write authority per class, additive field introduction, no premature storage split, and clear evaluation between memory classes.

---

## 4. Core design policy for Phase 3

### Canonical public class vocabulary

Use these class names in new docs, code comments, tests, and review artifacts:
- `working`
- `continuity`
- `episodic`
- `semantic`
- `procedural`
- `resource`
- `rule`

### Canonical object contract

Phase 3 should converge toward a canonical memory object family with these top-level concepts:
- `memory_id`
- `memory_type`
- `kind`
- `scope`
- `time_interval` or observed-time metadata
- `provenance_refs`
- `grounding_refs`
- `confidence_state`
- `utility_state`
- `lifecycle_state`
- `sensitivity`
- optional class-specific metadata

### Relationship between `memory_type` and `kind`

Use this separation:
- `memory_type` = broad class authority/retention/retrieval semantics.
- `kind` = finer-grained subtype or behavioral label inside a class.

Examples:
- `memory_type=procedural`, `kind=workflow`
- `memory_type=procedural`, `kind=recovery_pattern`
- `memory_type=semantic`, `kind=preference`
- `memory_type=semantic`, `kind=constraint`
- `memory_type=rule`, `kind=escalation_rule`
- `memory_type=resource`, `kind=artifact_ref`

This keeps current `kind` vocabulary useful while giving Phase 3 a stable class layer.

### Authority model by class

| Class | Typical contents | Authority | Default write path | Retention |
|---|---|---|---|---|
| working | active goals, plan state, open loops, tool state, failures, recoveries | non-authoritative | runtime/live-context capture | minutes to session |
| continuity | compact checkpoint, resumable state deltas, cautions, commitments | advisory | harvest/continuity compaction | session to days |
| episodic | timestamped episodes with provenance, actors, outcomes, tools, references | review-gated | session harvest / episode capture | days to months |
| semantic | stable facts, preferences, constraints, concepts, distilled lessons | authoritative after review | reviewed promotion / distillation | long-term |
| procedural | workflows, skills, recovery recipes, tool patterns | authoritative after review/eval | explicit remember / skill-oriented promotion | long-term |
| resource | file refs, screenshots, URLs, code spans, logs, artifacts | authoritative by reference | explicit artifact/resource registration | long-term |
| rule | explicit policies, supersession decisions, guardrails | highest authority after review | reviewed rule promotion / config path | long-term |

### Implementation hardening rules

1. One canonical class contract, many compatibility readers.
2. One write-authority path per class in the first implementation wave.
3. No automatic durable semantic promotion from working/context entries.
4. No implicit blob-dump resource memory.
5. No class-specific storage backend split in the first implementation wave.
6. No destructive backfill required for old cells to remain readable.
7. Every class addition must include read/write/retrieval/verification semantics, not just enum entries.

---

## 5. Phase 3 package shape target

This is the intended end state after autonomous tranches, before final human approval.

### Core code targets

- `src/shyftr/models.py`
  - retains backward compatibility for existing `Memory` records;
  - gains canonical class-aware fields/validation or delegates to a new class module.

- `src/shyftr/memory_types.py` or `src/shyftr/memory_classes.py`
  - new canonical module for class definitions, metadata, authority rules, role defaults, retention defaults, and compatibility helpers.

- `src/shyftr/provider/memory.py`
  - class-aware `remember`, `search`, and profile behavior.

- `src/shyftr/provider/trusted.py`
  - trusted-memory allowances reconciled with canonical class policy.

- `src/shyftr/pack.py`
  - pack role mapping driven by canonical class metadata instead of drifting hardcoded sets alone.

- `src/shyftr/continuity.py`
  - continuity/carry export semantics reconciled with canonical `continuity` class.

- `src/shyftr/live_context.py`
  - live-context harvest/classification aligned with working/continuity/episodic boundaries without requiring a full redesign first.

- `src/shyftr/evolution.py`
  - class-aware proposals where needed for merge/supersede/promote behavior.

- `src/shyftr/mutations.py`
  - lifecycle/update behavior remains compatibility-safe while class metadata is respected.

- `src/shyftr/retrieval/*.py`
  - retrieval filters and simple class-aware weighting/selection where necessary.

### Docs targets

- `README.md`
- `docs/concepts/cells.md`
- `docs/concepts/storage-retrieval-learning.md`
- `docs/concepts/runtime-continuity-provider.md` if touched
- `docs/concepts/live-context-optimization-and-session-harvest.md` if touched
- `docs/future-work.md`
- `docs/skills.md` if public skill behavior needs explanation

### Verification and artifact targets

- `tests/` additions for class-aware behavior
- `scripts/current_state_baseline.py`
- `scripts/compare_current_state_baseline.py`
- repo-local `docs/status/` review artifacts if needed
- final closeout packet for Phase 3

---

## 6. File discovery and prerequisite audit tranche

Before any mutation, inspect and inventory these likely target files:

### Must-read source files
- `src/shyftr/models.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/provider/trusted.py`
- `src/shyftr/pack.py`
- `src/shyftr/continuity.py`
- `src/shyftr/live_context.py`
- `src/shyftr/evolution.py`
- `src/shyftr/mutations.py`
- `src/shyftr/retrieval/hybrid.py`
- `src/shyftr/retrieval/sparse.py`
- `src/shyftr/store/sqlite.py`

### Must-read docs/contracts
- `README.md`
- `docs/concepts/cells.md`
- `docs/concepts/storage-retrieval-learning.md`
- `docs/future-work.md`
- any currently relevant continuity/live-context concept docs

### Must-check verification surfaces
- current baseline fixtures under `examples/evals/current-state-baseline/`
- tests covering pack/provider/continuity/live-context/evolution/models
- terminology/public-readiness gates

### Required output of this audit tranche

Write a repo-local inventory artifact that records:
1. current `kind` taxonomy and all call sites;
2. any existing implicit class semantics already present;
3. class-sensitive consumers that would break if `memory_type` were mishandled;
4. which behaviors are canonical, compatibility, or deferred.

---

## 7. Tranche summary

| Tranche | Name | Purpose |
|---|---|---|
| 0 | prerequisite inventory and boundary lock | inspect current class-like surfaces and freeze assumptions |
| 1 | canonical class contract and ADR | define class model, authority, and compatibility rules |
| 2 | class metadata scaffolding in code | add canonical enum/module/helpers without breaking readers |
| 3 | `memory_type` compatibility introduction | add typed field support and backward-compatible serialization |
| 4 | semantic + procedural class landing | route current stable durable kinds into canonical durable classes |
| 5 | episodic + continuity boundary landing | formalize episode/continuity behavior without full context redesign |
| 6 | resource + rule class landing | add grounded reference memory and explicit policy memory behaviors |
| 7 | provider/pack/retrieval class integration | make retrieval/filter/pack semantics class-aware |
| 8 | live-context and harvest bridging | connect current live-context outputs to working/continuity/episodic classes |
| 9 | migration/backfill and projection hardening | support old cells and SQLite/materialized views safely |
| 10 | docs/skill/readiness convergence | align public and operator-facing docs with the landed contract |
| 11 | full regression + benchmark comparison | prove no baseline regression and validate class-specific checks |
| 12 | final review packet | pool open decisions, compatibility debt, and follow-ons |
| 13 | optional post-approval landing actions | commit/push or other gated actions only after approval |

---

## Tranche 0: prerequisite inventory and boundary lock

**Objective:** Build a file-backed inventory of current memory-kind/class-like behavior and confirm the exact Phase 3 mutation boundary before edits begin.

**Files:**
- Read: all files listed in section 6.
- Create: `docs/status/phase-3-memory-class-inventory.md` if repo-local status artifacts remain the working convention.

**Steps:**
1. Read the current target source files and note where `kind`, trust tiers, pack roles, continuity roles, live-context entry kinds, and trusted-memory rules are defined.
2. Inventory every current `MEMORY_KINDS` value and classify likely target `memory_type`.
3. Inventory every retrieval/pack/continuity/live-context branch that assumes a flat kind list.
4. Record what Phase 3 will not do in the first wave:
   - no storage split;
   - no cloud backend;
   - no forced migration of old cells;
   - no deletion of compatibility aliases.
5. Record any blocker that truly prevents Phase 3 from proceeding autonomously.

**Verification:**
- Read back the inventory artifact.
- Confirm each target source file was inspected.
- Confirm the inventory explicitly lists `working`, `continuity`, `episodic`, `semantic`, `procedural`, `resource`, `rule`.

**Stop boundary:** No code mutation yet.

---

## Tranche 1: canonical class contract and ADR

**Objective:** Define the authoritative Phase 3 class model and compatibility doctrine before implementation code spreads new assumptions.

**Files:**
- Create/modify concept/ADR doc under `docs/concepts/` or `docs/architecture/` if such location exists.
- Modify: `README.md` only if a compact status-safe mention is needed.

**Steps:**
1. Draft a canonical class contract doc covering:
   - class definitions;
   - authority and retention rules;
   - `memory_type` vs `kind` separation;
   - compatibility policy for old ledgers and fields;
   - write-authority mapping by class;
   - retrieval/pack expectations by class.
2. Classify current durable kinds into class families with a deterministic mapping table.
3. Define which classes may be absent/null on old memories and how they are interpreted.
4. Explicitly state that rule memory outranks other durable classes, but remains review-gated.
5. Explicitly state that resource memory stores references/handles, not blob payloads.

**Verification:**
- Read back the class contract doc.
- Confirm it does not promise hosted/platform/frontier benchmarks.
- Confirm it preserves local-first and append-only truth.

**Stop boundary:** Documentation/contract only; still no broad code refactor.

---

## Tranche 2: class metadata scaffolding in code

**Objective:** Add one canonical class-definition module and its helpers without yet changing existing storage semantics.

**Files:**
- Create: `src/shyftr/memory_types.py` or `src/shyftr/memory_classes.py`
- Modify: `src/shyftr/models.py`
- Modify: any narrow helper modules needed for imports/tests
- Add tests covering the new module

**Steps:**
1. Write failing tests for class metadata:
   - known class names;
   - authority defaults;
   - retention defaults;
   - allowed role defaults;
   - compatibility helpers for old records.
2. Add the canonical class-definition module.
3. Add mapping helpers from existing `kind` values to default class families where safe.
4. Keep the new module import-light and reusable by provider/pack/continuity/live-context.
5. Add compatibility helpers that treat missing `memory_type` as valid legacy input.

**Verification:**
- Focused tests for the new module pass.
- Existing import surfaces still load.
- `python -m compileall -q src scripts examples`

**Stop boundary:** No behavior-changing retrieval/pack changes yet.

---

## Tranche 3: `memory_type` compatibility introduction

**Objective:** Introduce the `memory_type` field into core memory serialization/deserialization paths without breaking existing cells or tests.

**Files:**
- Modify: `src/shyftr/models.py`
- Modify: `src/shyftr/provider/memory.py`
- Modify: `src/shyftr/store/sqlite.py` if projection needs additive support
- Modify tests for models/provider/sqlite compatibility

**Steps:**
1. Write failing tests proving:
   - old memory records without `memory_type` still deserialize;
   - new memory records with `memory_type` serialize and deserialize;
   - old field aliases remain accepted;
   - null/absent `memory_type` is treated as legacy-compatible.
2. Add `memory_type` support to the canonical memory object or compatible adapter layer.
3. Preserve `kind` as a subtype/label field.
4. Add additive SQLite/materialization support only as needed.
5. Do not require backfill to pass basic tests.

**Verification:**
- Focused tests for models/provider/sqlite pass.
- Existing baseline fixtures remain readable.
- Search confirms no unsafe global replacement accidentally removed compatibility readers.

**Stop boundary:** Field compatibility landed; class-specific behavior still mostly inert.

---

## Tranche 4: semantic + procedural class landing

**Objective:** Formalize the durable classes that are already most natural in the current repo: semantic and procedural memory, and make `evolution.py` class-aware for the durable-class operations introduced in this tranche.

**Files:**
- Modify: `src/shyftr/provider/memory.py`
- Modify: `src/shyftr/provider/trusted.py`
- Modify: `src/shyftr/models.py`
- Modify: `src/shyftr/evolution.py`
- Modify: retrieval/pack helpers if needed
- Add/modify focused tests

**Steps:**
1. Build a mapping table from current stable durable kinds into `semantic` vs `procedural`.
2. Suggested safe default mapping:
   - `preference`, `constraint` -> `semantic`
   - `workflow`, `recovery_pattern`, `verification_heuristic`, `routing_heuristic`, `tool_quirk` -> `procedural`
   - `success_pattern` -> procedural unless clearly distilled into semantic concept later
3. Reconcile trusted-memory rules with the canonical class contract.
4. Ensure procedural memory semantics emphasize repeatable workflows/recipes, not fact storage.
5. Keep explicit review gates for durable authority.
6. Make `evolution.py` class-aware where merge/supersede/promote behavior now depends on semantic versus procedural durable-class distinctions, and defer any broader evolution redesign that exceeds this tranche.

**Verification:**
- Focused provider/trusted-memory tests pass.
- Search/profile surfaces can filter or report by class where intended.
- No regression in old non-class-aware calls.

**Stop boundary:** Only semantic/procedural durable landing; no episodic/resource/rule yet.

---

## Tranche 5: episodic + continuity boundary landing

**Objective:** Introduce a formal distinction between continuity memory and episodic memory while preserving current carry/live-context safety posture.

**Files:**
- Modify: `src/shyftr/continuity.py`
- Modify: `src/shyftr/live_context.py`
- Modify: `src/shyftr/models.py` or helper module
- Add tests for continuity/episode boundaries
- Update relevant docs if needed

**Steps:**
1. Define the minimum episodic object behavior Phase 3 actually lands.
2. Keep continuity as advisory/exported state, not durable semantic truth.
3. Introduce episode-ready records or mappings for harvested session segments that are important enough to preserve with provenance.
4. Do not attempt the full typed live-context redesign here.
5. Ensure continuity packs and episodic records are not conflated.

**Verification:**
- Continuity tests continue to pass.
- New episodic tests prove provenance/timestamp/authority behavior.
- Session-harvest paths do not accidentally route transient working state into semantic memory.

**Stop boundary:** No deep redesign of live-context object model yet.

---

## Tranche 6: resource + rule class landing

**Objective:** Add first-class grounding/reference memory and explicit policy/rule memory with strict authority boundaries.

**Files:**
- Modify: `src/shyftr/models.py`
- Modify: provider/pack/retrieval surfaces as needed
- Modify relevant docs and tests

**Steps:**
1. Introduce resource-memory schema/support for references to:
   - file paths;
   - screenshots;
   - URLs;
   - code spans;
   - log spans;
   - tool outputs/artifact handles.
2. Ensure resource memory stores references plus provenance, not arbitrary blob content.
3. Introduce explicit rule-memory handling for reviewed policies/guardrails/supersession decisions.
4. Define retrieval precedence where rule memory acts as higher-authority guidance.
5. Keep rule promotion reviewed and compatibility-safe.

**Verification:**
- Resource-memory tests prove reference-only posture.
- Rule-memory tests prove authority/precedence behavior.
- Search/pack outputs clearly label rule/resource items.

**Stop boundary:** No multimodal ANN upgrade or artifact-store rewrite.

---

## Tranche 7: provider/pack/retrieval class integration

**Objective:** Make the main runtime-facing behaviors class-aware while preserving explainability and local determinism.

**Files:**
- Modify: `src/shyftr/provider/memory.py`
- Modify: `src/shyftr/pack.py`
- Modify: `src/shyftr/retrieval/hybrid.py`
- Modify: `src/shyftr/retrieval/sparse.py` if needed
- Modify: `src/shyftr/integrations/pack_api.py` and compatibility surfaces if needed
- Add focused tests

**Steps:**
1. Add optional class filters to search/pack behavior where appropriate.
2. Move pack role defaults toward canonical class metadata instead of fragile flat-kind sets.
3. Introduce only simple class-aware weighting rules needed to express the class boundary.
4. Keep explainability in retrieval traces.
5. Do not introduce learned rerankers or opaque scoring.

**Verification:**
- Focused pack/retrieval/provider tests pass.
- Role assignment is deterministic and explainable.
- Legacy calls without class filters continue to work.

**Stop boundary:** Retrieval remains local-first and deterministic.

---

## Tranche 8: live-context and harvest bridging

**Objective:** Connect the current live-context pipeline to the new class model without requiring the full future typed-state redesign.

**Files:**
- Modify: `src/shyftr/live_context.py`
- Modify: `src/shyftr/continuity.py`
- Modify tests and docs as needed

**Steps:**
1. Map current harvest buckets and entry kinds to class-aware destinations.
2. Preserve the rule that live context is not durable memory by default.
3. Ensure harvest outputs can distinguish:
   - working state to discard/archive;
   - continuity carry-forward state;
   - episodic candidates;
   - semantic/procedural candidates only when properly grounded/reviewable.
4. Keep direct durable-memory auto-write disabled unless current reviewed policy explicitly allows it.
5. Record any remaining gap that belongs to later typed working-state redesign.

**Verification:**
- Harvest tests pass.
- No transient working-state pollution into durable semantic memory.
- Continuity and episodic destinations are distinguishable in outputs.

**Stop boundary:** This tranche bridges current behavior; it is not the full future state-graph redesign.

---

## Tranche 9: migration/backfill and projection hardening

**Objective:** Add safe migration/backfill support so existing cells and SQLite/materialized projections can coexist with the new class-aware model.

**Files:**
- Modify/create migration/backfill scripts as needed
- Modify: `src/shyftr/store/sqlite.py`
- Possibly add utility scripts for audit/backfill dry-runs
- Add tests

**Steps:**
1. Add a dry-run backfill/audit path that classifies existing records.
2. Mark ambiguous records for review instead of forcing unsafe assignment.
3. Ensure SQLite/materialized projections preserve `memory_type` when present and tolerate absence when legacy.
4. Keep migration additive and reversible where possible.
5. Do not require all existing memories to be backfilled for the repo to function.

**Verification:**
- Dry-run migration script produces deterministic output.
- Projection rebuild tests pass for mixed old/new records.
- Old fixtures and new fixtures both remain supported.

**Stop boundary:** No destructive migration, no irreversible rewrite of historical ledgers.

---

## Tranche 10: docs/skill/readiness convergence

**Objective:** Align public docs, concept docs, and the repo-bundled/local ShyftR skill with the landed Phase 3 behavior.

**Files:**
- Modify: `README.md`
- Modify: concept docs listed above
- Modify: `adapters/hermes/skills/shyftr/SKILL.md` if needed
- Sync local runtime skill copy after repo-bundled skill changes

**Steps:**
1. Update docs to describe the class model accurately without overclaiming.
2. Preserve the stable local-first release posture.
3. Explain `memory_type` vs `kind` clearly.
4. Document class boundaries, authority, and resource/reference policy.
5. Sync the repo-bundled and local ShyftR skill if the skill content changes.

**Verification:**
- Read back all changed docs.
- Run terminology/public-readiness gates.
- Verify repo-bundled and local skill copies match if changed.

**Stop boundary:** Docs reflect landed behavior only; no speculative frontier claims.

---

## Tranche 11: full regression + benchmark comparison

**Objective:** Prove the Phase 3 landing did not regress the stable local-first baseline and that class-aware behavior is covered by focused tests.

**Files:**
- Use existing scripts and comparison artifacts
- Save repo-local comparison/closeout artifacts as needed

**Required verification commands:**
```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
python scripts/current_state_baseline.py --mode all
python scripts/compare_current_state_baseline.py docs/status/current-state-baseline-summary.json docs/status/current-state-baseline-summary.json --markdown-out docs/status/current-state-baseline-comparison.md
PYTHONPATH=.:src python -m pytest -q
git diff --check
```

**Additional Phase 3-specific checks:**
- focused tests for memory-type serialization/deserialization;
- class-mapping behavior;
- continuity/episode boundary behavior;
- resource/rule authority behavior;
- mixed old/new fixture compatibility;
- class-aware pack/search behavior;
- old baseline fixtures under `examples/evals/current-state-baseline/` still pass without requiring backfill, and any fixture lacking `memory_type` continues to produce compatibility-safe baseline output.

**Success criteria:**
- baseline harness still passes;
- no new high-severity regression against Phase 1 behavior;
- old cells remain readable;
- class-aware behavior is deterministic and file-backed;
- docs/readiness/terminology gates pass.

---

## Tranche 12: final review packet

**Objective:** Pool every remaining decision, compatibility debt item, and future-phase boundary into one final human-review artifact.

**Files:**
- Create: `docs/status/phase-3-human-review-packet.md`
- Create or update a closeout summary if useful

**Packet must include:**
1. What landed.
2. What remained compatibility-only.
3. Any ambiguous backfill assignments deferred.
4. Any class-policy questions still open.
5. Exact follow-on items for later phases:
   - deeper typed working-state redesign;
   - stronger retrieval orchestration;
   - offline consolidation;
   - richer multimodal/resource retrieval;
   - evaluation expansions.
6. Whether commit/push is approved or blocked.

**Verification:**
- Read back the review packet.
- Ensure all should-fix items are either handled or explicitly deferred.

---

## Tranche 13: optional post-approval landing actions

**Objective:** Execute only those side effects that require explicit approval after the final packet exists.

**Potential actions after approval:**
- final cleanup of cheap safe should-fixes;
- final verification rerun;
- commit;
- push;
- any release-note/status artifact adjustments explicitly approved.

**Do not execute without approval:**
- commit/push if the operator wants a read-only plan/review first;
- destructive compatibility cleanups;
- broader public-release decisions.

---

## 8. Deterministic class mapping proposal

Use this as the starting mapping unless repo inspection proves a better local fit.

| Current kind or source behavior | Proposed `memory_type` | Notes |
|---|---|---|
| live context working entries | working | non-authoritative by default |
| carry/continuity pack state | continuity | advisory/exported state |
| session-harvested important event records | episodic | provenance and timestamps required |
| preference | semantic | stable user/environment fact |
| constraint | semantic | durable rule-like fact, unless elevated to explicit rule |
| workflow | procedural | repeatable steps |
| recovery_pattern | procedural | fix recipe |
| verification_heuristic | procedural | proof recipe |
| routing_heuristic | procedural | decision/use pattern |
| tool_quirk | procedural | operational tool knowledge |
| success_pattern | procedural by default | may distill into semantic later |
| failure_signature | procedural or episodic depending representation | preserve caution semantics |
| anti_pattern | procedural or rule depending authority | reviewed caution |
| escalation_rule | rule | explicit policy/guardrail behavior |
| supersession | rule or semantic metadata | depends on landed design |
| file/log/url/code-span refs | resource | reference-only |

Any ambiguous mapping discovered during implementation should be recorded in the review packet rather than hidden.

---

## 9. Phase 3 anti-patterns to forbid

1. Do not add all new class behavior directly into `kind` and skip `memory_type`.
2. Do not create separate storage backends per class in the first implementation wave.
3. Do not force every old record to be backfilled before the repo can run.
4. Do not let live-context/transient working state auto-promote into durable semantic memory.
5. Do not store blob payloads as resource memory when a stable handle/reference exists.
6. Do not add opaque learned rerankers or cloud retrieval in the name of class separation.
7. Do not expand docs into hosted/frontier claims just because the class architecture looks richer.
8. Do not silently break old field aliases, legacy tests, or compatibility readers.
9. Do not treat the final review packet as optional.

---

## 10. Verification matrix

| Verification target | Why it matters |
|---|---|
| old record deserialization still works | prevents historical cell breakage |
| `memory_type` round-trip works | proves canonical field landed |
| semantic/procedural split is deterministic | prevents durable class drift |
| continuity != episodic | protects carry semantics |
| resource memory stores references only | preserves local-first inspectability and avoids blob drift |
| rule memory precedence is explicit | avoids hidden policy conflicts |
| class-aware search/pack remains explainable | prevents opaque retrieval drift |
| baseline comparison passes | protects stable local-first proof path |
| docs/readiness/terminology checks pass | keeps public posture truthful |

---

## 11. Expected repo surfaces likely touched

Likely high-touch files:
- `src/shyftr/models.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/provider/trusted.py`
- `src/shyftr/pack.py`
- `src/shyftr/continuity.py`
- `src/shyftr/live_context.py`
- `src/shyftr/evolution.py`
- `src/shyftr/mutations.py`
- `src/shyftr/store/sqlite.py`
- retrieval modules under `src/shyftr/retrieval/`
- tests covering these modules
- relevant docs and the repo-bundled skill

Likely lower-touch or read-mostly files:
- `README.md`
- `docs/future-work.md`
- concept docs
- baseline scripts and comparison artifacts

Unlikely to need meaningful Phase 3 mutation unless inspection proves otherwise:
- low-level append-only ledger writer itself
- public hosted/platform surfaces
- unrelated console/productization workflows

---

## 12. Definition of done

Phase 3 is done when all of the following are true:

1. ShyftR has a canonical first-class memory-class contract on disk and in code.
2. `memory_type` is supported compatibly for old and new records.
3. Working, continuity, episodic, semantic, procedural, resource, and rule boundaries are explicit in docs and tests.
4. Provider/pack/retrieval behavior can respect classes without breaking legacy flows.
5. Old cells remain readable without destructive migration.
6. Baseline and regression gates pass.
7. Public docs do not overclaim what Phase 3 delivered.
8. A final review packet exists listing compatibility debt and future follow-ons.

---

## 13. Execution handoff

After saving this plan, the next execution mode should be:
- follow the tranches in order;
- use fresh bounded worker/reviewer lanes only after reading the whole plan;
- verify every tranche before moving on;
- stop before Tranche 13 unless the operator explicitly approves landing side effects.

If execution is delegated later, the executor should treat this file as the canonical Phase 3 plan artifact and create tranche-specific repo-local status artifacts rather than relying on chat memory.