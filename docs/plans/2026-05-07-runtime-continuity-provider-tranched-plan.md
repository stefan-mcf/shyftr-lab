# Runtime continuity provider tranched plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

Date: 2026-05-07
Status: proposed plan
Scope: public-safe, runtime-neutral ShyftR continuity support for context compaction

## Goal

Add an opt-in ShyftR continuity provider path for runtimes that already perform context compaction. The runtime keeps ownership of mechanical context trimming and summarization. ShyftR supplies bounded, trust-labeled continuity packs before compaction and records feedback after resumed work.

## Architecture

The feature adds a second optional ShyftR role beside ordinary durable memory:

```text
runtime memory path -> ShyftR memory cell
runtime compaction path -> ShyftR continuity cell
```

The memory cell answers long-term recall questions. The continuity cell learns what should survive context pressure, what helped after compaction, what was noisy, and which missing-memory notes deserve review-gated promotion.

Public ShyftR should expose this as runtime-neutral continuity support. Runtime-specific adapters may map it to particular hooks, but the public contract, fixtures, CLI, API, docs, and tests should avoid naming a single runtime as the product surface.

## Product claim

ShyftR can attach to a runtime's memory path and context-compaction path as two separate opt-in cells:

- memory cell: durable recall across sessions;
- continuity cell: compaction survival, feedback, and review-gated learning around context pressure.

The continuity provider assists a runtime compactor. It does not claim hosted operation, multi-tenant operation, real-data pilots, or private ranking/scoring behavior in public `main`.

## Human input requirement

None for tranches 0 through 12 when implemented against synthetic fixtures and repo-local temporary cells.

Human/operator approval is required for:

- enabling continuity support in a real runtime profile;
- mutating user-level runtime config outside a temporary test home;
- using real memory data, customer data, employer data, regulated data, or private runtime transcripts;
- publishing packages, changing release posture, or making hosted-production claims;
- adding private scoring/ranking/advanced compaction heuristics to public `main`;
- promoting shadow/advisory mode to default authority for any runtime.

## Terminology policy

Use these public terms:

- cell
- ledger
- regulator
- grid
- pack
- feedback
- confidence
- proposal
- memory cell
- continuity cell
- continuity pack
- compaction feedback
- runtime adapter

Avoid runtime-specific product names in public generic docs, config keys, and CLI names. Runtime names may appear only in adapter-specific examples or deferred private notes.

Avoid claiming that ShyftR replaces the compactor. The safe claim is:

```text
ShyftR supplies continuity packs and feedback learning around a runtime-owned context compactor.
```

## Target public files

Likely creates:

- `src/shyftr/continuity.py`
- `src/shyftr/continuity_models.py`
- `src/shyftr/continuity_cli.py` or commands inside the existing CLI module
- `tests/test_continuity_models.py`
- `tests/test_continuity_pack.py`
- `tests/test_compaction_feedback.py`
- `tests/test_continuity_cli.py`
- `tests/test_continuity_runtime_demo.py`
- `examples/integrations/runtime-continuity/adapter.yaml`
- `examples/integrations/runtime-continuity/pre_compaction_context.json`
- `examples/integrations/runtime-continuity/mock_compaction_result.json`
- `examples/integrations/runtime-continuity/feedback.json`
- `docs/concepts/runtime-continuity-provider.md`
- `docs/runtime-continuity-example.md`

Likely modifies:

- `src/shyftr/loadout.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/server.py`
- `src/shyftr/console_api.py`
- `docs/concepts/runtime-integration-contract.md`
- `docs/sdk/adapter-sdk.md`
- `README.md` only after the feature is implemented and verified
- `docs/status/current-implementation-status.md` only after closeout evidence exists

Forbidden without approval:

- changing global runtime profiles;
- writing outside repo-local temp cells during tests;
- adding real transcript fixtures;
- introducing private scoring/ranking logic;
- making continuity support default-on for installed users.

## Desired user setup shape

A user should be able to choose either or both ShyftR roles:

```yaml
memory:
  provider: shyftr
  cell: default-memory

continuity:
  provider: shyftr
  enabled: true
  cell: default-continuity
  mode: shadow
  max_pack_tokens: 1200
  feedback: true
```

Allowed continuity modes:

- `off`: no continuity provider activity;
- `shadow`: generate and log what ShyftR would have supplied, without changing compaction input;
- `advisory`: return a continuity pack that the runtime may include as compactor scaffolding;
- `authority`: reserved for later gate; pack sections become required scaffold for selected bounded contexts after evidence review.

Public implementation should ship `off`, `shadow`, and `advisory`. `authority` can exist in schema as a reserved value only if tests prove it cannot be activated accidentally.

## End-to-end flow

```text
1. runtime detects context pressure
2. runtime sends a pre-compaction snapshot to ShyftR
3. ShyftR reads the continuity cell and optionally the memory cell
4. ShyftR builds a bounded continuity pack
5. runtime compactor uses the pack as advisory scaffolding
6. runtime resumes from compacted context
7. runtime reports compaction feedback
8. ShyftR records feedback in the continuity cell
9. ShyftR emits review-gated proposals for memory promotion, stale-memory caution, or pack tuning
```

## Core schemas

### continuity pack request

Contract id: `shyftr.continuity_pack_request.v1`

Required fields:

- `cell_path` or `cell_id`
- `request_id`
- `runtime_id`
- `mode`
- `context_pressure_reason`
- `active_goal`
- `recent_user_intent`
- `max_tokens`
- `created_timestamp`

Optional fields:

- `memory_cell_path`
- `active_task_refs`
- `open_decisions`
- `recent_tool_summary`
- `excluded_content_notes`
- `trust_tiers`
- `tags`
- `metadata`

### continuity pack

Contract id: `shyftr.continuity_pack.v1`

Required fields:

- `pack_id`
- `request_id`
- `cell_id`
- `mode`
- `items`
- `token_estimate`
- `created_timestamp`
- `retrieval_log_id`

Item sections:

- `active_intent`
- `durable_constraints`
- `verified_decisions`
- `project_context`
- `caution_items`
- `open_questions`
- `explicit_exclusions`
- `missing_memory_prompts`

Each item includes:

- `item_id`
- `source_memory_id` when applicable
- `trust_tier`
- `confidence`
- `section`
- `text`
- `rationale`
- `provenance_refs`
- `expires_at` when applicable
- `runtime_authority`: `advisory`

### compaction feedback

Contract id: `shyftr.compaction_feedback.v1`

Required fields:

- `feedback_id`
- `pack_id`
- `request_id`
- `runtime_id`
- `result`: `success`, `partial`, `failure`, or `unknown`
- `created_timestamp`

Optional fields:

- `useful_item_ids`
- `harmful_item_ids`
- `ignored_item_ids`
- `stale_item_ids`
- `missing_memory_notes`
- `over_retrieval_notes`
- `post_compaction_issue_notes`
- `verification_refs`
- `metadata`

Feedback writes to the continuity cell by default. Promotions into durable memory remain proposal-first and review-gated.

## Tranche 0: repo-state and terminology preflight

Objective: start from verified repository state and prevent public vocabulary drift.

Stop line: produce a preflight note or terminal log with current branch, changed files, and accepted dirty-state explanation.

Steps:

1. Run:

   ```bash
   git status --short --branch
   ```

2. Inspect current public status and concept inputs:

   ```bash
   python scripts/public_readiness_check.py
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   ```

3. Read:

   - `docs/status/tranched-plan-status.md`
   - `docs/status/current-implementation-status.md`
   - `docs/concepts/runtime-integration-contract.md`
   - `docs/sources/2026-05-07-shyftr-context-compaction-integration-viability.md`

4. Confirm public/private classification:

   - public proof: contracts, fixtures, deterministic tests, docs;
   - public examples: synthetic runtime-continuity example;
   - private/deferred: real runtime data, private compaction heuristics, hosted operations.

Verification:

- terminology guards pass before implementation begins;
- repo dirty state is understood and no unrelated files are edited.

## Tranche 1: continuity model contracts

Objective: add typed or dataclass model definitions for continuity pack request, continuity pack, continuity pack item, and compaction feedback.

Files:

- Create: `src/shyftr/continuity_models.py`
- Create: `tests/test_continuity_models.py`

Steps:

1. Write tests for required fields and JSON serialization.
2. Write tests rejecting missing `request_id`, `runtime_id`, `mode`, `pack_id`, or invalid feedback result.
3. Implement model classes using the project's existing style.
4. Add reserved-mode handling so `authority` can be parsed but cannot be activated by default config.
5. Verify stable contract ids:

   - `shyftr.continuity_pack_request.v1`
   - `shyftr.continuity_pack.v1`
   - `shyftr.compaction_feedback.v1`

Verification:

```bash
python -m pytest -q tests/test_continuity_models.py
```

Expected: all tests pass.

Hardening notes:

- validate token budgets as positive integers;
- clamp extreme max-token requests at a safe default limit;
- require advisory runtime authority on pack items for public modes;
- reject unknown result values.

## Tranche 2: continuity cell ledger layout

Objective: define append-only ledgers for continuity requests, packs, retrieval logs, and compaction feedback inside a cell.

Files:

- Modify: existing cell/ledger helper module if present
- Create or modify tests: `tests/test_continuity_pack.py`

Expected ledger names:

- `continuity_requests.jsonl`
- `continuity_packs.jsonl`
- `continuity_feedback.jsonl`
- reuse or link existing retrieval log ledgers where possible

Steps:

1. Write a fixture that creates a temporary continuity cell.
2. Write tests that append a request, pack, and feedback row.
3. Verify rows are append-only and include contract id, timestamps, ids, and runtime refs.
4. Implement the minimal ledger helper calls.
5. Verify repeated writes create additional rows rather than rewriting history.

Verification:

```bash
python -m pytest -q tests/test_continuity_pack.py::test_continuity_ledgers_are_append_only
```

Expected: pass.

Hardening notes:

- never overwrite ledger rows;
- keep generated indexes rebuildable;
- reject writes outside the selected cell path;
- keep feedback writes isolated from durable-memory promotion.

## Tranche 3: continuity pack assembler baseline

Objective: build deterministic continuity packs from existing memory/search/pack primitives without private ranking logic.

Files:

- Create: `src/shyftr/continuity.py`
- Modify: `src/shyftr/loadout.py` only if reuse requires a small public extension
- Create or modify: `tests/test_continuity_pack.py`

Steps:

1. Write fixture memories for:

   - durable constraint;
   - project context;
   - verified decision;
   - caution item;
   - stale item;
   - transient operational note.

2. Write failing tests proving the pack includes durable constraint, project context, verified decision, and caution item.
3. Write failing tests proving transient operational notes are excluded or labeled ephemeral.
4. Implement a deterministic section mapper:

   - durable preference/constraint -> `durable_constraints`;
   - decision -> `verified_decisions`;
   - project fact -> `project_context`;
   - failure pattern/caution -> `caution_items`;
   - open question -> `open_questions`.

5. Enforce max item count and max token estimate.
6. Return retrieval log id with every pack.

Verification:

```bash
python -m pytest -q tests/test_continuity_pack.py
```

Expected: pass.

Hardening notes:

- deterministic ordering for equal scores;
- token budget applied after section priority;
- every item must carry rationale and provenance;
- no pack item becomes a runtime instruction by default.

## Tranche 4: compaction feedback recording

Objective: record post-compaction feedback and keep it separate from direct memory mutation.

Files:

- Modify: `src/shyftr/continuity.py`
- Modify: `src/shyftr/provider/memory.py` if provider-level helper is appropriate
- Create: `tests/test_compaction_feedback.py`

Steps:

1. Write tests for useful, harmful, ignored, stale, and missing-memory feedback.
2. Write tests proving feedback appends to the continuity feedback ledger.
3. Write tests proving feedback creates proposal candidates rather than directly changing durable memory status.
4. Implement `record_compaction_feedback(...)`.
5. Link feedback rows to pack id and retrieval log id.

Verification:

```bash
python -m pytest -q tests/test_compaction_feedback.py
```

Expected: pass.

Hardening notes:

- missing-memory notes require length caps;
- harmful/stale feedback should lower confidence projections only through existing safe mechanisms;
- destructive deprecation stays review-gated;
- feedback row validation must reject ids from unrelated cells unless explicitly cross-cell linked.

## Tranche 5: CLI surface for local-first continuity support

Objective: add opt-in commands for continuity pack and compaction feedback using repo-local or user-selected cell paths.

Files:

- Modify existing CLI module or create: `src/shyftr/continuity_cli.py`
- Create: `tests/test_continuity_cli.py`
- Add fixture files under `examples/integrations/runtime-continuity/`

Proposed CLI:

```bash
shyftr continuity pack --cell <path> --request <request.json> --json
shyftr continuity feedback --cell <path> --feedback <feedback.json> --write
shyftr continuity validate --request <request.json>
shyftr continuity validate-feedback --feedback <feedback.json>
```

Steps:

1. Write CLI tests with temporary cells.
2. Validate request JSON without writes by default.
3. Generate pack JSON with `--json`.
4. Require explicit `--write` for feedback ledger writes.
5. Add clear error messages for missing cell, invalid mode, invalid token budget, and unknown ids.

Verification:

```bash
python -m pytest -q tests/test_continuity_cli.py
```

Expected: pass.

Hardening notes:

- stdout must stay protocol-clean for JSON mode;
- write operations require explicit flags;
- avoid touching global config in tests;
- all examples use synthetic data.

## Tranche 6: MCP/API contract extension

Objective: expose continuity pack and compaction feedback through the same runtime-neutral integration style as existing pack and feedback operations.

Files:

- Modify: `src/shyftr/mcp_server.py`
- Modify: `src/shyftr/server.py`
- Modify: `src/shyftr/console_api.py` if API status surfaces are needed
- Create tests fitting the existing MCP/API test style

Proposed MCP tools:

- `shyftr_continuity_pack`
- `shyftr_compaction_feedback`

Proposed API routes:

- `POST /v1/continuity/pack`
- `POST /v1/continuity/feedback`

Steps:

1. Write tests for dry-run pack generation through API/MCP helpers.
2. Write tests that feedback is write-gated.
3. Implement handlers by calling the continuity module.
4. Include contract ids and advisory flags in responses.
5. Verify compatibility with existing OpenAPI/public readiness constraints.

Verification:

```bash
python -m pytest -q tests/test_api_v1_contract.py tests/test_compaction_feedback.py tests/test_continuity_pack.py
```

Expected: pass.

Hardening notes:

- no external runtime mutation;
- API responses include `advisory_only: true` for pack and proposal export flows;
- OpenAPI generation must avoid compatibility vocabulary drift;
- request size limits should match existing service protections.

## Tranche 7: deterministic runtime-continuity demo

Objective: prove the complete loop with a synthetic runtime fixture.

Files:

- Create: `examples/integrations/runtime-continuity/adapter.yaml`
- Create: `examples/integrations/runtime-continuity/pre_compaction_context.json`
- Create: `examples/integrations/runtime-continuity/mock_compaction_result.json`
- Create: `examples/integrations/runtime-continuity/feedback.json`
- Create: `docs/runtime-continuity-example.md`
- Create: `tests/test_continuity_runtime_demo.py`

Demo flow:

```text
synthetic runtime context pressure
-> continuity pack request
-> deterministic mock compaction
-> resumed-work check
-> compaction feedback write
-> proposal export check
```

Steps:

1. Build a synthetic temp cell with known memory records.
2. Load `pre_compaction_context.json`.
3. Request a continuity pack.
4. Run deterministic mock compaction that preserves required continuity sections.
5. Compare result to expected compacted context.
6. Record feedback from `feedback.json`.
7. Assert ledger rows and proposal outputs.

Verification:

```bash
python -m pytest -q tests/test_continuity_runtime_demo.py
```

Expected: pass.

Hardening notes:

- demo must be replayable offline;
- no network calls;
- no browser calls;
- no real runtime profile mutation;
- fixture names stay generic.

## Tranche 8: continuity metrics and evaluation harness

Objective: measure whether continuity support helps without causing token bloat or stale-memory pollution.

Files:

- Modify: `src/shyftr/metrics.py`
- Create or modify tests: `tests/test_metrics.py`
- Add docs section in `docs/runtime-continuity-example.md`

Metrics:

- pack application rate;
- useful item rate;
- harmful item rate;
- ignored item rate;
- stale item rate;
- missing-memory note rate;
- token budget utilization;
- over-retrieval notes;
- proposal pressure.

Steps:

1. Write fixture feedback rows.
2. Test metric calculation from append-only ledgers.
3. Verify de-duplication of ids per feedback row.
4. Add CLI/API readout if consistent with current metrics surfaces.
5. Keep decay/scoring effects transparent and review-gated.

Verification:

```bash
python -m pytest -q tests/test_metrics.py tests/test_compaction_feedback.py
```

Expected: pass.

Hardening notes:

- metrics are projections over ledgers;
- no separate truth store;
- missing-memory notes are counted, not auto-promoted;
- harmful/stale rates must be visible in closeout evidence.

## Tranche 9: configuration and install UX docs

Objective: document opt-in setup for memory and continuity as separate ShyftR roles.

Files:

- Modify: `docs/concepts/runtime-integration-contract.md`
- Create: `docs/concepts/runtime-continuity-provider.md`
- Modify: `docs/sdk/adapter-sdk.md`
- Modify: `README.md` only after implementation proof exists

Steps:

1. Add a concept doc that explains memory cell versus continuity cell.
2. Add setup examples for `off`, `shadow`, and `advisory` modes.
3. Document that the continuity cell may read memory-cell packs if configured.
4. Document feedback and proposal review flow.
5. Add adapter guidance for runtimes that have pre-compaction hooks.
6. Keep runtime names out of the generic path.

Verification:

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
```

Expected: all pass.

Hardening notes:

- docs must avoid release overclaims;
- default mode is `off` unless the user opts in;
- public examples use synthetic data;
- authority mode remains gated.

## Tranche 10: adapter contract hardening

Objective: ensure runtime adapters can use continuity support safely without ShyftR taking ownership of runtime execution.

Files:

- Modify: `docs/sdk/adapter-sdk.md`
- Modify or create tests around adapter validation
- Modify: example adapter config

Adapter responsibilities:

- detect context pressure;
- provide pre-compaction snapshot;
- call continuity pack;
- pass advisory pack to runtime compactor when configured;
- report compaction feedback after resumed work;
- keep runtime scheduling, execution, model choice, retry, and config under runtime control.

ShyftR responsibilities:

- validate request;
- assemble pack;
- record retrieval log;
- record feedback;
- emit review-gated proposals;
- preserve append-only ledgers.

Steps:

1. Add adapter validation rules for continuity config.
2. Reject adapter configs that request `authority` without explicit experimental flag.
3. Add tests proving adapter discovery remains introspection-only.
4. Add tests proving adapter validation does not ingest evidence or mutate cells.

Verification:

```bash
PYTHONPATH=src python -m shyftr.cli adapter validate --config examples/integrations/runtime-continuity/adapter.yaml
PYTHONPATH=src python -m shyftr.cli adapter discover --config examples/integrations/runtime-continuity/adapter.yaml --dry-run
python -m pytest -q tests/test_runtime_integration_demo.py tests/test_continuity_runtime_demo.py
```

Expected: validation succeeds; discovery is dry-run and mutation-free.

Hardening notes:

- adapter discovery must stay safe without optional runtime dependencies;
- validation should catch unknown mode, missing cell, and missing request path;
- runtime-specific packages can live outside ShyftR core.

## Tranche 11: security, privacy, and failure-mode hardening

Objective: close common safety gaps before any user-facing status update.

Files:

- Add focused tests where current test organization fits best
- Modify docs with safety notes where needed

Required hardening tests:

1. Path safety:

   - reject path traversal outside selected cell;
   - use temporary cells in tests.

2. Data sensitivity:

   - reject or quarantine known sensitive fixture patterns if current regulator supports it;
   - ensure feedback notes are bounded and sanitized.

3. Prompt-injection resistance:

   - pack items labeled as advisory reference;
   - runtime latest user message remains authoritative;
   - pack text cannot set runtime config.

4. Token budget:

   - large cells still produce bounded packs;
   - extreme max-token requests clamp safely.

5. Stale-memory handling:

   - stale item becomes caution or is excluded;
   - stale feedback does not silently delete memory.

6. Corrupt input:

   - invalid JSON rejected cleanly;
   - unknown ids reported without traceback;
   - partial feedback writes avoided.

Verification:

```bash
python -m pytest -q tests/test_continuity_models.py tests/test_continuity_pack.py tests/test_compaction_feedback.py tests/test_continuity_cli.py tests/test_continuity_runtime_demo.py
```

Expected: all pass.

## Tranche 12: public readiness and release-scope closeout

Objective: prove the continuity provider feature is public-safe before status claims.

Files:

- Modify: `docs/status/current-implementation-status.md`
- Create or modify: `docs/status/runtime-continuity-provider-closeout.md`
- Modify: `README.md` only if release-scope evidence is complete

Steps:

1. Run focused tests:

   ```bash
   python -m pytest -q tests/test_continuity_models.py tests/test_continuity_pack.py tests/test_compaction_feedback.py tests/test_continuity_cli.py tests/test_continuity_runtime_demo.py
   ```

2. Run relevant existing runtime integration tests:

   ```bash
   python -m pytest -q tests/test_runtime_integration_demo.py tests/test_api_v1_contract.py tests/test_metrics.py
   ```

3. Run full suite if scope touched API, CLI, metrics, or provider internals:

   ```bash
   python -m pytest -q
   ```

4. Run public checks:

   ```bash
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   python scripts/public_readiness_check.py
   git diff --check
   ```

5. If release gate exists in the checkout, run:

   ```bash
   bash scripts/release_gate.sh
   ```

6. Write closeout evidence with:

   - feature summary;
   - implemented files;
   - test commands and results;
   - public/private split confirmation;
   - known deferred runtime-specific adapter work;
   - default mode confirmation: off unless configured.

Verification:

- tests pass;
- terminology guards pass;
- public readiness passes;
- release gate passes when applicable;
- closeout doc states no real runtime profile was changed.

## Tranche 13: deferred real-runtime adapter pilot

Objective: connect the runtime-neutral continuity provider to a real runtime hook only after public proof is complete.

Status: deferred; requires operator approval.

Suggested pilot stages:

1. `shadow`:

   - runtime calls continuity pack at context pressure;
   - pack id and selected item ids are logged;
   - compactor input remains unchanged.

2. `advisory`:

   - runtime includes the continuity pack as scaffold/reference;
   - runtime keeps existing compactor protections;
   - pack size remains bounded.

3. `feedback`:

   - runtime records useful, harmful, ignored, stale, and missing-memory feedback;
   - feedback writes to the continuity cell.

4. `evaluation`:

   - replay same transcripts with baseline and ShyftR-assisted paths;
   - compare active-goal retention, durable-constraint retention, stale-memory avoidance, token cost, and operator burden.

5. `gate`:

   - operator reviews evidence before changing defaults.

Verification:

- live profile smoke tests if approved;
- no public claim until evidence is written;
- adapter-specific docs remain separate from generic continuity docs.

## Tranche 14: hardening follow-up after dogfood

Objective: convert observed feedback into safe product hardening.

Status: future tranche after dogfood evidence.

Possible work:

- section weighting refinements;
- better missing-memory proposal grouping;
- continuity-specific stale-memory reports;
- runtime adapter conformance tests;
- faster pack assembly under pressure;
- pack comparison reports for baseline versus assisted compaction;
- optional private-core experiments kept outside public `main` until approved.

Verification:

- dogfood report exists;
- harmful/stale/ignored rates reviewed;
- no silent promotion to durable memory;
- improvements covered by deterministic regression tests.

## Testing matrix

| Area | Test files | Proof |
| --- | --- | --- |
| model contracts | `tests/test_continuity_models.py` | schemas validate and serialize |
| ledger writes | `tests/test_continuity_pack.py` | append-only request/pack/feedback rows |
| pack assembly | `tests/test_continuity_pack.py` | deterministic bounded packs with provenance |
| feedback | `tests/test_compaction_feedback.py` | useful/harmful/ignored/stale/missing rows recorded |
| CLI | `tests/test_continuity_cli.py` | dry-run by default, explicit feedback writes |
| API/MCP | existing API/MCP tests plus new focused tests | advisory responses and write gates |
| demo | `tests/test_continuity_runtime_demo.py` | full synthetic loop replay |
| metrics | `tests/test_metrics.py` | ledger-backed rates and de-duplication |
| public readiness | scripts | terminology and release posture stay clean |
| security | focused negative tests | path safety, token limits, bad input, advisory labels |

## Acceptance criteria

The plan is complete when:

- continuity support can be enabled separately from memory support;
- default install leaves continuity off unless configured;
- `shadow` mode produces packs and logs without changing compactor input;
- `advisory` mode returns bounded continuity packs with trust labels, rationale, provenance, and retrieval logs;
- compaction feedback records useful, harmful, ignored, stale, and missing-memory notes;
- feedback does not directly mutate durable memory;
- proposals remain review-gated;
- all examples use synthetic data;
- public docs use runtime-neutral naming;
- runtime-specific adapter work is deferred or clearly adapter-scoped;
- test suite and public-readiness gates pass.

## Closeout checklist

- [ ] Current repo state inspected.
- [ ] Existing dirty files protected from unrelated edits.
- [ ] Public/private split documented.
- [ ] Continuity model contracts implemented.
- [ ] Continuity cell ledgers append-only.
- [ ] Continuity pack assembler deterministic and bounded.
- [ ] Compaction feedback write-gated.
- [ ] CLI validates without writing by default.
- [ ] API/MCP responses advisory and scoped.
- [ ] Synthetic runtime demo replayable offline.
- [ ] Metrics projected from ledgers.
- [ ] Security and privacy negative tests pass.
- [ ] Terminology guards pass.
- [ ] Public readiness passes.
- [ ] Release gate passes when available.
- [ ] Status/closeout artifact written.
- [ ] Real-runtime adapter activation remains operator-gated.
