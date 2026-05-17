# P11-3: public-safe LOCOMO-mini fixture

Status: Phase 11 harness milestone. This is NOT a full LOCOMO run.

## What this is

- A tiny, checked-in JSON fixture under `fixtures/benchmarks/locomo-mini.fixture.json`.
- It uses the existing Phase 11 fixture schema (`shyftr-memory-benchmark-fixture/v0`).
- It is explicitly public-safe and marked `contains_private_data: false`.
- It exists to prove the harness can run a *non-synthetic-name* dataset fixture shape before we add full datasets.

## What this is NOT

- NOT the full LOCOMO dataset.
- NOT a benchmark download/vendoring mechanism.
- NOT evidence for broad performance, capability, or superiority claims.

## How to run

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id locomo-mini-dev \
  --output artifacts/benchmarks/locomo_mini_report.json \
  --top-k 10
```

Optional: specify a custom fixture path.

By default, fixtures marked `contains_private_data=true` are rejected.

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path /absolute/or/relative/path/to/fixture.json \
  --run-id local-private \
  --output tmp/private_report.json
```

If you truly need to run a private fixture locally (do not publish):

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path /path/to/private.fixture.json \
  --allow-private-fixture \
  --run-id local-private \
  --output tmp/private_report.json
```

## Expected results (minimal)

- `no-memory` backend status: `ok`, with retrieval recall at k expected to be 0.0 on this fixture.
- `shyftr` backend status: `ok`, with retrieval recall at k expected to be > 0.0.

These expectations are limited to this tiny fixture.
