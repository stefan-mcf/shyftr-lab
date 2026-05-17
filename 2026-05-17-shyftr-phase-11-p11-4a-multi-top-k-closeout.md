# ShyftR Phase 11 P11-4a closeout: multi-top-k report readiness

Status: implemented and locally verified.

## Scope

P11-4a is a prerequisite tranche before larger benchmark adapters. It keeps runs fixture-safe and public-safe while adding report mechanics needed for LOCOMO-standard, LongMemEval, and BEAM-style evaluation later.

Implemented:

- CLI accepts a single `--top-k` value or comma-separated cutoffs such as `1,3,5`.
- Runner normalizes positive top-k cutoffs and rejects invalid non-positive values.
- Runner calls each backend once per question at the largest requested k.
- Runner computes `metrics.retrieval_by_k` for every requested cutoff from the same ranked list.
- Existing `metrics.retrieval` remains as a compatibility block for the largest evaluated k.
- Successful backend results now include `cost_latency.summary`.
- `aggregate_metrics` now includes backend status counts, cost/latency summaries, and a timeout summary.
- Timeout enforcement is explicitly `reported_only`; hard cancellation is deferred to a later larger-run tranche.

Not implemented:

- No full LOCOMO, LongMemEval, or BEAM download.
- No broad benchmark or superiority claims.
- No hosted, production, or task-success claims.
- No backend-owned answering.

## Smoke command

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id p11-4a-smoke \
  --output artifacts/benchmarks/p11_4a_smoke.json \
  --top-k 1,3,5 \
  --include-retrieval-details
```

Observed smoke report properties:

- runner version: `phase11-p11-4a`
- fairness top-k values: `[1, 3, 5]`
- `shyftr`: status `ok`, searched at k=5, reported `retrieval_by_k` keys `1`, `3`, `5`
- `no-memory`: status `ok`, searched at k=5, reported `retrieval_by_k` keys `1`, `3`, `5`
- aggregate backend status counts: `{"ok": 2}`
- aggregate timeout summary: `timeout_seconds=60`, `timeout_failures=[]`, `timeout_enforcement=reported_only`

The smoke report artifact was removed after inspection and is not committed.

## Verification

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

- focused benchmark tests: `7 passed`
- full suite: `1102 passed, 40 warnings`
- terminology public-stale check: pass
- terminology capitalized prose check: pass
- public readiness check: pass
- git diff whitespace check: pass

## Next tranche

P11-4b should add hard timeout/resume controls or the first download-free standard-dataset mapping boundary. Do not run or commit large third-party datasets until timeout, resume, and report artifact policies are proven.
