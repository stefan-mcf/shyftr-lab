# ShyftR broad roadmap concept

Source context: `deep-research-report.md` in this directory, plus follow-up discussion about when experiments and benchmarks should happen.

Purpose: this is a broad concept roadmap, not a tranche plan. Use it as the source document for creating smaller execution plans. The main principle is that ShyftR should not add frontier-memory features on top of unresolved schema and correctness drift. It should first stabilize the core, then evolve into a typed, evaluated, multi-class memory substrate.

## Strategic direction

ShyftR should remain local-first, ledger-backed, inspectable, scoped, and review-aware.

The goal is not to become an opaque vector-memory service. The goal is to become a high-integrity agent memory substrate with:

- append-only canonical ledgers as truth;
- rebuildable indexes and projections as acceleration layers;
- review-gated durable memory promotion;
- trust-labelled and policy-aware retrieval;
- explicit separation between working context, carry/continuity, durable semantic memory, procedural memory, episodic memory, and resource memory;
- evaluation strong enough to prove memory utility, not just memory persistence.

## Core thesis from the report

The report's central finding is that ShyftR's conceptual architecture is ahead of its current implementation quality.

The repo already has strong seams:

- cells as bounded memory namespaces;
- canonical append-only ledgers;
- candidate-to-memory lifecycle;
- bounded packs;
- feedback and confidence evolution;
- negative-space retrieval for cautions and anti-patterns;
- separate continuity/carry and live-context paths;
- local-first safety posture.

The next phase should therefore prioritize disciplined consolidation before large feature expansion.

## Roadmap principle: benchmark while building, not after

Experiments and benchmarks should not wait until the roadmap is complete.

They should begin immediately as a baseline and mature alongside the roadmap.

Use this rule:

- early benchmarks steer the roadmap;
- tranche benchmarks prove each layer adds value;
- final benchmarks validate the full system only after the relevant pieces exist.

Avoid a long build followed by a late discovery that the architecture did not improve task success, memory utility, or stale-memory suppression.

## Phase 0: Baseline and evidence harness

Goal: establish current ShyftR behavior before major changes.

This phase should happen before or alongside the first stabilization tranche.

Scope:

- define small ShyftR-native synthetic tasks;
- capture current durable-memory-only behavior;
- capture durable + carry/continuity behavior;
- capture durable + continuity + live-context behavior;
- capture current pack/loadout behavior;
- capture current stale-memory, harmful-memory, ignored-memory, and missing-memory rates;
- preserve deterministic fixtures that can be rerun after each major tranche.

Outputs:

- baseline evaluation fixtures;
- baseline metrics report;
- minimal command or script entrypoint for rerunning baseline;
- documented interpretation of what the baseline does and does not prove.

Key metrics:

- pack size;
- useful-memory inclusion rate;
- stale-memory inclusion rate;
- harmful-memory inclusion rate;
- missing-memory rate;
- ignored-memory rate;
- resume-state correctness where applicable;
- deterministic replay/projection correctness.

This should stay lightweight at first. It does not need to be a full academic benchmark harness yet.

## Phase 1: Core memory model stabilization

Goal: remove correctness and schema drift before building more advanced memory layers.

This is the highest-priority implementation phase.

Scope:

- decide the canonical internal abstraction for `pack` versus `loadout`;
- keep public language centered on evidence, candidate, memory, pack, and feedback;
- keep legacy aliases only as compatibility surfaces or raw historical fields;
- fix append-only latest-row semantics in confidence and lifecycle paths;
- fix retrieval-log writer/projection schema mismatch;
- ensure append-only duplicate rows collapse consistently during replay/materialization;
- add contract tests for ledger append, replay, projection, and latest-row behavior;
- add migration/adapters where compatibility is required;
- update status/docs so public claims match implementation.

Expected outputs:

- canonical schema or ADR;
- pack/loadout unification plan or implementation;
- confidence stale-read fix;
- retrieval-log schema fix;
- ledger replay/projection contract tests;
- terminology guard updates if needed;
- docs/status correction pass.

Benchmarks during this phase:

- append-only replay correctness;
- latest-row-wins behavior;
- retrieval-log projection completeness;
- pack/loadout equivalence before and after unification;
- no regression against Phase 0 baseline;
- clean public/readiness terminology checks.

Success criteria:

- no known high-severity consistency bug in append-only memory paths;
- no duplicate core pack logic without an explicit compatibility boundary;
- public docs and implemented surfaces tell the same story;
- deterministic baseline still passes.

## Phase 2: Typed working context and carry-state model

Goal: turn the live context cell from flat text entries into typed working state that can survive compression and support reliable resume.

The report validates the carry/context-cell concepts, but says their implementation needs stronger typed abstractions.

Scope:

Add or formalize typed working-memory records such as:

- `goal`;
- `subgoal`;
- `plan_step`;
- `constraint`;
- `decision`;
- `assumption`;
- `artifact_ref`;
- `tool_state`;
- `error`;
- `recovery`;
- `open_question`;
- `verification_result`.

Each record should support, where useful:

- timestamp or interval;
- source/evidence reference;
- parent/child relationship;
- scope;
- sensitivity;
- TTL or retention hint;
- status;
- confidence or utility signal;
- grounding/resource refs.

Carry/continuity should evolve from bounded durable-memory advisory packs toward compact session-state deltas:

- unresolved goals;
- current plan position;
- open loops;
- commitments;
- constraints;
- active assumptions;
- recent failures and recoveries;
- important artifact refs;
- cautions required for resumption.

Expected outputs:

- typed live-context schema;
- carry-state/checkpoint object shape;
- capture APIs/CLI/MCP updates if needed;
- harvest rules that classify typed entries correctly;
- docs/examples showing session resume from typed state.

Benchmarks during this phase:

- heuristic live context versus typed live context;
- resume success rate;
- missing-state rate;
- wrong-state inclusion rate;
- pack size;
- ability to preserve decisions, constraints, failures, recoveries, open questions, and artifact refs;
- operator review burden;
- harvest classification precision/recall for discard, archive, continuity, memory, and skill routing.

Success criteria:

- typed context packs are smaller or more accurate than flat text packs;
- session resumption improves on realistic multi-step tasks;
- durable memory is not polluted with transient working state;
- carry remains advisory unless an explicit reviewed policy says otherwise.

## Phase 3: First-class memory classes

Goal: formalize distinct memory classes with distinct write, merge, retention, and retrieval rules.

The report recommends treating these as first-class stores or object types:

- working/context memory;
- carry/continuity memory;
- episodic memory;
- semantic memory;
- procedural memory;
- resource memory;
- rule memory.

Proposed class responsibilities:

| Memory class | Contents | Authority | Retention |
|---|---|---|---|
| Working/context | active goals, current plan, open loops, tool state, recent observations | non-authoritative | minutes to session |
| Carry/continuity | compact checkpoint, high-salience state deltas, resumable intent, constraints, cautions | advisory | session to days |
| Episodic | timestamped episodes with provenance, actors, tools, outcomes | review-gated | days to months |
| Semantic | stable facts, preferences, concepts, distilled lessons | authoritative after review | long-term |
| Procedural | skills, workflows, recovery recipes, tool-use patterns | authoritative after review/evaluation | long-term |
| Resource | file refs, screenshots, URLs, artifacts, code spans, log spans, tool outputs | authoritative by reference | long-term |
| Rule | explicit policies, guardrails, supersession decisions | authoritative after review | long-term |

Expected outputs:

- canonical memory object or family of objects;
- memory-type field and lifecycle policy;
- retention and promotion rules per memory class;
- retrieval filters by memory type;
- migration path from existing traces/fragments/sources where needed;
- docs explaining the hierarchy without overclaiming.

Benchmarks during this phase:

- durable-only versus durable + carry/live context;
- typed context versus typed context + episodic support;
- stale-memory suppression by memory class;
- harmful/ignored/missing memory feedback by class;
- review burden by class.

Success criteria:

- memory classes have clear boundaries;
- write paths do not mix transient state with durable semantic memory;
- procedural memory routes toward skills/workflows rather than generic fact storage;
- resource memory stores references and grounding handles instead of dumping large blobs.

## Phase 4: Retrieval orchestration upgrade

Goal: move beyond lexical and heuristic retrieval in newer paths while preserving explainability and local-first operation.

Current hybrid retrieval is a good base, but frontier behavior needs policy orchestration across multiple retrieval signals.

Scope:

- strengthen local semantic retrieval path;
- consider `sqlite-vec`, FAISS, or another local ANN baseline before any dedicated vector service;
- add temporal retrieval/reranking;
- add explicit valid-time, observed-time, expiry, and freshness-window handling where useful;
- add structural or graph-aware reranking;
- add utility-aware reranking from feedback;
- add contradiction and supersession handling;
- preserve negative-memory/caution retrieval;
- condition retrieval on current plan step, tool state, memory class, and scope;
- add query-aware reranking so packs optimize for resume utility, not only overlap;
- keep retrieval logs explainable.

Candidate retrieval signals:

- lexical relevance;
- dense semantic similarity;
- tag/kind match;
- scope match;
- time/recency;
- confidence;
- utility/reuse;
- decay;
- trust tier;
- contradiction/supersession state;
- negative-space relevance;
- current plan-step match;
- resource proximity.

Expected outputs:

- retrieval orchestration policy;
- explainable score traces;
- local ANN/index implementation or adapter;
- temporal/utility reranker;
- contradiction/staleness suppression logic;
- temporal metadata contract for freshness and chronology;
- benchmark harness for retrieval metrics.

Benchmarks during this phase:

- Precision@k;
- Recall@k;
- MRR;
- nDCG;
- stale-memory inclusion rate;
- contradiction rate;
- caution/negative-memory recall;
- p50/p95 retrieval latency;
- pack token count;
- task success lift.

Success criteria:

- retrieval improves under paraphrase, abstraction, long-horizon recall, and multi-step plans;
- caution and anti-pattern memories are surfaced when relevant;
- stale or superseded memories are suppressed;
- explainability is preserved.

## Phase 5: Episodic consolidation and rehearsal

Goal: add offline or sleep-time consolidation so memory improves without bloating online context.

The report highlights LightMem, Generative Agents, and ExpeL-style ideas: cheap online capture, heavier offline consolidation, reflection, rehearsal, and procedural learning.

Scope:

- cluster episodes;
- deduplicate paraphrastic or equivalent memories;
- merge stable concepts;
- propose semantic memory promotions;
- propose procedural skill/workflow memories;
- archive low-value context;
- identify stale or contradictory memories;
- add explicit demotion, challenge, and oblivion proposal paths for memories that should decay or be retired;
- rehearse high-value memories against held-out or synthetic tasks;
- record consolidation decisions as review-gated proposals.

Expected outputs:

- consolidation pipeline;
- duplicate merge proposal format;
- semantic promotion proposal format;
- procedural skill proposal format;
- stale/challenge/deprecate proposal format;
- rehearsal task fixtures;
- operator review surface or report.

Benchmarks during this phase:

Compare:

- no consolidation;
- rule-only consolidation;
- semantic cluster/merge consolidation;
- consolidation + rehearsal.

Measure:

- duplicate growth;
- semantic drift;
- stale recall;
- operator review burden;
- downstream task success;
- memory utility feedback;
- harmful/ignored/missing memory rates;
- calibration quality.

Success criteria:

- memory base becomes smaller, cleaner, or more useful over time;
- consolidation does not silently mutate durable memory without review;
- procedural lessons route into skills/workflows where appropriate;
- rehearsal improves retrieval or task success measurably.

## Phase 6: Resource and multimodal memory

Goal: make ShyftR remember agent environment evidence, not only conversation text.

The report argues this is a major frontier-memory differentiator: agents need to remember files, screenshots, logs, code spans, browser state, and produced artifacts.

Scope:

- add first-class `resource` memory objects;
- store references, not large raw blobs by default;
- support file paths, URLs, screenshots, code spans, notebook cells, terminal output spans, browser state, and generated artifacts;
- support typed artifact-state slots, hashes, and deltas for current file/tool/artifact state where useful;
- attach grounding refs to semantic/procedural/episodic memories;
- add resource-aware retrieval;
- add sensitivity and retention policy for resource refs;
- avoid leaking private local artifacts into public examples.

Expected outputs:

- resource memory schema;
- artifact/ref capture helpers;
- resource retrieval hooks;
- screenshot/file/log/code-span examples with synthetic fixtures;
- privacy guardrails for resource refs.

Benchmarks during this phase:

- resource-memory grounding benchmark;
- screenshot/resource QA tasks where applicable;
- file/log/code-span recall tasks;
- answer faithfulness to referenced evidence;
- broken-reference detection;
- storage/index overhead.

Success criteria:

- memories can point to the exact evidence that supports them;
- agents can resume artifact-heavy workflows more accurately;
- resource memory improves task success beyond text-only memory;
- public docs/examples remain synthetic and privacy-safe.

## Phase 7: Privacy, policy, and safety hardening

Goal: make memory authority, sensitivity, and write policy robust enough for serious use.

Scope:

- field-level sensitivity labels;
- stronger policy engine for memory writes and promotions;
- poisoning and prompt-injection tests;
- conflict and contradiction handling;
- explicit authority boundaries between runtime, memory cell, carry cell, and durable memory;
- review surfaces for proposed durable changes;
- safe defaults for MCP/HTTP/CLI write paths;
- redactable projections and provable export filters for public/private boundaries;
- public/private boundary checks.

Expected outputs:

- policy schema updates;
- safety test fixtures;
- poisoning/contradiction benchmark tasks;
- explicit direct-write guardrails;
- export/redaction verification fixtures;
- updated public/private readiness checks.

Benchmarks during this phase:

- harmful-memory inclusion rate;
- prompt-injection success rate;
- poisoning suppression rate;
- sensitive-memory leakage rate;
- contradiction handling precision;
- review burden;
- false positive/false negative safety decisions.

Success criteria:

- ShyftR proposes; runtime/operator applies;
- durable mutation remains review-gated unless explicitly enabled by local policy;
- private data and private-core heuristics do not leak into public surfaces;
- safety checks are measurable, not only documented.

## Phase 8: Full-system evaluation and frontier-readiness report

Goal: validate whether the completed memory system actually improves agent performance, cost, and continuity.

This is the phase that should wait until major roadmap pieces exist.

Compare at least:

- no memory;
- durable memory only;
- durable + continuity;
- durable + continuity + live context;
- full tiered ShyftR with episodic/semantic/procedural/resource memory;
- long-context-only baseline if practical;
- vanilla RAG baseline if practical.

Additional benchmark tracks:

- harvest classification benchmark for discard/archive/continuity/memory/skill routing;
- memory hygiene benchmark for duplicate rate, stale-memory rate, contradiction rate, and harmful-memory survival over time;
- latency and throughput benchmark for append latency, pack latency, index rebuild time, and token cost versus corpus size.

Metric families:

| Metric family | Concrete measures |
|---|---|
| Retrieval quality | Precision@k, Recall@k, MRR, nDCG, contradiction rate, stale-memory inclusion rate |
| Answer quality | exact match/F1 where available, citation correctness, faithfulness to evidence |
| Memory utility | task success lift, harmful-memory rate, ignored-memory rate, missing-memory rate |
| Efficiency | tokens per successful task, API calls per task, p50/p95 retrieval latency, pack size |
| Stability | performance over time, duplicate growth rate, semantic drift, supersession correctness |
| Calibration | Brier score or ECE over confidence/usefulness predictions, challenge/deprecate precision |

Potential external benchmarks or inspirations:

- LoCoMo for long-term conversational memory;
- LongMemEval for long-term memory quality and efficiency;
- LongBench for broader long-context understanding;
- ScreenshotVQA or synthetic screenshot/resource QA if resource memory is implemented;
- ShyftR-native fixtures for lifecycle, review gates, continuity, public/private, and local operator workflows.

Expected outputs:

- full benchmark report;
- ablation table;
- visualizations for architecture layers, continuity lifecycle, retrieval/latency tradeoffs, and compaction-recovery quality under fixed token budgets;
- frontier-readiness assessment;
- known limitations;
- next-research backlog;
- public-safe claims that match measured evidence.

Success criteria:

- each memory layer shows measurable value or is revised/removed;
- ShyftR demonstrates lower prompt bloat and better continuity without claiming to expand provider context windows;
- claims are grounded in reproducible evidence;
- public wording says what the proof shows, not what the architecture hopes to show.

## Suggested tranche families

Use the phases above to create concrete tranche plans. A likely tranche breakdown:

1. Baseline evaluation harness and current-state metrics.
2. Canonical ontology/schema ADR.
3. Pack/loadout unification.
4. Append-only correctness fixes: confidence, retrieval logs, replay/projection.
5. Projection-fidelity and provider-contract regression tests, including SQLite rebuild, provider trust-tier semantics, and grid-fingerprint double-count protection.
6. Docs/CLI example and terminology alignment pass so public surfaces match the canonical parser and contracts.
7. Typed live-context schema MVP.
8. Carry-state/checkpoint MVP.
9. Typed context versus heuristic context benchmark.
10. First-class episodic memory objects.
11. Semantic/procedural/resource memory class boundaries.
12. Retrieval orchestration policy and local ANN path.
13. Temporal/utility/contradiction reranking.
14. Offline consolidation proposal pipeline.
15. Rehearsal and memory-utility evaluation.
16. Resource/artifact memory MVP.
17. Privacy/policy hardening, export-filter verification, and poisoning tests.
18. Full ablation benchmark and frontier-readiness report.

These do not need to be executed as one giant program. The first four are the stabilizing foundation. The next three validate the carry/context-cell idea. The later phases should be gated by measured improvement.

## Claim discipline

Use careful language in plans and public docs.

Safe claims:

- ShyftR reduces prompt bloat by retrieving bounded memory packs.
- ShyftR improves continuity by separating live context, carry/continuity, and durable memory.
- ShyftR uses append-only ledgers as canonical memory truth.
- ShyftR keeps durable mutation review-gated by default.
- ShyftR can evaluate whether memory layers improve task success and reduce stale recall.

Avoid unless directly proven:

- ShyftR is frontier-grade.
- ShyftR expands a model's hard context window.
- ShyftR outperforms long-context models or RAG generally.
- ShyftR supports production multi-tenant memory.
- ShyftR has robust multimodal memory before resource-memory work is actually implemented.

## Design posture

The roadmap should stay ruthless about consolidation.

Before adding a feature, ask:

- Which memory class owns this?
- Is this canonical truth, projection, pack, feedback, or proposal?
- Does this belong in durable memory, carry state, live context, procedural skill memory, or resource memory?
- Is the write path review-gated?
- Can the behavior be replayed from ledgers?
- Can the result be measured?
- Does it reduce task failure, stale recall, missing context, token bloat, or operator burden?

If the answer is unclear, the tranche should start with schema and evaluation, not implementation expansion.
