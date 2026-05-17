# ShyftR Phase 11 — P11-3 closeout: public-safe LOCOMO-mini fixture

Date: 2026-05-17

Scope

- Adds a tiny checked-in, public-safe fixture named `locomo-mini`.
- Updates the CLI runner to select fixtures by name or by explicit JSON path.
- Adds fixture loader safety: private-data fixtures (`contains_private_data=true`) are rejected by default.
- Adds focused tests to ensure `locomo-mini` can be loaded and run through ShyftR + no-memory.

Important limitations

- This is NOT the full LOCOMO dataset.
- No datasets are downloaded.
- No private data is used.
- No broad performance / task-success / superiority claims are supported.

Smoke command

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id locomo-mini-dev \
  --output artifacts/benchmarks/locomo_mini_report.json \
  --top-k 10
```

Expected high-level statuses/metrics (fixture-limited)

- Backend `no-memory`: status `ok`; retrieval recall_at_k expected 0.0.
- Backend `shyftr`: status `ok`; retrieval recall_at_k expected > 0.0; control_audit.provenance_coverage expected 1.0.

Observed controller smoke result

```text
schema_version: shyftr-memory-benchmark-report/v0
dataset: locomo-mini v0 locomo-mini-001
shyftr ok recall_at_k=1.0 mrr=0.8333333333333334 provenance_coverage=1.0
no-memory ok recall_at_k=0.0 mrr=0.0 provenance_coverage=0.0
```

Verification gates run

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py tests/test_benchmark_locomo_mini_fixture.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
PYTHONPATH=.:src pytest -q
```

Result:

```text
7 passed
ShyftR public readiness check
PASS
1102 passed, 40 warnings in 18.34s
```

Warnings are existing `httpx` TestClient deprecation warnings in FastAPI tests.

Notes

- Report files are intentionally not committed. The harness writes to allowed roots only: artifacts/, reports/, tmp/.
