# ShyftR Phase 2 Typed Working Context and Carry-State Tranched Plan

> For Hermes: use `subagent-driven-development` or bounded helper/review lanes only after reading this entire plan. Execute tranches in order. Do not cross the final human-review tranche unless the operator explicitly approves.

Goal: turn ShyftR's live context cell from flat text entries into typed working state that survives compression, supports reliable resume, and improves carry/continuity quality without polluting durable memory or breaking the current local-first, append-only, review-gated architecture.

Architecture: Phase 2 is a typed-state expansion phase built on top of the completed Phase 1 stabilization work. It must preserve three-cell separation (live context, continuity/carry, durable memory), dry-run-by-default write posture, append-only ledgers, advisory continuity, and review-gated durable promotion. The implementation should add one canonical typed working-state layer plus one compact carry-state/checkpoint layer, then progressively route pack, harvest, continuity, CLI/MCP/HTTP, and evaluation surfaces through those layers with additive compatibility.

Tech stack: Python 3.11/3.12, JSONL append-only ledgers, SQLite projections/indexes where already present, ShyftR CLI/MCP/HTTP/provider surfaces, deterministic synthetic fixtures, current-state baseline harness, terminology/readiness gates, focused pytest regression suites.

Primary repo: `/Users/stefan/ShyftR`

Planning/reference artifacts:
- `/Users/stefan/Desktop/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/Desktop/ShyftR/deep-research-report.md`
- `/Users/stefan/Desktop/ShyftR/2026-05-07-shyftr-phase-1-pass-off-report.md`
- `/Users/stefan/Desktop/ShyftR/2026-05-07-shyftr-phase-1-core-memory-model-stabilization-tranched-plan.md`
- `/Users/stefan/Desktop/ShyftR/2026-05-07-shyftr-phase-3-first-class-memory-classes-tranched-plan.md`

-------------------------------------------------------------------------------

## 0. Executive summary

Phase 0 baseline/evidence harness work is complete.

Phase 1 core memory model stabilization is complete and landed on `main` with:
- canonical public `pack` surface;
- `loadout` retained as compatibility shim;
- latest-row-wins append-only semantics through shared helpers;
- retrieval-log/runtime compatibility hardening;
- tracked baseline harness scripts and fixtures;
- passing terminology, readiness, baseline, and pytest gates.

Phase 2 is now the first major post-stabilization feature phase. It should not assume any already-landed typed live-context redesign; the Phase 1 pass-off explicitly says this work was not started.

The roadmap and deep research agree on the core objective:
- keep live context, continuity/carry, and durable memory distinct;
- replace flat text working-state entries with typed records;
- evolve continuity from a durable-memory-only advisory wrapper toward compact session-state deltas;
- improve session resume correctness while keeping carry advisory and durable promotion review-gated;
- prove the value through deterministic baseline-aligned evaluation, not only through schema additions.

This plan therefore uses a phased-assembly shape with additive compatibility, explicit stop boundaries, focused regression gates, and a final human-review tranche.

-------------------------------------------------------------------------------

## 1. Non-negotiable scope boundary

### In scope for Phase 2

- define a canonical typed working-context contract for the live context cell;
- add typed working-state records for the roadmap-defined state categories;
- preserve backward readability for current live-context entries and ledgers;
- introduce a compact carry-state/checkpoint object shape that captures resumable session deltas;
- evolve continuity packs so they can include typed carry-state information without losing current durable-memory behavior;
- upgrade harvest classification so typed entries route correctly into discard/archive/continuity/proposal buckets;
- add typed retrieval/ranking behavior for live context while preserving explainability and bounded pack limits;
- add deterministic evaluation for resume correctness, missing-state, wrong-state, token/pack size, and harvest classification quality;
- update CLI/MCP/HTTP/docs/examples to expose the typed-state model compatibly;
- save repo-local review/closeout artifacts and a final human-review packet.

### Explicitly out of scope for Phase 2

- removing legacy compatibility aliases or readers;
- destructive migration of old live-context or continuity ledgers;
- replacing JSONL append-only ledgers as canonical truth;
- hosted, multi-tenant, or cloud-service posture changes;
- Phase 3 first-class episodic/semantic/procedural/resource/rule memory implementation;
- full retrieval-orchestration overhaul beyond what typed working-state needs locally;
- advanced learned rerankers or service-dependent retrieval infrastructure;
- sleep-time consolidation/offline rehearsal pipelines beyond targeted Phase 2 evaluation fixtures;
- package publishing, public release-tag decisions, or hosted API productization;
- direct durable-memory auto-write expansion beyond current explicit policy-gated behavior.

### Phase boundary discipline

Phase 2 should leave the repo in a state where Phase 3 can safely build on a stable typed working/context and carry substrate.

Phase 2 should not quietly absorb:
- first-class episodic memory objects;
- semantic/procedural/resource/rule authority implementation;
- destructive cell migration;
- alias-removal cleanup;
- broad privacy/policy redesign;
- high-scale distributed retrieval changes.

### Collision boundary

Expected write surface: `/Users/stefan/ShyftR`

Do not:
- rewrite historical canonical ledgers;
- widen scope into unrelated roadmap phases;
- treat ignored `docs/status/` paths as public repo truth;
- mutate global Hermes config or unrelated local runtime state.

-------------------------------------------------------------------------------

## 2. Human input requirement

Autonomous tranches 0-11 require no human input by design.

All human-gated review items are pooled into the final tranches:
- Tranche 12: final review packet and decision matrix.
- Tranche 13: optional post-approval landing actions.

Before Tranche 12, the executor should not ask the operator to choose type names, field names, or migration semantics unless a true blocker is discovered. Use the safe defaults below.

### Safe defaults for autonomous execution

1. The canonical working-state surface remains the live context cell.
2. Existing flat `LiveContextEntry` rows stay readable.
3. New typed state is introduced additively, not via destructive replacement.
4. `content` remains available as a human-readable summary even when typed fields exist.
5. The canonical typed field for state category is `entry_kind` expanded to the roadmap vocabulary; compatibility readers may continue to accept current alpha names.
6. `metadata` remains available for additive compatibility during transition, but Phase 2 should move core semantics into explicit fields.
7. Carry remains advisory; it does not gain durable-memory write authority.
8. Direct durable memory remains opt-in/policy-gated and defaults to proposal routing.
9. Resource-like references in Phase 2 are working-state or carry references only; they are not full Phase 3 resource memory.
10. Every new typed behavior must be proven against deterministic fixtures and the current-state baseline before landing.

-------------------------------------------------------------------------------

## 3. Evidence base from source artifacts

### From `broad-roadmap-concept.md`

Phase 2 is explicitly defined as `Typed working context and carry-state model`.

The roadmap says the goal is to turn the live context cell from flat text entries into typed working state that survives compression and supports reliable resume.

The roadmap names these target typed working-state categories:
- `goal`;
- `subgoal`;
- `plan_step`;
- `constraint`;
- `decision`;
- `assumption`;
- `artifact_ref`;
- `tool_state`;
- `error`;
- `recovery`;
- `open_question`;
- `verification_result`.

The roadmap also says each record should support where useful:
- timestamp or interval;
- source/evidence reference;
- parent/child relationship;
- scope;
- sensitivity;
- TTL or retention hint;
- status;
- confidence or utility signal;
- grounding/resource refs.

For continuity/carry, the roadmap says it should evolve from bounded durable-memory advisory packs toward compact session-state deltas covering:
- unresolved goals;
- current plan position;
- open loops;
- commitments;
- constraints;
- active assumptions;
- recent failures and recoveries;
- important artifact refs;
- cautions required for resumption.

### From `deep-research-report.md`

The report states:
- the carry-cell/continuity-cell concept is good;
- the context-cell idea is also good;
- both need to move from bounded text bundle heuristics to typed working-state and episodic-state abstractions;
- typed working-state should use structured records instead of generic text entries;
- continuity is currently directionally right but still mostly a safe bounded wrapper over durable memory rather than a true compacted session-state abstraction;
- the next priority is stabilizing memory model boundaries, typed state, stronger retrieval, and evaluation, not feature sprawl.

The report specifically recommends typed structures carrying:
- timestamps;
- parent links;
- evidence refs;
- TTL;
- provenance/grounding;
- structured resume/state semantics.

The report also emphasizes evaluation beyond persistence, including:
- retrieval quality;
- memory utility;
- stale-memory suppression;
- contradiction avoidance;
- token/cost efficiency;
- task-success lift;
- calibration over time.

### From the Phase 1 pass-off report

Phase 1 explicitly states as not started:
- Phase 2 typed live-context state model work;
- destructive migration tooling;
- compatibility alias removals.

Phase 1 also leaves the repo in a good position because:
- canonical pack naming is settled enough for deeper typed-context work;
- append-only effective-state reads are consistent across key paths;
- retrieval-log projection is more reliable for evaluation/audit work;
- compatibility boundaries are explicit instead of implicit;
- baseline harness artifacts are tracked and usable as regression anchors.

### From current repo inspection

Current implemented/public-alpha docs and code establish these facts:
- `docs/concepts/live-context-optimization-and-session-harvest.md` says ShyftR captures live working context into cells, returns bounded packs, and harvests durable lessons at session close.
- `docs/concepts/runtime-continuity-provider.md` says carry/continuity currently supplies bounded continuity packs around context compression while the runtime retains ownership of mechanical compaction.
- `src/shyftr/live_context.py` currently uses a flat `LiveContextEntry` dataclass with `content` plus limited metadata.
- `src/shyftr/live_context.py` currently supports these entry kinds:
  - `active_goal`
  - `active_plan`
  - `active_artifact`
  - `decision`
  - `constraint`
  - `failure`
  - `recovery`
  - `verification`
  - `open_question`
- `src/shyftr/live_context.py` currently scores pack entries largely by lexical overlap plus light recency/role heuristics.
- `src/shyftr/live_context.py` currently classifies harvest decisions primarily through rule-based logic over kind and retention/sensitivity hints.
- `src/shyftr/continuity.py` currently builds continuity packs from durable memory via pack/loadout assembly, not from a dedicated carry-state/checkpoint object.
- current tests cover layout, append-only capture, dry-run posture, bounded advisory packs, harvest idempotence, continuity pack behavior, and feedback surfaces.

These inspected facts define the real starting boundary for Phase 2.

-------------------------------------------------------------------------------

## 4. Current-state preservation contract

Phase 2 must preserve the following verified behaviors unless an explicit tranche says otherwise and regression tests are updated accordingly.

### Behavior that must remain true

1. Three-cell separation remains intact:
   - live context cell = high-churn working state;
   - continuity/carry cell = context-management evidence and feedback;
   - memory cell = reviewed durable memory.

2. Append-only ledger discipline remains intact.

3. Capture/pack/harvest/carry write surfaces remain dry-run by default unless explicit `write=true` or `--write` is supplied.

4. Continuity remains advisory and runtime-owned mechanical compression remains outside ShyftR.

5. Harvest remains review-gated and idempotent.

6. Bounded pack assembly remains enforced with max-item and max-token caps.

7. Duplicate suppression and stale suppression remain active.

8. CLI/MCP/HTTP compatibility aliases for carry/continuity remain supported.

9. Existing alpha live-context ledgers remain readable without a destructive migration step.

10. Current focused test behaviors remain covered and must continue to pass.

### Phase 2 implication

Any schema, API, or retrieval change that violates one of the preservation items above must be treated as a design bug unless the plan explicitly routes that item to a later approved phase.

-------------------------------------------------------------------------------

## 5. Core design policy for Phase 2

### Canonical typed working-state vocabulary

Use these names in new docs, code comments, tests, and artifacts:
- `goal`
- `subgoal`
- `plan_step`
- `constraint`
- `decision`
- `assumption`
- `artifact_ref`
- `tool_state`
- `error`
- `recovery`
- `open_question`
- `verification_result`

### Compatibility mapping from current alpha vocabulary

Phase 2 should map current entry kinds forward like this:
- `active_goal` -> `goal`
- `active_plan` -> `plan_step` or `subgoal` depending on structure
- `active_artifact` -> `artifact_ref`
- `failure` -> `error`
- `verification` -> `verification_result`
- `decision` -> `decision`
- `constraint` -> `constraint`
- `recovery` -> `recovery`
- `open_question` -> `open_question`

The mapping must be explicit, tested, and documented.

### Canonical typed working-state fields

The Phase 2 typed working-state layer should converge toward these explicit fields:
- `entry_id`
- `entry_kind`
- `content`
- `created_at`
- `updated_at` when needed
- `runtime_id`
- `session_id`
- `task_id`
- `source_ref`
- `evidence_refs`
- `grounding_refs`
- `parent_entry_id`
- `child_entry_ids`
- `scope`
- `sensitivity_hint`
- `retention_hint`
- `status`
- `confidence`
- `utility_signal`
- `valid_until` or equivalent TTL field
- type-specific metadata only when not worth promoting to a canonical field

### Carry-state/checkpoint design policy

Phase 2 should add a compact carry-state/checkpoint object that represents resumable state rather than only durable-memory retrieval output.

The checkpoint should contain compact structured sections for:
- unresolved goals;
- active subgoals;
- current plan position;
- blocked or open plan steps;
- commitments or promised next actions;
- active constraints;
- active assumptions;
- recent errors;
- recent recoveries;
- artifact refs and grounding handles needed for resume;
- resumption cautions.

### Retrieval policy for Phase 2

Phase 2 retrieval should stay local-first and explainable.

Do:
- use typed fields to improve retrieval/ranking;
- keep lexical fallback for compatibility;
- add score traces or equivalent explainable ranking evidence where practical;
- prioritize active/unresolved state over archived or stale state.

Do not:
- rely on opaque learned rerankers;
- assume giant context windows make selection unnecessary;
- silently ship a full retrieval-orchestration redesign.

### Harvest policy for Phase 2

Harvest must classify typed entries with more structure than the current alpha logic, but still preserve these categories:
- discard;
- archive;
- continuity_feedback;
- memory_candidate;
- direct_durable_memory;
- skill_proposal.

Typed entries should not automatically become durable semantic memory just because they were useful in the session.

-------------------------------------------------------------------------------

## 6. Recommended repo surfaces

### Read first for concept alignment
- `README.md`
- `docs/concepts/live-context-optimization-and-session-harvest.md`
- `docs/concepts/runtime-continuity-provider.md`
- `docs/concepts/runtime-integration-contract.md`
- `docs/concepts/storage-retrieval-learning.md`

### Primary implementation files likely touched
- `src/shyftr/live_context.py`
- `src/shyftr/continuity.py`
- `src/shyftr/cli.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/server.py`
- `src/shyftr/models.py` only if Phase 2 decides to centralize shared typed-state helpers there
- supporting helper modules only if the implementation proves they are needed

### Primary tests likely touched/expanded
- `tests/test_live_context.py`
- `tests/test_session_harvest.py`
- `tests/test_continuity.py`
- `tests/test_cli.py`
- `tests/test_mcp_server.py`
- `tests/test_server.py`
- `tests/test_current_state_baseline_smoke.py`
- `tests/test_current_state_metrics_schema.py`
- new focused typed-state/resume fixtures as needed

### Baseline/eval surfaces likely touched
- `scripts/current_state_baseline.py`
- `scripts/compare_current_state_baseline.py`
- `examples/evals/current-state-baseline/`
- new Phase 2 deterministic fixtures/scripts only if they remain repo-local and reproducible

### Docs/examples likely touched
- `docs/concepts/live-context-optimization-and-session-harvest.md`
- `docs/concepts/runtime-continuity-provider.md`
- `docs/runtime-context-optimization-example.md`
- `docs/skills.md` only if examples/skill-facing claims need adjustment

-------------------------------------------------------------------------------

## 7. Benchmark and evaluation doctrine for Phase 2

Phase 2 must benchmark while building, not only after landing.

### Required benchmark categories

1. Heuristic live context vs typed live context.
2. Resume success rate.
3. Missing-state rate.
4. Wrong-state inclusion rate.
5. Pack size and token efficiency.
6. Preservation of decisions, constraints, failures, recoveries, open questions, and artifact refs.
7. Harvest classification precision/recall across buckets.
8. Operator review burden.
9. No regression against Phase 0 baseline.

### Minimum deterministic fixture families

1. Multi-step resume fixture.
2. Typed-vs-flat representation fixture.
3. Harvest routing fixture with expected bucket labels.
4. Boundary fixture for TTL, stale, superseded, and private/sensitive entries.
5. Empty/compatibility fixture proving old cells still work.
6. Carry-state parity fixture proving current continuity behavior remains unchanged when no typed carry state is present.

### Required measurement outputs

At minimum, Phase 2 should produce repo-local or tracked evaluation artifacts showing:
- fixture name;
- pre/post token counts;
- selected state items;
- missing-state count;
- wrong-state count;
- resume verdict;
- harvest bucket counts;
- baseline comparison verdict.

-------------------------------------------------------------------------------

## 8. Tranche plan

### Tranche 0: Preflight and current-state inventory

Objective: lock the exact Phase 2 starting boundary from the live repo and source artifacts before implementation.

Files:
- Read: `/Users/stefan/Desktop/ShyftR/broad-roadmap-concept.md`
- Read: `/Users/stefan/Desktop/ShyftR/deep-research-report.md`
- Read: `/Users/stefan/Desktop/ShyftR/2026-05-07-shyftr-phase-1-pass-off-report.md`
- Read: `docs/concepts/live-context-optimization-and-session-harvest.md`
- Read: `docs/concepts/runtime-continuity-provider.md`
- Read: `src/shyftr/live_context.py`
- Read: `src/shyftr/continuity.py`
- Read: current tests covering live context, continuity, and session harvest
- Write: repo-local inventory/status artifact if desired under ignored status path or tracked docs/plans support path

Steps:
1. Verify repo is clean and on the intended branch/worktree.
2. Inventory current live-context entry kinds, harvest buckets, continuity pack schema, and CLI/MCP/HTTP arguments.
3. Record what Phase 2 must preserve from current behavior.
4. Record exact gaps against roadmap/research goals.
5. Record explicit deferred boundaries for Phase 3 and later.

Verification:
- Read the inventory artifact back.
- Confirm it lists current alpha entry kinds and preservation rules.
- Confirm it explicitly says Phase 1 marked typed live-context work as not started.

Stop boundary:
- Do not edit implementation files in this tranche.

### Tranche 1: Typed working-state contract and compatibility map

Objective: define and land the canonical typed working-state schema with additive compatibility.

Files:
- Modify: `src/shyftr/live_context.py`
- Modify if needed: `src/shyftr/models.py`
- Create or modify tests for schema validation
- Modify docs describing live-context entry kinds

Steps:
1. Introduce a canonical typed working-state contract covering the roadmap categories.
2. Decide whether this is represented as an evolved `LiveContextEntry`, a companion typed dataclass, or a wrapper model around current rows.
3. Add explicit canonical fields for parent/child relationships, scope, status, confidence, grounding refs, evidence refs, and TTL.
4. Keep backward reading support for current alpha rows.
5. Define and test the mapping from current alpha names to new canonical names.
6. Keep `content` as a human-readable summary field.

Verification:
- Focused unit tests for new schema validation and compatibility reads.
- Read back representative rows created by old and new paths.
- Confirm no destructive migration is required.

Stop boundary:
- Do not yet redesign continuity pack assembly.

### Tranche 2: Capture-surface evolution for typed entries

Objective: let live-context capture accept structured typed state while preserving current CLI/MCP/HTTP usage.

Files:
- Modify: `src/shyftr/live_context.py`
- Modify: `src/shyftr/cli.py`
- Modify: `src/shyftr/mcp_server.py`
- Modify: `src/shyftr/server.py`
- Modify: related tests

Steps:
1. Extend capture requests to accept the new typed fields.
2. Preserve current alpha call shapes and defaults.
3. Ensure dry-run remains default.
4. Add validation for typed fields and relationship consistency.
5. Add tests for CLI/MCP/HTTP capture flows using both legacy and typed inputs.

Verification:
- Focused tests for capture via Python API, CLI, MCP bridge, and HTTP endpoints.
- Confirm dry-run still avoids ledger writes.
- Confirm old capture style still passes.

Stop boundary:
- Do not yet redesign retrieval/scoring.

### Tranche 3: Carry-state/checkpoint object shape

Objective: create the compact resumable state object that Phase 2 roadmap work requires.

Files:
- Modify: `src/shyftr/live_context.py`
- Modify: `src/shyftr/continuity.py`
- Create/modify focused tests
- Update docs explaining carry-state semantics

Steps:
1. Add a canonical carry-state/checkpoint dataclass or object family.
2. Define its sections for unresolved goals, plan position, open loops, commitments, constraints, assumptions, errors/recoveries, artifact refs, and cautions.
3. Add deterministic serialization for the checkpoint.
4. Ensure it is compact and bounded.
5. Keep it clearly advisory.

Verification:
- Unit tests for checkpoint serialization and deterministic shape.
- Fixture proving checkpoint size stays within expected bounds.
- Read-back verification of written checkpoint records if ledger-backed.

Stop boundary:
- Do not yet merge carry-state into continuity pack output.

### Tranche 4: Continuity evolution from durable-memory-only wrapper to mixed carry support

Objective: let continuity packs incorporate typed carry-state while preserving current durable-memory behavior.

Files:
- Modify: `src/shyftr/continuity.py`
- Modify: `src/shyftr/live_context.py` only as needed for integration
- Modify continuity tests
- Possibly modify CLI/MCP/HTTP surfaces if explicit checkpoint export/import is added

Steps:
1. Add a path for continuity to read the new carry-state/checkpoint object.
2. Merge carry-state and durable-memory retrieval into one bounded advisory continuity output.
3. Preserve current behavior when no carry-state exists.
4. Keep durable memory and carry-state distinguishable in output semantics.
5. Add diagnostics proving what came from carry-state versus durable memory.

Verification:
- Regression test proving empty/no-carry path remains equivalent to current continuity behavior.
- New tests proving continuity can emit typed resumable state deltas.
- Confirm advisory-only posture remains true.

Stop boundary:
- Do not yet change harvest routing logic.

### Tranche 5: Typed harvest classifier and proposal routing

Objective: upgrade session-close harvest so typed entries route correctly and predictably.

Files:
- Modify: `src/shyftr/live_context.py`
- Modify: `tests/test_session_harvest.py`
- Add deterministic labeled fixtures for classification quality
- Update harvest docs/examples

Steps:
1. Replace or extend rule-only classification so it uses typed fields such as status, TTL, relationships, and explicit kinds.
2. Preserve current bucket vocabulary.
3. Make assumptions, tool state, plan steps, and verification results route intentionally rather than by generic string fallback.
4. Keep direct durable memory opt-in/policy-gated.
5. Add labeled fixtures for precision/recall measurement.

Verification:
- Focused harvest tests covering every bucket.
- Idempotence regression still passes.
- Precision/recall or deterministic expected-classification fixture passes.

Stop boundary:
- Do not yet change pack ranking.

### Tranche 6: Typed live-context retrieval and explainable scoring

Objective: improve live-context pack relevance by using typed fields instead of mostly lexical heuristics.

Files:
- Modify: `src/shyftr/live_context.py`
- Modify tests covering pack behavior
- Update docs or status notes describing pack logic

Steps:
1. Introduce typed ranking signals such as active status, unresolved state, TTL freshness, confidence, and relationship locality.
2. Preserve lexical fallback and explainability.
3. Ensure duplicate suppression and stale suppression remain intact.
4. Add diagnostics or score traces where practical.
5. Compare typed scoring against heuristic scoring with deterministic fixtures.

Verification:
- Focused tests proving packs remain bounded and advisory.
- Fixture-based comparison showing typed scoring is at least as good or smaller/more accurate than the heuristic baseline.
- Confirm active prompt suppression still works.

Stop boundary:
- Do not yet implement explicit session resume reconstruction.

### Tranche 7: Resume-state reconstruction flow

Objective: prove that typed state and carry-state actually support better session resume.

Files:
- Modify: `src/shyftr/live_context.py`
- Modify: `src/shyftr/continuity.py`
- Add or expand deterministic resume fixtures/tests
- Update docs/example flow

Steps:
1. Add a resume/reconstruction flow that reads continuity/carry output and rebuilds the minimal working state needed for a new session.
2. Make the resume flow deterministic and inspectable.
3. Ensure it rebuilds active goals, current plan position, open loops, constraints, assumptions, and recent failure/recovery context where available.
4. Add a verification step that checks reconstructed state for broken references or expired items.
5. Keep the result compact and advisory.

Verification:
- Resume fixture suite passes.
- Missing-state and wrong-state metrics are recorded.
- No regression to durable-memory pollution.

Stop boundary:
- Do not yet widen public claims beyond what the tests prove.

### Tranche 8: Evaluation harness and baseline comparison hardening

Objective: make Phase 2 measurable and regression-safe.

Files:
- Modify: `scripts/current_state_baseline.py` only if Phase 2 metrics belong there
- Modify: `scripts/compare_current_state_baseline.py` if needed
- Create/update deterministic Phase 2 fixtures/scripts
- Modify: `examples/evals/current-state-baseline/` or an adjacent clearly named Phase 2 evaluation area
- Modify tests verifying metric schema if needed

Steps:
1. Add deterministic metrics for resume correctness, missing-state, wrong-state, typed-vs-flat token efficiency, and harvest routing quality.
2. Ensure artifacts can be rerun locally without hidden dependencies.
3. Compare typed implementation against current-state baseline.
4. Document what the evaluation proves and does not prove.
5. Keep compatibility allowances explicit if fixtures intentionally use legacy terms.

Verification:
- Evaluation commands run successfully.
- Baseline comparison shows no unexpected regressions.
- Metric schema tests pass.

Stop boundary:
- Do not yet edit broad README/posture text.

### Tranche 9: CLI/MCP/HTTP parity and docs/examples

Objective: finish the exposed interfaces and public-alpha docs so they match the landed typed behavior.

Files:
- Modify: `src/shyftr/cli.py`
- Modify: `src/shyftr/mcp_server.py`
- Modify: `src/shyftr/server.py`
- Modify: `docs/concepts/live-context-optimization-and-session-harvest.md`
- Modify: `docs/concepts/runtime-continuity-provider.md`
- Modify: `docs/runtime-context-optimization-example.md`
- Modify tests for CLI/MCP/HTTP parity

Steps:
1. Ensure typed live-context capture/pack/harvest semantics are exposed consistently across surfaces.
2. Keep carry/continuity aliases intact.
3. Document typed resume-state and carry-state behavior with synthetic/operator-safe examples.
4. Keep public wording honest: context optimization, bounded packs, resume support, no hard context-window overclaim.
5. Update examples to show typed fields and resumable carry-state.

Verification:
- CLI/MCP/HTTP tests pass.
- Read docs back and confirm they match actual syntax/behavior.
- Confirm no numeric context-window expansion claims were introduced.

Stop boundary:
- Do not yet prepare final landing packet.

### Tranche 10: Full verification and closeout artifact pass

Objective: run the full verification stack for the implementation before final review.

Files:
- Verification-only unless fixes are required
- Write repo-local closeout/status artifacts as needed

Steps:
1. Run compile, terminology, readiness, focused pytest, and any new evaluation commands.
2. Run the baseline harness and comparison commands required by the implementation.
3. Verify git diff hygiene and search for stale terminology where Phase 2 intentionally changed names.
4. Save a closeout artifact that records:
   - what changed;
   - what stayed compatible;
   - what evaluation passed;
   - what remains deferred to Phase 3+.

Verification:
- All required commands pass.
- Closeout artifact is read back.
- Deferred items are clearly listed.

Stop boundary:
- No commit/push until after review if the requested execution flow requires human approval first.

### Tranche 11: Final self-audit against roadmap/report/Phase 1 boundary

Objective: verify the finished Phase 2 implementation still matches the original request and did not widen scope.

Files:
- Review generated artifacts and changed implementation/doc/test files

Steps:
1. Compare landed behavior against the roadmap Phase 2 section.
2. Compare against the deep research recommendations actually in scope for Phase 2.
3. Confirm no Phase 3 memory-class implementation was accidentally shipped.
4. Confirm no destructive migration or alias-removal work slipped in.
5. Record must-fix and should-fix items before the human review tranche.

Verification:
- Produce a concise internal audit artifact or review note.
- Read it back and confirm it explicitly mentions preserved boundaries.

Stop boundary:
- No human-facing “complete” claim until this audit passes.

### Tranche 12: Human review packet and decision matrix

Objective: prepare the final approval bundle at the review boundary.

Files:
- Write: repo-local human review packet
- Possibly update: repo-local closeout packet

Packet contents should include:
1. Goal and scope recap.
2. Exact files changed.
3. Typed-state contract summary.
4. Compatibility map from current alpha names to canonical names.
5. Carry-state/checkpoint object summary.
6. Continuity behavior before vs after.
7. Harvest routing behavior before vs after.
8. Evaluation commands and results.
9. Baseline comparison summary.
10. Docs/examples updated.
11. Deferred Phase 3+ items.
12. Approve/revise/block decision checklist.

Verification:
- Read the packet back.
- Confirm it includes Phase 1 “not started” boundary and Phase 3 deferrals.

Stop boundary:
- Wait for approval before final landing actions if approval is required.

### Tranche 13: Optional post-approval landing actions

Objective: perform only the explicitly approved post-review actions.

Possible actions:
- final should-fix cleanup;
- final verification rerun;
- skill sync if skill text changed;
- commit;
- push;
- pass-off report.

Verification:
- exact commit SHA captured;
- remote SHA verified if pushed;
- final repo cleanliness confirmed;
- final pass-off report read back.

-------------------------------------------------------------------------------

## 9. Required verification commands

Run from `/Users/stefan/ShyftR`.

Core verification:
- `PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `python scripts/terminology_inventory.py --fail-on-public-stale`
- `python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `python scripts/public_readiness_check.py`
- `git diff --check`

Focused regression commands should include at minimum:
- `PYTHONPATH=.:src python -m pytest -q tests/test_live_context.py tests/test_session_harvest.py tests/test_continuity.py tests/test_cli.py tests/test_mcp_server.py tests/test_server.py`
- any new typed-state/resume/eval test files added by the implementation

Baseline/evaluation commands should include the current-state baseline plus any new Phase 2 evaluation commands added by the implementation:
- `python scripts/current_state_baseline.py --mode all`
- `python scripts/compare_current_state_baseline.py <before> <after> --markdown-out <path>`

If Phase 2 adds a dedicated evaluation script, it must be deterministic, local-first, and documented in the closeout artifact.

-------------------------------------------------------------------------------

## 10. Risks and pitfalls that must be encoded in execution

### Risk 1: Schema breakage for existing live-context rows

Mitigation:
- additive fields only;
- compatibility reader tests;
- no required destructive migration.

### Risk 2: Carry-state becomes bloated and defeats prompt reduction

Mitigation:
- explicit bounded checkpoint design;
- active/unresolved-state-first policy;
- token-budget tests.

### Risk 3: Continuity regression when typed carry support is added

Mitigation:
- parity regression proving current behavior is unchanged when no carry-state exists.

### Risk 4: Harvest silently changes old routing behavior

Mitigation:
- regression tests for current alpha kinds;
- explicit mapping table and fixture-based expected routing.

### Risk 5: Relationship graph bugs (cycles, orphans, stale references)

Mitigation:
- explicit validation;
- reject or flag invalid relations deterministically;
- resume verification step.

### Risk 6: Ambiguous status or TTL semantics

Mitigation:
- define canonical status values early;
- prefer explicit `valid_until`/TTL semantics;
- test expiry handling.

### Risk 7: Scope creep into Phase 3 memory-class work

Mitigation:
- keep typed working/context and carry-state framed as Phase 2 substrate work only;
- defer first-class durable memory classes explicitly.

### Risk 8: Over-engineered ontology before real evaluation proves value

Mitigation:
- keep the type system minimal and evidence-backed;
- expand only where deterministic fixtures show real gaps.

### Risk 9: Public/docs claims run ahead of proven implementation

Mitigation:
- docs updated only after tests/evals pass;
- closeout packet must say exactly what Phase 2 proves.

### Risk 10: Working-state pollution of durable memory

Mitigation:
- keep direct durable-memory writes policy-gated;
- prefer continuity feedback, candidates, and skill proposals over direct promotion.

-------------------------------------------------------------------------------

## 11. Definition of done for Phase 2

Phase 2 is complete only when all of the following are true:

1. A canonical typed working-state contract exists and is implemented.
2. Existing live-context alpha rows remain readable.
3. Capture surfaces accept typed state compatibly.
4. A compact carry-state/checkpoint object exists and is used in continuity/resume flows.
5. Continuity can incorporate typed carry-state without losing its current durable-memory behavior.
6. Harvest classifies typed entries correctly and predictably.
7. Typed retrieval/ranking is implemented and benchmarked against the prior heuristic behavior.
8. Resume correctness is measured with deterministic fixtures.
9. Baseline and focused regression gates pass.
10. Docs/examples match the landed behavior.
11. Deferred Phase 3+ items are explicitly documented.
12. Final review packet is ready and truthful.

-------------------------------------------------------------------------------

## 12. Explicitly deferred to Phase 3+

These items must remain deferred unless the operator explicitly broadens scope:
- first-class episodic memory objects;
- first-class semantic/procedural/resource/rule authority implementation;
- destructive migration tooling;
- alias-removal cleanup;
- hosted/multi-tenant platform claims;
- offline consolidation/sleep-time rehearsal pipelines beyond local Phase 2 fixtures;
- advanced retrieval-orchestration or external ANN/database upgrades.

-------------------------------------------------------------------------------

## 13. Execution handoff note

Plan complete and saved.

Recommended execution shape:
- controller-owned phased implementation in `/Users/stefan/ShyftR`;
- bounded helper/review lanes for read-only audits or final review only;
- no persistent swarm required by default;
- preserve file-backed artifacts and deterministic verification throughout.

If executed exactly as written, this phase should harden ShyftR's typed working-context and carry substrate without widening into Phase 3 memory-class work too early.
