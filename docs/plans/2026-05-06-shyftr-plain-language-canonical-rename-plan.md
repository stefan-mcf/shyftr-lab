# ShyftR Plain-Language Canonical Rename Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Complete a deep ShyftR terminology migration from mixed legacy/power-themed vocabulary to the plain lifecycle `evidence -> candidate -> memory -> pattern -> rule`, while preserving compatibility, processing all docs/plans/mentions/capitalization, and leaving no unclassified legacy terms behind.

**Architecture:** This is a phased docs + code + compatibility + verification migration. Public docs and glossary establish the new canonical terms first, code introduces new model/API/CLI names with backward-compatible aliases, fixtures/tests migrate next, and final tranches enforce stale-term/capitalization scans so future changes cannot reintroduce the old vocabulary accidentally.

**Tech Stack:** Python 3.11+, argparse CLI, dataclass models, append-only JSONL ledgers, pytest, FastAPI service docs, React console docs, ripgrep-style scans, repo-local validation scripts.

---

## Human input requirement

None for planning and safe repo-local implementation tranches.

Final human approval is required only before any of these side effects:

- pushing to GitHub;
- publishing a package/release/tag;
- deleting compatibility aliases for old user data;
- declaring backward compatibility intentionally dropped;
- changing public repo visibility or inviting testers based on the rename.

All implementation tranches below are repo-local and should not mutate global Hermes config, private memory data, external services, browser sessions, credentials, or production user cells.

## Scope boundary

Canonical repo:

- the canonical public ShyftR checkout

Source decision note:

- `docs/sources/2026-05-06-shyftr-plain-lifecycle-naming-review.md`

Allowed mutation surface:

- public docs under `README.md`, `docs/`, `examples/`;
- source code under `src/shyftr/`;
- tests and fixtures under `tests/`;
- console source/docs under `apps/console/`;
- scripts under `scripts/`;
- repo-local compatibility/migration docs;
- this plan and status docs.

Forbidden without approval:

- deleting real user cells or runtime memory;
- irreversible ledger migration without backup/restore proof;
- pushing to remote;
- changing package distribution status;
- mutating the operator-local Hermes configuration except separately approved skill doctrine updates after the repo plan is proven.

## Canonical target vocabulary

### Lifecycle terms

Use these as canonical public terms:

```text
evidence -> candidate -> memory -> pattern -> rule
```

Formal glossary labels may use title case:

```text
Evidence -> Candidate -> Memory -> Pattern -> Rule
```

Normal prose must use lowercase common nouns:

- evidence
- candidate
- memory
- pattern
- rule

### Current and legacy mappings to process

| Old/current term | New canonical term | Notes |
| --- | --- | --- |
| Pulse | Evidence | Current themed public term. |
| pulse | evidence | Normal prose lowercase. |
| Source | Evidence | Legacy implementation/model term. |
| source | evidence | Rename only when it means ShyftR raw input evidence; keep generic programming uses where appropriate but classify them. |
| Feed | Evidence | Legacy/source-doc term. |
| feed | evidence | Keep only in historical migration notes if needed. |
| Spark | Candidate | Current themed public term. |
| spark | candidate | Normal prose lowercase. |
| Fragment | Candidate | Legacy implementation/model term. |
| fragment | candidate | Rename when it means extracted candidate memory. |
| Charge | Memory | Current themed public term. |
| charge | memory | Normal prose lowercase. |
| Trace | Memory | Legacy implementation/model term. |
| trace | memory | Rename when it means approved durable memory. Keep generic stack traces only if any exist and classify. |
| Coil | Pattern | Current themed public term. |
| coil | pattern | Normal prose lowercase. |
| Circuit | Pattern | Prior source-doc alternative; migrate to pattern. |
| circuit | pattern | Rename when lifecycle concept. |
| Alloy | Pattern | Legacy implementation/model term. |
| alloy | pattern | Rename when lifecycle concept. |
| Rail | Rule | Current themed public term. |
| rail | rule | Normal prose lowercase. |
| Doctrine | Rule | Legacy implementation/model term. |
| doctrine | rule | Rename when lifecycle concept; keep only in private historical notes if required. |
| DoctrineProposal | RuleProposal | Implementation class/API rename with alias. |
| doctrine_id | rule_id | Schema rename with backward read support. |
| source_id | evidence_id | Schema rename with backward read support. |
| fragment_id | candidate_id | Schema rename with backward read support. |
| trace_id | memory_id | Schema rename with backward read support. |
| alloy_id | pattern_id | Schema rename with backward read support. |
| source_fragment_ids | source_candidate_ids or evidence_candidate_ids | Prefer `source_candidate_ids` only if code needs transitional clarity; final should be `candidate_ids` or `source_candidate_ids` depending model needs. |
| source_trace_ids | source_memory_ids or memory_ids | Prefer `memory_ids` when provenance is already represented elsewhere. |
| source_alloy_ids | source_pattern_ids or pattern_ids | Prefer `pattern_ids` when provenance is already represented elsewhere. |

### Support terms

Keep as canonical unless a tranche explicitly decides otherwise:

| Current term | Target style | Notes |
| --- | --- | --- |
| Cell | cell in prose, Cell in glossary/headings | Keep concept. Lowercase in normal prose. |
| Cell Ledger | cell ledger / ledger in prose | Keep. |
| Regulator | regulator in prose | Keep. |
| Grid | grid in prose | Keep for now; means rebuildable retrieval/index layer. |
| Pack | pack in prose | Keep; optionally `context pack` in explanatory prose. |
| Signal | feedback | Rename; clearer support term. |
| signal | feedback | Rename unless generic telemetry signal. |
| Outcome | Feedback | Legacy implementation/API term. |
| outcome | feedback | Rename when it means pack-use result. |
| Loadout | Pack | Legacy implementation/API term. |
| loadout | pack | Rename. |
| Isolation | Quarantine | Rename when memory safety state. |
| isolation | quarantine | Keep generic security/isolation only if unrelated and classify. |
| Decay | decay | Keep lowercase in prose. |

## Capitalization house style

Use lowercase common nouns in normal prose. Reserve title case/capitals for:

- sentence starts;
- headings;
- diagrams;
- glossary labels;
- UI labels that literally display the label;
- class/type/API names where code requires capitalization;
- the product name `ShyftR` and CLI/package name `shyftr`.

Correct prose:

```text
Evidence enters the cell ledger. A candidate is reviewed into memory. Related memories can form a pattern. A high-confidence pattern can become a rule.
```

Avoid:

```text
Evidence enters the Cell Ledger. A Candidate is reviewed into Memory. Related Memories can form a Pattern. A high-confidence Pattern can become a Rule.
```

Expected final docs style:

- lifecycle diagrams may say `Evidence -> Candidate -> Memory -> Pattern -> Rule`;
- paragraphs should say `evidence`, `candidate`, `memory`, `pattern`, `rule`, `cell`, `ledger`, `regulator`, `grid`, `pack`, `feedback`, `decay`, `quarantine`.

## Current inventory snapshot

Initial scan across README/docs/examples/src/tests/apps found these notable counts:

```text
Cell 545
Regulator 66
Pulse 240
Spark 214
Charge 471
Coil 63
Rail 90
Grid 111
Pack 388
Signal 269
Isolation 33
Source 103
Fragment 90
Trace 228
Alloy 79
Doctrine 26
Loadout 75
Outcome 88
Feed 2
Boundary 4
```

Top impacted implementation files include:

- `src/shyftr/models.py`
- `src/shyftr/cli.py`
- `src/shyftr/ingest.py`
- `src/shyftr/extract.py`
- `src/shyftr/promote.py`
- `src/shyftr/loadout.py`
- `src/shyftr/outcomes.py`
- `src/shyftr/confidence.py`
- `src/shyftr/sweep.py`
- `src/shyftr/resonance.py`
- `src/shyftr/distill/alloys.py`
- `src/shyftr/distill/doctrine.py`
- `src/shyftr/integrations/loadout_api.py`
- `src/shyftr/integrations/outcome_api.py`
- `src/shyftr/console_api.py`
- `src/shyftr/audit/challenger.py`
- retrieval modules and store modules that use `trace`/`source` naming

Top impacted tests include:

- `tests/test_models.py`
- `tests/test_ingest.py`
- `tests/test_extract.py`
- `tests/test_review.py`
- `tests/test_promote.py`
- `tests/test_loadout.py`
- `tests/test_outcomes.py`
- `tests/test_alloys.py`
- `tests/test_doctrine.py`
- `tests/test_resonance.py`
- `tests/test_challenger.py`
- `tests/test_sweep.py`
- `tests/test_sqlite_store.py`
- `tests/test_sparse_retrieval.py`
- `tests/test_hybrid_retrieval.py`
- `tests/test_runtime_integration_demo.py`
- `tests/test_loadout_api.py`
- `tests/test_outcome_api.py`

Top impacted docs include:

- `README.md`
- `docs/concepts/power-vocabulary.md`
- `docs/concepts/cells.md`
- `docs/concepts/storage-retrieval-learning.md`
- `docs/concepts/runtime-integration-contract.md`
- `docs/concepts/memory-provider-contract.md`
- `docs/concepts/differentiation-and-positioning.md`
- `docs/concepts/universal-memory-substrate.md`
- all `docs/plans/2026-04-24-*.md`
- `docs/demo.md`
- `docs/demo-runtime-integration.md`
- `docs/api.md`
- `docs/console.md`
- `examples/README.md`
- example lifecycle files under `examples/`

## Stop conditions

Stop and write a blocker note if any of these occur:

- a schema rename would make existing cells unreadable without a clear alias path;
- a ledger/file rename would destroy or hide data without backup/restore proof;
- public docs require a product positioning decision beyond the approved vocabulary;
- tests reveal incompatible external behavior that needs a human decision;
- stale-term scans still show old terms in non-migration contexts after two cleanup passes.

Do not stop for routine test failures caused by expected rename work; fix them in the appropriate tranche.

---

## Tranche 0: Baseline verification and rename ledger

**Objective:** Establish a clean starting point, create a tracked rename ledger, and prevent ambiguous untracked changes from contaminating the migration.

**Files:**

- Read: `README.md`
- Read: `docs/sources/2026-05-06-shyftr-plain-lifecycle-naming-review.md`
- Read: `src/shyftr/models.py`
- Create: `docs/status/plain-language-rename-ledger.md`

**Steps:**

1. Run baseline status:

   ```bash
   git status --short --branch
   git rev-parse HEAD
   ```

   Expected: clean or only the plan/source note changes intentionally present.

2. Run baseline tests:

   ```bash
   python -m pytest -q
   ```

   Expected: pass before rename work begins. If not, record pre-existing failures in the ledger and do not attribute them to rename work.

3. Create `docs/status/plain-language-rename-ledger.md` with sections:

   - decision summary;
   - old-to-new mapping;
   - files touched;
   - compatibility aliases intentionally kept;
   - stale-term scan results;
   - capitalization scan results;
   - test evidence;
   - open decisions.

4. Commit or checkpoint if the workflow requires frequent commits:

   ```bash
   git add docs/plans/2026-05-06-shyftr-plain-language-canonical-rename-plan.md docs/sources/2026-05-06-shyftr-plain-lifecycle-naming-review.md docs/status/plain-language-rename-ledger.md
   git commit -m "docs: plan plain-language terminology migration"
   ```

   If not committing yet, record this as a pending checkpoint in the ledger.

**Verification:**

```bash
git diff --check
git status --short
```

Expected: only intended plan/ledger/source-note files changed if not committed.

---

## Tranche 1: Add terminology inventory and stale-term guard scripts

**Objective:** Make the rename measurable before mass edits begin.

**Files:**

- Create: `scripts/terminology_inventory.py`
- Create or modify: `scripts/check.sh`
- Create: `tests/test_terminology_inventory.py` if the script has reusable logic
- Modify: `docs/status/plain-language-rename-ledger.md`

**Steps:**

1. Implement `scripts/terminology_inventory.py` with repo-local scanning only.

2. The script must report:

   - old/current themed terms;
   - legacy implementation terms;
   - support legacy terms;
   - capitalized canonical terms in prose contexts;
   - intentional allowlist matches.

3. Use an allowlist file or inline allowlist for migration-only documents:

   - this plan;
   - `docs/status/plain-language-rename-ledger.md`;
   - a future compatibility document;
   - historical source notes only when explicitly marked historical.

4. Add command modes:

   ```bash
   python scripts/terminology_inventory.py --report
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   ```

5. Add focused tests for word-boundary handling:

   - `traceback` must not match `trace`;
   - `source` in `source code` can be classified as generic or allowlisted;
   - `ShyftR` remains allowed;
   - headings/glossary/diagram labels can use title case;
   - prose `Candidate`, `Memory`, `Pattern`, `Rule` should be flagged when not sentence-start/headings/glossary/table labels.

6. Wire the fail modes into `scripts/check.sh` only after the repo has been migrated enough that the check can pass. Until then, add it as a commented or documented pending check in the ledger.

**Verification:**

```bash
python scripts/terminology_inventory.py --report
python -m pytest tests/test_terminology_inventory.py -q
git diff --check
```

Expected: script runs deterministically and produces a complete inventory. Fail modes may still fail until later tranches; record current counts in the ledger.

---

## Tranche 2: Canonical glossary and public vocabulary docs

**Objective:** Replace the old power vocabulary page with the plain-language vocabulary and capitalization house style.

**Files:**

- Rename or replace: `docs/concepts/power-vocabulary.md`
- Consider creating: `docs/concepts/plain-language-vocabulary.md`
- Modify: `README.md`
- Modify: `docs/concepts/cells.md`
- Modify: `docs/concepts/storage-retrieval-learning.md`
- Modify: `docs/status/plain-language-rename-ledger.md`

**Steps:**

1. Decide file naming:

   Preferred: create `docs/concepts/plain-language-vocabulary.md` and update links away from `power-vocabulary.md`.

   Compatibility option: keep `power-vocabulary.md` as a short redirect-style historical page that says ShyftR formerly used power vocabulary and now uses plain lifecycle terms. If retained, it must be explicitly migration/historical and allowlisted.

2. Write the canonical glossary:

   ```text
   evidence -> candidate -> memory -> pattern -> rule
   ```

3. Include definitions:

   - evidence: raw append-only proof;
   - candidate: extracted possible lesson awaiting review;
   - memory: reviewed durable memory;
   - pattern: recurring lesson/workflow distilled across memories;
   - rule: high-confidence reviewed guidance;
   - cell, ledger, regulator, grid, pack, feedback, decay, quarantine.

4. Add the capitalization house style.

5. Update README summary, why-it-exists bullets, quickstart explanation, safety model, architecture diagram, and docs index.

6. Update `docs/concepts/cells.md` and `docs/concepts/storage-retrieval-learning.md` to use lowercase prose and the new lifecycle.

7. Run stale-term report and record remaining matches.

**Verification:**

```bash
python scripts/terminology_inventory.py --report
python scripts/public_readiness_check.py
bash scripts/check.sh || true
```

Expected: public glossary and README use the new plain lifecycle. `bash scripts/check.sh` may still fail if terminology guard is not fully enabled; record status honestly.

---

## Tranche 3: Public docs, examples, demo docs, and API docs

**Objective:** Process all public-facing docs and examples so testers see only the new vocabulary except in explicit compatibility notes.

**Files:**

- Modify: `docs/demo.md`
- Modify: `docs/demo-runtime-integration.md`
- Modify: `docs/api.md`
- Modify: `docs/console.md`
- Modify: `docs/status/current-implementation-status.md`
- Modify: `docs/status/alpha-readiness.md`
- Modify: `examples/README.md`
- Modify/rename: `examples/pulse.md`
- Modify/rename: `examples/integrations/worker-runtime/pulse-closeout.md`
- Modify: example config/fixture references that mention pulse/source/fragment/trace/loadout/outcome

**Steps:**

1. Rename example files where the filename is public vocabulary:

   ```text
   examples/pulse.md -> examples/evidence.md
   examples/integrations/worker-runtime/pulse-closeout.md -> examples/integrations/worker-runtime/evidence-closeout.md
   ```

2. Update all scripts/docs/tests that reference renamed example files.

3. Update demo command examples to prefer new commands after CLI tranches land. If CLI command aliases are not implemented yet, add temporary notes in the ledger and return after Tranche 7.

4. Replace prose terms:

   - pulse/source -> evidence;
   - spark/fragment -> candidate;
   - charge/trace -> memory;
   - coil/alloy/circuit -> pattern;
   - rail/doctrine -> rule;
   - signal/outcome -> feedback;
   - loadout -> pack;
   - isolation -> quarantine.

5. Lowercase canonical nouns in paragraphs.

6. Keep title case in headings only when they are heading labels.

**Verification:**

```bash
python scripts/terminology_inventory.py --report
rg -n 'pulse|Pulse|spark|Spark|charge|Charge|coil|Coil|rail|Rail|loadout|Loadout|outcome|Outcome' README.md docs examples
bash examples/run-local-lifecycle.sh
```

Expected: remaining matches are either gone or recorded as intentional compatibility/historical matches.

---

## Tranche 4: Historical plans, sources, feeds, and runbooks cleanup

**Objective:** Process all older plans and source docs so repo-wide docs do not leave confusing mixed terminology behind.

**Files:**

- Modify: all `docs/plans/*.md`
- Modify: all `docs/sources/*.md`
- Modify: all `docs/feeds/*.md`
- Modify: all `docs/runbooks/*.md`
- Create: `docs/concepts/terminology-compatibility.md`
- Modify: `docs/status/plain-language-rename-ledger.md`

**Steps:**

1. For active plans, fully migrate terms to the new vocabulary and lowercase prose.

2. For historical source docs that should preserve original wording, add a short header:

   ```text
   Historical vocabulary note: this source originally used older ShyftR terms. Current canonical terms are evidence, candidate, memory, pattern, rule, pack, feedback, and quarantine.
   ```

   Then either:

   - migrate terms where the doc is still used operationally; or
   - mark the file as historical and allowlist it in terminology inventory.

3. Create `docs/concepts/terminology-compatibility.md` with mapping tables and compatibility rules.

4. Ensure no public-facing current plan says the old lifecycle is canonical.

5. Ensure no public-facing plan capitalizes lifecycle nouns in prose.

**Verification:**

```bash
python scripts/terminology_inventory.py --report
python scripts/terminology_inventory.py --fail-on-public-stale || true
python scripts/terminology_inventory.py --fail-on-capitalized-prose || true
git diff --check
```

Expected: old terms remain only in `terminology-compatibility.md`, this plan, the rename ledger, and explicitly historical source sections.

---

## Tranche 5: Model layer rename with compatibility aliases

**Objective:** Introduce canonical Python model names and schema fields while preserving backward reads for existing ledgers and tests during transition.

**Files:**

- Modify: `src/shyftr/models.py`
- Modify: `tests/test_models.py`
- Modify: `docs/concepts/terminology-compatibility.md`
- Modify: `docs/status/plain-language-rename-ledger.md`

**Steps:**

1. Add new canonical dataclasses:

   - `Evidence`
   - `Candidate`
   - `Memory`
   - `Pattern`
   - `RuleProposal`
   - `Pack`
   - `Feedback`

2. Define canonical fields:

   - `evidence_id`
   - `candidate_id`
   - `memory_id`
   - `pattern_id`
   - `rule_id`
   - `pack_id`
   - `feedback_id`
   - `candidate_ids`
   - `memory_ids`
   - `pattern_ids`

3. Add backward-compatible `from_dict` alias handling for old field names:

   - `source_id` -> `evidence_id`
   - `fragment_id` -> `candidate_id`
   - `trace_id` -> `memory_id`
   - `alloy_id` -> `pattern_id`
   - `doctrine_id` -> `rule_id`
   - `loadout_id` -> `pack_id`
   - `outcome_id` -> `feedback_id`
   - `source_fragment_ids` -> `candidate_ids`
   - `source_trace_ids` -> `memory_ids`
   - `source_alloy_ids` -> `pattern_ids`

4. Decide serialization policy:

   Preferred: new models serialize canonical field names only.

   Compatibility: old aliases read successfully but are not emitted unless a specific compatibility export flag is later added.

5. Keep old class aliases temporarily:

   ```python
   Source = Evidence
   Fragment = Candidate
   Trace = Memory
   Alloy = Pattern
   DoctrineProposal = RuleProposal
   Loadout = Pack
   Outcome = Feedback
   ```

   Mark them deprecated in comments/docstrings.

6. Update `TRACE_KINDS` to `MEMORY_KINDS` and decide value migration:

   - `rail_candidate` -> `rule_candidate`;
   - other kind values can remain if already plain enough.

7. Update tests to assert:

   - canonical names serialize canonical fields;
   - legacy payloads load correctly;
   - unknown old fields still fail if not mapped;
   - aliases remain importable during compatibility period.

**Verification:**

```bash
python -m pytest tests/test_models.py -q
python -m pytest tests/test_import.py -q
```

Expected: model compatibility and import compatibility both pass.

---

## Tranche 6: Ledger layout and file naming compatibility

**Objective:** Rename ledger/file concepts without losing ability to read old cells.

**Files:**

- Modify: `src/shyftr/layout.py`
- Modify: `src/shyftr/ledger.py`
- Modify: `src/shyftr/ledger_verify.py`
- Modify: `src/shyftr/backup.py`
- Modify: `tests/test_layout.py`
- Modify: `tests/test_ledger.py`
- Modify: `tests/test_ledger_verification.py`
- Modify: `tests/test_backup_restore.py`
- Modify: fixtures under `tests/fixtures/`

**Steps:**

1. Define canonical ledger paths for new cells:

   ```text
   ledger/evidence.jsonl
   ledger/candidates.jsonl
   ledger/memories/approved.jsonl
   ledger/patterns/proposed.jsonl
   ledger/rules/proposed.jsonl
   ledger/packs.jsonl
   ledger/feedback.jsonl
   ```

2. Define legacy read aliases:

   ```text
   ledger/sources.jsonl -> ledger/evidence.jsonl
   ledger/fragments.jsonl -> ledger/candidates.jsonl
   ledger/traces/approved.jsonl -> ledger/memories/approved.jsonl
   ledger/alloys/proposed.jsonl -> ledger/patterns/proposed.jsonl
   ledger/doctrine/proposals.jsonl -> ledger/rules/proposed.jsonl
   ledger/loadouts.jsonl -> ledger/packs.jsonl
   ledger/outcomes.jsonl -> ledger/feedback.jsonl
   ```

3. New cells should create canonical paths only.

4. Existing cells with old paths should remain readable. Do not auto-migrate in normal reads.

5. Add an explicit migration helper later only if needed:

   ```bash
   shyftr migrate-terminology <cell_path> --dry-run
   shyftr migrate-terminology <cell_path> --write --backup-first
   ```

   This helper is optional and can be deferred unless tests or alpha use require it.

6. Backup/restore and ledger verification must understand both canonical and legacy paths.

7. Update fixture cells or create dual fixtures:

   - one new canonical fixture;
   - one legacy fixture proving backward reads.

**Verification:**

```bash
python -m pytest tests/test_layout.py tests/test_ledger.py tests/test_ledger_verification.py tests/test_backup_restore.py -q
```

Expected: new cells use canonical file names; legacy fixtures remain readable.

---

## Tranche 7: CLI command rename and compatibility aliases

**Objective:** Make the user-facing CLI speak the new vocabulary while preserving old commands as deprecated aliases.

**Files:**

- Modify: `src/shyftr/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_demo_flow.py`
- Modify: `docs/demo.md`
- Modify: `README.md`
- Modify: `examples/run-local-lifecycle.sh`

**Steps:**

1. Update preferred command names:

   ```text
   ingest remains ingest, but help says evidence file
   fragment -> candidate
   review approve/reject <candidate_id>
   promote -> memory
   loadout -> pack
   outcome -> feedback
   ```

   Candidate command set:

   ```bash
   shyftr ingest <cell_path> <evidence_file> --kind KIND
   shyftr candidate <cell_path> <evidence_id>
   shyftr review approve <cell_path> <candidate_id> --reviewer NAME --rationale TEXT
   shyftr memory <cell_path> <candidate_id> --promoter NAME
   shyftr pack <cell_path> <query> --task-id ID
   shyftr feedback <cell_path> <pack_id> <result> [options]
   ```

2. Keep deprecated aliases:

   ```text
   fragment -> candidate
   promote -> memory
   loadout -> pack
   outcome -> feedback
   ```

3. Alias behavior must print or expose deprecation warning only if it does not break JSON stdout. Prefer stderr warning for CLI invocations, never mixed into JSON stdout.

4. Update help strings to use lowercase prose nouns.

5. Update README quickstart and demo scripts to use new commands.

6. Tests must assert:

   - new commands work;
   - old aliases still work;
   - JSON stdout remains parseable;
   - deprecation warnings, if present, go to stderr.

**Verification:**

```bash
python -m pytest tests/test_cli.py tests/test_demo_flow.py -q
bash examples/run-local-lifecycle.sh
```

Expected: lifecycle demo runs using new vocabulary commands and canonical IDs.

---

## Tranche 8: Core modules rename and internal API migration

**Objective:** Rename internal modules/functions/variables from legacy terms to canonical terms without breaking behavior.

**Files:**

- Modify/rename: `src/shyftr/ingest.py`
- Modify/rename: `src/shyftr/extract.py`
- Modify/rename: `src/shyftr/promote.py`
- Modify/rename: `src/shyftr/loadout.py`
- Modify/rename: `src/shyftr/outcomes.py`
- Modify: `src/shyftr/confidence.py`
- Modify: `src/shyftr/mutations.py`
- Modify: `src/shyftr/profile.py`
- Modify: `src/shyftr/privacy.py`
- Modify: related tests

**Steps:**

1. Rename preferred functions:

   ```text
   ingest_source -> ingest_evidence
   extract_fragments -> extract_candidates
   approve_fragment/reject_fragment -> approve_candidate/reject_candidate
   promote_fragment -> promote_candidate_to_memory or promote_memory
   build_loadout/assemble_loadout -> build_pack/assemble_pack
   record_outcome -> record_feedback
   ```

2. Keep old function aliases where tests or external users may import them.

3. Rename local variables and docstrings to lowercase canonical terms.

4. Update field handling to canonical IDs.

5. Keep compatibility reads for old ledger fields until Tranche 13 final review confirms all tests cover backward compatibility.

6. Update tests module-by-module, not in one massive edit.

**Verification:**

```bash
python -m pytest tests/test_ingest.py tests/test_extract.py tests/test_review.py tests/test_promote.py -q
python -m pytest tests/test_loadout.py tests/test_outcomes.py tests/test_confidence.py -q
```

Expected: core lifecycle behavior passes under new names and old aliases.

---

## Tranche 9: Retrieval, store, audit, sweep, pattern/rule distillation migration

**Objective:** Migrate deeper internals that still use trace/alloy/doctrine/outcome naming.

**Files:**

- Modify: `src/shyftr/retrieval/sparse.py`
- Modify: `src/shyftr/retrieval/hybrid.py`
- Modify: `src/shyftr/retrieval/vector.py`
- Modify: `src/shyftr/retrieval/lancedb_adapter.py`
- Modify: `src/shyftr/store/sqlite.py`
- Modify: `src/shyftr/audit.py`
- Modify: `src/shyftr/audit/challenger.py`
- Modify: `src/shyftr/sweep.py`
- Modify: `src/shyftr/resonance.py`
- Rename or replace: `src/shyftr/distill/alloys.py` -> `src/shyftr/distill/patterns.py`
- Rename or replace: `src/shyftr/distill/doctrine.py` -> `src/shyftr/distill/rules.py`
- Modify: `src/shyftr/distill/__init__.py`
- Modify: related tests

**Steps:**

1. Rename retrieval table/variable naming from traces to memories where practical.

2. If SQLite table names are persisted, support legacy table names during read/rebuild. New rebuilds should create canonical table names where safe.

3. Rename `alloys` distillation to `patterns`.

4. Rename `doctrine` distillation to `rules`.

5. Keep module alias shims:

   - `src/shyftr/distill/alloys.py` may import from `patterns.py` with deprecation comments;
   - `src/shyftr/distill/doctrine.py` may import from `rules.py` with deprecation comments.

6. Rename tests:

   - `tests/test_alloys.py` -> `tests/test_patterns.py`
   - `tests/test_doctrine.py` -> `tests/test_rules.py`

7. Update challenger/sweep/confidence language:

   - memory confidence;
   - feedback updates;
   - quarantine candidate;
   - rule candidate.

**Verification:**

```bash
python -m pytest tests/test_sparse_retrieval.py tests/test_vector_retrieval.py tests/test_hybrid_retrieval.py tests/test_lancedb_adapter.py -q
python -m pytest tests/test_sqlite_store.py tests/test_challenger.py tests/test_sweep.py -q
python -m pytest tests/test_patterns.py tests/test_rules.py tests/test_resonance.py -q
```

Expected: retrieval and active-learning internals pass with canonical names.

---

## Tranche 10: Runtime integration, API, server, provider, and console migration

**Objective:** Ensure all integration boundaries use canonical pack/feedback/lifecycle naming while reading old payloads where necessary.

**Files:**

- Modify: `src/shyftr/server.py`
- Modify: `src/shyftr/console_api.py`
- Modify: `src/shyftr/provider/memory.py`
- Modify: `src/shyftr/provider/trusted.py`
- Modify/rename: `src/shyftr/integrations/loadout_api.py` -> `src/shyftr/integrations/pack_api.py`
- Modify/rename: `src/shyftr/integrations/outcome_api.py` -> `src/shyftr/integrations/feedback_api.py`
- Modify: `src/shyftr/integrations/protocols.py`
- Modify: `src/shyftr/integrations/file_adapter.py`
- Modify: `src/shyftr/integrations/config.py`
- Modify: `src/shyftr/integrations/proposals.py`
- Modify: `apps/console/src/api.ts`
- Modify: `apps/console/src/main.tsx`
- Modify: related tests

**Steps:**

1. Rename public API docs and code surfaces from loadout/outcome to pack/feedback.

2. Add compatibility parsing for old JSON request/response fields where tests show existing fixtures.

3. Avoid breaking JSON stdout/API fields without explicit compatibility tests.

4. Update FastAPI route names only if route compatibility aliases are kept:

   Preferred new routes:

   ```text
   /packs
   /feedback
   ```

   Compatibility aliases:

   ```text
   /loadouts -> /packs
   /outcomes -> /feedback
   ```

5. Update console labels to lowercase prose where in sentences; UI labels can use title case.

6. Update tests for both new and legacy route behavior.

**Verification:**

```bash
python -m pytest tests/test_server.py tests/test_console_api.py -q
python -m pytest tests/test_loadout_api.py tests/test_outcome_api.py -q
python -m pytest tests/test_integration_protocols.py tests/test_integration_config.py tests/test_file_adapter.py tests/test_runtime_integration_demo.py tests/test_runtime_proposals.py -q
(cd apps/console && npm run build)
```

Expected: new API terms work; old route/payload aliases remain verified.

---

## Tranche 11: Tests, fixtures, filenames, and examples full migration

**Objective:** Rename tests and fixtures so test names do not keep old terminology alive except dedicated compatibility tests.

**Files:**

- Rename tests with old terms in filename:
  - `tests/test_loadout.py` -> `tests/test_pack.py`
  - `tests/test_outcomes.py` -> `tests/test_feedback.py`
  - `tests/test_loadout_api.py` -> `tests/test_pack_api.py`
  - `tests/test_outcome_api.py` -> `tests/test_feedback_api.py`
  - `tests/test_alloys.py` -> `tests/test_patterns.py`
  - `tests/test_doctrine.py` -> `tests/test_rules.py`
- Modify all test files containing old terminology.
- Modify fixtures under `tests/fixtures/`.
- Keep/create compatibility tests:
  - `tests/test_legacy_terminology_compatibility.py`

**Steps:**

1. Rename filenames first with `git mv` to preserve history.

2. Update imports, function names, variable names, fixture names, and assertion strings.

3. Keep old terms only in `tests/test_legacy_terminology_compatibility.py`.

4. Add tests proving old JSON payloads and old CLI aliases still work.

5. Update any snapshot/fixture JSON keys to canonical fields unless the fixture is specifically a legacy fixture.

6. Update CI/check docs if they list old test paths.

**Verification:**

```bash
python -m pytest -q
python scripts/terminology_inventory.py --report
```

Expected: full test suite passes. Remaining old test-term matches are confined to compatibility tests and migration docs.

---

## Tranche 12: Capitalization pass across all docs and public strings

**Objective:** Enforce professional lowercase prose style across docs, CLI help, API docs, UI copy, and examples.

**Files:**

- Modify: `README.md`
- Modify: all `docs/**/*.md`
- Modify: all `examples/**/*.md`
- Modify: CLI help strings in `src/shyftr/cli.py`
- Modify: console UI copy in `apps/console/src/main.tsx`
- Modify: `scripts/terminology_inventory.py`
- Modify: `docs/status/plain-language-rename-ledger.md`

**Steps:**

1. Run capitalization scan.

2. For each hit, classify as:

   - allowed heading;
   - allowed diagram/glossary/table label;
   - allowed class/type/API name;
   - sentence-start false positive;
   - prose violation to fix.

3. Fix prose violations:

   - `Cell` -> `cell`
   - `Cell Ledger` -> `cell ledger`
   - `Regulator` -> `regulator`
   - `Grid` -> `grid`
   - `Pack` -> `pack`
   - `Feedback` -> `feedback`
   - `Evidence/Candidate/Memory/Pattern/Rule` -> lowercase unless heading/diagram/glossary.

4. Do not lowercase product/package/class names:

   - `ShyftR`
   - `SerializableModel`
   - dataclass names in code examples if code snippets require exact names.

5. Update the inventory script allowlist based on real acceptable contexts, not broad file-level skips where avoidable.

**Verification:**

```bash
python scripts/terminology_inventory.py --fail-on-capitalized-prose
git diff --check
```

Expected: capitalization guard passes or remaining matches are narrow and documented.

---

## Tranche 13: Final stale-term eradication and compatibility classification

**Objective:** Ensure every old term is either removed, renamed, or explicitly classified as compatibility/historical.

**Files:**

- Modify: `docs/status/plain-language-rename-ledger.md`
- Modify: `docs/concepts/terminology-compatibility.md`
- Modify: `scripts/terminology_inventory.py`
- Modify: any file still flagged by the report

**Steps:**

1. Run full stale-term report:

   ```bash
   python scripts/terminology_inventory.py --report
   ```

2. For every match of these terms, classify and resolve:

   ```text
   pulse, spark, charge, coil, rail,
   source, fragment, trace, alloy, doctrine,
   loadout, outcome, signal, isolation,
   feed, boundary,
   Circuit/circuit if used as lifecycle term
   ```

3. Fix remaining unintentional matches.

4. Move intentional compatibility language into the compatibility document or compatibility tests.

5. The final allowlist must be narrow and justified. Avoid allowlisting whole directories unless they are explicitly historical source archives.

6. Update `scripts/check.sh` to include:

   ```bash
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   ```

7. Update public readiness checks if they currently expect old terms.

**Verification:**

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
bash scripts/check.sh
```

Expected: stale-term and capitalization checks pass.

---

## Tranche 14: Full repo verification, alpha gate, and docs readback

**Objective:** Prove the migration is complete end-to-end.

**Files:**

- Modify: `docs/status/plain-language-rename-ledger.md`
- Modify: `docs/status/current-implementation-status.md` if capability wording changed
- Modify: `CHANGELOG.md` if present and current

**Steps:**

1. Run full Python tests:

   ```bash
   python -m pytest -q
   ```

2. Run lifecycle demo:

   ```bash
   bash examples/run-local-lifecycle.sh
   ```

3. Run full check script:

   ```bash
   bash scripts/check.sh
   ```

4. Run alpha gate:

   ```bash
   bash scripts/alpha_gate.sh
   ```

   Expected final line:

   ```text
   ALPHA_GATE_READY
   ```

5. Build console:

   ```bash
   (cd apps/console && npm run build && npm audit --omit=dev)
   ```

6. Run final text scans:

   ```bash
   python scripts/terminology_inventory.py --report
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   rg -n '<<<<<<<|=======|>>>>>>>' .
   git diff --check
   git status --short
   ```

7. Read back key docs manually:

   - `README.md`
   - canonical vocabulary doc
   - `docs/demo.md`
   - `docs/api.md`
   - `docs/concepts/terminology-compatibility.md`
   - `docs/status/plain-language-rename-ledger.md`

8. Update the rename ledger with final evidence:

   - test commands and result summaries;
   - old terms intentionally retained;
   - compatibility aliases retained;
   - remaining human decisions;
   - commit hash if committed.

**Verification:**

All commands above pass. Final `git status --short` shows only intended tracked changes if not committed, or clean if committed.

---

## Tranche 15: Skill/doctrine and memory alignment after repo proof

**Objective:** Update durable ShyftR doctrine only after the repo migration is verified, so future Hermes work uses the new vocabulary.

**Files / systems:**

- Patch skill: `shyftr-project-doctrine`
- Optional durable memory update if not already stored
- Do not store operational state or migration progress in memory

**Steps:**

1. Read current `shyftr-project-doctrine` skill.

2. Patch canonical vocabulary section from:

   ```text
   Pulse -> Spark -> Charge -> Coil -> Rail
   ```

   to:

   ```text
   evidence -> candidate -> memory -> pattern -> rule
   ```

3. Update stale-term scans in the skill to include the old power terms and legacy implementation terms.

4. Add capitalization house style to the skill.

5. Keep compatibility mapping in the skill concise; detailed migration docs remain file-backed in the repo.

6. Save only durable preference/doctrine in memory, not task progress.

**Verification:**

- Reload the skill with `skill_view(name="shyftr-project-doctrine")`.
- Confirm the old canonical power lifecycle is no longer presented as preferred current doctrine.
- Confirm the repo path and public/private boundaries remain intact.

---

## Tranche 16: Final human review / optional remote sync

**Objective:** Present the completed rename for human review and only then perform remote-visible side effects if approved.

**Human-gated actions:**

- push to `origin/main`;
- tag/release;
- external alpha tester announcement;
- deleting old aliases in a future breaking-change release.

**Steps after approval only:**

```bash
git status --short
git rev-parse HEAD
git rev-parse origin/main
python -m pytest -q
bash scripts/alpha_gate.sh
git push origin main
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
```

Expected:

- local status clean before push;
- tests and alpha gate pass;
- `HEAD == origin/main` after push/fetch.

---

## Final acceptance criteria

The migration is complete only when all are true:

1. Public lifecycle is consistently:

   ```text
   evidence -> candidate -> memory -> pattern -> rule
   ```

2. Public support terms are consistently:

   ```text
   cell, ledger, regulator, grid, pack, feedback, decay, quarantine
   ```

3. Normal prose uses lowercase common nouns.

4. Old terms are absent from current public docs except explicit compatibility/historical notes:

   ```text
   pulse, spark, charge, coil, rail,
   source, fragment, trace, alloy, doctrine,
   loadout, outcome, signal, isolation,
   feed, boundary
   ```

5. New CLI/API/docs examples use:

   ```text
   ingest evidence -> candidate -> review -> memory -> pack -> feedback
   ```

6. Legacy CLI/API/model/ledger aliases are tested and documented.

7. Full tests pass:

   ```bash
   python -m pytest -q
   ```

8. Public readiness and alpha gate pass:

   ```bash
   python scripts/public_readiness_check.py
   bash scripts/alpha_gate.sh
   ```

9. Terminology guards pass:

   ```bash
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   ```

10. The rename ledger classifies every intentional leftover legacy term.

11. The ShyftR doctrine skill is updated after repo proof.

12. No operational state, secrets, or private memory data were copied into public docs.

## Suggested commit sequence

Use small commits so regressions can be isolated:

```bash
git commit -m "docs: add plain-language terminology migration plan"
git commit -m "chore: add terminology inventory guards"
git commit -m "docs: migrate public vocabulary to plain lifecycle"
git commit -m "docs: migrate historical ShyftR plans terminology"
git commit -m "refactor: add plain lifecycle model aliases"
git commit -m "refactor: migrate ledger terminology with legacy reads"
git commit -m "feat: add plain lifecycle CLI commands"
git commit -m "refactor: migrate core lifecycle internals"
git commit -m "refactor: migrate retrieval and distillation terminology"
git commit -m "refactor: migrate runtime APIs to pack feedback terminology"
git commit -m "test: rename terminology fixtures and compatibility tests"
git commit -m "docs: enforce lowercase terminology style"
git commit -m "chore: enable stale terminology checks"
git commit -m "docs: record plain-language rename verification"
```

Do not push until the final human review tranche is approved.
