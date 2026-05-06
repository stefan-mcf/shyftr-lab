# ShyftR Runtime Integration Adapter Follow-up Plan

> For Hermes: implement this after the main MVP lifecycle is working. Keep this plan runtime-agnostic. Do not bake in any one agent system, queue implementation, or orchestration vocabulary.

Status: follow-up implementation plan. This plan extends `docs/plans/2026-04-24-shyftr-implementation-tranches.md` by adding the plug-and-play integration layer needed for external agent runtimes to use ShyftR as a closed learning loop.

Goal: make any agent runtime able to attach a ShyftR cell by sending evidences through the regulator, requesting packs, reporting feedback, and receiving review-gated proposals.

Canonical system vocabulary for adapter authors:

- ShyftR cell: a bounded attachable memory unit.
- regulator: the review and policy layer controlling admission, promotion, retrieval, and export.
- cell ledger: the append-only canonical truth inside a cell.
- memory: a reviewed durable memory item.
- grid: the rebuildable retrieval and index layer.
- pack: the bounded memory bundle supplied to an agent or runtime.
- feedback: the evidenceback record that tells ShyftR whether retrieved memory helped or harmed.

Core integration contract:

```text
External runtime -> evidences -> ShyftR cell
External runtime <- packs <- ShyftR cell
External runtime -> feedback -> ShyftR cell
External runtime <- Proposals <- ShyftR cell
```

ShyftR remains runtime-agnostic:

- no runtime queue state as durable memory
- no active execution state as durable memory
- no hardcoded worker framework
- no hardcoded transport
- no direct mutation of external runtime policy by default
- all durable learning remains provenance-linked and review-gated

Core rules remains:

```text
cell ledgers are truth.
The regulator controls admission, promotion, retrieval, and export.
The grid is acceleration.
The pack is application.
feedback is learning.
memory confidence is evolution.
```

---

## Relationship to the other plans

Main MVP plan:

- `docs/plans/2026-04-24-shyftr-implementation-tranches.md`

Active-learning follow-up plan:

- `docs/plans/2026-04-24-shyftr-active-learning-follow-up-plan.md`

This runtime integration plan should begin after the main MVP cut line, because it needs:

1. cell initialization
2. append-only ledgers
3. evidence ingestion
4. candidate extraction
5. candidate review
6. memory promotion
7. retrieval
8. pack assembly
9. feedback recording

Recommended sequencing:

```text
Main plan Tranches 0-11
  -> Runtime Integration Adapter Follow-up Plan
  -> Active Learning Follow-up Plan
```

Reason: runtime integration gives ShyftR real external evidence and feedback. Active-learning features such as pack Misses, Sweep reports, and Challenger audits become more valuable once external runtimes can supply evidence and consume the loop.

---

## Product thesis

ShyftR should be easy to attach to an existing agent runtime without forcing that runtime to adopt ShyftR internals.

A runtime should only need to implement four flows:

1. evidence ingest: send ShyftR evidence from work, logs, notes, reviews, tool runs, or artifacts.
2. pack request: ask ShyftR what memory applies before work begins.
3. feedback report: tell ShyftR what happened and which memory helped or hurt.
4. Proposal review: receive suggested memory/policy/routing/process improvements without automatic unsafe mutation.

The minimal promise:

```text
Send evidence.
Receive memory.
Report feedback.
Improve next run.
```

---

## Runtime regulator

External runtimes own operational execution.

External runtime responsibilities:

- task scheduling
- active task state
- queue state
- worker execution
- model/backend selection
- retries
- monitors
- runtime-specific policy files
- immediate safety decisions

ShyftR responsibilities:

- durable evidence capture into the cell ledger
- candidate extraction
- regulator admission, review, retrieval, and export policy
- review-gated memory promotion
- trust-labeled pack assembly
- feedback learning
- confidence evolution
- anti-pattern and caution memory
- proposal generation
- audit and hygiene

ShyftR may advise a runtime, but should not silently control it.

---

## Tranche RI-0: Runtime integration contract document

Objective: document the runtime-agnostic plug-and-play contract before building adapters.

Files:

- Create: `docs/concepts/runtime-integration-contract.md`
- Modify: `docs/concepts/storage-retrieval-learning.md`
- Test: none required beyond stale-term scan

Tasks:

1. Define the four runtime integration flows:
   - evidence ingest
   - pack request
   - feedback report
   - proposal review/export
2. Define what external runtimes own versus what ShyftR owns.
3. Document required external identity fields:
   - `external_system`
   - `external_scope`
   - `external_run_id`
   - `external_task_id`
   - optional external references
4. Document idempotency requirements for file and JSONL ingest.
5. Document the safety regulator: ShyftR proposes; the runtime applies.
6. Commit: `docs: define runtime integration contract`.

Acceptance criteria:

- A new runtime author can understand how to attach to ShyftR.
- The contract contains no runtime-specific product assumptions.
- The contract reinforces the regulator between operational state and durable memory.

---

## Tranche RI-1: Adapter protocol interfaces

Objective: add small, stable protocols for external evidence and feedback adapters.

Files:

- Create: `src/shyftr/integrations/__init__.py`
- Create: `src/shyftr/integrations/protocols.py`
- Create: `tests/test_integration_protocols.py`

Tasks:

1. Define `ExternalevidenceRef` model with:
   - adapter ID
   - external system
   - external scope
   - evidence kind
   - evidence URI/path
   - evidence line offset where applicable
   - stable external IDs
   - metadata
2. Define `evidencePayload` model with:
   - text or bytes hash
   - kind
   - metadata
   - external refs
3. Define `evidenceAdapter` protocol:
   - `discover_evidences()`
   - `read_evidence(ref)`
   - `evidence_metadata(ref)`
4. Define `feedbackAdapter` protocol:
   - `discover_feedback()`
   - `read_feedback(ref)`
   - `map_feedback(payload)`
5. Keep interfaces dependency-free.
6. Test protocol model serialization.
7. Commit: `feat: define runtime adapter protocols`.

Acceptance criteria:

- Adapter protocols are runtime-agnostic.
- External identity and provenance can be preserved.
- Tests pass without network or optional dependencies.

---

## Tranche RI-2: Adapter config schema and validation

Objective: let runtimes attach through declarative configuration rather than custom code for every evidence.

Files:

- Create: `src/shyftr/integrations/config.py`
- Create: `tests/test_integration_config.py`
- Create: `examples/integrations/runtime-adapter.yaml`

Tasks:

1. Define adapter config fields:
   - `adapter_id`
   - `cell_id`
   - `external_system`
   - `external_scope`
   - `evidence_root`
   - input definitions
   - identity mapping
   - ingest options
2. Support input definitions for:
   - single file
   - glob
   - JSONL file
   - directory tree
3. Validate that configured paths stay within allowed roots unless explicitly permitted.
4. Validate required evidence kind mappings.
5. Validate stable external ID mapping rules.
6. Add CLI-ready config loading helpers.
7. Commit: `feat: add runtime adapter config schema`.

Acceptance criteria:

- Invalid configs fail with useful errors.
- Valid configs load deterministically.
- Example config contains no runtime-specific assumptions.

---

## Tranche RI-3: Generic file and JSONL evidence adapter

Objective: implement a default adapter that can ingest common runtime evidence without custom plugin code.

Files:

- Create: `src/shyftr/integrations/file_adapter.py`
- Modify: `src/shyftr/ingest.py`
- Create: `tests/test_file_adapter.py`
- Create: `tests/fixtures/integrations/generic_runtime/`

Tasks:

1. Implement file discovery from adapter config.
2. Implement JSONL row discovery with stable row refs:
   - file path
   - byte offset or line number
   - row hash
3. Convert each discovered file or row into a ShyftR evidence payload.
4. Preserve external refs in evidence metadata.
5. Deduplicate by content hash and external ref.
6. Support dry-run discovery summary.
7. Test ingestion from:
   - markdown file
   - text log file
   - JSONL feedback-like rows
   - nested directory glob
8. Commit: `feat: add generic file runtime adapter`.

Acceptance criteria:

- A runtime with files and JSONL logs can produce ShyftR evidences without custom Python.
- Ingest is idempotent.
- evidence provenance includes external refs and line/row identity where available.

---

## Tranche RI-4: Integration CLI commands

Objective: expose adapter validation, dry-run discovery, ingest, and backfill through the CLI.

Files:

- Modify: `src/shyftr/cli.py`
- Modify: `src/shyftr/integrations/config.py`
- Modify: `src/shyftr/integrations/file_adapter.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_integration_cli.py`

Tasks:

1. Add CLI command:
   - `shyftr adapter validate --config <path>`
2. Add CLI command:
   - `shyftr adapter discover --config <path> --dry-run`
3. Add CLI command:
   - `shyftr adapter ingest --config <path>`
4. Add CLI command:
   - `shyftr adapter backfill --config <path> --dry-run`
5. Ensure commands produce machine-readable JSON output with `--json`.
6. Ensure dry-run writes no evidence records.
7. Add tests for help text and dry-run behavior.
8. Commit: `feat: expose runtime adapter CLI`.

Acceptance criteria:

- A user can validate an adapter config before ingesting.
- Dry-run reports discovered evidence counts and kinds.
- Ingest writes evidences append-only.
- CLI output is suitable for automation.

---

## Tranche RI-5: pack request API contract

Objective: make pack requests easy for external runtimes to consume through JSON input and JSON output.

Files:

- Modify: `src/shyftr/pack.py`
- Modify: `src/shyftr/cli.py`
- Create: `src/shyftr/integrations/pack_api.py`
- Modify: `tests/test_pack.py`
- Create: `tests/test_pack_api.py`
- Create: `examples/integrations/task-request.json`

Tasks:

1. Define `RuntimepackRequest` with:
   - cell path or cell ID
   - query/task text
   - task kind
   - external system
   - external scope
   - external task ID
   - tags
   - max items/tokens
   - requested trust tiers
2. Define `RuntimepackResponse` with:
   - pack ID
   - guidance items
   - caution items
   - background items
   - conflict items
   - risk flags
   - selected IDs
   - score memories
3. Add CLI command shape:
   - `shyftr pack --request-json <path> --json`
4. Ensure all pack items include stable IDs, trust labels, confidence, kind, and provenance references.
5. Test JSON request/response round trips.
6. Commit: `feat: add runtime pack API contract`.

Acceptance criteria:

- External runtimes can call ShyftR without parsing prose.
- pack responses are deterministic and schema-stable.
- Returned memory is trust-labeled and provenance-linked.

---

## Tranche RI-6: Runtime feedback reporting contract

Objective: let external runtimes report what happened after a pack was supplied.

Files:

- Modify: `src/shyftr/feedback.py`
- Create: `src/shyftr/integrations/feedback_api.py`
- Modify: `src/shyftr/cli.py`
- Modify: `tests/test_feedback.py`
- Create: `tests/test_feedback_api.py`
- Create: `examples/integrations/feedback-report.json`

Tasks:

1. Define `RuntimefeedbackReport` with:
   - pack ID
   - external system
   - external scope
   - external run ID
   - external task ID
   - result
   - applied memory IDs
   - useful memory IDs
   - harmful memory IDs
   - ignored memory IDs
   - violated caution IDs
   - missing memory notes
   - verification evidence
   - runtime metadata
2. Add CLI command shape:
   - `shyftr feedback --report-json <path>`
3. Link feedback records back to pack/retrieval logs.
4. Preserve external refs in feedback metadata.
5. Ensure feedback recording remains append-only.
6. Test reporting success, failure, partial, and unknown feedback.
7. Commit: `feat: add runtime feedback reporting contract`.

Acceptance criteria:

- External runtimes can report memory application and task result.
- feedback can identify applied, ignored, useful, harmful, and missing memory.
- ShyftR can learn from the report without owning runtime execution.

---

## Tranche RI-7: Incremental sync state

Objective: make repeated ingest safe and efficient for append-only external logs.

Files:

- Create: `src/shyftr/integrations/sync_state.py`
- Modify: `src/shyftr/integrations/file_adapter.py`
- Modify: `src/shyftr/cli.py`
- Create: `tests/test_sync_state.py`
- Modify: `tests/test_file_adapter.py`

Tasks:

1. Add sync state under the cell config or indexes area:
   - adapter ID
   - evidence path
   - last byte offset
   - last line number
   - last content hash
   - last sync time
2. Support append-only JSONL incremental ingest.
3. Detect file truncation or rotation and require explicit reset/backfill.
4. Add CLI command:
   - `shyftr adapter sync --config <path>`
5. Add CLI command:
   - `shyftr adapter sync-status --config <path>`
6. Test idempotent repeated sync.
7. Test append-only new-row ingestion.
8. Commit: `feat: add runtime adapter incremental sync`.

Acceptance criteria:

- Repeated sync does not duplicate evidences.
- New JSONL rows are ingested without rereading the whole file.
- Rotation/truncation is detected and reported safely.

---

## Tranche RI-8: Generic worker-runtime example fixture

Objective: prove the integration contract with a runtime-neutral example that demonstrates a closed learning loop.

Files:

- Create: `examples/integrations/worker-runtime/adapter.yaml`
- Create: `examples/integrations/worker-runtime/evidence-closeout.md`
- Create: `examples/integrations/worker-runtime/feedback-log.jsonl`
- Create: `examples/integrations/worker-runtime/task-request.json`
- Create: `examples/integrations/worker-runtime/feedback-report.json`
- Create: `docs/demo-runtime-integration.md`
- Create: `tests/test_runtime_integration_demo.py`

Tasks:

1. Create a generic worker-runtime fixture with no product-specific naming.
2. Include evidence showing:
   - one successful workflow
   - one repeated failure signature
   - one recovery pattern
   - one caution/anti-pattern
3. Demonstrate adapter validation and ingest.
4. Demonstrate evidence -> candidate -> memory flow using the fixture.
5. Demonstrate pack request before a task.
6. Demonstrate feedback report after a task.
7. Demonstrate confidence or reportable learning feedback after the feedback.
8. Commit: `docs: add runtime integration demo`.

Acceptance criteria:

- Demo proves ShyftR can attach to an external runtime through files and JSONL.
- Demo contains no runtime-specific product dependency.
- Test exercises the closed loop end to end.

---

## Tranche RI-9: Proposal export contract

Objective: let ShyftR emit review-gated recommendations back to external runtimes without directly mutating their policies.

Files:

- Create: `src/shyftr/integrations/proposals.py`
- Modify: `src/shyftr/cli.py`
- Create: `tests/test_runtime_proposals.py`
- Modify: `docs/concepts/runtime-integration-contract.md`

Tasks:

1. Define `RuntimeProposal` with:
   - proposal ID
   - proposal type
   - target external system/scope
   - target external refs
   - recommendation
   - evidence memory IDs
   - evidence Evidence IDs
   - confidence
   - review status
   - created timestamp
2. Support proposal types:
   - `memory_application_hint`
   - `routing_hint`
   - `verification_hint`
   - `retry_caution`
   - `policy_change_candidate`
   - `missing_memory_candidate`
3. Add CLI command:
   - `shyftr proposals export --cell <path> --external-system <id> --json`
4. Ensure proposals are advisory by default.
5. Require explicit review before marking proposal accepted.
6. Test proposal export from fixture evidence.
7. Commit: `feat: add runtime proposal export contract`.

Acceptance criteria:

- External runtimes can consume ShyftR recommendations as data.
- ShyftR does not directly edit runtime policy files.
- Proposal evidence is provenance-linked and reviewable.

---

## Tranche RI-10: Plugin discovery and packaging

Objective: allow optional third-party runtime adapters without coupling them to ShyftR core.

Files:

- Modify: `pyproject.toml`
- Create: `src/shyftr/integrations/plugins.py`
- Create: `tests/test_integration_plugins.py`
- Modify: `docs/concepts/runtime-integration-contract.md`

Tasks:

1. Define adapter plugin entry point group.
2. Implement plugin discovery for installed adapters.
3. Keep built-in file/JSONL adapter available without plugin discovery.
4. Add CLI command:
   - `shyftr adapter list`
5. Add plugin metadata fields:
   - adapter name
   - version
   - supported input kinds
   - config schema version
6. Add tests using a fake in-process plugin.
7. Commit: `feat: add runtime adapter plugin discovery`.

Acceptance criteria:

- ShyftR core can load optional adapters.
- Default installation still works without optional plugins.
- Runtime-specific adapters can live outside the core package.

---

## Tranche RI-11: HTTP/local service wrapper

Objective: provide a simple local service interface for runtimes that cannot shell out to the CLI cleanly.

Files:

- Create: `src/shyftr/server.py`
- Modify: `pyproject.toml`
- Create: `tests/test_server.py`
- Modify: `docs/demo-runtime-integration.md`

Tasks:

1. Add optional local HTTP service extra.
2. Expose endpoints for:
   - adapter validation
   - evidence ingest
   - pack request
   - feedback report
   - proposal export
3. Keep CLI as the primary MVP interface.
4. Ensure the server is optional and local-first.
5. Add tests using a test client if the optional dependency is installed.
6. Commit: `feat: add optional runtime integration service`.

Acceptance criteria:

- Runtimes can integrate via CLI or local HTTP.
- Default ShyftR remains local-first and file-backed.
- The service does not change canonical truth semantics.

---

## Follow-up cut line

The first plug-and-play integration cut is complete after RI-8:

1. runtime integration contract
2. adapter protocols
3. config schema
4. generic file/JSONL evidence adapter
5. adapter CLI
6. JSON pack request/response contract
7. JSON feedback reporting contract
8. incremental sync
9. generic worker-runtime demo

RI-9 adds advisory proposal export.

RI-10 and RI-11 make the integration layer easier to extend and embed.

---

## Final verification before completing the runtime integration plan

Run from a private ShyftR lab checkout:

```bash
python3 -m pytest -q
# Run the project stale-terminology scan from the ShyftR rule skill against README.md and docs/.
git status --short
git push origin main
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
```

Expected:

- tests pass
- stale-term scan has no public-doc matches
- only intended files are committed
- local `HEAD` matches `origin/main` after push

---

## Summary

This plan makes ShyftR practical for closed learning loops in external agent runtimes.

The key promise is simple:

```text
Any runtime can attach a ShyftR cell by sending evidences, requesting packs, and reporting feedback.
```

The runtime stays in control of execution. ShyftR provides durable, auditable, feedback-aware memory.
