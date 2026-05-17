# ShyftR Phase 11 Plan: External Memory Benchmarking

Date: 2026-05-17
Repo: `/Users/stefan/ShyftR`
Baseline HEAD: `88a1871313705d41f4b3cbb055fe46f83cd10e00`
Status: P11-1 implemented locally; P11-2 mem0 OSS compatibility is next

## Purpose

Phase 11 creates a reproducible, public-safe benchmark track for comparing ShyftR with other memory systems, including mem0, without making unsupported performance claims.

The phase goal is not to claim that ShyftR is better than another system. The goal is to make fair comparison possible by publishing methodology, a neutral adapter contract, fixture-safe runners, and reports that separate retrieval quality, answer quality, and audit/control qualities.

## Current truth

ShyftR already has a local evaluation bundle and proxy metrics. That bundle is useful for local health and contract coverage, but it is not a cross-system task-success benchmark.

The README explicitly keeps benchmark claims out of scope unless methodology and reproducible scripts are published. Phase 11 is the path for adding that methodology and those scripts.

mem0 has an open benchmark suite at `mem0ai/memory-benchmarks` with LOCOMO, LongMemEval, and BEAM. Phase 11 should adapt to that style rather than inventing an unrelated evaluation world.

## Benchmark posture

All public wording must keep these claims separate:

1. retrieval quality: whether the memory system returns relevant reviewed material;
2. answer quality: whether a fixed answerer plus fixed judge produces correct answers from retrieved material;
3. control and audit qualities: provenance coverage, review-gate compliance, replayability, sensitivity handling, feedback visibility, and local reproducibility.

ShyftR should compete honestly on performance metrics and also expose the control/audit dimensions that define its product thesis.

## Comparator systems

Initial comparator set:

- ShyftR local cell backend;
- mem0 OSS backend;
- mem0 Cloud backend, optional and key-gated;
- no-memory baseline;
- simple local BM25 or vector baseline, optional after the adapter contract is stable.

Do not require hosted services for the first runnable phase. Keep mem0 Cloud optional.

## Datasets and order

Recommended order:

1. LOCOMO mini fixture: smallest public-safe compatibility run;
2. LOCOMO standard run: multi-session recall, temporal reasoning, and multi-hop questions;
3. LongMemEval subset: broader long-term recall across question classes;
4. BEAM 100K: larger-scale retrieval once ingestion and report costs are controlled;
5. BEAM larger buckets only after local runtime, cost, and timeout controls are proven.

The first implementation slice should use a tiny fixture committed in the repo or generated deterministically. Full third-party datasets should be downloaded or referenced by script, not vendored blindly.

## Metrics

Retrieval metrics:

- recall at k;
- precision at k;
- mean reciprocal rank;
- nDCG;
- answer-support coverage;
- stale or conflicting-memory retrieval rate.

Answer metrics:

- correctness against dataset labels;
- fixed judge score;
- temporal correctness;
- multi-hop correctness;
- unknown or abstention behavior.

Control/audit metrics:

- provenance coverage;
- review-gate compliance;
- replay status;
- sensitivity leak rate;
- append-only preservation;
- feedback visibility;
- pack compactness and useful context per token.

Cost and performance metrics:

- ingest duration;
- search latency p50 and p95;
- answer and judge latency;
- token usage;
- estimated cost;
- timeout and retry counts.

## Adapter contract

The neutral backend adapter should expose at least:

- `reset_run(run_id)`;
- `ingest_conversation(conversation)`;
- `search(query, top_k)`;
- do not implement `answer(...)` in P11-1; reserve it for explicitly scoped experiments. Runner-owned answer generation is the default;
- `export_retrieval_details()`;
- `export_cost_latency_stats()`;
- `close()`.

The first contract should prefer runner-owned answer generation so ShyftR and mem0 are compared as memory backends rather than as different agent loops.

## Tranches

### P11-0: Methodology and plan capture — complete locally

Deliverables:

- `docs/benchmarks/methodology.md`;
- `docs/benchmarks/adapter-contract.md`;
- `docs/benchmarks/report-schema.md`;
- `docs/benchmarks/fixture-schema.md`;
- this root phase plan;
- a post-Phase-10 / Phase-11 handoff packet.

Done means:

- the methodology names datasets, metrics, comparator systems, claim rules, and non-goals;
- the adapter contract defines the minimum backend shape;
- report and fixture schemas define the first JSON contracts;
- no performance claim is made;
- terminology and public-readiness gates pass.

### P11-1: Fixture-safe adapter harness — complete locally

Deliverables:

- `src/shyftr/benchmarks/adapters/base.py`;
- `src/shyftr/benchmarks/adapters/shyftr_backend.py`;
- `src/shyftr/benchmarks/report.py`;
- `scripts/run_memory_benchmark.py`;
- `tests/test_benchmark_adapter_contract.py`.

Done means:

- a tiny synthetic fixture can run through ShyftR and a no-memory baseline;
- report JSON includes run metadata, metrics, claims allowed, and claims not allowed;
- output location checks prevent writing outside approved locations;
- no mem0 dependency is required yet.

### P11-2: mem0 OSS compatibility — next

Deliverables:

- `src/shyftr/benchmarks/adapters/mem0_backend.py`;
- optional dependency detection or clear install guidance;
- fixture-safe tests that skip cleanly when mem0 is not installed;
- docs showing local mem0 OSS setup and run command.

Done means:

- the same tiny fixture can run through ShyftR and mem0 OSS;
- reports show side-by-side retrieval, latency, and audit/control metrics;
- missing mem0 dependencies produce an explicit skipped status rather than failure.

### P11-3: LOCOMO mini run

Deliverables:

- deterministic LOCOMO-shaped mini fixture or download adapter;
- one reproducible command;
- report artifact schema;
- public-safe example report.

Done means:

- ShyftR and at least one comparator run on the same fixture;
- answerer and judge models are pinned in the report;
- limitations are explicit;
- no broad winner claim appears.

### P11-4a: Multi-cutoff and run-summary readiness

Before larger dataset adapters, land the report mechanics needed by those runs:

- comma-separated top-k cutoffs in the CLI;
- one backend search per question at the largest requested k;
- `retrieval_by_k` metrics computed from the same ranked list;
- per-backend cost/latency summaries;
- aggregate backend status and timeout summaries.

This tranche still uses only fixture-safe datasets and does not download LOCOMO, LongMemEval, or BEAM.

### P11-4b: Timeout and resume readiness

Before adding larger standard-dataset adapters, prove local run controls:

- per adapter operation timeout configured through the CLI and report fairness block;
- timeout-shaped failures are reported per backend and aggregated;
- existing matching reports can be resumed by reusing completed `ok` or `skipped` backend results;
- retry policy is disclosed but not executed until timeout/resume behavior is stable.

This tranche still uses only fixture-safe datasets and does not download LOCOMO, LongMemEval, or BEAM.

### P11-4c: Deterministic retry accounting

After timeout/resume controls, make retry behavior executable and auditable:

- `max_retries` applies to adapter reset, ingest, and search operations;
- retry events are recorded per backend with operation, attempt, status, and error type;
- aggregate reports disclose which backends had retry events;
- adapter-declared skips remain skips and are not retried.

This tranche still uses only fixture-safe datasets and does not download LOCOMO, LongMemEval, or BEAM.

### P11-4: Larger benchmark expansion

Deliverables:

- LOCOMO standard support;
- LongMemEval subset support;
- BEAM 100K support after timeout and cost controls are proven.

Done means:

- larger runs are resumable;
- reports include cost and timeout summaries;
- public docs separate benchmark method from any optional local run artifacts.

## Non-goals

Phase 11 does not include:

- hosted ShyftR operation;
- production managed-memory replacement claims;
- private-core ranking or compaction release;
- undisclosed datasets or private memory data;
- broad public superiority claims;
- changing ShyftR's review-gated durable-memory policy to mimic another system.

## Verification plan

For P11-0:

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

For implementation tranches, add:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py
PYTHONPATH=.:src pytest -q
```

## Claim rule

Any public benchmark report must include:

- dataset and version;
- run command;
- git SHA;
- backend config summary;
- answerer model;
- judge model;
- embedding model where applicable;
- top-k values;
- token and cost accounting method;
- limitations;
- claims allowed;
- claims not allowed.
