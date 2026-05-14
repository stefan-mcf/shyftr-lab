# ShyftR Phase 6 handoff packet

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 6 — resource and multimodal memory
Status: ready to start from hardened P6-0 truth
Resume from this exact truth.

Canonical predecessor:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-5-closeoff.md`

Canonical Phase 6 planning artifact:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-tranche-p6-0-plan.md`

## What is already complete and proven

1. Phase 5 is complete.
   - Final closeoff exists.
   - Repo was previously verified clean and pushed for the Phase 5 completion tranche.
   - Canonical pushed commit for that milestone: `013ce7b06dd51baaec8c641bc91343ff3404be5d`

2. Phase 6 kickoff planning is complete.
   - The original P6-0 kickoff plan has now been hardened with deeper repo inspection and swarm review.
   - The hardened P6-0 plan is now the authoritative Phase 6 planning artifact.

3. Deep research for Phase 6 has already been done for this tranche.
   - Controller inspected:
     - `src/shyftr/models.py`
     - `src/shyftr/memory_classes.py`
     - `src/shyftr/provider/memory.py`
     - `src/shyftr/pack.py`
     - `src/shyftr/retrieval/sparse.py`
     - `src/shyftr/retrieval/hybrid.py`
     - `src/shyftr/privacy.py`
     - `src/shyftr/store/sqlite.py`
     - existing tests covering models/provider/pack/retrieval
   - Swarm lanes actually used:
     - `swarm2` read-only deep-research memo on Phase 6 hardening and tranche split
     - `swarm3` read-only compatibility memo on breakpoints and additive-safe design

4. The current optimized conclusion is settled.
   - Phase 6 should not start with “full multimodal memory”.
   - It should start with a narrow additive `resource_ref` contract and provider/model round-trip slice first.
   - Retrieval/pack changes must come only after schema/provider compatibility is pinned.

## Current truth boundary

This handoff is for execution resume after planning only.
No Phase 6 implementation has been started in this tranche.

Current repo-state facts at handoff time:
- branch: `main`
- status at planning close:
  - untracked Phase 6/closeoff docs only
- active new artifacts:
  - `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-5-closeoff.md`
  - `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-tranche-p6-0-plan.md`
  - `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-handoff-packet.md`

Authoritative planning truth:
- Phase 6 is ready to start.
- The exact next tranche is P6-1.
- P6-1 must be schema/provider-first.
- P6-2 is where retrieval/pack integration belongs.

## Key design decisions already made

1. `resource_ref` is the canonical typed resource-reference object.
   Baseline fields:
   - `ref_type`
   - `locator`
   - `label`
   - `span`
   - `content_digest`
   - `captured_at`
   - `origin` / `tool_name`
   - `mime_type`
   - `size_bytes`

2. Resource memory remains reference-first.
   - No blobs in ledgers.
   - No OCR.
   - No image embeddings.
   - No browser-capture automation in P6-1.

3. Existing provenance flow stays intact in P6-1.
   - Use the current source -> fragment -> approved memory row pipeline.
   - Do not introduce a separate resource ledger in the first implementation slice.

4. New fields must remain additive and optional.
   - Do not break `Trace.from_dict(...)` compatibility.
   - Do not break SQLite rebuilds.
   - Do not require new fields globally on legacy rows.

5. Retrieval hardening rule is fixed.
   - Search safe display text (`statement`, `label`, maybe `ref_type`), not raw sensitive locators by default.
   - Preserve empty-query behavior.

6. Naming normalization is fixed.
   - `resource_ref` = primary typed reference on a resource memory row
   - `grounding_refs` = links from other memory rows to resource identities/handles
   - `evidence_refs` remains separate unless explicitly unified later

## Exact ordered continuation sequence

1. Preflight the repo again.
   - Confirm repo path is `/Users/stefan/ShyftR`.
   - Confirm branch/worktree state with live `git status --short --branch`.
   - Read the Phase 5 closeoff, hardened P6-0 plan, and this handoff packet first.

2. Start Phase 6 P6-1 only.
   - Do not jump to retrieval or pack work yet.
   - Keep scope strictly to schema/provider compatibility.

3. Write focused failing tests first for P6-1.
   Minimum first wave:
   - resource-backed memory round-trip through provider/model path with `memory_type="resource"`
   - typed `resource_ref` serialization/deserialization round-trip
   - legacy non-resource approved-row round-trip remains unchanged
   - SQLite rebuild compatibility for resource metadata
   - `grounding_refs` compatibility on non-resource memories
   - blob-only resource validation rejection

4. Implement the smallest additive code to make P6-1 green.
   Likely file touchpoints:
   - `src/shyftr/models.py`
   - `src/shyftr/memory_classes.py`
   - `src/shyftr/provider/memory.py`
   - `src/shyftr/store/sqlite.py`
   - maybe `src/shyftr/privacy.py` if immediate structured projection/redaction support is required

5. Verify P6-1 before any retrieval work.
   Focused gates:
   - `tests/test_phase6_resource_memory_schema.py`
   - `tests/test_phase6_resource_memory_provider.py`
   - `tests/test_models.py tests/test_phase3_memory_classes.py tests/test_memory_provider.py`

6. Only after P6-1 is green, open P6-2.
   - extend sparse/hybrid/pack integration for safe display-text search and pack visibility
   - add the retrieval/pack tests then implement

7. After P6-2 focused green, run broader repo verification.
   - full pytest
   - compileall
   - terminology inventory checks
   - public readiness
   - `git diff --check`

8. Land a canonical Phase 6 tranche closeout artifact after P6-1 or P6-2, depending on the stop point reached.

## Do-not-redo / non-goals

Do not redo:
- Phase 5 completion assessment
- broad “is Phase 6 next?” analysis
- generic roadmap brainstorming already captured in the hardened P6-0 plan
- the already completed deep-research pass for this kickoff tranche

Do not do in P6-1:
- OCR
- screenshot embeddings
- large binary/blob persistence
- browser automation capture pipelines
- ANN/vector backend swaps for multimodal support
- a parallel dedicated resource ledger/model unless compatibility forces it and the tests prove the need
- broad retrieval scoring changes

## Known risks to watch during implementation

1. Provenance breakage
- current approved memory rows depend on `source_fragment_ids`
- resource memory must not bypass that invariant accidentally in P6-1

2. Schema drift
- avoid making `resource_ref` mandatory for all approved memory rows
- keep old rows loadable without migration pain

3. Privacy leakage
- locators, file paths, and spans can leak sensitive data more easily than statements
- tests must cover this explicitly

4. Retrieval leakage
- avoid default indexing/search over raw locators
- preserve empty-query behavior

5. Naming drift
- don’t let `resource_ref`, `resource_refs`, `grounding_refs`, and `evidence_refs` blur together during implementation

## Read-first file set for the next operator

Planning / truth artifacts:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-5-closeoff.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-tranche-p6-0-plan.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-6-handoff-packet.md`

Core code:
- `/Users/stefan/ShyftR/src/shyftr/models.py`
- `/Users/stefan/ShyftR/src/shyftr/memory_classes.py`
- `/Users/stefan/ShyftR/src/shyftr/provider/memory.py`
- `/Users/stefan/ShyftR/src/shyftr/privacy.py`
- `/Users/stefan/ShyftR/src/shyftr/store/sqlite.py`

Then later for P6-2:
- `/Users/stefan/ShyftR/src/shyftr/retrieval/sparse.py`
- `/Users/stefan/ShyftR/src/shyftr/retrieval/hybrid.py`
- `/Users/stefan/ShyftR/src/shyftr/pack.py`

Existing tests to extend first:
- `/Users/stefan/ShyftR/tests/test_models.py`
- `/Users/stefan/ShyftR/tests/test_phase3_memory_classes.py`
- `/Users/stefan/ShyftR/tests/test_memory_provider.py`
- `/Users/stefan/ShyftR/tests/test_sparse_retrieval.py`
- `/Users/stefan/ShyftR/tests/test_pack.py`

## Recommended next user-facing command of work

Proceed optimally into Phase 6 P6-1:
- write the focused failing schema/provider tests first
- implement the smallest additive resource-ref/provider baseline
- verify before opening retrieval/pack work

## One-line summary

Phase 6 has been research-hardened already; resume from this exact point by executing a narrow P6-1 schema/provider tranche first, not a broad multimodal or retrieval-heavy build.