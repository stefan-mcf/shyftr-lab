# Benchmark adapter contract

Status: Phase 11 planning surface. This contract defines the neutral backend shape for memory benchmarks.

## Purpose

The benchmark adapter contract lets ShyftR compare against other memory systems without hard-coding benchmark logic to one backend API.

Adapters should expose memory-backend behavior only. The benchmark runner owns dataset iteration, answer generation, judging, report writing, and fairness controls unless a later experiment explicitly tests backend-owned agent loops.

## Required methods

A backend adapter should provide:

```text
reset_run(run_id)
ingest_conversation(conversation)
search(query, top_k)
export_retrieval_details()
export_cost_latency_stats()
close()
```

`answer(question, retrieved_items)` may be added only for experiments where backend-owned answer generation is intentionally being evaluated.

## Data objects

Conversation input should include:

- conversation id;
- session id when available;
- ordered messages or events;
- timestamp when available;
- actor label when available;
- public-safe metadata.

Search input should include:

- question id;
- query text;
- top-k value;
- optional expected answer labels, used only for evaluation and never provided to the backend adapter;
- optional temporal hints;
- optional memory class hints.

Search output should include:

- backend name;
- run id;
- query id;
- ranked items;
- score when available;
- text payload returned to the answerer;
- provenance identifiers when available;
- sensitivity label when available;
- review status when available;
- timing and token counters when available.

## ShyftR mapping

The ShyftR adapter should map:

- benchmark conversation input to local cell evidence and reviewed memory setup;
- benchmark query to ShyftR pack/search behavior;
- ranked returned items to pack candidates or search capsules;
- provenance identifiers to ledger-backed memory or Episode anchors;
- review status to approved/proposed/rejected state;
- feedback visibility to pack feedback records when a run records feedback.

The adapter must not weaken review-gated behavior merely to match another backend. If a fixture requires approved memory, the fixture setup should approve it deliberately.

## mem0 mapping

The mem0 adapter should map:

- benchmark conversation input to mem0 add/ingest operations;
- benchmark query to mem0 search;
- returned memories to ranked search items;
- entity or graph details to retrieval details when available;
- latency and token counters where the mem0 API exposes them.

mem0 Cloud must be optional and key-gated. mem0 OSS should be the first comparator target after the ShyftR/no-memory harness is stable.

## No-memory baseline

The no-memory adapter returns no retrieved items. It establishes the answerer-only baseline and helps separate memory value from model prior knowledge.

## Error and skip handling

Adapters must report:

- `ok` when a backend completed the run;
- `skipped` when a dependency or credential is missing;
- `failed` when the backend attempted the run and errored.

Skip and failure reasons must be included in the report.

## Report contract

Every adapter result must be serializable to JSON and safe to include in public fixture reports. Real private memory data must not appear in committed reports.

Reports must include `claims_allowed` and `claims_not_allowed` blocks so readers do not confuse a fixture pass with a broad performance claim.
