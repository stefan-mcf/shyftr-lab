# Benchmarks (Phase 11)

Status: Phase 11 harness docs. No benchmark result claim is made by this folder.

## P11-1: fixture-safe adapter harness

This repo includes a minimal, synthetic, fixture-safe harness for exercising the Phase 11 adapter contract.

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
  --top-k 10 \
  --include-retrieval-details
```

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
