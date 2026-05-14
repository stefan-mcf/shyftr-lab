# ShyftR Phase 1 Core Memory Model Stabilization Tranched Plan

> **For Hermes:** Use `subagent-driven-development` or named persistent worker lanes only after reading this entire plan. Execute tranches in order. Do not cross the final human-review tranche unless the operator explicitly approves.

**Goal:** Stabilize ShyftR's core memory model by resolving naming/schema drift, pack/loadout duplication, append-only latest-row correctness, retrieval-log projection mismatch, and public/docs/code skew before Phase 2 typed context work begins.

**Architecture:** Phase 1 is a consolidation tranche, not a feature-expansion tranche. It preserves ShyftR's local-first append-only ledgers and current public safety posture while introducing explicit compatibility boundaries, contract tests, and a single canonical pack/memory read path. Ledger files remain historically readable; no destructive cell migration or legacy reader deletion is allowed in autonomous tranches.

**Tech Stack:** Python 3.11/3.12, JSONL ledgers, SQLite projections, ShyftR CLI/MCP/HTTP/provider surfaces, deterministic synthetic fixtures, repo-local scripts, public-readiness and terminology gates.

**Primary repo:** `/Users/stefan/ShyftR`

**Planning/reference artifacts:**
- `/Users/stefan/Desktop/ShyftR/deep-research-report.md`
- `/Users/stefan/Desktop/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/Desktop/ShyftR/phase0-current-state-baseline-implementation-report.md`
- `/Users/stefan/Desktop/ShyftR/phase1-implementation-guide.md` if still present; auxiliary research artifact, not canonical truth
- `/Users/stefan/ShyftR/docs/status/phase-1-plan-hardening-audit.md` if still present; auxiliary local audit artifact, not canonical truth

---

## 0. Executive summary

Phase 0 baseline work is complete and has a report at `/Users/stefan/Desktop/ShyftR/phase0-current-state-baseline-implementation-report.md`. Phase 1 should use that baseline as the regression anchor while continuing not to wait for the whole future roadmap.

The first implementation target is not typed context, episodic memory, retrieval orchestration, resource memory, or consolidation. The first target is core correctness and naming convergence.

The report identifies four high-priority Phase 1 defects:

1. Public ontology and internal ontology diverge.
2. `pack` and `loadout` overlap and drift.
3. Confidence updates read the first append-only trace row instead of the latest row.
4. Retrieval-log writer/projection schemas disagree.

This plan turns those findings into autonomous, verifiable tranches. All human-gated decisions are intentionally pooled into final tranches. Earlier tranches use safe defaults, additive compatibility, draft decisions, tests, and shims so work can proceed without blocking on manual review.

---

## 1. Non-negotiable scope boundary

### In scope for Phase 1

- Baseline handoff from Phase 0.
- Current-state inventory for naming/schema/code/docs surfaces.
- Contract tests for append-only latest-row semantics.
- Contract tests for retrieval-log write -> SQLite projection round trip.
- Contract tests for pack/loadout equivalence and compatibility shims.
- Confidence latest-row bug fix.
- Retrieval-log schema fix.
- Pack/loadout convergence to one canonical implementation surface.
- Compatibility shims for deprecated import/API names.
- Canonical terminology contract docs.
- Terminology/public-readiness gate updates.
- Skill/docs sync after implementation.
- Final human review packet for decisions that should not interrupt autonomous execution.

### Explicitly out of scope for Phase 1

- Typed live-context state model. Phase 2.
- Carry-state/checkpoint object redesign. Phase 2.
- First-class episodic/semantic/procedural/resource memory classes. Phase 3.
- Retrieval orchestration upgrades beyond preserving current behavior. Phase 4.
- New ANN/vector index choices. Phase 4.
- Offline consolidation/rehearsal. Phase 5.
- Multimodal/resource memory. Phase 6.
- Privacy/policy hardening beyond schema/readiness alignment. Phase 7.
- Full frontier benchmark claims. Phase 8.
- Hosted/multi-tenant/productized claims.
- Public package publication.
- Real memory data, customer data, or private cell ledgers.
- Destructive migration of existing cell ledger files.
- Removal of legacy field readers or compatibility aliases before final human approval.

### Collision boundary

Phase 0 is complete but has git-visible untracked files in `/Users/stefan/ShyftR`:

- `examples/evals/current-state-baseline/`
- `scripts/current_state_baseline.py`
- `scripts/compare_current_state_baseline.py`

Phase 1 implementers may use those files as baseline inputs. They should not rewrite Phase 0 fixture/expected-output files unless Phase 1 explicitly discovers a baseline-contract defect and records that change in the Phase 1 closeout.

---

## 2. Human input requirement

Autonomous tranches 0-10 require no human input by design.

All human-gated review items are allocated to the final tranches:

- Tranche 11: final review packet and decision matrix.
- Tranche 12: optional post-approval landing actions.

Before Tranche 11, the executor must not ask the operator to choose between pack/loadout naming options or approve API/schema decisions. Instead, use the safe defaults below and document them as provisional until final review.

### Safe defaults for autonomous execution

1. `pack` is the public/canonical user-facing noun.
2. `loadout` remains a compatibility alias and import shim.
3. Append-only effective state means latest-row-wins by logical key.
4. Existing ledger file names remain readable and are not rewritten.
5. Retrieval logs should be additive-compatible: emit both currently expected and compatibility timestamp/id fields where needed.
6. `/v1` API compatibility is additive-only: accept legacy request fields, emit canonical fields, and include compatibility fields when needed.
7. No compatibility alias or legacy field reader is deleted before final human approval.

---

## 3. Evidence base from source artifacts

### From `deep-research-report.md`

The report's Phase 1-relevant findings are:

- Terminology and schema drift: public docs describe evidence/candidate/memory/pack/feedback while core code still uses source/fragment/trace/loadout/outcome and charge/pulse/spark compatibility aliases.
- Pack/loadout overlap: `src/shyftr/pack.py`, `src/shyftr/loadout.py`, `src/shyftr/integrations/pack_api.py`, and `src/shyftr/integrations/loadout_api.py` overlap.
- Confidence stale-read bug: `confidence.py` appends updated trace rows but `_trace_by_id()` returns the first matching row.
- Retrieval-log mismatch: `loadout.py` emits `generated_at` and omits `cell_id`; `store/sqlite.py` expects `cell_id` and `logged_at`.
- Docs/status/code skew: public posture can run ahead of current implementation if not verified from repo files.

### From `broad-roadmap-concept.md`

Phase 1 is defined as:

- remove correctness and schema drift;
- decide canonical internal abstraction for pack/loadout;
- keep public language centered on evidence, candidate, memory, pack, feedback;
- keep legacy aliases only as compatibility surfaces or raw historical fields;
- fix append-only latest-row semantics;
- fix retrieval-log writer/projection mismatch;
- add contract tests;
- add migration/adapters where compatibility is required;
- update status/docs so public claims match implementation.

### From read-only plan-hardening audits

Controller and helper audits confirmed:

- `pack.py` and `loadout.py` are not only duplicated; `loadout.py` currently appears feature-richer in some paths, so convergence must preserve behavior rather than blindly deleting one file.
- `mcp_server.py` and `frontier.py` import from `pack.py`, while CLI/provider/continuity/integration paths tend to import from `loadout.py`.
- `pack_api.py` and `loadout_api.py` are near-identical API surfaces.
- `models.py` carries public models, legacy models, and older power-themed aliases.
- `store/sqlite.py` projection schema remains legacy-shaped in several places.
- Public/private readiness and terminology gates already exist and should become verification gates for Phase 1.

---

## 4. Terminology policy for Phase 1

### Canonical public terms

Use these in new user-facing docs, CLI help, status files, README updates, and skills:

- evidence
- candidate
- memory
- pattern
- rule
- pack
- feedback
- memory_id
- pack_id

### Compatibility terms

These may remain only in compatibility sections, internal adapters, raw ledger readers, quoted historical fields, or deprecation shims:

- source / source_id
- fragment / fragment_id
- trace / trace_id
- alloy / alloy_id
- doctrine / doctrine_id
- loadout / loadout_id
- outcome / outcome_id
- pulse / spark / charge / coil / rail / signal

### Required classification for each legacy/dead-end item

Every surfaced mismatch must be classified as exactly one of:

- `canonical`: preferred implementation and public contract.
- `compatibility-read`: old field or object accepted for historical cells.
- `compatibility-shim`: old import/API path preserved temporarily.
- `internal-raw-ledger`: historical on-disk path that remains inspectable.
- `migrate-later`: safe to defer, requires migration path.
- `deprecate-later`: allowed now, candidate for final human review.
- `remove-after-approval`: not removed in autonomous tranches.
- `out-of-scope-phase-later`: belongs to Phase 2+.

This classification should appear in the Phase 1 closeout packet.

---

## 5. Planned package shape after Phase 1

This is the intended end state after autonomous tranches, before final human approval.

### Core code

- `src/shyftr/pack.py`
  - canonical public implementation surface for bounded memory packs;
  - must include all behavior currently present in both `pack.py` and `loadout.py`, including feature deltas currently present only in `loadout.py`.

- `src/shyftr/loadout.py`
  - compatibility shim only;
  - re-exports canonical pack implementation names or deprecated aliases;
  - contains no independent business logic after convergence.

- `src/shyftr/integrations/pack_api.py`
  - canonical integration API surface.

- `src/shyftr/integrations/loadout_api.py`
  - compatibility shim only;
  - re-exports or delegates to `pack_api.py`;
  - contains no independent business logic after convergence.

- `src/shyftr/confidence.py`
  - latest-row-wins read semantics for append-only approved traces.

- `src/shyftr/mutations.py`
  - remains consistent with the same latest-row-wins semantics.

- `src/shyftr/store/sqlite.py`
  - retrieval-log projection reads canonical and compatibility fields.

- `src/shyftr/models.py`
  - public models remain primary in new docs/import guidance;
  - legacy classes/aliases remain readable/exported for compatibility.

Optional new helper module if implementation needs it:

- `src/shyftr/ledger_state.py` or `src/shyftr/canonical.py`
  - centralizes append-only effective-state helpers such as latest-row-wins by logical key;
  - must stay small and mechanical;
  - must not become a new broad architecture layer that absorbs Phase 2+ work.

### Docs/status

Likely docs to update or create:

- `docs/concepts/terminology-compatibility.md`
- `docs/concepts/storage-retrieval-learning.md`
- `docs/api.md`
- `docs/mcp.md`
- `docs/future-work.md`
- `docs/status/current-pack-loadout-behavior.md` or a superseding closeout file
- `docs/status/release-readiness.md` if public posture changes
- `adapters/hermes/skills/shyftr/SKILL.md`
- local Hermes skill copy if the bundled skill changes

Scripts/gates likely to update:

- `scripts/terminology_inventory.py`
- `scripts/public_readiness_check.py` only if new required file/readiness behavior is needed

---

## 6. Verification command set

Run from repo root unless stated otherwise:

```bash
cd /Users/stefan/ShyftR
git status --short --branch
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

Because Phase 0 baseline is complete, also run the Phase 0 comparison gate:

```bash
cd /Users/stefan/ShyftR
python scripts/current_state_baseline.py --mode all
python scripts/compare_current_state_baseline.py docs/status/current-state-baseline-summary.json docs/status/current-state-baseline-summary.json --markdown-out docs/status/current-state-baseline-comparison.md
```

Use the exact Phase 0 baseline command from `/Users/stefan/Desktop/ShyftR/phase0-current-state-baseline-implementation-report.md` unless a later closeout supersedes it.

If test files are public or local fixtures are available, use focused tests first, then full gates:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m pytest -q
```

If `pytest` is unavailable or tests are intentionally local/ignored, do not fail the tranche solely for absent public tests. Instead, require compile smoke, deterministic scripts, and direct fixture scripts.

---

# Autonomous tranches

## Tranche 0: Phase 0 handoff and collision preflight

**Objective:** Confirm the completed Phase 0 baseline state before Phase 1 writes begin.

**Stop boundary:** No source-code changes in this tranche.

**Files to read:**
- `/Users/stefan/Desktop/ShyftR/phase0-current-state-baseline-implementation-report.md`
- `/Users/stefan/ShyftR/git status`
- `/Users/stefan/ShyftR/examples/evals/current-state-baseline/`
- `/Users/stefan/ShyftR/scripts/current_state_baseline.py`
- `/Users/stefan/ShyftR/scripts/compare_current_state_baseline.py`
- `/Users/stefan/ShyftR/docs/status/current-state-baseline-summary.json`
- `/Users/stefan/ShyftR/docs/status/current-state-harness-surface-inventory.md` if present

**Steps:**

1. Run:
   ```bash
   cd /Users/stefan/ShyftR
   git status --short --branch
   ```
2. Read `/Users/stefan/Desktop/ShyftR/phase0-current-state-baseline-implementation-report.md`.
3. Confirm the baseline harness files and summary artifacts named in that report exist on disk.
4. Record git-visible and git-ignored Phase 0 artifacts separately because the Phase 0 report notes that `tests/` and `docs/status/` artifacts may be ignored by `.gitignore`.
5. Preserve Phase 0 fixture/expected-output files unless Phase 1 explicitly updates the baseline contract and explains why.
6. Use this exact Phase 0 baseline command as the regression anchor unless the Phase 0 closeout supersedes it:
   ```bash
   cd /Users/stefan/ShyftR
   python scripts/current_state_baseline.py --mode all
   python scripts/compare_current_state_baseline.py docs/status/current-state-baseline-summary.json docs/status/current-state-baseline-summary.json --markdown-out docs/status/current-state-baseline-comparison.md
   ```

**Verification:**

```bash
cd /Users/stefan/ShyftR
git status --short --branch
```

Expected: current dirty/untracked state is understood and classified; no new writes from this tranche.

**Closeout artifact:**

- Add a section to the eventual Phase 1 closeout packet: `Phase 0 baseline handoff status`.

---

## Tranche 1: Phase 1 current-state inventory and mismatch ledger

**Objective:** Create a precise inventory of every Phase 1 mismatch before production edits.

**Stop boundary:** Inventory/doc artifact only. No code changes.

**Files to inspect:**
- `src/shyftr/models.py`
- `src/shyftr/pack.py`
- `src/shyftr/loadout.py`
- `src/shyftr/integrations/pack_api.py`
- `src/shyftr/integrations/loadout_api.py`
- `src/shyftr/confidence.py`
- `src/shyftr/mutations.py`
- `src/shyftr/store/sqlite.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/frontier.py`
- `src/shyftr/cli.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/continuity.py`
- `src/shyftr/live_context.py` read only, for import-surface awareness only
- `docs/concepts/terminology-compatibility.md`
- `docs/status/current-pack-loadout-behavior.md`
- `docs/api-versioning.md`
- `scripts/terminology_inventory.py`

**Create or update:**

Preferred local/status artifact:

- `docs/status/phase-1-core-model-inventory.md`

If `docs/status/` is intentionally ignored/local-only, that is acceptable. The closeout packet should later summarize the inventory.

**Required inventory sections:**

1. Pack/loadout import graph.
2. Pack/loadout behavior delta.
3. Integration API duplication graph.
4. Append-only ledger readers and whether each uses latest-row-wins.
5. Retrieval-log writer fields versus SQLite projection fields.
6. Public/legacy model and field alias map.
7. Docs that must be updated.
8. Items explicitly deferred to Phase 2+.
9. Legacy/dead-end classification table.

**Commands/searches:**

```bash
cd /Users/stefan/ShyftR
python - <<'PY'
from pathlib import Path
for p in Path('src/shyftr').rglob('*.py'):
    text = p.read_text(errors='ignore')
    if 'loadout' in text or 'pack' in text or 'trace_id' in text or 'charge_id' in text:
        print(p)
PY
```

```bash
cd /Users/stefan/ShyftR
python - <<'PY'
from pathlib import Path
needles = ['from shyftr.pack', 'from .pack', 'import shyftr.pack', 'from shyftr.loadout', 'from .loadout', 'import shyftr.loadout']
for p in Path('src').rglob('*.py'):
    text = p.read_text(errors='ignore')
    hits = [n for n in needles if n in text]
    if hits:
        print(p, hits)
PY
```

**Verification:**

- Read the inventory artifact back.
- Confirm it lists the four report findings explicitly.
- Confirm it states Phase 2+ exclusions.

---

## Tranche 2: Contract tests for append-only effective state

**Objective:** Add failing/regression tests that define latest-row-wins semantics before fixing confidence and duplicate trace consumption.

**Files likely to modify/create:**
- `tests/` if tests are tracked/available, or local test area if this repo intentionally keeps tests ignored.
- Preferred names if tests are available:
  - `tests/test_append_only_effective_state.py`
  - `tests/test_confidence_latest_row.py`
- If public tests are unavailable/ignored, create a deterministic script instead:
  - `scripts/check_append_only_effective_state.py`

**Behavior to test:**

1. Given `traces/approved.jsonl` with multiple rows for the same `trace_id`, effective reads use the last row.
2. Repeated confidence adjustments compound from the latest confidence, not the original confidence.
3. Pack assembly does not include duplicate memory candidates for duplicate append-only rows representing the same logical memory.
4. Mutation paths and confidence paths agree on the same effective row.

**Example test intent:**

```python
def test_confidence_adjustment_reads_latest_trace_row(tmp_path):
    # seed approved trace t1 at confidence 0.50
    # adjust confidence useful once -> latest row 0.55
    # adjust confidence useful again -> old_confidence must be 0.55, new 0.60
    # fail if old_confidence is still 0.50
```

```python
def test_approved_trace_projection_is_latest_row_wins(tmp_path):
    # append t1 confidence 0.50 then t1 confidence 0.70
    # effective projection returns one t1 row at 0.70
```

**Verification:**

Before code fix, the confidence stale-read test should fail if current bug remains. If it unexpectedly passes, inspect whether Phase 0 or another branch already fixed it.

Run focused verification:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m pytest -q tests/test_confidence_latest_row.py tests/test_append_only_effective_state.py
```

or script fallback:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python scripts/check_append_only_effective_state.py
```

**Closeout evidence:**

- test/script path;
- initial fail or proof bug already fixed;
- exact expected semantics documented in test names/comments.

---

## Tranche 3: Shared append-only effective-state helper

**Objective:** Add or consolidate one mechanical helper for latest-row-wins append-only reads so confidence, mutations, and pack assembly do not drift again.

**Files likely to modify/create:**
- Create one small helper if needed:
  - `src/shyftr/ledger_state.py` or `src/shyftr/canonical.py`
- Modify:
  - `src/shyftr/confidence.py`
  - `src/shyftr/mutations.py` only if it can use the helper without widening scope
  - `src/shyftr/pack.py` and/or `src/shyftr/loadout.py` if they currently read approved traces directly

**Design rule:**

The helper is mechanical only. It should not introduce a new memory hierarchy, typed context model, resource store, or retrieval policy.

**Suggested functions:**

```python
def latest_by_key(records: Iterable[dict], key: str) -> list[dict]:
    """Return records deduplicated by logical key, preserving first-seen order but keeping latest values."""
```

```python
def latest_record_by_key(records: Iterable[dict], key: str, value: str) -> dict | None:
    """Return the last record whose key equals value."""
```

Optional trace-specific wrapper:

```python
def latest_approved_trace_by_id(cell_path: PathLike, trace_id: str) -> dict | None:
    ...
```

**Steps:**

1. Create helper module with no ShyftR business logic beyond effective-state mechanics.
2. Add tests for helper ordering and latest-row behavior.
3. Replace local first-match logic in `confidence.py` with helper.
4. Consider replacing duplicate latest-row projection in `mutations.py` with helper if low-risk.
5. Do not rewrite ledger file names.
6. Do not change public APIs in this tranche.

**Verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src
PYTHONPATH=.:src python -m pytest -q tests/test_append_only_effective_state.py tests/test_confidence_latest_row.py
```

Fallback if no pytest:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python scripts/check_append_only_effective_state.py
```

---

## Tranche 4: Confidence latest-row bug fix

**Objective:** Fix the confirmed stale-read bug in `src/shyftr/confidence.py`.

**Files to modify:**
- `src/shyftr/confidence.py`
- tests/scripts from Tranche 2/3

**Current problem:**

`_trace_by_id()` scans approved trace rows and returns the first matching `trace_id`. In an append-only ledger, repeated updates append later rows, so first-match reads stale state.

**Required behavior:**

`_trace_by_id()` or its replacement must return the latest matching row.

**Implementation options:**

Preferred:

- Use the helper from Tranche 3.

Acceptable minimal fallback:

```python
def _trace_by_id(cell_path: Path, trace_id: str) -> Optional[Dict[str, Any]]:
    latest = None
    for record in _read_traces(cell_path):
        if record.get("trace_id") == trace_id or record.get("memory_id") == trace_id:
            latest = record
    return latest
```

If compatibility needs public IDs:

- Accept both `trace_id` and `memory_id` keys.
- Preserve existing error behavior for missing records.

**Steps:**

1. Run focused test and confirm current behavior.
2. Patch `_trace_by_id()` or route it through helper.
3. Ensure repeated confidence updates compound correctly.
4. Inspect any other first-match readers in `confidence.py`.
5. Re-run focused tests.
6. Run compile smoke.

**Verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m pytest -q tests/test_confidence_latest_row.py
PYTHONPATH=.:src python -m compileall -q src
```

Fallback:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python scripts/check_append_only_effective_state.py
PYTHONPATH=.:src python -m compileall -q src
```

**Acceptance criteria:**

- Repeated confidence adjustments use the latest prior confidence.
- No first-match trace reader remains in the confidence adjustment path.
- Existing append-only ledgers remain readable.

---

## Tranche 5: Retrieval-log schema contract and projection fix

**Objective:** Align retrieval-log writer output with SQLite projection expectations while preserving compatibility with existing logs.

**Files to inspect/modify:**
- `src/shyftr/pack.py`
- `src/shyftr/loadout.py`
- `src/shyftr/store/sqlite.py`
- `src/shyftr/integrations/retrieval_logs.py` if it consumes retrieval logs
- tests/scripts for retrieval-log projection

**Current problem:**

The writer emits fields such as:

- `retrieval_id`
- `loadout_id`
- `query`
- `generated_at`
- selected/candidate/caution/suppressed ids

The SQLite projection expects fields such as:

- `retrieval_id`
- `cell_id`
- `query`
- `selected_ids`
- `score_traces`
- `logged_at`

`cell_id` and `logged_at` are missing or mismatched.

**Required behavior:**

New retrieval-log rows must include enough fields for complete SQLite projection and public compatibility.

Recommended additive fields:

- `cell_id`
- `pack_id`
- `loadout_id` as compatibility alias during Phase 1
- `logged_at`
- `generated_at` as compatibility alias during Phase 1
- `selected_ids`
- `score_traces`
- `candidate_ids`
- `caution_ids`
- `suppressed_ids`

**Steps:**

1. Add a failing regression test or deterministic script:
   - assemble a pack/loadout in a temp cell;
   - rebuild SQLite projection;
   - assert retrieval log row has non-null `cell_id` and timestamp;
   - assert old logs with `generated_at` still project to `logged_at`.
2. Patch retrieval-log dataclass/model to carry `cell_id` if absent.
3. Patch `to_dict()` to emit additive canonical and compatibility fields.
4. Patch SQLite rebuild to accept both `logged_at` and `generated_at`.
5. Patch any retrieval log consumers to prefer canonical fields while accepting legacy aliases.
6. Re-run focused projection test.

**Verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m pytest -q tests/test_retrieval_log_projection.py
PYTHONPATH=.:src python -m compileall -q src
```

Fallback:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python scripts/check_retrieval_log_projection.py
```

**Acceptance criteria:**

- Fresh retrieval logs project into SQLite with non-null `cell_id` and timestamp.
- Existing `generated_at` logs remain readable.
- No public API breaking change is introduced.
- Retrieval provenance is inspectable from ledger and projection.

---

## Tranche 6: Pack/loadout convergence tests and behavior freeze

**Objective:** Freeze current pack/loadout behavior before unifying modules so behavior is preserved.

**Files to inspect/modify:**
- `src/shyftr/pack.py`
- `src/shyftr/loadout.py`
- `src/shyftr/integrations/pack_api.py`
- `src/shyftr/integrations/loadout_api.py`
- tests/scripts for pack/loadout equivalence

**Known risk:**

`loadout.py` currently appears to include behavior not present in `pack.py`, including query sparse scoring and memory decay scoring. The unification must preserve the richer behavior.

**Steps:**

1. Create an equivalence fixture with synthetic approved memories, candidates, tags, confidence, and a query.
2. Exercise both current module paths if they still exist:
   - `shyftr.pack`
   - `shyftr.loadout`
   - `shyftr.integrations.pack_api`
   - `shyftr.integrations.loadout_api`
3. Record differences explicitly.
4. Decide behavior freeze target:
   - preserve all feature-complete behavior from `loadout.py`;
   - expose it through canonical `pack.py` and pack API names.
5. Add regression expectations for selected ids, scoring fields, caution ids, suppressed ids, and retrieval-log shape.

**Verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m pytest -q tests/test_pack_loadout_equivalence.py
```

Fallback:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python scripts/check_pack_loadout_equivalence.py
```

**Acceptance criteria:**

- Behavior deltas are captured before module convergence.
- The future canonical pack implementation target is explicit.
- The test/script will fail if a convergence patch drops currently-used scoring or selection behavior.

---

## Tranche 7: Pack/loadout module convergence

**Objective:** Make `pack` the canonical public implementation surface and reduce `loadout` to compatibility only, without breaking existing importers.

**Files to modify:**
- `src/shyftr/pack.py`
- `src/shyftr/loadout.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/frontier.py`
- `src/shyftr/cli.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/continuity.py`
- `src/shyftr/live_context.py` if it imports loadout
- `src/shyftr/integrations/pack_api.py`
- `src/shyftr/integrations/loadout_api.py`
- any docs/examples that import module paths directly

**Canonical direction:**

- Public noun: `pack`.
- Compatibility noun: `loadout`.
- Canonical module: `src/shyftr/pack.py`.
- Compatibility shim: `src/shyftr/loadout.py`.

**Implementation strategy:**

1. Move or copy feature-complete behavior into `pack.py`.
2. Ensure `pack.py` includes any behavior currently only present in `loadout.py`.
3. Update first-party imports to use `shyftr.pack` or `.pack`.
4. Reduce `loadout.py` to a shim that re-exports canonical functions/classes.
5. Add deprecation warning only if it does not break tests/CLI output; otherwise defer warning text to docs and final review.
6. Preserve old class aliases if needed:
   - `LoadoutTaskInput = PackTaskInput`
   - `LoadoutItem = PackItem`
   - `AssembledLoadout = AssembledPack`
   - `assemble_loadout = assemble_pack`
7. Preserve old field aliases in serialized outputs where `/v1` compatibility requires them.

**Important:**

Do not delete `loadout.py` in autonomous tranches. It must remain as a compatibility shim until final human review approves removal in a future phase.

**Verification searches:**

```bash
cd /Users/stefan/ShyftR
python - <<'PY'
from pathlib import Path
for p in Path('src/shyftr').rglob('*.py'):
    text = p.read_text(errors='ignore')
    if 'from .loadout' in text or 'from shyftr.loadout' in text or 'import shyftr.loadout' in text:
        print(p)
PY
```

Expected after convergence: only the compatibility shim or explicitly allowed compatibility tests should import `loadout`.

**Functional verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src python -m pytest -q tests/test_pack_loadout_equivalence.py
```

Fallback:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python scripts/check_pack_loadout_equivalence.py
```

**Acceptance criteria:**

- One canonical pack implementation exists.
- Loadout path remains import-compatible.
- No first-party production code depends on independent loadout business logic.
- MCP/CLI/provider/continuity paths use the same underlying behavior.

---

## Tranche 8: Integration API convergence and `/v1` compatibility

**Objective:** Converge `pack_api` and `loadout_api` surfaces while preserving runtime/API compatibility.

**Files to modify:**
- `src/shyftr/integrations/pack_api.py`
- `src/shyftr/integrations/loadout_api.py`
- `src/shyftr/server.py` if routes import either API
- `src/shyftr/console_api.py` if it exposes pack/loadout payloads
- `docs/api.md`
- `docs/api-versioning.md` only if policy clarification is needed
- tests/scripts for API compatibility

**Implementation strategy:**

1. Make `pack_api.py` canonical.
2. Reduce `loadout_api.py` to a compatibility wrapper that delegates to `pack_api.py`.
3. Preserve request compatibility for `loadout_id` and canonicalize internally to `pack_id` when possible.
4. Responses should prefer `pack_id` while keeping `loadout_id` if existing `/v1` clients require it.
5. Maintain deprecation headers on unversioned routes if already defined.
6. Do not remove old endpoint names in autonomous tranches.

**Tests/scripts should cover:**

- canonical pack request succeeds;
- legacy loadout-shaped request still succeeds;
- response contains canonical fields;
- compatibility field is present if required;
- retrieval log still writes correctly;
- docs examples match behavior.

**Verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src
PYTHONPATH=.:src python -m pytest -q tests/test_pack_api_compatibility.py
```

Fallback:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python scripts/check_pack_api_compatibility.py
```

**Acceptance criteria:**

- Canonical and legacy API surfaces delegate to one implementation.
- `/v1` remains additive-compatible.
- No destructive behavior is added to MCP/HTTP/CLI write paths.

---

## Tranche 9: Documentation, terminology gates, and skill sync

**Objective:** Align docs, terminology checks, public posture, and Hermes skill content with the Phase 1 implementation.

**Files to inspect/update:**
- `docs/concepts/terminology-compatibility.md`
- `docs/concepts/storage-retrieval-learning.md`
- `docs/api.md`
- `docs/mcp.md`
- `docs/status/current-pack-loadout-behavior.md` or a superseding status/closeout doc
- `docs/status/release-readiness.md`
- `docs/future-work.md`
- `README.md` only if current capability claims changed
- `scripts/terminology_inventory.py`
- `scripts/public_readiness_check.py` only if needed
- `adapters/hermes/skills/shyftr/SKILL.md`
- local Hermes skill copy if repo-bundled skill changes

**Doc rules:**

1. New public prose uses canonical terms.
2. Legacy terms only appear in compatibility sections, raw field names, migration notes, or quoted historical paths.
3. No numeric context-window expansion claim.
4. No hosted/multi-tenant/production service overclaim.
5. No private-core scoring/ranking/compaction details.
6. No real cell paths or memory data.
7. If docs mention `loadout`, they must classify it as compatibility/legacy.
8. If docs mention old ledger file names, they must clarify historical on-disk compatibility rather than public vocabulary preference.

**Skill sync:**

If `adapters/hermes/skills/shyftr/SKILL.md` changes, sync the local Hermes skill copy according to the ShyftR skill rule:

- repo-bundled skill: `adapters/hermes/skills/shyftr/SKILL.md`
- local runtime skill: `/Users/stefan/.hermes/skills/software-development/shyftr/SKILL.md`

Do not silently mutate local Hermes skills unless this plan is being executed with explicit permission to sync operator skill content. If permission is not available, write a final review item instead.

**Verification:**

```bash
cd /Users/stefan/ShyftR
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

**Acceptance criteria:**

- Public docs and implementation agree.
- Terminology gates pass.
- Public readiness passes.
- Any skill sync requirement is completed or queued in final human review.

---

## Tranche 10: Full regression and Phase 0 baseline comparison

**Objective:** Prove Phase 1 did not regress the Phase 0 current-state baseline or core public gates.

**Prerequisite:** Phase 0 baseline artifacts are complete per `/Users/stefan/Desktop/ShyftR/phase0-current-state-baseline-implementation-report.md` and must be used as the regression anchor.

**Steps:**

1. Run compile smoke:
   ```bash
   cd /Users/stefan/ShyftR
   PYTHONPATH=.:src python -m compileall -q src scripts examples
   ```
2. Run focused contract tests/scripts from Tranches 2-8.
3. Run terminology gates:
   ```bash
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   ```
4. Run public readiness:
   ```bash
   python scripts/public_readiness_check.py
   ```
5. Run Phase 0 baseline comparison using the exact command from the Phase 0 report:
   ```bash
   python scripts/current_state_baseline.py --mode all
   python scripts/compare_current_state_baseline.py docs/status/current-state-baseline-summary.json docs/status/current-state-baseline-summary.json --markdown-out docs/status/current-state-baseline-comparison.md
   ```
6. Run git whitespace check:
   ```bash
   git diff --check
   ```
7. Capture `git diff --stat`.
8. Capture `git status --short --branch`.

**Expected result:**

- All Phase 1-focused checks pass.
- Phase 0 baseline comparison passes or differences are explained as intentional/additive and queued for final review.
- Worktree changes are known and limited to Phase 1 scope plus any Phase 0 files already present before Phase 1.

**Closeout artifact:**

Create:

- `docs/status/phase-1-core-model-stabilization-closeout.md`

The closeout should include:

- summary of changes;
- files changed;
- tests/scripts run with outputs;
- Phase 0 baseline comparison result;
- terminology/public-readiness result;
- compatibility/deprecation classification table;
- any final human decisions remaining.

---

# Final human-gated tranches

The following tranches are intentionally at the end. They collect all manual/operator decisions so autonomous execution can proceed without scattered review interruptions.

## Tranche 11: Final human review packet and decision matrix

**Objective:** Present all human-gated review items after safe autonomous implementation is complete.

**Human gate:** Required. Do not proceed to Tranche 12 without explicit operator approval.

**Create/update:**

- `docs/status/phase-1-human-review-packet.md`

**Packet sections:**

1. Executive summary.
2. Exact diff summary.
3. Verification evidence table.
4. Phase 0 baseline comparison result.
5. Pack/loadout final naming decision.
6. Legacy/dead-end classification table.
7. Compatibility shims kept.
8. Compatibility aliases proposed for future removal, if any.
9. API compatibility notes.
10. Retrieval-log schema decision.
11. Append-only latest-row semantics decision.
12. Skill sync decision.
13. Public docs claim review.
14. Deferred Phase 2+ items.
15. Approve/revise/block decision checklist.

**Decision checklist:**

- H-01: Approve `pack` as canonical public/internal implementation surface and `loadout` as compatibility shim.
- H-02: Approve latest-row-wins as the canonical effective-state rule for append-only ledger rows keyed by logical id.
- H-03: Approve retrieval-log additive field shape: `cell_id`, `pack_id`, `loadout_id` compatibility, `logged_at`, `generated_at` compatibility.
- H-04: Approve keeping historical ledger file names readable without destructive migration.
- H-05: Approve docs/status/API wording after Phase 1.
- H-06: Approve terminology inventory reclassification of `loadout` as compatibility-only after convergence.
- H-07: Approve syncing repo-bundled Hermes skill to local Hermes runtime skill if needed.
- H-08: Decide whether any compatibility aliases should be scheduled for removal in a later phase.
- H-09: Decide whether a future `shyftr migrate-cell --to-canonical` command should be planned. No implementation in Phase 1.
- H-10: Decide whether the unified schema should be treated as public API contract or internal implementation detail.

**Verification before presenting to human:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
git status --short --branch
```

**Acceptance criteria:**

- Human review packet exists and is readable.
- It does not ask the human to reconstruct technical context from raw diffs.
- It clearly separates decisions required now from future/deferred decisions.
- It contains no secrets, raw private memory data, or private-core heuristics.

---

## Tranche 12: Optional post-approval landing, cleanup, and publication gates

**Objective:** Perform only the actions explicitly approved in Tranche 11.

**Human gate:** Required. This tranche must not run without explicit approval after Tranche 11.

**Possible approved actions:**

- Commit Phase 1 changes.
- Push to remote.
- Open PR.
- Sync local Hermes skill from repo-bundled ShyftR skill.
- Reclassify compatibility terms more strictly in CI.
- Create follow-on Phase 2 plan issues.
- Schedule legacy alias removal for a later phase.

**Actions still forbidden unless separately approved:**

- Delete legacy readers.
- Rewrite existing cell ledgers.
- Publish package.
- Change global Hermes config.
- Use real/private memory data in examples/tests.
- Add hosted/multi-tenant claims.
- Start Phase 2 typed context implementation.

**Pre-commit verification:**

```bash
cd /Users/stefan/ShyftR
git status --short --branch
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

If committing:

```bash
cd /Users/stefan/ShyftR
git add <approved-files-only>
git commit -m "fix: stabilize core memory model semantics"
```

If pushing, first verify GitHub identity:

```bash
gh auth status
git config user.name
git config user.email
```

Expected GitHub identity should be compatible with the user's established noreply identity before public push.

**Acceptance criteria:**

- Only approved actions are performed.
- Final worktree state is reported.
- Commit SHA and CI/run handles are captured if a commit/push occurs.
- Follow-on Phase 2 items remain planned, not started.

---

## 7. Recommended execution shape

Use a phased-assembly shape with independent inspection overlays:

1. Controller owns Tranche 0 collision/preflight and final integration.
2. One implementation lane can own append-only confidence/retrieval-log correctness.
3. One implementation lane can own pack/loadout convergence after behavior tests exist.
4. One docs/gates lane can own terminology/docs/skill sync after code changes settle.
5. Independent reviewer lane should review the final diff before Tranche 11 packet.

Do not run multiple writers against the same files simultaneously. Serialize changes touching:

- `src/shyftr/pack.py`
- `src/shyftr/loadout.py`
- `src/shyftr/models.py`
- `src/shyftr/store/sqlite.py`
- `scripts/terminology_inventory.py`
- docs/skill files

---

## 8. Review checklist for future implementers

Before marking Phase 1 complete, verify:

- [ ] Phase 0 baseline handoff is understood.
- [ ] `confidence.py` no longer reads first matching trace row as effective state.
- [ ] Repeated confidence updates compound from latest confidence.
- [ ] Approved trace effective-state logic is consistent across confidence, mutations, and pack assembly.
- [ ] Retrieval logs contain/project `cell_id` and timestamp correctly.
- [ ] `generated_at` compatibility remains readable if existing logs use it.
- [ ] `pack.py` is canonical or the final human packet clearly explains any deviation.
- [ ] `loadout.py` contains no independent business logic after convergence.
- [ ] `pack_api.py` is canonical or the final human packet clearly explains any deviation.
- [ ] `loadout_api.py` is compatibility-only.
- [ ] Existing CLI/MCP/HTTP/provider surfaces still work.
- [ ] Public docs use canonical vocabulary.
- [ ] Legacy terms are isolated to compatibility/raw-ledger sections.
- [ ] No Phase 2+ functionality has started.
- [ ] No legacy readers or aliases were deleted without human approval.
- [ ] No existing cell ledger files were destructively rewritten.
- [ ] Compile/readiness/terminology/diff checks pass.
- [ ] Human review packet exists before any commit/push/public decision.

---

## 9. Known risks and mitigations

### Risk: pack/loadout convergence drops behavior

Mitigation:

- Write behavior-freeze tests before moving code.
- Preserve feature-complete behavior currently in `loadout.py`.
- Keep `loadout.py` shim until final human approval.

### Risk: latest-row helper changes ordering semantics

Mitigation:

- Preserve first-seen order for unique logical ids while using latest row values.
- Add explicit tests for ordering and latest values.

### Risk: retrieval-log additive fields break old consumers

Mitigation:

- Emit both canonical and compatibility fields where needed.
- Make SQLite rebuild accept both `logged_at` and `generated_at`.
- Do not remove `loadout_id` before approval.

### Risk: terminology gates break due to compatibility terms

Mitigation:

- Update `COMPATIBILITY_FILES` and stale-term policy deliberately.
- Keep compatibility sections clearly marked.
- Run both terminology commands before closeout.

### Risk: Phase 1 accidentally starts Phase 2

Mitigation:

- Do not add typed goal/plan_step/tool_state objects.
- Do not redesign live-context or carry-state models.
- Defer all typed-context notes into the final packet's Phase 2 backlog.

### Risk: public/private leakage

Mitigation:

- Use synthetic fixtures only.
- Run `public_readiness_check.py`.
- Do not include private-core scoring or compaction heuristics in public docs.
- Do not include real memory cell paths or private ledgers.

---

## 10. Suggested commit sequence after approval

If the operator approves committing after Tranche 11, prefer small commits:

1. `test: add core memory model regression contracts`
2. `fix: make confidence reads latest append-only trace row`
3. `fix: align retrieval log ledger and sqlite projection schema`
4. `refactor: converge pack and loadout implementation paths`
5. `docs: document phase 1 compatibility and terminology policy`
6. `chore: update public readiness and terminology gates`

Do not commit Phase 2 docs or implementation in these commits.

---

## 11. Phase 2 handoff notes

Phase 1 should end with a clean handoff to Phase 2, not by starting Phase 2.

Handoff should say:

- core pack/memory naming is stable enough for typed context work;
- append-only effective-state reads are consistent;
- retrieval-log projections are reliable for evaluation/audit;
- pack/loadout compatibility boundary is explicit;
- legacy aliases are documented and still readable;
- final human decisions are resolved or deferred.

Phase 2 can then address typed working context and carry-state model without inheriting unresolved naming/schema drift.
