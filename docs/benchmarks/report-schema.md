# Benchmark report schema

Status: Phase 11 planning surface. This schema is the first public-safe report contract for fixture and comparator runs.

## Purpose

Benchmark reports must be machine-readable, reproducible, and honest about limits. A report is not a marketing claim. It records exactly what ran, which backends completed, which backends skipped, which metrics were computed, and which claims are allowed.

## Top-level object

A report JSON object should include:

```json
{
  "schema_version": "shyftr-memory-benchmark-report/v0",
  "run_id": "local-dev-001",
  "generated_at": "2026-05-17T00:00:00Z",
  "runner": {},
  "dataset": {},
  "fairness": {},
  "models": {},
  "backend_results": [],
  "aggregate_metrics": {},
  "limitations": [],
  "claims_allowed": [],
  "claims_not_allowed": []
}
```

Required fields:

- `schema_version`: fixed schema identifier;
- `run_id`: stable run label chosen by the runner;
- `generated_at`: ISO-8601 timestamp;
- `runner`: repo and command metadata;
- `dataset`: dataset name, version, split, and item counts;
- `fairness`: top-k values, timeout, retry, and cold/warm settings;
- `models`: answerer, judge, and embedding model disclosures where applicable;
- `backend_results`: one entry per backend;
- `aggregate_metrics`: cross-backend comparison summary;
- `limitations`: list of run limitations;
- `claims_allowed`: bounded claims supported by this run;
- `claims_not_allowed`: claims this run does not support.

## Runner object

The `runner` object should include:

- `name`: runner name;
- `version`: runner schema or package version;
- `git_sha`: ShyftR git SHA when run from this repo;
- `command`: argv list or command string;
- `cwd`: working directory;
- `python_version`: Python version;
- `environment_notes`: public-safe notes such as OS and optional dependency status.

## Dataset object

The `dataset` object should include:

- `name`: dataset name, for example `synthetic-mini`, `locomo`, `longmemeval`, or `beam`;
- `version`: dataset version or commit identifier when known;
- `split`: split or subset label;
- `conversation_count`: count of conversations or sessions ingested;
- `question_count`: count of evaluated questions;
- `fixture_path`: path or documented locator, public-safe only;
- `contains_private_data`: boolean, must be false for committed reports.

## Fairness object

The `fairness` object should include:

- `top_k_values`: list of evaluated k values;
- `timeout_seconds`: per backend operation timeout;
- `max_retries`: retry count;
- `cold_run`: whether each backend was reset before ingest;
- `answerer_owned_by_runner`: boolean;
- `judge_owned_by_runner`: boolean;
- `backend_answering_enabled`: boolean, expected false for P11-1.

Default P11-1 values:

```json
{
  "top_k_values": [10],
  "timeout_seconds": 60,
  "max_retries": 0,
  "cold_run": true,
  "answerer_owned_by_runner": true,
  "judge_owned_by_runner": true,
  "backend_answering_enabled": false
}
```

## Backend result object

Each backend result should include:

- `backend_name`: backend label;
- `status`: `ok`, `skipped`, or `failed`;
- `status_reason`: reason for skipped or failed status;
- `config_summary`: public-safe backend config summary;
- `ingest`: duration and item counts;
- `search`: latency and returned item counts;
- `metrics`: per-backend metrics;
- `retrieval_details`: optional public-safe ranked details;
- `cost_latency`: token, cost, and timing summary;
- `control_audit`: provenance, review, replay, sensitivity, and feedback metrics;
- `errors`: public-safe errors when status is `failed`.

## Metric semantics

Retrieval metrics:

- `recall_at_k`: relevant returned items divided by relevant expected items;
- `precision_at_k`: relevant returned items divided by returned items;
- `mrr`: reciprocal rank of the first relevant returned item;
- `ndcg`: discounted gain using relevance labels;
- `answer_support_coverage`: questions whose returned items contain enough material to answer;
- `conflict_retrieval_rate`: questions where returned items include stale or conflicting material.

Control/audit metrics:

- `provenance_coverage`: returned items with evidence or anchor identifiers divided by returned items;
- `review_gate_compliance`: returned authoritative items that satisfy the backend's declared approval policy;
- `replay_status`: `passed`, `failed`, `not_supported`, or `not_run`;
- `sensitivity_leak_rate`: unsafe returned items divided by returned items;
- `append_only_preservation`: `passed`, `failed`, or `not_supported`;
- `feedback_visibility`: whether the backend can record whether retrieved material helped;
- `pack_compactness`: useful returned text tokens divided by total returned text tokens.

When a backend cannot expose a metric, use `not_supported` rather than inventing a number.

## Claim blocks

`claims_allowed` should include only claims supported by the run. `claims_not_allowed` should explicitly block broad superiority, production, hosted, or unmeasured task-success claims.
