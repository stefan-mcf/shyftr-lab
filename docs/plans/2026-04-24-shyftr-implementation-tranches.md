# ShyftR Fully Tranched Implementation Plan

## Strategic Product Definition

ShyftR should become the default modular memory substrate for agents.

Core product promise:

1. Capture evidence from agents, tools, docs, runtimes, and users.
2. Convert evidence into reviewable memory candidates.
3. Promote only reviewed, provenance-linked durable memory.
4. Retrieve bounded, role-labelled Packs for agent tasks.
5. Record Signal after use.
6. Learn from useful, harmful, ignored, missing, and over-retrieved memory.
7. Maintain trust through audit, challenge, replay, and review gates.
8. Expose the system through CLI, local HTTP API, and a minimal operator UI.

The MVP should not be "a vector store with notes". It should be:

A local-first agent memory control plane with:
- append-only ledger truth
- review-gated memory
- Pack generation
- Signal reporting
- memory health reporting
- extensive observability for optimization and audit
- minimal frontend inspection and review

Important source concepts:
- [Runtime-neutral pivot concept review](../sources/2026-05-05-shyftr-runtime-neutral-pivot-concept-review.md)
- [Compaction Intelligence Concept](../sources/2026-05-05-shyftr-compaction-intelligence-concept.md)

The compaction intelligence concept is a future product direction, but it should influence the near-term architecture now. ShyftR should be able to provide continuity-oriented Packs before a runtime compacts context, then learn from Compaction Signals after resumed work. This reinforces the main Pack -> Signal learning loop and strengthens ShyftR's role as a replacement-grade memory substrate rather than a passive store.

---

# Phase 0: Stabilisation and Repository Fixes

Goal: remove ambiguity, fix correctness risks, and make the current repo trustworthy before adding more feature surface.

## Tranche 0.1: Repo Reality Audit

### Objective
Produce a clean map of what is actually implemented versus what exists only in docs/plans.

### Tasks
1. Inventory all modules under `src/shyftr/`.
2. Inventory all tests under `tests/`.
3. Map current implemented surfaces:
   - CLI commands
   - local HTTP routes
   - provider API
   - adapter API
   - Pack/Loadout API
   - Signal/Outcome API
   - Sweep
   - Challenger
   - vector/Grid backends
   - front end status
4. Compare current implementation against:
   - main MVP plan
   - active-learning plan
   - runtime integration plan
   - memory-provider contract
5. Create `docs/status/current-implementation-status.md`.

### Acceptance Criteria
- Status doc separates:
  - implemented
  - partially implemented
  - planned
  - stale/deprecated
- Every public claim in README has a corresponding implementation or is marked planned.
- No ambiguity remains about what the current repo can actually do.

---

## Tranche 0.2: Test Suite Baseline and CI Gate

### Objective
Make test status non-negotiable before any new work.

### Tasks
1. Run full test suite locally:
   - `python -m pytest -q`
2. Add or repair GitHub Actions:
   - Python 3.11
   - Python 3.12
   - core tests without optional extras
   - optional tests skipped unless extras installed
3. Add a `make test` or `scripts/test.sh`.
4. Add `scripts/check.sh` for:
   - tests
   - import smoke
   - CLI smoke
   - demo flow
5. Add a README badge only after CI is genuinely passing.

### Acceptance Criteria
- CI runs on push and PR.
- CI passes on a clean clone.
- Optional LanceDB/FastAPI tests do not break default CI.
- New work cannot be considered complete unless CI passes.

---

## Tranche 0.3: Vocabulary and Ledger Compatibility Lock

### Objective
Resolve the split between legacy implementation names and public vocabulary.

Current code appears to use implementation names like:
- Source / Fragment / Trace / Loadout / Outcome

Public vocabulary wants:
- Pulse / Spark / Charge / Pack / Signal

### Tasks
1. Define a formal compatibility matrix:
   - Source = Pulse
   - Fragment = Spark
   - Trace = Charge
   - Loadout = Pack
   - Outcome = Signal
2. Add `docs/concepts/vocabulary-compatibility.md`.
3. Ensure all public docs use the power vocabulary.
4. Ensure code can keep legacy names internally without confusing external APIs.
5. API outputs should expose both where useful:
   - `charge_id`
   - `trace_id` as compatibility field
6. Add tests that confirm backwards compatibility.

### Acceptance Criteria
- Public docs no longer oscillate between names without explanation.
- External API consumers can use the public names.
- Existing tests using legacy names still pass.
- No destructive migration required.

---

## Tranche 0.4: Canonical Ledger Path Lock

### Objective
Stop ambiguity between `charges/approved.jsonl` and `traces/approved.jsonl`, and between `pulses/sparks` and `sources/fragments`.

### Tasks
1. Decide canonical write paths for MVP:
   - Prefer public paths:
     - `ledger/pulses.jsonl`
     - `ledger/sparks.jsonl`
     - `charges/approved.jsonl`
     - `ledger/signals.jsonl`
   - Or formally keep internal legacy paths and expose projection aliases.
2. Add a `ledger_paths.py` module with constants.
3. Replace hardcoded string paths across the codebase.
4. Add compatibility readers for old cells.
5. Add migration validation:
   - detects both old and new paths
   - reports duplicate canonical/legacy rows
   - never rewrites without explicit migration command

### Acceptance Criteria
- There is one authoritative path policy.
- New cells are deterministic.
- Old cells can still be read.
- Tests prove readers handle both old and new ledger locations.

---

## Tranche 0.5: Atomic Append and File Locking

### Objective
Make ShyftR safe for real runtime use where multiple agents/processes may write to the same cell.

### Tasks
1. Add file locking around append-only ledger writes.
2. Ensure `append_jsonl`:
   - acquires lock
   - writes one complete line
   - flushes
   - fsyncs
   - releases lock
3. Add corruption detection:
   - invalid JSONL line
   - partial final line
   - duplicate IDs
4. Add recovery mode:
   - read-only report
   - quarantine corrupt rows into a repair report
5. Add tests for concurrent appends.

### Acceptance Criteria
- Concurrent append test with N workers produces valid JSONL.
- No partial rows under simulated interruption.
- Corrupt ledger rows are reported, not silently ignored.
- Canonical ledgers remain append-only.

---

## Tranche 0.6: Schema Versioning and Migration Guard

### Objective
Prevent future schema changes from breaking existing cells.

### Tasks
1. Add `schema_version` to:
   - cell manifest
   - ledger records where appropriate
   - API responses
2. Add `shyftr validate-cell`.
3. Add `shyftr migrate --dry-run`.
4. Add migration manifest output:
   - current version
   - target version
   - required changes
   - risk level
5. Add tests for older fixture cells.

### Acceptance Criteria
- Every cell reports schema version.
- Migration dry-run is read-only.
- Validation catches missing ledgers, malformed rows, unknown schema versions.
- Existing demo cells remain valid.

---

## Tranche 0.7: Packaging, README, and Installation Repair

### Objective
Make the project installable and understandable.

### Tasks
1. Confirm `pyproject.toml` has correct dependencies.
2. Add extras:
   - `dev`
   - `service`
   - `lancedb`
   - `ui-dev` if needed later
3. Write README sections:
   - What ShyftR is
   - Boundaries and non-goals
   - Quickstart
   - CLI demo
   - local HTTP service
   - MVP status
   - safety/ledger model
4. Add `docs/demo.md` and keep it synchronized with actual commands.
5. Add `examples/`.

### Acceptance Criteria
- New user can clone, install, run demo, and understand the architecture.
- README does not overclaim production readiness.
- All docs commands are tested or smoke-tested.

---

# Phase 1: Closed-Loop Engine MVP

Goal: finish the backend MVP as a reliable, heavily tested, observable local-first memory engine before building a larger UI. Phase 1 should make ShyftR usable through CLI/API and ready for the first bounded managed-memory replacement pilot.

## Tranche 1.1: Provider API Completion

### Objective
Make the provider API the stable programmatic surface.

### Required Provider Operations
1. `remember`
2. `remember_trusted`
3. `search`
4. `profile`
5. `pack`
6. `record_signal`
7. `forget`
8. `replace`
9. `deprecate`
10. `export_snapshot`
11. `import_snapshot`

### Tasks
1. Add/complete `MemoryProvider`.
2. Ensure every operation returns:
   - stable ID
   - status
   - provenance
   - warnings
   - schema version
3. Make provider operations call existing core modules.
4. Add provider tests independent of CLI.

### Acceptance Criteria
- External Python code can use ShyftR without shelling out.
- Provider API covers the full MVP lifecycle.
- Provider API does not bypass review or ledger rules.

---

## Tranche 1.2: Runtime Pack API Hardening

### Objective
Freeze the JSON contract used by external runtimes.

### Tasks
1. Finalize `RuntimeLoadoutRequest`.
2. Finalize `RuntimeLoadoutResponse`.
3. Ensure response includes:
   - pack/loadout ID
   - selected IDs
   - guidance items
   - caution items
   - background items
   - conflict items
   - score traces
   - trust labels
   - provenance references
   - token estimate
4. Add compatibility aliases:
   - Pack = Loadout
   - Charge = Trace
5. Add JSON schema docs.

### Acceptance Criteria
- Same request produces deterministic output against same cell state.
- Response is usable by an external agent without extra parsing.
- Every item has a reason for selection.

---

## Tranche 1.3: Runtime Signal API Hardening

### Objective
Make runtime feedback structured enough to drive learning.

### Tasks
1. Finalize `RuntimeOutcomeReport`.
2. Support:
   - success
   - failure
   - partial
   - abandoned
   - unknown
3. Support memory feedback:
   - applied
   - useful
   - harmful
   - ignored
   - contradicted
   - over-retrieved
   - missing
4. Require:
   - pack ID
   - task ID
   - runtime ID
   - actor/source identity
5. Append Signal/Outcome records.
6. Generate missing-memory candidates from missing entries.

### Acceptance Criteria
- Signal can be linked back to Pack retrieval logs.
- Useful/harmful/missing feedback is persisted.
- Missing memory does not bypass review.

---

## Tranche 1.4: Pack Compiler MVP

### Objective
Move Pack output from “retrieved list” to “agent-ready memory packet”.

### Pack Sections
1. Mission-relevant guidance
2. Known failure signatures
3. Caution / anti-patterns
4. Verification heuristics
5. Constraints and preferences
6. Conflicts and unresolved risks
7. Suggested next check

### Tasks
1. Add `PackCompiler`.
2. Convert selected retrieval items into structured Pack sections.
3. Keep provenance for every section.
4. Enforce token budget.
5. Add compiler modes:
   - conservative
   - balanced
   - exploratory
   - audit
6. Add tests with fixed fixtures.

### Acceptance Criteria
- Pack is directly consumable by an agent prompt.
- Guidance and caution are clearly separated.
- Compiler never invents unbacked memory.
- Output remains deterministic.

---

## Tranche 1.5: Pack-Miss Learning MVP

### Objective
Teach ShyftR when retrieved memory was not useful.

### Tasks
1. Compare each Signal against its Pack.
2. Derive miss categories:
   - not_relevant
   - not_actionable
   - contradicted
   - duplicative
   - unknown
3. Track over-retrieval separately from harmful memory.
4. Add reports:
   - most missed Charges
   - high-confidence missed Charges
   - over-retrieved Charges
   - mixed-signal Charges
5. Ensure a single miss does not automatically reduce global confidence.

### Acceptance Criteria
- Loaded-but-unused memory becomes measurable.
- Relevance can improve without treating every miss as false memory.
- Miss reports are visible through CLI/API.

---

## Tranche 1.6: Confidence Events MVP

### Objective
Turn Signal into append-only confidence evolution.

### Tasks
1. Add confidence event schema:
   - increase
   - decrease
   - no_change
   - manual_review_required
2. Record event source:
   - signal
   - sweep
   - audit
   - manual review
3. Derive current confidence projection from event history.
4. Do not rewrite original Charge confidence.
5. Add tests for:
   - useful applied memory
   - harmful applied memory
   - missed memory
   - contradictory memory

### Acceptance Criteria
- Confidence is replayable from ledgers.
- Useful Signals can raise confidence.
- Harmful Signals can lower confidence.
- Misses influence retrieval affinity before confidence.

---

## Tranche 1.7: Retrieval Affinity Events MVP

### Objective
Separate false-memory judgments from task-specific usefulness judgments.

### Tasks
1. Add retrieval affinity event ledger.
2. Track:
   - query text
   - query tags
   - task kind
   - selected IDs
   - used IDs
   - missed IDs
3. Add affinity adjustment projection.
4. Use affinity in hybrid scoring.
5. Add tests for repeated over-retrieval.

### Acceptance Criteria
- Repeated misses reduce retrieval affinity for similar queries.
- Confidence remains separate from relevance.
- Pack quality improves without destructive mutation.

---

## Tranche 1.8: Local HTTP Service Hardening

### Objective
Make the existing local service a reliable backend for the MVP front end.

The current server already exposes local endpoints for validate, ingest, pack, signal, proposals, and health while keeping the CLI as the primary interface and avoiding a second truth path :contentReference[oaicite:1]{index=1}.

### Tasks
1. Add endpoints:
   - `GET /cells`
   - `GET /cell/{id}/status`
   - `GET /cell/{id}/sparks`
   - `POST /cell/{id}/spark/{id}/approve`
   - `POST /cell/{id}/spark/{id}/reject`
   - `GET /cell/{id}/charges`
   - `GET /cell/{id}/hygiene`
   - `GET /cell/{id}/sweep`
   - `POST /cell/{id}/pack`
   - `POST /cell/{id}/signal`
2. Add consistent error schema.
3. Add request IDs.
4. Add localhost-only default.
5. Add CORS config only for local UI.
6. Add OpenAPI docs.

### Acceptance Criteria
- Front end can run entirely through local HTTP API.
- API never writes outside explicit commands.
- Errors are structured and recoverable.
- Service remains optional.

---

## Tranche 1.9: Replacement Readiness, Observability, and Test Harness

### Objective
Make ShyftR functional enough to replace a managed agent-memory backend for a bounded pilot domain as soon as possible, with robust tests, replay evidence, rollback, and detailed logging before authority is expanded.

This tranche is the first explicit replacement-readiness gate. It should be completed before treating ShyftR as a primary memory provider for any real runtime domain.

### Tasks
1. Add a replacement-readiness test harness covering:
   - remember / search / profile / pack / signal lifecycle;
   - import/export snapshot round trip;
   - repeated Pack generation from the same Cell state;
   - missing-memory feedback;
   - harmful and contradicted memory feedback;
   - stale-memory exclusion;
   - rollback to prior backend/export state.
2. Add replay fixtures that simulate an existing managed memory backend migration:
   - exported memories;
   - task closeouts;
   - user/project preferences;
   - noisy operational state that must be rejected;
   - repeated successful and failed Pack applications.
3. Add structured observability for optimization:
   - request ID;
   - cell ID;
   - runtime ID;
   - operation name;
   - selected Charge IDs;
   - scoring components;
   - Pack token estimate;
   - Signal linkage;
   - confidence / affinity event IDs;
   - warnings and Regulator decisions;
   - latency and error class.
4. Add CLI/API access to diagnostic logs and replay reports.
5. Add regression tests for replacement-critical behavior:
   - no ledger write bypass;
   - deterministic Pack compilation;
   - provenance on every Pack section;
   - review-gated promotion;
   - fallback/export path preserved;
   - no secret or operational-state promotion.
6. Add a replacement-readiness report command, for example `shyftr readiness --replacement-pilot`, that returns pass/fail with blocking reasons.
7. Document the first functional replacement runbook:
   - shadow import;
   - advisory Pack comparison;
   - bounded-domain primary mode;
   - fallback mode;
   - rollback/archive procedure.

### Acceptance Criteria
- Full replacement-readiness test suite passes locally and in CI.
- A replay fixture proves ShyftR can ingest exported managed-memory records, produce Packs, record Signals, and update confidence without losing provenance.
- Diagnostic logs can explain why every Pack item was selected or excluded.
- Replacement-readiness report clearly says whether ShyftR is safe for bounded-domain primary memory.
- Existing memory backend remains available as fallback/archive during the first replacement pilot.
- This tranche does not require the front end; CLI and local HTTP API are sufficient for the first replacement checkpoint.

---

## Runtime Memory Integration Checkpoints

These checkpoints define when ShyftR should begin attaching to a real target runtime and how strongly it should influence memory authority. They are deliberately progressive: observe first, advise second, replace only after validation. Named runtimes and legacy memory systems belong in adapter notes or source references; the main plan stays runtime-neutral.

### Checkpoint A: after Tranche 1.3 — read-only / shadow mode

Begin the earliest safe runtime integration after:

- Tranche 1.1: Provider API Completion
- Tranche 1.2: Runtime Pack API Hardening
- Tranche 1.3: Runtime Signal API Hardening

At this point, ShyftR can sit beside a target runtime without controlling execution or memory authority.

Connect ShyftR to:

- target runtime task IDs
- bounded-domain or component names
- worker/actor role
- task summary
- completion closeouts
- review outcomes
- success/failure labels

Rules:

- Do not replace the existing memory backend yet.
- Do not inject ShyftR output as authoritative memory yet.
- Use this stage to answer: “Can ShyftR observe a real runtime and produce useful Packs without breaking anything?”

### Checkpoint B: after Tranche 1.5 — advisory Pack injection

Begin advisory integration after:

- Tranche 1.4: Pack Compiler MVP
- Tranche 1.5: Pack-Miss Learning MVP

At this point, ShyftR becomes useful enough to feed bounded runtime domains, but it is still not the main memory provider.

Where to plug it in:

- Add ShyftR at the planning, orchestration, or bounded-domain manager boundary first.
- Start with a small set of functional domains such as development, documentation, and review/QA.
- Avoid plugging directly into every low-level worker immediately.
- Prefer a higher-context manager layer first because it has more context and fewer noisy task events.

Rules:

- ShyftR Packs may be injected as advisory context.
- Managers should label ShyftR material as advisory.
- The existing memory backend remains primary during this checkpoint.
- Pack misses and over-retrieval should be measured before expanding scope.

### Checkpoint C: after Tranche 1.9 plus controlled replay — first managed-memory replacement checkpoint

This is the earliest point where ShyftR may functionally replace a managed agent-memory backend for a bounded pilot domain.

Consider bounded-domain primary memory only after:

- Tranche 1.6: Confidence Events MVP
- Tranche 1.7: Retrieval Affinity Events MVP
- Tranche 1.8: Local HTTP Service Hardening
- Tranche 1.9: Replacement Readiness, Observability, and Test Harness
- a controlled replay or pilot harness has passed the replacement-readiness report

At this point, ShyftR has:

- stable Pack API
- stable Signal API
- memory feedback loop
- retrieval-affinity learning
- confidence evolution
- local HTTP service
- structured observability and diagnostic logs
- replacement-readiness tests and replay fixtures
- fallback/export path for rollback
- separation between “false memory” and “not relevant for this task”

Replacing a memory backend changes memory authority, not storage location alone.

Rules:

- Start with bounded-domain memory, not runtime-wide memory authority.
- Keep the existing memory backend as fallback/archive during the first bounded-domain replacement pass.
- Require Signal reporting for every ShyftR-influenced runtime task.
- Require diagnostic logs for every Pack, Signal, confidence event, and retrieval-affinity event.
- Require review of harmful, contradicted, or repeatedly ignored memory before expanding authority.
- Functional replacement can begin here without waiting for the Phase 2 front end, provided CLI/API readiness checks pass.

### Checkpoint D: after bounded-domain pilot success — runtime-wide memory authority

Only after bounded-domain memory pilots show stable Pack quality, useful Signals, bounded operator burden, and recoverable failure modes should ShyftR become the primary durable memory provider for a whole runtime.

Replacement sequence:

1. Stage A: existing backend primary, ShyftR shadow.
2. Stage B: existing backend primary, ShyftR advisory Pack injected.
3. Stage C: ShyftR primary for bounded-domain memory, existing backend fallback.
4. Stage D: ShyftR primary for runtime-wide memory, existing backend disabled or archive-only.

Rules:

- Do not hard-swap immediately.
- Preserve rollback by keeping existing backend export/archive available until ShyftR has passed replay and audit checks.
- ShyftR must be able to explain which Charges influenced a Pack and which Signals updated them.
- Runtime-wide memory replacement requires explicit operator approval after pilot metrics are reviewed.

---

# Replacement Readiness Cut Line

ShyftR is ready to begin the first functional managed-memory replacement pilot when:

1. Phase 1 through Tranche 1.9 is complete.
2. Full test suite and CI pass.
3. Replacement-readiness replay passes.
4. Pack and Signal APIs are stable enough for a bounded runtime domain.
5. Diagnostic logs can explain Pack selection, exclusion, Signal linkage, confidence updates, and retrieval-affinity changes.
6. Existing backend export/archive remains available for rollback.
7. Operator explicitly approves bounded-domain primary memory mode.

This cut line is intentionally before the Phase 2 front end. The front end improves usability and inspection, but the first replacement milestone should be reachable through robust CLI/API workflows so ShyftR can start replacing managed agent-memory backends as soon as the backend is trustworthy.

---

# Phase 2: MVP Front End / ShyftR Control Console

Goal: build the smallest useful UI for inspecting and operating the memory system.

## MVP Front End Positioning

The front end should not be a full product workspace yet.

It should be a local operator console with:
- cell dashboard
- ingestion view
- Spark review queue
- Charge explorer
- Pack debugger
- Signal viewer
- hygiene/sweep reports
- proposal review

Preferred stack:
- React + TypeScript
- Vite
- Tailwind or minimal CSS
- Local HTTP API backend
- Later wrapped in Tauri if desired

## Tranche 2.1: Front End Scaffold

### Objective
Create a minimal local web UI.

### Tasks
1. Add `apps/console/`.
2. Set up:
   - React
   - TypeScript
   - Vite
   - local API client
3. Add environment config:
   - `SHYFTR_API_URL=http://127.0.0.1:8014`
4. Add simple navigation:
   - Cells
   - Review
   - Charges
   - Packs
   - Signal
   - Reports
   - Settings
5. Add test/build scripts.

### Acceptance Criteria
- `npm install && npm run dev` starts console.
- Console can call `/health`.
- Frontend lives outside core package.
- No core Python dependency on UI.

---

## Tranche 2.2: Cell Dashboard

### Objective
Give the user a live overview of a selected Cell.

### Dashboard Cards
1. Pulse count
2. Spark count
3. Pending review count
4. Approved Charge count
5. Signals recorded
6. Open proposals
7. Hygiene warnings
8. Grid status

### Tasks
1. Add backend cell summary endpoint.
2. Add dashboard UI.
3. Add empty-state UX.
4. Add refresh button.
5. Add JSON inspect toggle.

### Acceptance Criteria
- User can select a Cell and see memory health.
- Dashboard numbers match ledger counts.
- JSON inspect helps debugging.

---

## Tranche 2.3: Ingestion Console

### Objective
Allow local file/adapter ingestion through UI.

### Tasks
1. Add adapter config selector.
2. Add dry-run discover.
3. Show discovered sources:
   - path
   - kind
   - hash
   - already ingested
   - rejected
4. Add ingest button.
5. Show ingestion result.

### Acceptance Criteria
- User can validate config.
- User can dry-run before ingestion.
- User can ingest from UI.
- Ingested sources appear in Cell dashboard.

---

## Tranche 2.4: Spark Review Queue

### Objective
Make review gates usable without CLI.

### UI Features
1. Pending Sparks table
2. Spark detail pane
3. Source excerpt
4. Tags/kind/confidence
5. Boundary/regulator status
6. Approve
7. Reject
8. Split proposal
9. Merge proposal
10. Review rationale field

### Tasks
1. Add review queue API endpoints.
2. Add review queue UI.
3. Require rationale before approval/rejection.
4. Add keyboard shortcuts later if useful.
5. Add filters:
   - pending
   - approved
   - rejected
   - boundary failed
   - kind
   - tag

### Acceptance Criteria
- User can approve/reject Sparks from UI.
- Every review writes append-only event.
- UI does not mutate Spark rows directly.
- Review queue is usable for real pilot work.

---

## Tranche 2.5: Charge Explorer

### Objective
Inspect durable memory.

### UI Features
1. Charge table
2. Search
3. Filter by:
   - kind
   - confidence
   - status
   - tag
   - source
4. Detail pane:
   - statement
   - rationale
   - provenance
   - review history
   - Signal history
   - confidence events
   - related misses
5. Actions:
   - deprecate
   - forget
   - replace
   - challenge
   - export JSON

### Acceptance Criteria
- User can inspect why a Charge exists.
- Provenance chain is visible.
- Lifecycle actions append events only.
- Deprecated/forgotten/replaced state is clear.

---

## Tranche 2.6: Pack Debugger

### Objective
Let users understand why ShyftR retrieved a Pack.

### UI Features
1. Query input
2. Task kind/tags
3. Mode:
   - conservative
   - balanced
   - exploratory
   - audit
4. Result sections:
   - guidance
   - caution
   - background
   - conflict
5. Score trace display
6. Suppressed items display
7. Token budget display
8. Copy Pack JSON
9. Copy agent prompt version

### Acceptance Criteria
- User can simulate Pack generation.
- Every selected item has score explanation.
- Suppressed/caution items are visible.
- Pack output can be copied into an agent.

---

## Tranche 2.7: Signal Console

### Objective
Record and inspect task outcomes.

### UI Features
1. Select Pack ID
2. Select outcome:
   - success
   - failure
   - partial
   - abandoned
3. Mark items:
   - applied
   - useful
   - harmful
   - ignored
   - contradicted
   - over-retrieved
4. Add missing memory text.
5. Add verification evidence.
6. Submit Signal.
7. Show derived misses.

### Acceptance Criteria
- User can record Signal from UI.
- Signal links to Pack.
- Derived miss report appears after submit.
- Missing memory becomes candidate, not approved memory.

---

## Tranche 2.8: Hygiene and Sweep Reports UI

### Objective
Make memory health operationally visible.

### UI Features
1. Hygiene report summary
2. Duplicate Charges
3. Conflicting Charges
4. Missing references
5. Most missed Charges
6. Over-retrieved Charges
7. Mixed-signal Charges
8. Sweep dry-run proposals

### Acceptance Criteria
- Reports are readable without opening JSON.
- Raw JSON remains available.
- Reports are read-only unless user explicitly writes proposals.

---

## Tranche 2.9: Proposal Review UI

### Objective
Review advisory proposals from Sweep/Challenger/runtime exports.

### UI Features
1. Proposal inbox
2. Proposal types:
   - confidence increase/decrease
   - retrieval affinity decrease
   - manual review
   - split candidate
   - supersession candidate
   - isolation candidate
3. Evidence view
4. Accept/reject/defer
5. Rationale required

### Acceptance Criteria
- Proposals are reviewable.
- Accepted proposals append review/decision events.
- UI never silently changes memory authority.

---

## Tranche 2.10: MVP Demo Script and Frontend Walkthrough

### Objective
Make the product demonstrable.

### Demo Flow
1. Start backend service.
2. Open console.
3. Create/select Cell.
4. Ingest demo evidence.
5. Review Sparks.
6. Promote Charge.
7. Generate Pack.
8. Record Signal.
9. View hygiene/Sweep output.
10. Export proposals.

### Acceptance Criteria
- Demo works from clean clone.
- Demo is documented in README.
- Demo is covered by smoke tests where practical.

---

# MVP Cut Line

MVP is complete when:

1. Core test suite passes.
2. CI passes.
3. Cell layout and ledgers are stable.
4. Provider API supports full lifecycle.
5. Local HTTP API supports front end.
6. Front end supports:
   - dashboard
   - ingest
   - review queue
   - Charge explorer
   - Pack debugger
   - Signal console
   - hygiene/sweep reports
7. End-to-end demo works:
   - Pulse -> Spark -> Review -> Charge -> Pack -> Signal -> Report
8. ShyftR can be attached to one real internal runtime.
9. No memory write bypasses Regulator and append-only ledgers.
10. Product is clearly labelled as controlled pilot, not broad production.
11. Replacement-readiness logs and replay reports remain available for optimization beyond the first backend replacement milestone.

---

# Phase 3: Controlled Real-World Pilot

Goal: prove ShyftR with actual runtime traffic.

## Tranche 3.1: Runtime Adapter / Pilot Harness

### Objective
Attach ShyftR to one real or simulated target runtime through the runtime-neutral integration contract.

### Tasks
1. Define adapter config for target runtime closeouts or pilot-harness task records.
2. Ingest:
   - task closeouts
   - actor/worker summaries
   - review outcomes
   - failure reports
   - proposal decisions
3. Ensure operational state is rejected or isolated.
4. Generate Packs for future tasks.
5. Record Signal after task completion.
6. Keep named-runtime mapping in adapter config or source notes, not the core plan.

### Acceptance Criteria
- The target runtime or pilot harness can request Pack before task.
- The target runtime or pilot harness can report Signal after task.
- ShyftR learns from real or replayable task outcomes.
- Operational queue state does not become durable memory.

---

## Tranche 3.2: Pilot Metrics

### Objective
Measure whether ShyftR is actually useful.

### Metrics
1. Pack application rate
2. Useful Charge rate
3. Harmful Charge rate
4. Ignored Charge rate
5. Over-retrieval rate
6. Missing-memory rate
7. Review approval rate
8. Proposal acceptance rate
9. Time saved per task
10. Task failure reduction

### Acceptance Criteria
- Metrics visible in UI.
- Metrics export as JSON/CSV.
- Pilot can answer: “Is ShyftR improving agent performance?”

---

## Tranche 3.3: Operator Burden Report

### Objective
Measure review cost.

### Tasks
1. Track:
   - pending Sparks
   - pending proposals
   - average review time
   - stale review items
   - rejected item ratio
2. Add review workload dashboard.
3. Add “review pressure” score.

### Acceptance Criteria
- You can see whether ShyftR creates too much review overhead.
- Review queue does not silently grow without reporting.

---

## Tranche 3.4: Policy Tuning Pass

### Objective
Tune Regulator rules based on pilot evidence.

### Tasks
1. Identify common false rejections.
2. Identify common false approvals.
3. Adjust pollution rules.
4. Add policy regression fixtures.
5. Add import sensitivity fields.

### Acceptance Criteria
- Regulator precision improves.
- Policy changes are regression-tested.
- Operational state remains rejected.

---

# Phase 4: Active Learning and Self-Correction

Goal: make ShyftR visibly self-learning while preserving review-gated memory authority.

## Execution Rule for `/goal`: Phase 4 to next major checkpoint

A `/goal` runner may proceed autonomously from Tranche 4.1 through the Phase 5 durability checkpoint if every tranche gate below passes.

Stop at the **Phase 5 durability checkpoint** after Tranche 5.5 is committed, verified, and the repo is clean. Do not start Phase 6 without a new instruction because Phase 6 introduces multi-Cell intelligence and cross-boundary memory behavior.

Only stop earlier for: failing tests that cannot be resolved, dependency/auth failure, unclear destructive migration risk, a violated Cell-ledger authority boundary, or a reviewer gate that returns blocking issues.

Global execution rules:

- Use tranche-sized commits; do not bundle Phase 4.2+ work into the Tranche 4.1 commit.
- Treat all active-learning outputs as append-only proposals, audit Sparks, or review events until explicit review applies authority.
- Deduplicate proposals against decision-folded open proposal projections, not raw proposal rows.
- Preserve Cell ledgers as canonical truth; Grid/API/UI/Sweep/Challenger are projections or delegated append-only writers.
- Run the stated gate before each tranche commit, then run the phase gate before crossing from Phase 4 to Phase 5.

## Tranche 4.1: Sweep Proposal Engine

### Objective
Turn read-only Sweep reports into reviewable append-only proposals.

### Proposal Types
1. Confidence increase
2. Confidence decrease
3. Retrieval affinity decrease
4. Manual review required
5. Split candidate
6. Supersession candidate
7. Deprecation candidate

### Tasks
1. Add a Sweep proposal generation path that reads existing Sweep/hygiene output and writes proposals to an append-only proposal ledger.
2. Generate stable proposal identifiers from proposal type, target Charge/Spark, and evidence fingerprint.
3. Fold latest `ledger/proposal_decisions.jsonl` decisions before determining whether a proposal is open.
4. Deduplicate only against decision-folded open proposals.
5. Add tests for all supported proposal types where practical.

### Gate before commit
- Duplicate open proposal is not re-emitted.
- Accepted proposal no longer counts as open and can be re-proposed only if new evidence/fingerprint changes.
- Rejected proposal no longer counts as open and can be re-proposed only if new evidence/fingerprint changes.
- Deferred proposal remains reviewable and blocks duplicate open emission.
- Proposal generation does not change Charge confidence, lifecycle status, retrieval affinity, or Pack output directly.
- `python3 -m pytest tests/test_console_api.py tests/test_server.py -q` passes.
- Focused Sweep/proposal tests pass.

### Acceptance Criteria
- Sweep proposals are append-only.
- Duplicate open proposals are deduped.
- Proposals require review before authority changes.
- Commit message: `feat: add sweep proposal engine`.

---

## Tranche 4.1G: Proposal Review Regression Gate

### Objective
Make proposal state safe enough for the rest of Phase 4.

### Tasks
1. Add or extend fixtures for proposal decisions: accept, reject, defer, missing rationale, duplicate open, and stale decision records.
2. Verify proposal inbox, metrics, dashboard open counts, and CSV/export metrics all use decision-folded status.
3. Add a no-direct-authority-change regression test around proposal acceptance.
4. Confirm UI/API proposal decisions append to `ledger/proposal_decisions.jsonl` only.

### Gate before commit
- Missing rationale returns validation failure.
- Accept/reject/defer append decision events without rewriting proposal records.
- Accepted/rejected proposals are absent from open proposal counts.
- Deferred proposals remain visible as reviewable.
- Proposal acceptance does not mutate `traces/approved.jsonl`, `charges/approved.jsonl`, confidence events, lifecycle events, or Grid files.
- Full Python suite passes: `python3 -m pytest -q`.
- Console build passes: `cd apps/console && npm run build`.

### Acceptance Criteria
- Proposal review state is decision-folded everywhere used by Phase 4.
- The implementation can safely proceed to Challenger without ambiguous proposal status.
- Commit message: `test: harden proposal review gates`.

---

## Tranche 4.2: Challenger Audit Loop

### Objective
Add adversarial memory review.

### Tasks
1. Rank high-impact Charges by confidence, Pack frequency, useful/harmful Signal history, and recency.
2. Search local Cell evidence for counter-evidence.
3. Classify findings:
   - direct contradiction
   - supersession
   - scope exception
   - temporal update
   - environment-specific
   - ambiguous
4. Emit audit Sparks or Challenger proposals for review.
5. Add UI/API review path only as projection plus append-only decisions.

### Gate before commit
- Known contradiction fixture produces an audit Spark/proposal.
- Ambiguous evidence remains reviewable and does not demote memory.
- Challenger emits no direct delete, demote, isolate, replace, or supersede mutation.
- Audit Sparks/proposals preserve source Charge IDs and evidence provenance.
- Existing proposal decision folding remains intact.
- Focused Challenger tests pass.
- `python3 -m pytest tests/test_console_api.py tests/test_server.py -q` passes.

### Acceptance Criteria
- Challenger catches known contradiction fixtures.
- False positives are reviewable.
- No Charge is automatically deleted or demoted.
- Commit message: `feat: add challenger audit loop`.

---

## Tranche 4.3: Isolation and Challenge Workflow

### Objective
Contain risky memory without destroying provenance.

### Tasks
1. Add lifecycle events:
   - challenged
   - isolation_candidate
   - isolated
   - restored
2. Update retrieval:
   - challenged appears with warning
   - isolation candidates excluded from normal guidance unless explicitly requested
   - isolated guidance excluded from normal Packs
   - audit mode can include all with warnings
3. Add UI controls that append lifecycle/review events through existing mutation paths.
4. Add tests for normal Pack exclusion and audit-mode inclusion.

### Gate before commit
- Challenged Charges still retain full provenance.
- Isolation candidates and isolated Charges are excluded from normal guidance Packs.
- Audit mode includes challenged/isolated items only with warning metadata.
- Restored lifecycle event makes restored item eligible again according to policy.
- No lifecycle path rewrites or deletes original Charge records.
- Focused retrieval/lifecycle tests pass.
- Full Python suite passes: `python3 -m pytest -q`.

### Acceptance Criteria
- Risky memory can be contained.
- Containment is append-only.
- Normal Packs do not include isolated guidance.
- Commit message: `feat: add isolation challenge workflow`.

---

## Tranche 4.4: Memory Conflict Arbitration

### Objective
Move from “conflict detected” to “conflict resolved into scoped doctrine”.

### Tasks
1. Detect conflicting Charges.
2. Determine likely conflict cause:
   - context mismatch
   - temporal update
   - tool version difference
   - agent preference difference
   - domain-specific exception
3. Propose:
   - split by scope
   - supersession
   - combined rule
   - keep both with conditions
4. Add review UI/API projection for conflict proposals.

### Gate before commit
- Conflict fixture produces actionable proposal(s) with both evidence chains attached.
- Temporal update and scope-exception fixtures do not overwrite older memory silently.
- Supersession proposal does not apply lifecycle changes until reviewed.
- Split/combined-rule proposals preserve source Charge IDs.
- No silent overwrite of Charge text, scope, confidence, or lifecycle state.
- Focused conflict arbitration tests pass.
- Console build passes if UI changed.

### Acceptance Criteria
- Conflicts become actionable proposals.
- Resolution preserves both evidence chains.
- No silent overwrite.
- Commit message: `feat: add memory conflict arbitration`.

---

## Phase 4 Gate: Active-Learning Authority Review

### Objective
Verify Phase 4 is complete before durability work starts.

### Required checks
```bash
python3 -m pytest tests/test_console_api.py tests/test_server.py -q
python3 -m pytest -q
cd apps/console && npm run build && npm audit --omit=dev
cd /Users/stefan/ShyftR && git diff --check
```

### Required review evidence
- Sweep, Challenger, isolation, and conflict workflows are append-only or projection-only until review.
- Proposal counts and metrics fold latest decisions.
- Normal Packs exclude isolated guidance.
- Audit mode includes risky guidance only with warnings.
- No new canonical store exists outside Cell ledgers.
- Reviewer verdict: PASS required before Phase 5.

### Phase 4 closeout commit
If final gate fixes/docs are needed, commit them with: `chore: pass active learning authority gate`.

---

# Phase 5: Scale, Backup, and Durability

Goal: make ShyftR trustworthy as a long-lived memory substrate.

Recommended autonomous order: 5.1, 5.3, 5.4, 5.5, then 5.2 only if lightweight optional-vector dependency risk remains bounded. If 5.2 requires a heavy native dependency or unclear provider choice, stop after 5.5 and leave 5.2 as an explicit follow-up.

## Tranche 5.1: Grid Metadata and Staleness

### Objective
Make indexes auditable and rebuildable.

### Tasks
1. Store Grid metadata:
   - backend
   - embedding model
   - embedding version
   - dimensions
   - ledger hashes
   - ledger offsets
   - created_at
2. Add `grid status`.
3. Add stale detection.
4. Add `grid rebuild`.

### Gate before commit
- Grid metadata records ledger offsets/hashes sufficient to detect staleness.
- `grid status` distinguishes fresh, stale, missing, and rebuild-required states.
- `grid rebuild` can rebuild from Cell ledgers without treating Grid as truth.
- Tampering with ledger content or offset makes Grid status stale/rebuild-required.
- Focused Grid tests pass.
- Existing Pack/retrieval tests pass.

### Acceptance Criteria
- User can see if retrieval index is stale.
- Index can be rebuilt from ledgers.
- Grid is never canonical truth.
- Commit message: `feat: add grid metadata and staleness`.

---

## Tranche 5.2: Disk-Backed Vector Adapter

### Objective
Scale beyond in-memory vector search with one optional local backend.

### Options
1. SQLite-vec
2. LanceDB
3. Qdrant later

### MVP Choice
Implement one optional local backend first only if it does not make the default install heavy or fragile.

### Gate before commit
- Default install and default tests do not require the optional vector backend.
- Optional backend dependency is isolated behind an extra or feature flag.
- Backend files live under Cell `grid/`.
- Rebuild path works from ledgers.
- If optional dependency installation fails or requires system-specific native setup, stop and document 5.2 as deferred rather than blocking the Phase 5 durability checkpoint.
- Default full Python suite passes without optional backend installed.
- Optional backend tests pass when the dependency is available, or are skipped with an explicit reason.

### Acceptance Criteria
- Default install does not require heavy vector backend.
- Optional backend passes tests when installed.
- Backend files live under Cell `grid/`.
- Rebuild path works.
- Commit message: `feat: add optional disk backed vector adapter`.

---

## Tranche 5.3: Backup and Restore

### Objective
Make Cells portable and recoverable.

### Tasks
1. Add `shyftr backup`.
2. Add `shyftr restore`.
3. Include:
   - ledgers
   - config
   - schema version
   - optional indexes or rebuild instructions
4. Add integrity manifest.
5. Add restore validation.

### Gate before commit
- Backup includes ledgers, manifest/config, schema/version metadata, and rebuild instructions for non-canonical indexes.
- Restore into a new path validates successfully.
- Restored Cell produces equivalent key counts and passes Cell validation.
- Restore does not overwrite an existing Cell unless an explicit force flag exists and is tested.
- Backup excludes transient caches/build artifacts unless explicitly documented.
- Focused backup/restore tests pass.
- Full Python suite passes: `python3 -m pytest -q`.

### Acceptance Criteria
- Cell backup can be restored elsewhere.
- Restored Cell passes validation.
- Indexes can be rebuilt.
- Commit message: `feat: add cell backup and restore`.

---

## Tranche 5.4: Tamper-Evident Ledger Hash Chains

### Objective
Add cryptographic trust to ledgers.

### Tasks
1. Add per-row hash.
2. Add previous-row hash.
3. Add ledger head manifest.
4. Add `shyftr verify-ledger`.
5. Add optional signed review events later.

### Gate before commit
- Ledger verification report is deterministic.
- Appending valid rows advances the hash chain.
- Modifying a historical row is detected.
- Removing or reordering rows is detected.
- Existing Cells can adopt hash-chain manifests through an explicit migration/adoption command or documented compatibility path.
- Verification does not mutate ledgers unless an explicit adoption command is invoked.
- Focused ledger verification tests pass.
- Backup/restore tests still pass.

### Acceptance Criteria
- Ledger tampering is detectable.
- Verification report is deterministic.
- Existing cells can adopt hash chains through migration.
- Commit message: `feat: add tamper evident ledger verification`.

---

## Tranche 5.5: Privacy and Sensitivity Scoping

### Objective
Prevent memory leakage across users, projects, agents, or domains.

### Tasks
1. Add sensitivity fields:
   - public
   - internal
   - private
   - secret
   - restricted
2. Add Cell access policies.
3. Add Pack export policy.
4. Add redaction projection.
5. Add UI warnings.

### Gate before commit
- Sensitive Charges are excluded from Packs unless runtime identity and export policy allow them.
- Redaction projection hides sensitive content without destroying provenance.
- Secrets/restricted memory cannot cross Cell/runtime scope in default policy.
- UI/API warnings appear for sensitive or restricted guidance.
- Existing public/internal/private fixture coverage proves policy behavior.
- No secure-delete behavior is introduced unless separately designed and gated.
- Focused privacy/export-policy tests pass.
- Full Python suite passes: `python3 -m pytest -q`.
- Console build/audit passes if UI changed.

### Acceptance Criteria
- Sensitive Charges excluded by default where policy requires.
- Pack generation respects runtime identity.
- Redaction does not destroy audit trail unless explicit secure-delete mode is designed.
- Commit message: `feat: add memory sensitivity scoping`.

---

## Phase 5 Gate: Durability Checkpoint

### Objective
Close the next major checkpoint before any Phase 6 multi-Cell intelligence work.

### Required checks
```bash
python3 -m pytest tests/test_console_api.py tests/test_server.py -q
python3 -m pytest -q
cd apps/console && npm run build && npm audit --omit=dev
cd /Users/stefan/ShyftR && git diff --check && git status --short --branch
```

### Required review evidence
- Grid remains rebuildable/non-canonical.
- Backup/restore round trip succeeds on a fixture Cell.
- Ledger verification detects tampering deterministically.
- Sensitivity/export policy prevents default leakage across runtime/user/project scopes.
- Optional disk-backed vector adapter is either complete and optional, or explicitly deferred with rationale.
- Reviewer verdict: PASS required before reporting the `/goal` complete.

### Stop condition
Stop here and report the Phase 5 durability checkpoint status. Do not start Phase 6 without a new `/goal` or explicit instruction.

---

# Phase 6: Multi-Cell Intelligence

Goal: move ShyftR from single-cell memory to a network of memory cells.

## Tranche 6.1: Cell Registry

### Objective
Track multiple Cells and their relationships.

### Tasks
1. Add registry file.
2. Track:
   - cell ID
   - cell type
   - path
   - owner
   - tags
   - domain
   - trust boundary
3. UI cell selector.
4. API registry endpoints.

### Acceptance Criteria
- Multiple Cells are discoverable.
- Cross-cell operations are explicit.
- No accidental cross-cell leakage.

---

## Tranche 6.2: Cross-Cell Resonance

### Objective
Detect repeated patterns across Cells.

### Tasks
1. Compare high-confidence Charges across Cells.
2. Compute resonance score:
   - recurrence
   - Cell diversity
   - confidence
   - useful Signal
   - recency
3. Propose cross-cell Rails.
4. Require explicit review.

### Acceptance Criteria
- Repeated local lessons can propose shared Rail.
- Shared memory never mutates local Cells silently.
- Resonance has provenance.

---

## Tranche 6.3: Rail Promotion Workflow

### Objective
Create global/shared doctrine safely.

### Tasks
1. Add Rail proposal queue.
2. Add Rail review UI.
3. Add Rail promotion event.
4. Add Pack retrieval from approved Rails.
5. Add scope constraints.

### Acceptance Criteria
- Rails are reviewed, scoped, and provenance-linked.
- Global policy cannot be created from one weak source.

---

## Tranche 6.4: Memory Federation Protocol

### Objective
Allow Cells to share memory without merging everything.

### Tasks
1. Define export format:
   - approved Charges only
   - Coils/Rails
   - summary statistics
   - redacted provenance
2. Define import format.
3. Support trust labels:
   - local
   - imported
   - federated
   - verified
4. Add import review queue.

### Acceptance Criteria
- Cell can import another Cell’s approved projection.
- Imported memory starts with a non-local trust label and requires review before local-truth treatment.
- Federation is selective and auditable.

---

# Phase 7: Frontier Differentiators

Goal: make ShyftR a standout product with frontier-grade memory learning.

## Tranche 7.1: Bayesian Confidence Model

### Objective
Replace single confidence floats with calibrated belief state.

### Tasks
1. Add confidence model:
   - prior
   - positive evidence count
   - negative evidence count
   - uncertainty
   - context-specific confidence
2. Add Beta-Binomial projection.
3. Display:
   - expected confidence
   - uncertainty interval
   - evidence count
4. Keep scalar compatibility field.

### Acceptance Criteria
- Confidence reflects uncertainty as well as score.
- New Charges with little evidence show uncertainty.
- Repeated useful Signal narrows uncertainty.

---

## Tranche 7.2: Causal Memory Graph

### Objective
Represent why memory helped or failed.

### Edge Types
1. caused_success
2. contributed_to_failure
3. contradicted_by
4. supersedes
5. depends_on
6. applies_under
7. invalid_under
8. co_retrieved_with
9. ignored_with

### Tasks
1. Add graph edge ledger.
2. Derive edges from Signal and review.
3. Add graph explorer UI.
4. Use graph in Pack compilation.

### Acceptance Criteria
- Memory can explain causal lineage.
- Pack Compiler can use dependency and invalidation edges.
- Graph is append-only/rebuildable.

---

## Tranche 7.3: Policy Simulation Sandbox

### Objective
Test retrieval and policy changes before applying them.

### Tasks
1. Replay historical Pack requests under new weights/policies.
2. Compare:
   - selected IDs
   - missed IDs
   - harmful IDs
   - caution ratio
   - token usage
3. Add UI diff:
   - current policy vs proposed policy
4. Add simulation report.

### Acceptance Criteria
- User can test a scoring change before applying it.
- Policy changes show projected effect.
- Simulation is read-only.

---

## Tranche 7.4: Adaptive Retrieval Modes

### Objective
Let runtimes select memory behaviour based on mission risk.

### Modes
1. conservative
2. balanced
3. exploratory
4. risk_averse
5. audit
6. doctrine_only
7. low_latency

### Tasks
1. Define mode config.
2. Add Pack request field.
3. Add scoring weights per mode.
4. Add UI selector.
5. Add tests.

### Acceptance Criteria
- Different modes produce expected retrieval differences.
- Risk-averse mode amplifies caution.
- Conservative mode excludes weak memory.
- Audit mode can include challenged/isolated memory with labels.

---

## Tranche 7.5: Memory Reputation System

### Objective
Track reliability of memory sources, agents, reviewers, and Cells.

### Reputation Targets
1. source adapter
2. runtime
3. agent
4. reviewer
5. Cell
6. imported memory source

### Metrics
1. approval rate
2. rejection rate
3. useful Signal rate
4. harmful Signal rate
5. contradiction rate
6. stale memory rate

### Acceptance Criteria
- Memory source quality is measurable.
- Reviewer reliability affects proposal priority.
- Reputation never silently bypasses review gates.

---

## Tranche 7.6: Self-Modifying Regulator Proposals

### Objective
Let ShyftR propose improvements to its own memory policy.

### Tasks
1. Detect repeated false approvals.
2. Detect repeated false rejections.
3. Propose new regulator rules.
4. Simulate rule effect before acceptance.
5. Require human review.

### Acceptance Criteria
- Regulator can propose policy updates.
- Policy updates are never automatic.
- Proposed rules include examples and counterexamples.

---

## Tranche 7.7: Synthetic Training and Test Data Generator

### Objective
Turn ShyftR memory into evaluation tasks for agents.

### Tasks
1. Generate benchmark tasks from:
   - repeated failures
   - missing memory
   - contradictions
   - high-value Charges
2. Generate expected Pack items.
3. Generate expected agent behaviour.
4. Export as test fixtures.

### Acceptance Criteria
- ShyftR can create regression tests for agents.
- Generated tasks are provenance-linked.
- Users can evaluate agent improvement over time.

---

# Phase 8: Productisation

Goal: prepare ShyftR for real users beyond your internal runtime.

## Tranche 8.1: Product Landing Docs

### Objective
Make positioning clear.

### Message
"ShyftR is a local-first, review-gated memory substrate for autonomous agents."

### Required Docs
1. Why ShyftR
2. Architecture
3. Quickstart
4. Concepts
5. CLI guide
6. HTTP API guide
7. Frontend guide
8. Integration guide
9. Safety model
10. Roadmap

### Acceptance Criteria
- New user understands what to install, run, and test.
- Docs do not overclaim.
- The product category is clear.

---

## Tranche 8.2: Plugin/Adapter SDK

### Objective
Let others build adapters.

### Tasks
1. Define adapter interface.
2. Add template adapter.
3. Add adapter test harness.
4. Add docs.
5. Add examples:
   - markdown folder
   - JSONL runtime logs
   - GitHub issue export
   - chat transcript export

### Acceptance Criteria
- New adapter can be built without touching core.
- Adapter tests enforce provenance and boundary checks.

---

## Tranche 8.3: Versioned Public API

### Objective
Stabilize external integration.

### Tasks
1. Add `/v1/` API namespace.
2. Freeze v1 schemas.
3. Generate OpenAPI spec.
4. Add API contract tests.
5. Add deprecation policy.

### Acceptance Criteria
- API changes are deliberate.
- External runtimes can depend on v1.

---

## Tranche 8.4: Desktop Shell

### Objective
Wrap local service and console into a desktop app.

### Recommended
Use Tauri only after web console is stable.

### Tasks
1. Tauri wrapper.
2. Start/stop local ShyftR service.
3. Select Cell directory.
4. Open console.
5. Local logs.
6. Bundle install docs.

### Acceptance Criteria
- Non-terminal user can operate ShyftR locally.
- Desktop app does not replace API/CLI.
- Web console remains portable.

---

## Tranche 8.5: Public Alpha

### Objective
Release to a small group of technical users.

### Requirements
1. CI green.
2. Docs complete.
3. Demo works.
4. Backup/restore works.
5. UI usable.
6. Local API stable.
7. At least one real runtime integration proven.
8. Clear warning: local-first alpha, not hosted SaaS.

### Acceptance Criteria
- 3-5 external testers can run it.
- Bugs are actionable.
- Product value is understandable without you explaining it live.

---

## Checkpoint E: Alpha Exit / Beta-Readiness Cut

### Objective
Define the earliest point where public-facing docs may stop describing ShyftR as alpha.

### Expected timing
Do not remove alpha status before Tranche 8.5 has run with external tester evidence and all criteria below pass. Until then, README, status docs, package metadata, and public gates must keep the alpha label.

### Required evidence
1. `scripts/alpha_gate.sh` passes from a clean public clone on at least two fresh environments.
2. Three to five external technical testers complete clone/install/gate/demo and produce actionable feedback.
3. Zero blocker issues remain open for install, CLI smoke, lifecycle demo, synthetic readiness replay, diagnostics, public-readiness scan, or console build.
4. At least one operator-owned dogfooding loop has run on non-sensitive or approved local data for a sustained period, with reviewed diagnostic/readiness evidence.
5. Backup/restore and ledger verification have been exercised on a fixture Cell and one operator-approved real local Cell.
6. Public docs still avoid production/service overclaims and describe only implemented behavior.
7. Private-core experiments required for advanced scoring/ranking/compaction are either explicitly not part of the beta boundary or have passed their private overlay gates.
8. The release decision is recorded in a status update before public wording changes.

### Stop condition
If any item above fails, keep ShyftR labelled alpha and continue hardening. Passing this checkpoint permits a later public-doc update from alpha to beta/developer preview, but does not imply production readiness or hosted-service readiness.

---

# Long-Term Product Cut Lines

## Replacement-Ready Backend
Complete Phase 1 through Tranche 1.9.

ShyftR can:
- run through CLI and local HTTP API
- ingest exported managed-memory records into Cell ledgers
- generate deterministic, provenance-linked Packs
- record Signals and update confidence / retrieval affinity
- produce diagnostic logs and replay reports
- pass a replacement-readiness gate for bounded-domain primary memory

## Internal MVP
Complete through Phase 2.

ShyftR can:
- run locally
- ingest evidence
- review memory
- generate Packs
- record Signal
- inspect memory health
- operate through a minimal front end

## Controlled Pilot
Complete through Phase 3.

ShyftR can:
- attach to one real runtime, pilot harness, or replayable integration loop
- ingest real task outputs
- improve Packs from Signal
- measure operator burden and memory usefulness

## Active Learning Release
Complete through Phase 4.

ShyftR can:
- propose confidence/retrieval changes
- challenge high-impact memory
- isolate risky memory
- arbitrate conflicts

## Durable Memory Platform
Complete through Phase 5 and 6.

ShyftR can:
- scale retrieval
- backup/restore Cells
- verify ledgers
- operate across multiple Cells
- propose shared Rails

## Frontier Product
Complete through Phase 7.

ShyftR becomes:
- probabilistic
- causal
- simulation-backed
- self-auditing
- self-improving
- reputation-aware

---

# Recommended Implementation Order

1. Tranche 0.1 - Repo Reality Audit
2. Tranche 0.2 - Test Suite Baseline and CI Gate
3. Tranche 0.3 - Vocabulary and Ledger Compatibility Lock
4. Tranche 0.4 - Canonical Ledger Path Lock
5. Tranche 0.5 - Atomic Append and File Locking
6. Tranche 0.6 - Schema Versioning and Migration Guard
7. Tranche 0.7 - Packaging, README, and Installation Repair

8. Tranche 1.1 - Provider API Completion
9. Tranche 1.2 - Runtime Pack API Hardening
10. Tranche 1.3 - Runtime Signal API Hardening
11. Tranche 1.4 - Pack Compiler MVP
12. Tranche 1.5 - Pack-Miss Learning MVP
13. Tranche 1.6 - Confidence Events MVP
14. Tranche 1.7 - Retrieval Affinity Events MVP
15. Tranche 1.8 - Local HTTP Service Hardening
16. Tranche 1.9 - Replacement Readiness, Observability, and Test Harness

17. Tranche 2.1 - Front End Scaffold
18. Tranche 2.2 - Cell Dashboard
19. Tranche 2.3 - Ingestion Console
20. Tranche 2.4 - Spark Review Queue
21. Tranche 2.5 - Charge Explorer
22. Tranche 2.6 - Pack Debugger
23. Tranche 2.7 - Signal Console
24. Tranche 2.8 - Hygiene and Sweep Reports UI
25. Tranche 2.9 - Proposal Review UI
26. Tranche 2.10 - MVP Demo Script and Frontend Walkthrough

27. Tranche 3.1 - Runtime Adapter / Pilot Harness
28. Tranche 3.2 - Pilot Metrics
29. Tranche 3.3 - Operator Burden Report
30. Tranche 3.4 - Policy Tuning Pass

31. Tranche 4.1 - Sweep Proposal Engine
32. Tranche 4.2 - Challenger Audit Loop
33. Tranche 4.3 - Isolation and Challenge Workflow
34. Tranche 4.4 - Memory Conflict Arbitration

35. Tranche 5.1 - Grid Metadata and Staleness
36. Tranche 5.2 - Disk-Backed Vector Adapter
37. Tranche 5.3 - Backup and Restore
38. Tranche 5.4 - Tamper-Evident Ledger Hash Chains
39. Tranche 5.5 - Privacy and Sensitivity Scoping

40. Tranche 6.1 - Cell Registry
41. Tranche 6.2 - Cross-Cell Resonance
42. Tranche 6.3 - Rail Promotion Workflow
43. Tranche 6.4 - Memory Federation Protocol

44. Tranche 7.1 - Bayesian Confidence Model
45. Tranche 7.2 - Causal Memory Graph
46. Tranche 7.3 - Policy Simulation Sandbox
47. Tranche 7.4 - Adaptive Retrieval Modes
48. Tranche 7.5 - Memory Reputation System
49. Tranche 7.6 - Self-Modifying Regulator Proposals
50. Tranche 7.7 - Synthetic Training and Test Data Generator

51. Tranche 8.1 - Product Landing Docs
52. Tranche 8.2 - Plugin/Adapter SDK
53. Tranche 8.3 - Versioned Public API
54. Tranche 8.4 - Desktop Shell
55. Tranche 8.5 - Public Alpha
