# ShyftR Phase 11 P11-4c closeout: deterministic retry accounting

Status: implemented and locally verified.

## Scope

P11-4c keeps the benchmark harness fixture-safe while making retry behavior executable and auditable before any larger standard-dataset run.

Implemented:

- `--max-retries` now applies to adapter `reset_run`, `ingest_conversation`, and `search` operations.
- Retry operations remain bounded by the configured per-operation timeout.
- `AdapterSkip` remains a skip and is not retried.
- Successful retries are recorded in backend `cost_latency.retry_summary`.
- Exhausted retries are recorded in failed backend `cost_latency.retry_summary`.
- Aggregate metrics include `aggregate_metrics.retry_summary`.
- Runner version is now `phase11-p11-4c`.

Not implemented:

- No full LOCOMO, LongMemEval, or BEAM download.
- No broad benchmark or superiority claims.
- No backend-owned answering.
- No retry backoff or jitter; retries are deterministic for report reproducibility.

## Smoke command

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_mini_fixture.py::test_retry_execution_records_successful_retry
```

Expected smoke properties:

- flaky backend status is `ok` after one retry;
- fairness `max_retries` is `1`;
- backend retry event count is `2` (`retrying`, then `succeeded_after_retry`);
- aggregate retry summary reports one backend with retry events.

## Verification

Smoke verification completed:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_mini_fixture.py::test_retry_execution_records_successful_retry
```

Observed smoke result:

- `1 passed`
- flaky backend status is `ok` after one retry;
- fairness `max_retries` is `1`;
- backend retry event count is `2` (`retrying`, then `succeeded_after_retry`);
- aggregate retry summary reports one backend with retry events.

Additional fixture smoke completed:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id p11-4c-smoke \
  --output artifacts/benchmarks/p11_4c_smoke.json \
  --top-k 1,3 \
  --timeout-seconds 5 \
  --max-retries 1
```

Observed report properties:

- runner version: `phase11-p11-4c`
- fairness max retries: `1`
- retry-event backend count: `0` for the non-flaky smoke adapters

Full gate verification completed before commit:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py tests/test_benchmark_locomo_mini_fixture.py
PYTHONPATH=.:src pytest -q
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

Result:

- focused benchmark tests: `10 passed`
- full suite: `1105 passed, 40 warnings`
- terminology public-stale check: pass
- terminology capitalized prose check: pass
- public readiness check: pass
- git diff whitespace check: pass

## Next tranche

P11-4d should start the first download-free standard-dataset mapping boundary, likely LOCOMO-standard schema mapping documentation and loader scaffolding without downloading or committing the full dataset.
