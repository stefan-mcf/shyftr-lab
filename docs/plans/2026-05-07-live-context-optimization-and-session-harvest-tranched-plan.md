# Live context optimization and session harvest tranched plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

Date: 2026-05-07
Status: proposed plan
Scope: public-safe, runtime-neutral ShyftR context optimization, live context capture, and session-close harvest

## goal

Add a ShyftR context optimization layer that helps agent runtimes keep active prompts lean. The runtime owns mechanical prompt construction and compaction. ShyftR captures useful live context into cells, retrieves bounded packs when needed, records continuity feedback, and harvests durable lessons at session close.

## architecture

```text
runtime session
  |
  +-> live context cell
  |     high-churn working context during a session
  |
  +-> continuity cell
  |     context-management events, packs, feedback, and proposals
  |
  +-> memory cell
        reviewed durable memory
```

The feature should be framed as context optimization, not numeric context-window expansion. It should help work continue longer by reducing prompt bloat and improving retrieval of relevant context.

## human input requirement

None for tranches 0 through 11 when implemented against synthetic fixtures, repo-local temporary cells, and dry-run defaults.

Human/operator approval is required for:

- enabling live context capture in real runtime profiles;
- harvesting real private transcripts;
- writing outside repo-local temporary cells during tests;
- promoting live context directly into durable memory for real users;
- changing hosted/package/release posture;
- enabling any managed or authority-like mode.

## terminology policy

Use:

- live context cell;
- continuity cell;
- memory cell;
- session harvest;
- bounded pack;
- context optimization;
- runtime compactor;
- prompt bloat;
- advisory pack;
- review-gated proposal.

Avoid:

- numeric context-window expansion claims;
- infinite context;
- replacing the runtime compactor;
- default-on managed memory;
- real transcript examples;
- private runtime names in generic public docs.

## target files

Likely creates:

- `src/shyftr/live_context.py`
- `tests/test_live_context.py`
- `tests/test_session_harvest.py`
- `examples/integrations/runtime-context-optimization/session_closeout.json`
- `examples/integrations/runtime-context-optimization/live_context.jsonl`
- `docs/concepts/live-context-optimization-and-session-harvest.md`
- `docs/runtime-context-optimization-example.md`

Likely modifies:

- `src/shyftr/layout.py`
- `src/shyftr/cli.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/server.py`
- `src/shyftr/continuity.py`
- `src/shyftr/provider/memory.py`
- `docs/concepts/runtime-continuity-provider.md`
- `docs/concepts/runtime-integration-contract.md`
- `docs/concepts/storage-retrieval-learning.md`
- `docs/status/current-implementation-status.md` after implementation evidence exists

Forbidden without approval:

- mutating installed runtime profiles;
- committing real session transcripts;
- making live capture default-on;
- silent direct promotion into durable memory for real profiles;
- private ranking/scoring or advanced compaction heuristics in public `main`.

---

## tranche 0: source and status preflight

**Objective:** verify current repo state and avoid colliding with existing continuity-provider work.

**Files:**

- Read: `docs/concepts/runtime-continuity-provider.md`
- Read: `docs/plans/2026-05-07-runtime-continuity-provider-tranched-plan.md`
- Read: `docs/status/current-implementation-status.md`
- Read: `src/shyftr/layout.py`
- Read: `src/shyftr/continuity.py` if present

**Steps:**

1. Run `git status --short --branch`.
2. Confirm whether runtime continuity provider files are tracked, untracked, or already merged.
3. Read the target docs listed above.
4. Record whether this plan is being implemented before or after the continuity provider alpha lands.
5. Stop if there are merge conflicts or unknown untracked files that overlap the target paths.

**Verification:**

```bash
git status --short --branch
python scripts/public_readiness_check.py
```

Expected: no conflicts; readiness check passes before new edits.

---

## tranche 1: live context cell layout

**Objective:** add public-safe cell layout support for live context ledgers.

**Files:**

- Modify: `src/shyftr/layout.py`
- Test: `tests/test_layout.py` or `tests/test_live_context.py`

**Steps:**

1. Write failing tests for a `live_context` cell type or live-context ledger group.
2. Add ledger path definitions such as:
   - `ledger/live_context_events.jsonl`
   - `ledger/live_context_entries.jsonl`
   - `ledger/live_context_packs.jsonl`
   - `ledger/session_harvests.jsonl`
   - `ledger/session_harvest_proposals.jsonl`
3. Ensure existing memory and continuity cell layouts remain unchanged.
4. Ensure layout creation is idempotent.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_layout.py tests/test_live_context.py
```

---

## tranche 2: live context models

**Objective:** define typed records for live context capture.

**Files:**

- Create: `src/shyftr/live_context.py`
- Test: `tests/test_live_context.py`

**Models:**

- `LiveContextEntry`
- `LiveContextCaptureRequest`
- `LiveContextPackRequest`
- `LiveContextPack`
- `SessionHarvestRequest`
- `SessionHarvestReport`
- `HarvestDecision`

**Required fields:**

- runtime id;
- session id;
- task id or run id;
- entry id;
- entry kind;
- content;
- created timestamp;
- source reference;
- retention hint;
- sensitivity hint;
- metadata.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_live_context.py
python -m py_compile src/shyftr/live_context.py
```

---

## tranche 3: append-only live context capture

**Objective:** allow runtimes to append working context entries without polluting durable memory.

**Files:**

- Modify: `src/shyftr/live_context.py`
- Test: `tests/test_live_context.py`

**Steps:**

1. Write tests for appending entries to a temporary live context cell.
2. Add content-hash dedupe so repeated writes are idempotent.
3. Add entry kinds:
   - `active_goal`
   - `active_plan`
   - `active_artifact`
   - `decision`
   - `constraint`
   - `failure`
   - `recovery`
   - `verification`
   - `open_question`
4. Ensure capture does not write to memory ledgers.
5. Ensure capture is dry-run by default where exposed through external surfaces.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_live_context.py
```

---

## tranche 4: bounded live context pack

**Objective:** return relevant live working context without dumping the whole cell into the prompt.

**Files:**

- Modify: `src/shyftr/live_context.py`
- Test: `tests/test_live_context.py`

**Steps:**

1. Write tests for token and item caps.
2. Add query-driven selection over live context entries.
3. Add duplicate suppression against provided current prompt excerpts or entry ids.
4. Add role sections:
   - guidance items;
   - current-state items;
   - caution items;
   - open-question items;
   - excluded or suppressed items.
5. Add provenance for every selected item.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_live_context.py
```

---

## tranche 5: session harvest classifier

**Objective:** classify live context entries at session close.

**Files:**

- Modify: `src/shyftr/live_context.py`
- Test: `tests/test_session_harvest.py`

**Harvest buckets:**

- discard;
- archive;
- continuity_feedback;
- memory_candidate;
- direct_durable_memory;
- skill_proposal.

**Steps:**

1. Write synthetic fixture entries covering each bucket.
2. Implement deterministic baseline classification using entry kind, retention hint, sensitivity hint, and confidence metadata.
3. Do not use private ranking/scoring heuristics.
4. Write harvest reports to `session_harvests.jsonl` when `write=True`.
5. Ensure repeated harvests do not duplicate report rows.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_session_harvest.py
```

---

## tranche 6: harvest outputs and proposal wiring

**Objective:** connect harvest to continuity feedback and memory promotion proposals without silently mutating durable memory.

**Files:**

- Modify: `src/shyftr/live_context.py`
- Modify: `src/shyftr/continuity.py`
- Test: `tests/test_session_harvest.py`
- Test: `tests/test_continuity.py`

**Steps:**

1. Write tests for harvest-generated continuity improvement proposals.
2. Write tests for harvest-generated memory promotion proposals.
3. Ensure direct durable memory writes are disabled unless a local policy explicitly allows them.
4. Ensure proposals include source session id, entry ids, rationale, and confidence.
5. Ensure continuity cell feedback remains append-only.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_session_harvest.py tests/test_continuity.py
```

---

## tranche 7: CLI surface

**Objective:** expose repo-local commands for capture, pack, harvest, and status.

**Files:**

- Modify: `src/shyftr/cli.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_live_context.py`

**Commands:**

```bash
shyftr live-context capture <cell> <content> --runtime-id <id> --session-id <id> --kind <kind> [--write]
shyftr live-context pack <cell> <query> --runtime-id <id> --session-id <id> --max-items <n> --max-tokens <n> [--write]
shyftr live-context harvest <live-cell> <continuity-cell> <memory-cell> --runtime-id <id> --session-id <id> [--write]
shyftr live-context status <cell>
```

**Rules:**

- pack and harvest should support dry-run behavior;
- write behavior must be explicit;
- examples should use temporary or synthetic cells.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_cli.py tests/test_live_context.py tests/test_session_harvest.py
```

---

## tranche 8: MCP and HTTP surfaces

**Objective:** expose runtime-neutral adapter surfaces.

**Files:**

- Modify: `src/shyftr/mcp_server.py`
- Modify: `src/shyftr/server.py`
- Test: `tests/test_mcp_server.py`
- Test: `tests/test_server.py`

**MCP tools:**

- `shyftr_live_context_capture`
- `shyftr_live_context_pack`
- `shyftr_session_harvest`
- `shyftr_live_context_status`

**HTTP endpoints:**

- `POST /live-context/capture`
- `POST /live-context/pack`
- `POST /live-context/harvest`
- `GET /live-context/status`

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_mcp_server.py tests/test_server.py
```

---

## tranche 9: synthetic runtime example

**Objective:** prove the concept without real runtime data.

**Files:**

- Create: `examples/integrations/runtime-context-optimization/session_closeout.json`
- Create: `examples/integrations/runtime-context-optimization/live_context.jsonl`
- Create: `docs/runtime-context-optimization-example.md`
- Test: `tests/test_runtime_context_optimization_demo.py`

**Demo flow:**

```text
create temp cells
-> capture live context entries
-> request live context pack
-> simulate context pressure and continuity pack
-> close session
-> harvest live context
-> inspect proposals
```

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_runtime_context_optimization_demo.py
```

---

## tranche 10: docs and status alignment

**Objective:** document the feature without overclaiming.

**Files:**

- Modify: `docs/concepts/live-context-optimization-and-session-harvest.md`
- Modify: `docs/concepts/runtime-continuity-provider.md`
- Modify: `docs/concepts/runtime-integration-contract.md`
- Modify: `docs/concepts/storage-retrieval-learning.md`
- Modify: `docs/status/current-implementation-status.md` only after tests pass

**Steps:**

1. Document the three cell roles.
2. Document session-close harvest buckets.
3. Document prompt-bloat control rules.
4. Document that runtime compaction remains runtime-owned.
5. Add a capability-matrix row only after implementation evidence exists.
6. Avoid numeric context-window claims.

**Verification:**

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

---

## tranche 11: evaluation metrics

**Objective:** measure whether context optimization helps without relying on real data.

**Files:**

- Create or modify: `src/shyftr/live_context.py`
- Test: `tests/test_session_harvest.py`
- Docs: `docs/runtime-context-optimization-example.md`

**Metrics:**

- pack item count;
- estimated pack tokens;
- duplicate suppression count;
- harvest bucket counts;
- memory proposal count;
- continuity improvement proposal count;
- useful/ignored/harmful feedback rates in synthetic fixtures;
- stale item suppression count.

**Verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_live_context.py tests/test_session_harvest.py
```

---

## tranche 12: operator-gated real-runtime pilot

**Objective:** prepare but do not automatically enable real runtime integration.

**Gate:** requires explicit operator approval.

**Allowed after approval:**

- configure one runtime profile in shadow mode;
- capture live context into a local live context cell;
- run harvest in dry-run mode;
- inspect proposals before any durable memory write;
- record continuity feedback and monitor ledgers.

**Blocked without approval:**

- default-on capture;
- real transcript commits;
- managed mode;
- direct memory promotion beyond local policy;
- hosted or package-release claims.

---

## final verification bundle

Run from the repository root:

```bash
PYTHONPATH=.:src pytest -q
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
git status --short
```

Expected:

- all tests pass;
- terminology checks pass;
- public-readiness check passes;
- no whitespace errors;
- no real transcript or private runtime data in tracked files.

## closeout artifact

After implementation and verification, write:

```text
docs/status/YYYY-MM-DD-live-context-optimization-closeout.md
```

Include:

- implemented files;
- test commands and results;
- current capability-matrix update;
- open gates;
- known limitations;
- whether any real runtime profile was touched.
