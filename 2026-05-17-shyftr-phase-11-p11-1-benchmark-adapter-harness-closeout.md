# ShyftR Phase 11 P11-1 Closeout: Fixture-Safe Benchmark Adapter Harness

Date: 2026-05-17
Repo: `/Users/stefan/ShyftR`
Baseline HEAD: `88a1871313705d41f4b3cbb055fe46f83cd10e00`
Status: P11-1 implemented and verified; repository landing is verified from the final git HEAD and origin/main ref

## Verdict

P11-1 is implemented locally. ShyftR now has a minimal fixture-safe benchmark harness that can compare the ShyftR local backend with a no-memory baseline on a tiny synthetic fixture and emit a public-safe JSON report.

This is not a broad benchmark claim. The run proves the adapter/report contract and local harness shape only.

## Implemented surface

Docs:

- `docs/benchmarks/README.md`
- `docs/benchmarks/methodology.md`
- `docs/benchmarks/adapter-contract.md`
- `docs/benchmarks/report-schema.md`
- `docs/benchmarks/fixture-schema.md`

Root planning and handoff:

- `2026-05-17-shyftr-phase-11-external-memory-benchmarking-tranched-plan.md`
- `2026-05-17-shyftr-phase-11-external-memory-benchmarking-handoff-packet.md`
- `2026-05-17-shyftr-phase-11-p11-1-benchmark-adapter-harness-closeout.md`

Code:

- `src/shyftr/benchmarks/__init__.py`
- `src/shyftr/benchmarks/types.py`
- `src/shyftr/benchmarks/fixture.py`
- `src/shyftr/benchmarks/report.py`
- `src/shyftr/benchmarks/runner.py`
- `src/shyftr/benchmarks/adapters/__init__.py`
- `src/shyftr/benchmarks/adapters/base.py`
- `src/shyftr/benchmarks/adapters/no_memory.py`
- `src/shyftr/benchmarks/adapters/shyftr_backend.py`
- `scripts/run_memory_benchmark.py`
- `tests/test_benchmark_adapter_contract.py`

## What works

The harness now supports:

- deterministic synthetic mini fixture;
- neutral backend adapter protocol;
- ShyftR local backend adapter;
- no-memory baseline adapter;
- report schema `shyftr-memory-benchmark-report/v0`;
- fixture schema `shyftr-memory-benchmark-fixture/v0`;
- safe report output limited to `artifacts/`, `reports/`, or `tmp/` under the repo;
- retrieval metrics for the tiny fixture: recall at k, precision at k, and MRR;
- control/audit metrics such as provenance coverage and sensitivity leak rate;
- public claim blocks that prevent broad performance or superiority claims.

## Smoke command

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --run-id p11-1-controller-smoke \
  --output artifacts/benchmarks/p11_1_controller_report.json \
  --top-k 5 \
  --include-retrieval-details
```

Observed smoke result:

```text
schema_version: shyftr-memory-benchmark-report/v0
shyftr: ok, recall_at_k 1.0, provenance_coverage 1.0
no-memory: ok, recall_at_k 0.0, provenance_coverage 0.0
```

The generated smoke report was removed from the worktree after verification so the commit set remains code/docs/tests only.

## Verification performed

Focused and doc gates:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

Result:

```text
2 passed
ShyftR public readiness check
PASS
```

Full regression:

```bash
PYTHONPATH=.:src pytest -q
```

Result:

```text
1097 passed, 40 warnings in 18.46s
```

Warnings are existing `httpx` TestClient deprecation warnings in FastAPI tests.

## Swarm execution

- `swarm3` reviewed P11-0 docs and found no blocker; it recommended adding report and fixture schemas before implementation.
- `swarm2` implemented P11-1 and reported focused verification green.
- Controller verified files from disk, ran the smoke command, tightened the ShyftR adapter/test so the synthetic fixture produces meaningful retrieval metrics, and ran focused plus full verification.

## Deferred work

Next tranche should be P11-2: mem0 OSS compatibility.

Do not start with mem0 Cloud. Keep Cloud optional and credential-gated.

P11-2 should add:

- `src/shyftr/benchmarks/adapters/mem0_backend.py`;
- optional dependency detection or clear install guidance;
- skipped status when mem0 is unavailable;
- a fixture-safe side-by-side report using the same synthetic fixture;
- docs that distinguish mem0 OSS from mem0 Cloud.

## Claim rule

The current harness supports only this claim:

- ShyftR has a fixture-safe local benchmark adapter harness that can compare ShyftR and no-memory backends under a synthetic fixture and emit a public-safe report.

It does not support:

- broad ShyftR-vs-mem0 performance claims;
- LOCOMO, LongMemEval, or BEAM claims;
- hosted or production claims;
- measured task-success lift.
