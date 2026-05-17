# ShyftR Phase 10: First-Class Episodic Memory Objects Tranched Plan

Date: 2026-05-16
Recorded: 2026-05-16 15:53:02 AEST
Repo: `/Users/stefan/ShyftR`
Status: implementation complete locally; closeout filed

> For Hermes: use the ShyftR skill, then use `subagent-driven-development` or persistent swarm lanes to execute this plan task-by-task. Keep implementation test-first, additive, compatibility-safe, and review-gated.

## Goal

Implement roadmap item 10, `First-class episodic memory objects`, as a complete but bounded Phase 10.

Phase 10 adds a first-class `Episode` object for timestamped, provenance-anchored, review-gated event history. It does not replace semantic, procedural, resource, rule, continuity, or working memory. It gives ShyftR a dedicated object for answering: what happened, when, during which runtime/session/task context, involving which actor/tool/action, with which outcome, and which evidence anchors prove it.

## Why this is next

The broad roadmap says ShyftR should become a typed, evaluated, multi-class memory substrate. The relevant roadmap tranche family is:

```text
10. First-class episodic memory objects.
```

The repo is ready for that item because the prerequisites are now in place:

- Phase 2 implemented typed live-context capture, carry-state checkpoints, resume reconstruction, and CLI/MCP/HTTP exposure for typed runtime context.
- Phase 8 implemented the evaluation track and local ablation/report bundle needed to measure later memory-layer work honestly.
- Phase 9 hardened the core contracts: pack is canonical, append-only latest-row reads are pinned where touched, retrieval-log projection/rebuild fidelity is tested, and provider filter/label semantics are explicit.
- `src/shyftr/memory_classes.py` already recognizes `episodic` as a memory class with review-gated authority, event-history retention, background role, and lower precedence than semantic/procedural/rule guidance.

The remaining gap is not the label `episodic`; it is the lack of a dedicated object contract and write/retrieval/projection surface for actual episodes.

## Research basis

This plan is grounded in:

- `/Users/stefan/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/ShyftR/deep-research-report.md`
- `/Users/stefan/ShyftR/2026-05-16-shyftr-post-phase-9-handoff-packet.md`
- `/Users/stefan/ShyftR/2026-05-16-shyftr-phase-9-core-contract-hardening-closeout.md`
- `/Users/stefan/ShyftR/docs/status/current-implementation-status.md`
- `/Users/stefan/ShyftR/docs/concepts/memory-class-contract.md`
- current code in `src/shyftr/memory_classes.py`, `src/shyftr/models.py`, `src/shyftr/live_context.py`, `src/shyftr/provider/memory.py`, `src/shyftr/pack.py`, and `src/shyftr/store/sqlite.py`
- supplemental read-only swarm/delegate research performed on 2026-05-16

The deep-research report recommends a real episodic store: materially important session segments should become episodes with actors, timestamps, outcomes, tools used, referenced resources, and extracted candidate lessons. It also warns that ShyftR should avoid frontier claims until the memory classes, retrieval, consolidation, and evaluation surfaces are measured.

## Current implementation truth

### Already implemented

- `episodic` is a valid `memory_type` in `src/shyftr/memory_classes.py`.
- Default class metadata exists:
  - authority: `review_gated`
  - retention: `event_history`
  - default role: `background`
  - precedence: lower than rule/semantic/procedural/resource guidance
- Generic durable-memory rows may carry `memory_type='episodic'`.
- Live-context harvest can classify archived or completed working-state rows as episodic archive material.
- Pack/provider paths already understand `memory_type` filtering at a generic level.
- SQLite projections preserve `memory_type` for generic durable-memory rows.

### Not yet implemented

- No dedicated `Episode` model.
- No episode-specific ledger namespace or append/read helper.
- No episode proposal/approval lifecycle.
- No anchor requirement for approved episodes.
- No episode-specific SQLite projection.
- No episode-aware pack selection policy.
- No CLI/MCP/HTTP episode capture/search surface.
- No tests proving episodes are separate from semantic/procedural guidance.
- No privacy/export hardening specific to event history.

## Canonical naming decision

Use this naming consistently:

- `Episode` = the first-class object.
- `episodic` = the memory class / `memory_type` value.
- `episode_id` = the stable logical identifier for an episode.
- `episode_kind` = a bounded subtype such as `session`, `task`, `incident`, `tool_outcome`, or `decision_context`.

Avoid adding parallel public nouns such as timeline object, session memory, event memory, or experience object unless they are explicitly defined as compatibility or subtype terms.

## Episode object contract

### Required fields

An approved `Episode` must carry:

- `episode_id`: stable logical identifier.
- `cell_id`: owning cell identifier.
- `episode_kind`: one of `session`, `task`, `incident`, `tool_outcome`, `decision_context`, or `custom`.
- `title`: short human-readable title.
- `summary`: concise narrative of what happened.
- `started_at`: ISO timestamp for the beginning of the episode window.
- `ended_at`: ISO timestamp for the end of the episode window.
- `actor`: runtime, operator, user, system, tool, or other bounded actor label.
- `action`: what was attempted or observed.
- `outcome`: one of `success`, `failure`, `partial`, `blocked`, `superseded`, `informational`, or `unknown`.
- `status`: one of `proposed`, `approved`, `archived`, `redacted`, `superseded`, or `rejected`.
- `memory_type`: fixed to `episodic`.
- `authority`: fixed/defaulted to `review_gated`.
- `retention`: fixed/defaulted to `event_history`.
- `confidence`: bounded numeric confidence.
- `sensitivity`: public/internal/private/sensitive style sensitivity label compatible with existing privacy filtering.
- `created_at`: append timestamp.

### Anchor requirement

An approved episode must include at least one audit anchor:

- `live_context_entry_ids`
- `memory_ids`
- `feedback_ids`
- `resource_refs`
- `grounding_refs`
- `artifact_refs`

A proposed episode may be anchor-incomplete only if it remains non-retrievable and review-gated. Approval must fail if all anchor lists are empty.

### Optional but planned fields

- `runtime_id`
- `session_id`
- `task_id`
- `tool_name`
- `tool_action`
- `key_points`
- `failure_signature`
- `recovery_summary`
- `parent_episode_id`
- `related_episode_ids`
- `derived_memory_ids`
- `supersedes_episode_id`
- `superseded_by_episode_id`
- `valid_until`
- `retention_hint`
- `metadata`

### Lifecycle contract

The lifecycle is append-only:

```text
proposed -> approved -> archived/redacted/superseded
proposed -> rejected
```

Rules:

- Every state transition appends a new episode row keyed by `episode_id`.
- Readers resolve latest-row-wins by `episode_id`.
- `approved` episodes are eligible for episode-aware retrieval.
- `archived` episodes remain inspectable but downranked or hidden from normal packs.
- `redacted` episodes preserve identifiers and anchors but redact sensitive prose fields.
- `rejected` episodes are not retrievable.
- No physical deletion is introduced by Phase 10.

### Authority contract

Episodes are event history, not guidance authority.

- Episodes may explain why a decision happened.
- Episodes may support later proposals for semantic/procedural/rule memory.
- Episodes must not outrank semantic/procedural/rule memory in default pack guidance.
- Episodes must not silently promote durable semantic/procedural memory.

### Retrieval contract

Phase 10 retrieval must stay deterministic and conservative.

Default behavior:

- Include episodes when the query explicitly asks for history, previous attempts, incidents, outcomes, failures, or provenance.
- Include episodes in diagnostic/forensics mode.
- Include only capsule fields by default: title, summary, outcome, timeframe, anchors, and sensitivity-safe key points.
- Keep role as `background` unless a future reviewed policy says otherwise.

Do not add learned rerankers, vector-service dependencies, or broad retrieval-orchestration rewrites in Phase 10.

### Privacy contract

Episodes are high-risk because they summarize real interactions and failures.

- Sensitivity defaults to the maximum sensitivity of included anchors.
- Private/sensitive episodes are excluded from public-safe exports and public packs.
- Redaction must preserve audit identity and anchors while redacting unsafe prose.
- Episode capture must never store raw large tool outputs or blob dumps; store resource handles/anchors instead.

## Phase 10 non-goals

Do not include these in Phase 10:

- offline episode clustering or sleep-time consolidation;
- automatic episode-to-semantic/procedural promotion;
- resource/multimodal expansion beyond using existing resource/grounding handles;
- learned reranking or ANN/vector redesign;
- hosted, multi-tenant, or production service claims;
- destructive migration of older ledgers;
- broad rewrite of live-context/carry behavior;
- UI polish beyond minimal local contract exposure if needed;
- public claim that episodes improve task success before the evaluation bundle measures it.

## Tranche plan

### P10-0: Contract freeze and public-safe plan lock

Objective: freeze the Episode contract before implementation.

Files:

- Create: `docs/concepts/episodic-memory-contract.md`
- Modify: `docs/concepts/memory-class-contract.md`
- Optional modify: `docs/status/current-implementation-status.md` only after implementation exists; not in P10-0 unless marking planned work is explicitly desired.

Steps:

1. Write `docs/concepts/episodic-memory-contract.md` with:
   - Episode vs episodic naming;
   - required fields;
   - anchor requirement;
   - lifecycle;
   - authority/retention;
   - privacy/export behavior;
   - non-goals.
2. Patch `docs/concepts/memory-class-contract.md` to point at the episodic contract and clarify that the old Phase 3 storage non-goal remains historical for Phase 3, while Phase 10 may add an additive episode ledger without rewriting older durable-memory rows.
3. Run terminology/public doc checks.

Verification:

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
```

Stop boundary:

- Stop before code changes if the contract is unclear or terminology checks fail.

### P10-1: Episode model and validation

Objective: add a first-class `Episode` data model with strict validation.

Files:

- Modify: `src/shyftr/models.py`
- Add or modify tests: `tests/test_phase10_episode_contract.py`

Minimum RED tests:

1. `Episode` round-trips through `to_dict()` / `from_dict()` with all required fields.
2. `Episode` rejects `memory_type` values other than `episodic`.
3. `Episode` rejects approval without at least one anchor list populated.
4. `Episode` rejects invalid lifecycle status.
5. `Episode` preserves sensitivity and relationship fields.

Implementation notes:

- Prefer extending the existing `SerializableModel` pattern.
- Keep `Episode` additive; do not alter generic durable-memory row behavior.
- Keep legacy durable-memory rows with `memory_type='episodic'` readable as compatibility rows, not as first-class episodes.

Verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_contract.py
PYTHONPATH=.:src python -m compileall -q src/shyftr/models.py
```

Stop boundary:

- Stop after model validation is green. No ledger writes yet.

### P10-2: Append-only episode ledger and latest-row reads

Objective: add durable episode proposal/approval storage with append-only latest-row semantics.

Files:

- Create: `src/shyftr/episodes.py` or `src/shyftr/episode.py` (choose one; recommended: `episodes.py` for module-level helpers)
- Modify if useful: `src/shyftr/layout.py`
- Modify if useful: `src/shyftr/ledger_state.py`
- Add/extend tests: `tests/test_phase10_episode_ledger.py`

Minimum RED tests:

1. Capturing a proposed episode appends a row without making it retrievable.
2. Approving an anchored episode appends an approved row.
3. Approving an anchorless episode fails.
4. Latest-row-wins resolves an approved row followed by an archived/redacted row correctly.
5. Legacy cells without episode ledgers still initialize/read without failure.

Implementation notes:

- Additive ledger path recommendation:
  - `ledger/episodes.jsonl`, or
  - `ledger/episodes/approved.jsonl` + `ledger/episodes/proposed.jsonl` if that matches current layout style better.
- Pick one path in P10-0 and stick with it.
- Reuse existing append-only helpers rather than inventing a second ledger mechanism.

Verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_ledger.py tests/test_phase10_episode_contract.py
PYTHONPATH=.:src python -m compileall -q src/shyftr/models.py src/shyftr/episodes.py src/shyftr/layout.py src/shyftr/ledger_state.py
```

Stop boundary:

- Stop before SQLite, pack, provider, CLI, MCP, or HTTP integration.

### P10-3: SQLite projection and rebuild fidelity

Objective: make episode projection rebuildable and test latest-row fidelity in SQLite.

Files:

- Modify: `src/shyftr/store/sqlite.py`
- Add/extend tests: `tests/test_phase10_episode_sqlite_projection.py`

Minimum RED tests:

1. SQLite rebuild creates/preserves an `episodes` projection table.
2. Projection stores capsule fields and JSON fields deterministically.
3. Projection resolves latest-row-wins for repeated `episode_id` rows.
4. Projection preserves anchors, sensitivity, timestamps, and lifecycle status.
5. Older cells with no episode ledger rebuild cleanly.

Suggested table fields:

- `episode_id`
- `cell_id`
- `episode_kind`
- `title`
- `summary`
- `started_at`
- `ended_at`
- `actor`
- `action`
- `outcome`
- `status`
- `confidence`
- `sensitivity`
- `anchors_json`
- `relationships_json`
- `created_at`
- `updated_at`

Verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_sqlite_projection.py tests/test_phase10_episode_ledger.py tests/test_phase10_episode_contract.py
PYTHONPATH=.:src python -m compileall -q src/shyftr/store/sqlite.py src/shyftr/episodes.py
```

Stop boundary:

- Stop before pack/provider/runtime surfaces.

### P10-4: Harvest-to-episode proposal bridge

Objective: convert selected live-context history into review-gated episode proposals without polluting durable memory.

Files:

- Modify: `src/shyftr/live_context.py`
- Possibly modify: `src/shyftr/episodes.py`
- Add/extend tests: `tests/test_phase10_episode_harvest.py`

Minimum RED tests:

1. A completed session harvest can emit a session episode proposal with live-context anchors.
2. Error/recovery clusters can emit an incident episode proposal when configured.
3. Sensitivity propagates from anchored live-context entries to the episode proposal.
4. Unclassified transient working-state text does not silently become an approved episode.
5. Existing harvest buckets remain compatible and review-gated.

Implementation notes:

- Do not turn every archived live-context row into a first-class episode.
- Use explicit boundary rules:
  - session episode: bounded by runtime/session ID at harvest time;
  - incident episode: bounded by related error/recovery entries;
  - task episode: bounded by task ID when present.
- Keep generated episodes proposed until reviewed.

Verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_harvest.py tests/test_session_harvest.py tests/test_live_context.py
PYTHONPATH=.:src python -m compileall -q src/shyftr/live_context.py src/shyftr/episodes.py
```

Stop boundary:

- Stop before retrieval inclusion if harvest proposal quality is noisy or anchor/sensitivity tests fail.

### P10-5: Episode-aware provider/search and pack policy

Objective: make approved episodes retrievable under explicit policy while preserving guidance hierarchy.

Files:

- Modify: `src/shyftr/provider/memory.py`
- Modify: `src/shyftr/pack.py`
- Possibly modify: `src/shyftr/retrieval/hybrid.py`
- Add/extend tests: `tests/test_phase10_episode_provider_pack.py`

Minimum RED tests:

1. Search with `memory_types=['episodic']` returns approved anchored episodes.
2. Normal semantic/procedural search does not accidentally include episodes unless requested or policy-triggered.
3. Episode pack items have role `background` and never outrank rule/semantic/procedural guidance.
4. Queries like `what happened last time` or `previous failure` can include episode capsules.
5. Private/sensitive episodes are filtered from public-safe packs.
6. Legacy generic durable-memory rows tagged episodic remain readable but distinguishable from first-class episodes.

Implementation notes:

- Keep first pass deterministic: lexical match + recency + anchor richness + sensitivity gate.
- Do not add learned reranking or vector dependencies in Phase 10.
- Preserve Phase 9 pack canonicalization: all new pack behavior goes through the canonical pack path.

Verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_provider_pack.py tests/test_phase9_provider_contract.py tests/test_phase9_pack_loadout_equivalence.py
PYTHONPATH=.:src python -m compileall -q src/shyftr/provider/memory.py src/shyftr/pack.py src/shyftr/retrieval/hybrid.py
```

Stop boundary:

- Stop before CLI/MCP/HTTP exposure if retrieval policy is not deterministic and tested.

### P10-6: CLI/MCP/HTTP episode surfaces

Objective: expose minimal local-first episode capture/search surfaces after the core contract is stable.

Files:

- Modify: `src/shyftr/cli.py`
- Modify: `src/shyftr/mcp_server.py`
- Modify: `src/shyftr/server.py`
- Add/extend tests:
  - `tests/test_phase10_episode_cli.py`
  - `tests/test_phase10_episode_mcp.py`
  - `tests/test_server.py` or a narrower episode server test

Minimum RED tests:

1. CLI can capture a proposed episode in dry-run/default-safe mode.
2. CLI can capture with `--write` only when required fields and anchors are present.
3. MCP episode capture defaults to dry-run unless `write=true`.
4. MCP/server search returns sensitivity-safe capsule fields.
5. Existing CLI/MCP/server tests remain green.

Implementation notes:

- New CLI shape recommendation:
  - `shyftr episode capture <cell> --title ... --summary ... --actor ... --action ... --outcome ... --anchor-live-entry ... --write`
  - `shyftr episode search <cell> "query" --memory-type episodic --limit 10`
- Do not require live external services.
- Keep dry-run defaults on write-capable external surfaces.

Verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_cli.py tests/test_phase10_episode_mcp.py tests/test_server.py
PYTHONPATH=.:src python -m compileall -q src/shyftr/cli.py src/shyftr/mcp_server.py src/shyftr/server.py
```

Stop boundary:

- Stop before docs/status closeout if external surfaces are not dry-run-safe.

### P10-7: Evaluation and report integration

Objective: add focused evaluation rows showing what Phase 10 proves without overclaiming task-success lift.

Files:

- Modify: `scripts/evaluation_bundle.py` if needed
- Possibly modify Phase 8 report scripts if they have extension points
- Add/extend tests: `tests/test_phase10_episode_evaluation.py`
- Update generated docs/status artifacts only if the existing evaluation flow requires regeneration.

Minimum RED tests:

1. Evaluation bundle can report episode contract coverage without failing when no episodes exist.
2. A synthetic episode fixture produces measurable counts: proposed, approved, archived/redacted, anchor completeness, sensitivity buckets.
3. Evaluation output marks task-success lift as unmeasured unless a specific benchmark is added.

Verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_phase10_episode_evaluation.py tests/test_phase8_eval_bundle_runner.py tests/test_phase8_cli_eval_bundle.py
PYTHONPATH=.:src python scripts/evaluation_bundle.py --help
```

Stop boundary:

- Stop before claiming improvement. This tranche measures contract coverage and readiness, not frontier performance.

### P10-8: Status docs, full verification, and closeout

Objective: make public truth match implementation and close the phase honestly.

Files:

- Modify: `docs/status/current-implementation-status.md`
- Create: `2026-05-16-shyftr-phase-10-first-class-episodic-memory-objects-closeout.md`
- Create: `2026-05-16-shyftr-post-phase-10-handoff-packet.md`
- Update this plan with completion notes as tranches close.

Verification bundle:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
PYTHONPATH=.:src pytest -q
```

Closeout requirements:

- State exactly which surfaces are implemented.
- State that episodes are review-gated event history, not guidance authority.
- State any deferred consolidation/retrieval/evaluation work.
- Include focused and full verification outputs.
- Preserve dirty-worktree context honestly; do not commit/reset/stash without explicit approval.

## Full phase success criteria

Phase 10 is complete when:

- `Episode` is a first-class model with validation.
- Episode ledger writes are append-only and latest-row reads are tested.
- Episode projection/rebuild fidelity is tested.
- Live-context harvest can create review-gated episode proposals with anchors.
- Approved episodes are retrievable under explicit episode-aware policy.
- Pack inclusion keeps episodes as background/provenance, not primary guidance.
- Public/dry-run external surfaces are tested if exposed.
- Evaluation/reporting reflects episode coverage without overclaiming task-success lift.
- Status docs and closeout are filed.
- Full verification bundle is green.

## Risk register

| Risk | Mitigation |
|---|---|
| Episode becomes another vague generic memory row | Add dedicated `Episode` model and tests; keep generic episodic rows as compatibility only. |
| Transient live context pollutes durable memory | Episode proposals stay review-gated; approved episodes require anchors. |
| Episodes leak sensitive session history | Sensitivity propagation, public-pack filtering, redacted lifecycle status. |
| Episode retrieval outranks actual guidance | Keep episode role as background and precedence lower than semantic/procedural/rule. |
| Implementation drifts into consolidation/rehearsal | Keep P10 non-goals explicit; defer clustering/promotion/rehearsal. |
| Terminology audit flags root plan prose | Use Episode/episodic naming consistently and avoid legacy implementation vocabulary except in raw paths or compatibility notes. |
| SQLite projection diverges from ledger truth | Add latest-row projection tests before pack/provider integration. |

## Execution recommendation

Run Phase 10 as implementation tranches, not one giant patch.

Recommended first execution slice:

1. P10-0: land `docs/concepts/episodic-memory-contract.md` and memory-class contract update.
2. P10-1: add `Episode` model and validation tests.
3. P10-2: add append-only episode ledger and SQLite projection tests.

Only after those are green should implementation move into harvest, retrieval, pack, and external surfaces.
