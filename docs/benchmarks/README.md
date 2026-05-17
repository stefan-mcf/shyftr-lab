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
