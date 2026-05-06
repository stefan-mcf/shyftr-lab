# ShyftR Active Learning Follow-up Plan

> For Hermes: implement this only after the main MVP tranche plan is complete and pushed. Use subagent-driven-development for implementation, and keep each tranche small, tested, and committed.

Status: follow-up implementation plan. This plan extends `docs/plans/2026-04-24-shyftr-implementation-tranches.md` after the MVP and public proof-of-work tranches.

evidence material: `docs/evidences/2026-04-24-active-learning-cell-implementation-evidence.md`.

Goal: evolve ShyftR from a feedback-aware file-backed memory cell into an active recall-and-learning cell that retrieves what to do, warns what not to do, learns from non-application, audits high-confidence memory, and can scale the rebuildable grid without compromising cell ledger authority.

Architecture: canonical truth remains the append-only cell ledger under each cell. The regulator remains the review and policy layer for admission, promotion, retrieval, and export. Background maintenance jobs append evidence and proposals. Review-gated events alter durable authority. The grid remains rebuildable acceleration. packs/packs become role-labeled application packages. feedback/feedback records become the learning feedback.

Canonical system vocabulary:

- ShyftR cell: a bounded attachable memory unit.
- regulator: the review and policy layer controlling admission, promotion, retrieval, and export.
- cell ledger: the append-only canonical truth inside a cell.
- memory: a reviewed durable memory item.
- grid: the rebuildable retrieval and index layer.
- pack: the bounded memory bundle supplied to an agent or runtime.
- feedback: the evidenceback record that tells ShyftR whether retrieved memory helped or harmed.

Current implementation naming note:

This plan uses the public power vocabulary above, but implementation tranches must target the names that exist in the repo today. Current Python modules and primary classes are:

- `Source` / `candidate` / `memory` / `pattern` / `ruleProposal` in `src/shyftr/models.py`.
- Power aliases already exist in `models.py`: `Feed = Source`, `candidate = candidate`, `memory = memory`, `pattern = pattern`, `ruleProposal = ruleProposal`, `pack = pack`, and `feedback = feedback`.
- pack/pack code lives in `src/shyftr/pack.py`, with tests in `tests/test_pack.py`.
- feedback/feedback code lives in `src/shyftr/feedbacks.py`, with tests in `tests/test_feedbacks.py`.
- Runtime JSON API surfaces live under `src/shyftr/integrations/pack_api.py` and `src/shyftr/integrations/feedback_api.py`.

When a tranche says memory, pack, feedback, candidate, pattern, or rule, implement against the corresponding current class/module names unless that tranche explicitly performs a naming migration. Do not invent `pack.py`, `feedback.py`, `memory`, `pack`, or `feedback`-only modules while the current codebase still uses `pack.py`, `feedbacks.py`, `memory`, `pack`, and `feedback` as primary implementation names.

Core rules remains:

```text
cell ledgers are truth.
The regulator controls admission, promotion, retrieval, and export.
The grid is acceleration.
The pack/pack is application.
feedback/feedback is learning.
memory/memory confidence is evolution.
```

---

## Relationship to the main plan

This is a follow-up plan, not a replacement for the MVP plan.

Main plan:

- `docs/plans/2026-04-24-shyftr-implementation-tranches.md`
- MVP cut line ends after Tranche 11.
- Tranches 12-16 harden distillation, multi-cell evolution, hygiene, CLI, demo, and CI.

This follow-up should begin only after:

1. The full local lifecycle works from CLI.
2. pack/pack and feedback/feedback records exist.
3. Hybrid retrieval and confidence evolution exist.
4. CI/demo proof-of-work exists.
5. The repo is clean and synced.

Recommended sequencing:

```text
Main plan Tranches 0-16
  -> Active Learning Follow-up Tranches AL-0 through AL-8
```

---

## Follow-up feature set

This plan adds five capability groups:

1. Negative-space retrieval: retrieve relevant failure signatures and anti-patterns as Caution items.
2. pack/pack Miss learning: record when loaded memories/memories were not applied and learn from over-retrieval.
3. Sweep maintenance pass: asynchronously propose confidence and retrieval-affinity changes.
4. Challenger audit loop: search for counter-evidence against high-impact memories/memories and create Audit candidates/candidates.
5. Disk-backed grid scale path: define and later implement optional larger vector index adapters.

Authority regulator:

- Background jobs may append proposals, reports, and derived events.
- Background jobs must not silently delete, rewrite, isolate, or deprecate durable memory in the first implementation.
- Review acceptance creates durable authority changes.

---

## Tranche AL-0: Active-learning schema expansion

Objective: add the schema fields needed for role-labeled packs/packs, explicit feedback/feedback misses, audit findings, and future grid metadata, using the current implementation modules and class names.

Files:

- Modify: `src/shyftr/models.py`
- Modify: `src/shyftr/pack.py`
- Modify: `src/shyftr/feedbacks.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_pack.py`
- Modify: `tests/test_feedbacks.py`

Tasks:

1. Add or lock memory/memory kind values, preserving current `memory` serialization:
   - `success_pattern`
   - `failure_signature`
   - `anti_pattern`
   - `recovery_pattern`
   - `verification_heuristic`
   - `routing_heuristic`
   - `tool_quirk`
   - `escalation_rule`
   - `preference`
   - `constraint`
   - `workflow`
   - `rule_candidate`
   - `supersession`
   - `scope_exception`
   - `audit_finding`
2. Add memory/memory status values, preserving current `memory.status` compatibility:
   - `approved`
   - `challenged`
   - `quarantine_candidate`
   - `isolated`
   - `superseded`
   - `deprecated`
3. Add `pack_role` (or a backward-compatible `pack_role` alias if needed) to `packItem` records:
   - `guidance`
   - `caution`
   - `background`
   - `conflict`
4. Add `retrieval_id` to retrieval logs and link retrieval logs to `pack_id`.
5. Expand feedback/feedback records with current `feedback` ledger compatibility:
   - `ignored_memory_ids`
   - `ignored_caution_ids`
   - `contradicted_memory_ids`
   - `over_retrieved_memory_ids`
   - `pack_misses`
6. Add deterministic JSON serialization tests for all new fields.
7. Preserve backward compatibility for existing fixture records where possible.
8. Commit: `feat: expand active learning schemas`.

Acceptance criteria:

- Existing tests still pass.
- New memory/memory kinds and statuses serialize deterministically.
- pack/pack items can be role-labeled without changing canonical provenance.
- feedback/feedback records can explicitly represent non-application and contradiction.

---

## Tranche AL-1: Active-learning ledgers and layout

Objective: seed append-only proposal and audit ledgers required by Sweep and Challenger passes.

Files:

- Modify: `src/shyftr/layout.py`
- Modify: `src/shyftr/ledger.py`
- Modify: `src/shyftr/store/sqlite.py`
- Modify: `tests/test_layout.py`
- Modify: `tests/test_ledger.py`
- Modify: `tests/test_sqlite_store.py`

Tasks:

1. Seed additional ledgers in every cell:
   - `ledger/confidence_events.jsonl`
   - `ledger/retrieval_affinity_events.jsonl`
   - `ledger/audit_candidates.jsonl`
   - `ledger/audit_reviews.jsonl`
2. Add reader helpers for each new ledger.
3. Add idempotent initialization tests for new ledgers.
4. Update SQLite rebuild/materialization to include these ledgers as audit/proposal views.
5. Ensure all new ledgers are append-only and replayable.
6. Commit: `feat: add active learning ledgers`.

Acceptance criteria:

- Re-running cell initialization creates no duplicate or destructive changes.
- SQLite remains rebuildable from JSONL.
- Empty proposal ledgers do not break existing CLI flows.

---

## Tranche AL-2: Negative-space retrieval scoring

Objective: make retrieval aware of failure signatures, anti-patterns, challenged memories/memories, and risk feedbacks.

Files:

- Modify: `src/shyftr/retrieval/hybrid.py`
- Modify: `src/shyftr/pack.py`
- Modify: `tests/test_hybrid_retrieval.py`
- Modify: `tests/test_pack.py`

Tasks:

1. Add positive and negative scoring components to hybrid retrieval:
   - positive similarity
   - negative similarity
   - confidence weight
   - proven feedback weight
   - symbolic match weight
   - risk penalty
   - final score
2. Define a configurable Caution Coefficient for negative feedbacks.
3. Treat these memory/memory kinds as negative-space candidates:
   - `failure_signature`
   - `anti_pattern`
   - `supersession`
4. Penalize or label these statuses:
   - `challenged`
   - `quarantine_candidate`
5. Exclude these statuses from normal guidance by default:
   - `isolated`
   - `superseded`
   - `deprecated`
6. Return explainable score memories including `selection_reason`:
   - `positive_guidance`
   - `caution`
   - `suppressed`
   - `filtered`
   - `conflict`
7. Test that a valid task can retrieve both a positive guidance memory/memory and a related Caution memory/memory.
8. Test that a high-risk anti-pattern can suppress or demote weak positive guidance.
9. Commit: `feat: add negative-space retrieval scoring`.

Acceptance criteria:

- A `failure_signature` memory/memory can appear as a Caution item.
- An `anti_pattern` memory/memory can reduce the score of related positive guidance.
- Negative-space score components are visible in `score_memory` / `score_memories`.
- Related failures do not block positive work by default.

---

## Tranche AL-3: Role-labeled pack/pack assembly

Objective: split packs/packs into guidance, caution, background, and conflict roles while keeping token and item limits bounded.

Files:

- Modify: `src/shyftr/pack.py`
- Modify: `tests/test_pack.py`
- Modify: `docs/concepts/storage-retrieval-learning.md`

Tasks:

1. Update pack/pack assembly to produce role-labeled items.
2. Add helper accessors or serialization fields for:
   - `guidance_items`
   - `caution_items`
   - `background_items`
   - `conflict_items`
3. Reserve a small caution budget so warnings do not crowd out all guidance.
4. Preserve a total token cap across all roles.
5. Append retrieval logs with:
   - `candidate_ids`
   - `selected_ids`
   - `caution_ids`
   - `suppressed_ids`
   - expanded `score_memories`
6. Ensure operational-state pollution checks apply to all pack/pack roles.
7. Test that Caution items are clearly labeled and provenance-linked.
8. Test that packs/packs remain deterministic under item/token caps.
9. Commit: `feat: assemble role-labeled packs`.

Acceptance criteria:

- packs/packs separate action guidance from warnings.
- Caution items carry trust tier, kind, confidence, score, and provenance.
- Operational state does not leak into any pack/pack role.
- Retrieval logs are rich enough for later Sweep analysis.

---

## Tranche AL-4: pack/pack Miss feedback learning

Objective: record and report when retrieved memories/memories were not applied, without incorrectly treating every miss as false memory.

Files:

- Modify: `src/shyftr/feedbacks.py`
- Modify: `src/shyftr/confidence.py`
- Modify: `src/shyftr/reports/hygiene.py`
- Modify: `tests/test_feedbacks.py`
- Modify: `tests/test_confidence.py`
- Modify: `tests/test_hygiene.py`

Tasks:

1. Compare each feedback against its linked pack/retrieval log.
2. Derive `pack_miss_ids` from selected guidance items not applied, useful, harmful, or explicitly contradicted.
3. Allow explicit `pack_misses` with miss types:
   - `not_relevant`
   - `not_actionable`
   - `contradicted`
   - `duplicative`
   - `unknown`
4. Record ignored Caution items separately from ignored guidance items.
5. Ensure a single miss does not lower global memory/memory confidence by itself.
6. Add hygiene summaries for:
   - most missed memories/memories
   - most over-retrieved memories/memories
   - memories/memories with high miss rate but high confidence
   - memories/memories with mixed useful/harmful feedback
7. Test miss derivation and explicit miss preservation.
8. Commit: `feat: record pack/pack Miss feedback`.

Acceptance criteria:

- feedback/feedback recording captures loaded-but-unused memories/memories.
- pack/pack Misses are visible in reports.
- Confidence changes distinguish harmful application from non-application.
- Misses are available for retrieval-affinity proposals in later tranches.

---

## Tranche AL-5: Sweep dry-run reports

Objective: add a safe maintenance pass that analyzes retrieval and feedback history without mutating durable authority.

Files:

- Create: `src/shyftr/sweep.py`
- Modify: `src/shyftr/reports/hygiene.py`
- Modify: `src/shyftr/cli.py`
- Create: `tests/test_sweep.py`
- Modify: `tests/test_cli.py`

Tasks:

1. Implement `shyftr sweep --cell <path> --dry-run`.
2. Read:
   - retrieval logs
   - feedback
   - audit candidates
   - confidence events
   - retrieval-affinity events
   - approved/deprecated/isolated memory/memory ledgers
3. Compute per-memory/memory metrics:
   - retrieval count
   - application count
   - useful count
   - harmful count
   - miss count
   - application rate
   - useful rate
   - harmful rate
   - miss rate
4. Compute per-query-tag or per-query-cluster summaries where available.
5. Emit a deterministic report containing proposed actions:
   - `retrieval_affinity_decrease`
   - `confidence_decrease`
   - `confidence_increase`
   - `manual_review`
   - `split_memory`
   - `supersession_candidate`
6. Ensure dry-run writes no ledger records unless an explicit output path is requested.
7. Test deterministic report output from fixtures.
8. Commit: `feat: add Sweep dry-run analysis`.

Acceptance criteria:

- Sweep runs without network access.
- Sweep never rewrites history.
- Repeated fixture runs produce stable reports.
- Repeated misses produce affinity proposals, not deprecation.
- Harmful applied memories/memories produce confidence-decrease proposals.

---

## Tranche AL-6: Sweep proposal events

Objective: allow the Sweep to append low-authority proposal events to active-learning ledgers.

Files:

- Modify: `src/shyftr/sweep.py`
- Modify: `src/shyftr/confidence.py`
- Modify: `src/shyftr/cli.py`
- Modify: `tests/test_sweep.py`
- Modify: `tests/test_confidence.py`
- Modify: `tests/test_cli.py`

Tasks:

1. Implement `shyftr sweep --cell <path> --propose`.
2. Append proposal records to:
   - `ledger/confidence_events.jsonl`
   - `ledger/retrieval_affinity_events.jsonl`
3. Deduplicate open proposals using stable proposal keys.
4. Keep proposal records separate from accepted confidence changes.
5. Add optional `--apply-low-risk` for retrieval-affinity events only.
6. Do not allow Sweep to isolate, deprecate, or delete memories/memories.
7. Add report output that lists written proposal IDs.
8. Commit: `feat: let Sweep append active learning proposals`.

Acceptance criteria:

- Proposal writes are append-only.
- Re-running Sweep does not duplicate identical open proposals.
- `--apply-low-risk` cannot alter memory status or destructive authority.
- Confidence-event proposals remain reviewable.

---

## Tranche AL-7: Challenger audit loop

Objective: add an audit pass that challenges high-impact memories/memories by searching for counter-evidence and creating Audit candidates/candidates.

Files:

- Create: `src/shyftr/audit/challenger.py`
- Modify: `src/shyftr/audit.py`
- Modify: `src/shyftr/cli.py`
- Create: `tests/test_challenger.py`
- Modify: `tests/test_audit.py`
- Modify: `tests/test_cli.py`

Tasks:

1. Implement `shyftr challenge --cell <path> --dry-run`.
2. Implement optional target selection:
   - `--memory-id <id>`
   - `--top-impact N`
3. Rank target memories/memories by:
   - confidence
   - retrieval frequency
   - application frequency
   - rule promotion readiness
   - old age with recent continued use
   - recent harmful feedback
   - unresolved miss/contradiction feedbacks
4. Search counter-evidence in:
   - evidences
   - candidates
   - feedback
   - audit records
   - newer memories/memories
   - deprecated/superseded memories/memories
5. Classify findings as:
   - `direct_contradiction`
   - `supersession`
   - `scope_exception`
   - `environment_specific`
   - `temporal_update`
   - `ambiguous_counterevidence`
   - `policy_conflict`
   - `implementation_drift`
6. Emit Audit candidates/candidates to `ledger/audit_candidates.jsonl` when run with `--propose`.
7. Keep quarantine and deprecation review-gated.
8. Test contradiction, supersession, and scope-exception fixtures.
9. Commit: `feat: add Challenger audit loop`.

Acceptance criteria:

- Challenger can identify high-impact memories/memories for audit.
- Challenger emits Audit candidates/candidates with counter-Evidence IDs.
- Challenger distinguishes contradiction from scope exception and supersession.
- No memory is deleted or silently demoted by Challenger.

---

## Tranche AL-8: Audit review and quarantine workflow

Objective: add explicit review commands for Audit candidates/candidates and wire challenged/quarantine status into retrieval behavior.

Files:

- Modify: `src/shyftr/audit.py`
- Modify: `src/shyftr/retrieval/hybrid.py`
- Modify: `src/shyftr/pack.py`
- Modify: `src/shyftr/cli.py`
- Modify: `tests/test_audit.py`
- Modify: `tests/test_hybrid_retrieval.py`
- Modify: `tests/test_pack.py`
- Modify: `tests/test_cli.py`

Tasks:

1. Implement audit review records in `ledger/audit_reviews.jsonl`.
2. Add CLI commands:
   - `shyftr audit list --cell <path>`
   - `shyftr audit review --cell <path> --audit-id <id> --accept|--reject`
   - `shyftr audit resolve --cell <path> --audit-id <id>`
3. On accepted audit findings, allow reviewed actions:
   - mark memory challenged
   - propose quarantine
   - propose supersession
   - propose confidence decrease
   - request rewrite or split
4. Keep final quarantine/deprecation status changes explicit and review-gated.
5. Update retrieval behavior:
   - low/medium challenged memories/memories may appear with warning labels.
   - high/critical quarantine candidates are excluded from normal guidance by default.
   - audit/debug mode can include all statuses with labels.
6. Test that challenged memories/memories are labeled or penalized.
7. Test that quarantine candidates do not appear as ordinary guidance.
8. Commit: `feat: add audit review workflow`.

Acceptance criteria:

- Audit findings are reviewable and replayable.
- Retrieval behavior respects challenged/quarantine status.
- Review actions append events instead of rewriting past records.
- High-risk memory can be contained without losing provenance.

---

## Tranche AL-9: Disk-backed grid adapter metadata

Objective: prepare the grid abstraction for optional disk-backed vector indexes without adding heavy dependencies by default.

Files:

- Modify: `src/shyftr/retrieval/vector.py`
- Modify: `src/shyftr/retrieval/embeddings.py`
- Modify: `src/shyftr/store/sqlite.py`
- Modify: `src/shyftr/cli.py`
- Modify: `tests/test_vector_retrieval.py`
- Create: `tests/test_grid_metadata.py`

Tasks:

1. Define or refine a `VectorIndex` protocol that supports:
   - rebuild
   - query
   - clear
   - status
   - metadata export
2. Record index metadata:
   - `index_id`
   - `cell_id`
   - `backend`
   - `embedding_model`
   - `embedding_dimension`
   - `embedding_version`
   - evidence ledger offsets or hashes
   - memory count
   - created timestamp
3. Add CLI commands:
   - `shyftr grid status --cell <path>`
   - `shyftr grid rebuild --cell <path>`
4. Detect stale indexes when embedding metadata or ledger offsets change.
5. Keep tests dependency-free with deterministic embeddings and local indexes.
6. Commit: `feat: add grid adapter metadata`.

Acceptance criteria:

- Vector index metadata is inspectable.
- Rebuild can wipe and recreate the local vector index from ledgers.
- The grid remains an acceleration layer, not canonical truth.
- No LanceDB/Qdrant dependency is required for default tests.

---

## Tranche AL-10: Optional LanceDB adapter spike

Objective: add an optional disk-backed vector adapter only after the local grid interface is stable.

Files:

- Create: `src/shyftr/retrieval/lancedb_adapter.py`
- Modify: `pyproject.toml`
- Modify: `src/shyftr/retrieval/vector.py`
- Modify: `src/shyftr/cli.py`
- Create: `tests/test_lancedb_adapter.py`

Tasks:

1. Add LanceDB as an optional extra, not a default dependency.
2. Implement a LanceDB-backed `VectorIndex` adapter behind the same protocol.
3. Store LanceDB files under the cell `grid/` directory.
4. Record backend metadata as `lancedb`.
5. Add skip-if-missing tests for the optional extra.
6. Add benchmark or smoke command for local comparison against the default vector adapter.
7. Avoid absolute performance claims in docs and CLI output.
8. Commit: `feat: add optional LanceDB grid adapter`.

Acceptance criteria:

- Default test suite passes without LanceDB installed.
- Optional LanceDB tests pass when extras are installed.
- The adapter is rebuildable from cell ledgers.
- LanceDB is clearly documented as optional acceleration, not durable truth.

---

## Final verification before completing the follow-up plan

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

## Follow-up cut line

The first active-learning cut is complete after AL-6:

1. active-learning schemas
2. active-learning ledgers
3. negative-space retrieval
4. role-labeled packs/packs
5. pack/pack Miss feedback/feedback
6. Sweep dry-run and proposal events

AL-7 and AL-8 add self-audit and quarantine workflows.

AL-9 and AL-10 prepare and optionally implement larger disk-backed grid adapters.
