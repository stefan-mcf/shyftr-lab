# ShyftR context compaction integration viability

Date: 2026-05-07
Status: source research note
Scope: runtime-neutral architecture assessment; no implementation approval by itself

## Question

Does the current ShyftR plan include a tranche for integrating ShyftR cell usage with a context compactor, and is the architecture viable as a stronger storage/retrieval layer than compaction alone?

## Short answer

Yes, the idea exists in the plan, but it is not yet a dedicated implementation tranche in the current active phase status.

The strongest architecture is a combined loop:

```text
runtime context pressure
-> ShyftR cell pack request for continuity-critical memory
-> runtime compactor performs mechanical compression using that pack as scaffolding
-> resumed runtime reports compaction feedback
-> ShyftR updates retrieval, confidence, and review-gated proposals
```

ShyftR should not initially replace the runtime compactor. It should make compaction memory-aware, provenance-aware, trust-labeled, and feedback-aware.

## Evidence from current ShyftR planning material

1. `docs/sources/2026-05-05-shyftr-compaction-intelligence-concept.md` already defines the core product thesis:
   - ShyftR can help compactors decide what deserves to survive.
   - It introduces the Continuity pack concept.
   - It proposes compaction feedback after resumed work.
   - It recommends keeping mechanical summarization in the runtime while ShyftR selects, justifies, and evaluates durable context.

2. `docs/plans/2026-04-24-shyftr-implementation-tranches.md` references the compaction concept in the strategic product definition and says it should influence near-term architecture. It explicitly says ShyftR should provide continuity-oriented packs before a runtime compacts context, then learn from compaction feedback after resumed work.

3. The same plan defines runtime memory integration checkpoints:
   - Checkpoint A: read-only / shadow mode after provider, pack, and feedback API hardening.
   - Checkpoint B: advisory pack injection after pack compiler and pack-miss learning.
   - Checkpoint C: bounded-domain memory replacement only after confidence, retrieval-affinity, local service, and replacement-readiness evidence.
   - Checkpoint D: runtime-wide memory authority only after bounded-domain pilot success.

4. `docs/status/tranched-plan-status.md` says the active public repo state has moved through Phase 11 release/operating discipline, while private scoring, ranking, compaction, commercial strategy, and real pilot data remain outside public scope unless separately approved. That means compaction integration is viable as a source/next-phase concept, but not currently opened as the next public implementation tranche.

5. `docs/concepts/runtime-integration-contract.md` already supplies the four needed flows:
   - evidence ingest;
   - pack request;
   - feedback report;
   - proposal review/export.

6. `docs/concepts/memory-provider-contract.md`, `src/shyftr/provider/memory.py`, `src/shyftr/loadout.py`, and `src/shyftr/mcp_server.py` already expose most of the practical foundation: remember/search/profile/pack/feedback, role-labeled pack items, retrieval logs, token budgets, dry-run pack construction, and write-gated feedback.

## Evidence from Hermes compaction surface

Hermes already has a useful integration seam:

- `agent/context_compressor.py` performs mechanical context compaction by pruning old tool outputs, protecting head and tail context, summarizing middle turns, preserving active task state, tracking iterative summaries, and inserting fallback markers on summary failure.
- `run_agent.py` calls memory-provider hooks before compression discards context, commits memory at compression boundaries, rotates session ids, and notifies memory providers and context engines of compression-driven session transitions.
- Hermes also supports pluggable context engines and pluggable memory providers, so ShyftR can integrate as memory substrate, MCP adapter, or future context-engine assist layer without hard-forking the compactor.

This is exactly the right shape for staged integration: ShyftR can start as pre-compression advisory memory and feedback storage, then later become a compaction-aware context-engine plugin or helper.

## Why compaction alone is insufficient

A compactor is good at shrinking visible context. It is weak at long-lived memory governance unless extra machinery exists. The missing functions are:

- separating durable user/project/runtime knowledge from transient task state;
- preserving provenance for why a fact survived;
- excluding stale, unsafe, duplicated, contradicted, or sensitivity-blocked material;
- labeling trust tier and confidence;
- recording whether preserved material helped after resume;
- learning from repeated misses and over-retrieval;
- producing review-gated proposals rather than silently mutating durable authority.

Those functions match ShyftR's cell, ledger, regulator, grid, pack, feedback, confidence, and proposal model. The compactor should remain the mechanical reducer; ShyftR should become the continuity selection and learning substrate.

## Recommended architecture

### Component roles

```text
Hermes / attached runtime
- detects context pressure
- owns active session execution
- runs mechanical summarization/compaction
- owns model/provider choice and retry behavior
- decides how to inject the compacted result into the live prompt

ShyftR
- stores canonical memory in append-only cell ledgers
- builds trust-labeled continuity packs
- records retrieval logs and pack ids
- receives compaction feedback after resumed work
- updates confidence projections and review-gated proposals
- stays advisory until operator-approved authority expansion
```

### Integration flow

```text
1. pre-compression hook
   Runtime sends a compact evidence snapshot: recent goal, active state, selected closeout/tool summaries, and external ids.

2. continuity pack request
   Runtime asks ShyftR for a continuity-oriented pack with max tokens and trust-tier constraints.

3. compactor prompt scaffolding
   Runtime compactor receives the normal transcript region plus ShyftR pack sections:
   - critical constraints;
   - active durable preferences;
   - project facts;
   - caution items;
   - open decisions;
   - exclusions / do-not-preserve notes.

4. mechanical compaction
   Runtime summarizes middle context while preserving the pack as a checklist, not as unquestioned truth.

5. resumed work
   Runtime continues with the compressed context and pack provenance markers.

6. compaction feedback
   Runtime reports which pack items were useful, harmful, ignored, missing, or stale.

7. ShyftR learning
   ShyftR adjusts confidence projections, proposes new memory/pattern/rule candidates, and preserves audit evidence.
```

## Proposed dedicated tranche

A clean future tranche could be named:

`Tranche 12.1: Continuity pack and compaction feedback pilot`

### Objective

Add a runtime-neutral public-safe pilot proving that ShyftR can assist context compaction without owning mechanical summarization or silently mutating runtime policy.

### Public-safe files likely involved

- `src/shyftr/continuity.py` or `src/shyftr/compaction.py`
- `src/shyftr/provider/memory.py`
- `src/shyftr/mcp_server.py`
- `src/shyftr/loadout.py`
- `tests/test_continuity_pack.py`
- `tests/test_compaction_feedback.py`
- `examples/integrations/worker-runtime/compaction-context.jsonl`
- `docs/concepts/context-compaction-integration.md`
- `docs/runtime-integration-example.md`

### Tasks

1. Define `continuity_pack` mode over the existing pack assembler.
2. Add pack sections tuned for compaction survival:
   - active intent;
   - durable constraints;
   - current state summary hints;
   - verified decisions;
   - caution items;
   - open questions;
   - explicit exclusions.
3. Add `compaction_feedback` schema as a subtype or extension of existing feedback.
4. Record selected pack ids, useful ids, harmful ids, ignored ids, and missing-memory notes.
5. Add deterministic fixture tests for:
   - preserving high-confidence constraints;
   - excluding transient operational state;
   - surfacing stale-memory caution;
   - generating missing-memory candidate notes from compaction feedback;
   - enforcing token budget.
6. Add a replayable adapter demo where a synthetic runtime requests a continuity pack, performs deterministic mock compaction, resumes, and records feedback.
7. Keep public docs clear that ShyftR assists compaction; it does not claim to be a hosted production compactor.

### Acceptance criteria

- Continuity pack generation is deterministic against fixed fixture cells.
- Every continuity item includes trust tier, rationale, and provenance.
- Operational state pollution is excluded or labeled as ephemeral, not promoted to durable memory.
- Feedback can identify missed, stale, harmful, useful, and ignored pack items.
- No runtime policy or memory authority is changed silently.
- Existing alpha/public-readiness gates still pass.

## Hermes-specific pilot path

For Hermes, the lowest-risk pilot should be private/local first:

1. Shadow mode:
   - use the existing pre-compression memory-provider hook;
   - request a ShyftR continuity pack;
   - log pack ids and selected memory ids;
   - do not change the actual compactor prompt yet.

2. Advisory mode:
   - inject a bounded ShyftR continuity pack into the compactor prompt as reference/checklist material;
   - keep Hermes' existing summary template, head/tail protection, tool-pair sanitization, fallback warning, and active-task anchoring.

3. Feedback mode:
   - after the next successful resumed turn, record compaction feedback: useful, ignored, missing, stale, or harmful pack items.

4. Evaluation mode:
   - compare baseline compaction vs ShyftR-assisted compaction using replayed transcripts and fixed questions.
   - score continuity preservation, active-task retention, stale-memory avoidance, token cost, and operator burden.

5. Promotion gate:
   - only after replay and dogfood evidence should ShyftR-assisted compaction become default for selected profiles.

## Main risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Over-preserving stale or irrelevant memory | Use confidence, lifecycle status, caution roles, and feedback-driven decay/proposals. |
| Polluting durable memory with transient task state | Keep active state in compaction summary/session evidence; only promote durable memory through regulator review. |
| Compactor treats ShyftR pack as active instruction | Mark packs as advisory reference with provenance and trust labels; keep latest user message and runtime state authoritative. |
| Token overhead cancels compaction savings | Hard token budgets, low-latency pack mode, max item caps, and retrieval logs. |
| Private-core leakage | Keep advanced scoring/ranking/compaction heuristics private; publish only contracts, fixtures, and deterministic baseline behavior. |
| Bad feedback corrupts memory confidence | Feedback changes projections and proposals; destructive deprecation remains review-gated. |

## Viability verdict

Viable and strategically strong.

The current ShyftR architecture already has the necessary primitives: cells, append-only ledgers, pack generation, feedback, confidence projection, MCP bridge, and runtime integration contracts. Hermes already has a compatible compaction boundary and memory-provider lifecycle hooks.

The best next step is not to make ShyftR the compactor. The best next step is to add a dedicated continuity-pack / compaction-feedback tranche, prove it with deterministic runtime-neutral fixtures, then run a private Hermes shadow/advisory pilot. If the pilot shows better continuity with bounded token overhead and low stale-memory risk, integrate it into Hermes' compression flow for selected profiles.

## Recommendation

Proceed, but stage it carefully:

1. Treat the current plan as having concept-level coverage, not completed tranche coverage.
2. Add a dedicated tranche only after Phase 11 closeout or separate operator approval for new phase work.
3. Implement public-safe continuity pack and compaction feedback contracts first.
4. Keep Hermes integration private/local until replay evidence proves value.
5. Preserve the product boundary: ShyftR selects, explains, and learns what should survive; the runtime compactor compresses.
