# Benchmarks (Phase 11)

Status: Phase 11 harness docs. No benchmark result claim is made by this folder.

## P11-1: fixture-safe adapter harness

This repo includes a minimal, fixture-safe harness for exercising the Phase 11 adapter contract.
It starts with a synthetic fixture, adds a tiny public-safe LOCOMO-mini shaped fixture (P11-3), reports retrieval metrics at multiple top-k cutoffs from one fair ranked-list call per question (P11-4a), includes a download-free LOCOMO-standard mapping layer (P11-4d), and now closes Phase 11 with measured fixture reports plus a polished HTML closeout dossier.

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
- Reports include `cost_latency.summary` per successful backend and an aggregate timeout summary. Hard timeout enforcement uses SIGALRM where available; environments without SIGALRM report timeout enforcement as unavailable.

P11-4b timeout and resume readiness:

- `--timeout-seconds` sets a per adapter operation timeout. The runner uses SIGALRM where available and reports timeout-shaped failures in `aggregate_metrics.timeout_summary`.
- `--resume-existing` reuses `ok` and `skipped` backend results from an existing report with the same run id and fixture identity, so larger local runs can resume without rerunning completed backends.
- `--max-retries` is now applied to adapter reset, ingest, and search operations. Retry details are recorded separately in the report.

P11-4c deterministic retry accounting:

- `--max-retries` now executes retry attempts for adapter reset, ingest, and search operations.
- Retry events are written to each backend's `cost_latency.retry_summary` and aggregated under `aggregate_metrics.retry_summary`.
- `AdapterSkip` remains a skip, not a retried failure.

P11-4d LOCOMO-standard mapping layer:

- `--fixture locomo-standard` is allowed only with an explicit local `--fixture-path`.
- `--fixture-format locomo-standard` maps a normalized local LOCOMO-style JSON file into the Phase 11 fixture contract.
- No dataset is downloaded by the runner, and full LOCOMO claims remain disallowed.

P11-4e LOCOMO local conversion helper:

- `scripts/convert_locomo_standard_fixture.py` converts operator-provided local normalized LOCOMO-style JSON/JSONL into guarded fixture JSON.
- The helper writes only under `artifacts/`, `reports/`, or `tmp/` and requires `.json` output.
- By default, the helper writes a `.manifest.json` sidecar with input/output SHA-256 digests, fixture counts, privacy posture, and claim limits.
- Private or unknown input requires `--allow-private-input`; public-safe output requires `--public-output` plus `contains_private_data: false`.

Final closeout:

- `reports/benchmarks/phase11_synthetic_mini.json` and `reports/benchmarks/phase11_locomo_mini.json` are the committed public-safe fixture reports.
- `docs/benchmarks/phase11-final-benchmark-report.json` summarizes the closeout in machine-readable form.
- `docs/benchmarks/phase11-final-benchmark-report.html` is the polished human-facing report.

Output write safety:

The runner and local conversion helper refuse to write reports or converted fixtures outside of:

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
- `locomo-standard` (P11-4d): download-free mapping layer for explicit local normalized LOCOMO-style JSON files.

Planned (not included / not downloaded by default): full LOCOMO execution, LongMemEval, BEAM.

Claim limitations:

- These fixtures are not a task-success benchmark.
- Do not use fixture runs for broad benchmark or superiority claims.
