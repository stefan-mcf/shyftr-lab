# Benchmarks (Phase 11)

Status: Phase 11 harness docs. No benchmark result claim is made by this folder.

## P11-1: fixture-safe adapter harness

This repo includes a minimal, fixture-safe harness for exercising the Phase 11 adapter contract.
It starts with a synthetic fixture, adds a tiny public-safe LOCOMO-mini shaped fixture (P11-3), and now reports retrieval metrics at multiple top-k cutoffs from one fair ranked-list call per question (P11-4a).

Key constraints:

- The fixture is tiny and deterministic.
- No third-party datasets are downloaded or run.
- No private data is used.
- The harness compares:
  - ShyftR local backend adapter
  - no-memory baseline adapter
- The harness emits a JSON report following `docs/benchmarks/report-schema.md`.

Run locally:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --run-id local-dev \
  --output artifacts/benchmarks/memory_report.json \
  --top-k 1,3,10 \
  --include-retrieval-details
```

P11-3 LOCOMO-mini fixture (public-safe, tiny, checked-in JSON; NOT the full LOCOMO dataset):

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id locomo-mini-dev \
  --output artifacts/benchmarks/locomo_mini_report.json \
  --top-k 10
```

P11-4a multi-cutoff readiness:

- `--top-k` accepts a single integer or comma-separated cutoffs such as `1,3,10`.
- The runner queries each backend once at the maximum requested k, then computes `metrics.retrieval_by_k` for every configured cutoff.
- Reports include `cost_latency.summary` per successful backend and an aggregate timeout summary. Timeout enforcement remains reported-only until a later larger-run tranche adds hard cancellation.

Output write safety:

The runner refuses to write reports outside of:

- `artifacts/`
- `reports/`
- `tmp/`

This is intended to reduce accidental side effects during local benchmark development.

## P11-2: mem0 OSS/local adapter (optional)

This harness can optionally include a mem0 OSS/local adapter.

Notes:

- This is NOT mem0 Cloud. Cloud/API-key flows are intentionally out-of-scope for the default public harness path.
- The mem0 OSS adapter is opt-in via a flag.
- If the mem0 Python package is not installed, the backend is reported as status `skipped` (not failed).

Run with mem0 OSS enabled:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --run-id local-dev \
  --output artifacts/benchmarks/memory_report.json \
  --top-k 10 \
  --include-mem0-oss
```

## Dataset status / order

- `synthetic-mini` (P11-1): deterministic in-code fixture, contract validation only.
- `locomo-mini` (P11-3): tiny checked-in JSON fixture with a LOCOMO-like shape, public-safe.

Planned (not included / not downloaded by default): full LOCOMO, LongMemEval, BEAM.

Claim limitations:

- These fixtures are not a task-success benchmark.
- Do not use fixture runs for broad benchmark or superiority claims.
