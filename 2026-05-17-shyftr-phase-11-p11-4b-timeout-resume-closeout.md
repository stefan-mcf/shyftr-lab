# ShyftR Phase 11 P11-4b closeout: timeout and resume readiness

Status: implemented and locally verified.

## Scope

P11-4b keeps the benchmark harness fixture-safe while adding run-control behavior needed before larger LOCOMO-standard, LongMemEval, or BEAM-style runs.

Implemented:

- CLI exposes `--timeout-seconds` for per adapter operation timeout.
- CLI exposes `--resume-existing` to reuse completed backend results from an existing matching report.
- CLI exposes `--max-retries` in fairness metadata; actual retry execution remains deferred.
- Runner applies operation timeout around adapter reset, ingest, and search calls using SIGALRM where available.
- Timeout-shaped backend failures are reported as `status=failed` and summarized in `aggregate_metrics.timeout_summary.timeout_failures`.
- Existing reports are resumable only when run id and fixture identity match.
- Resume mode reuses backend results with status `ok` or `skipped`; failed results are not reused.
- Aggregate metrics include `resume_summary`.

Not implemented:

- No full LOCOMO, LongMemEval, or BEAM download.
- No broad benchmark or superiority claims.
- No retry execution yet.
- No backend-owned answering.

## Smoke commands

Timeout smoke:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_mini_fixture.py::test_benchmark_timeout_marks_backend_failed
```

Resume smoke:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_mini_fixture.py::test_resume_existing_reuses_completed_backend_result
```

## Verification

Smoke verification completed:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_mini_fixture.py -q
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id p11-4b-smoke \
  --output artifacts/benchmarks/p11_4b_smoke.json \
  --top-k 1,3 \
  --timeout-seconds 5 \
  --resume-existing
```

Observed smoke report properties after the second resume run:

- runner version: `phase11-p11-4b`
- timeout seconds: `5`
- resumed backends: `shyftr`, `no-memory`
- timeout enforcement: `hard_signal_alarm`
- timeout failures: `[]`

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

- focused benchmark tests: `9 passed`
- full suite: `1104 passed, 40 warnings`
- terminology public-stale check: pass
- terminology capitalized prose check: pass
- public readiness check: pass
- git diff whitespace check: pass

## Next tranche

P11-4c should either add retry execution with deterministic retry accounting or start the first download-free standard-dataset mapping boundary. Do not run or commit large third-party datasets until retry/resume/report artifact policy is stable.
